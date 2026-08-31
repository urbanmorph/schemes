"""
Extract the Output-Outcome Monitoring Framework from the archived Outcome Budget.

AGENT-EDITABLE (PLAN.md §7). Reads archive/, writes data/outcome/. Never fetches.

The Outcome Budget states, per scheme, a financial outlay and a set of output and
outcome indicators each with a target for the coming year. myScheme publishes none of
this, and the document itself is a 302-page PDF, so the figures are effectively
unreachable per scheme. That is the definition of information this register should
surface.

    data/outcome/2026.json     one record per scheme section

Two structural facts the parser is built around:

  Scheme sections are headed like "2.  Modified Interest Subvention Scheme (MISS) (CS)".
  The trailing (CS) / (CSS) is the classification. Numbering restarts within each
  ministry, so the index is not a document-wide key and cannot be used for contiguity
  checks the way Statement 4A's can.

  OUTPUTS and OUTCOMES are side-by-side column groups, not sequential sections. A single
  text line carries an output indicator on the left and an outcome indicator on the
  right. Splitting on the column where "OUTCOMES" begins in the header line is what
  keeps an outcome target from being read as an output one.

What is deliberately NOT extracted: the prose of every indicator is wrapped across
several lines inside a narrow cell, and stitching it back together reliably is not
something a layout-based extraction can promise. Indicator *text* is captured as the
first line only and marked as such; the target values, which are what a reader wants
and what the government is on the hook for, are extracted in full.
"""

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, write_json  # noqa: E402

HEADER = re.compile(r"^\s*(\d{1,3})\.\s+(.{6,150}?)\s*\((CS|CSS|CS/CSS)\)\s*$", re.M)
# An indicator: "1.1", then wrapped text, then its target. Deliberately NOT anchored to
# end-of-line: within a column slice the next group's prose often follows the target on
# the same physical line ("1.1 Number of eligible   9.5   1.  Assured"), so anchoring
# silently dropped the first indicator of most schemes. `\d+\.\d+` also keeps it from
# matching an output/outcome group number like "1." on the same row.
INDICATOR = re.compile(r"(\d+\.\d+)\s+(\S.*?)\s{2,}([\d,]+(?:\.\d+)?)(?=\s|$)")
# The outlay is the leftmost figure of the scheme's first data row — which is the same
# physical line as its first indicator, so this must not require a line of its own.
OUTLAY_HINT = re.compile(r"^\s{0,12}([\d,]{3,}(?:\.\d+)?)\s{2,}")


def to_text(gz_path):
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext not found — install poppler-utils")
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "d.pdf")
        with gzip.open(gz_path, "rb") as s, open(pdf, "wb") as d:
            shutil.copyfileobj(s, d)
        txt = os.path.join(td, "d.txt")
        subprocess.run(["pdftotext", "-layout", pdf, txt],
                       check=True, capture_output=True, timeout=300)
        return open(txt, encoding="utf-8", errors="replace").read()


def split_column(block):
    """Character offset where the OUTCOMES column begins, or None.

    Without this the two column groups run together and an outcome target reads as an
    output one — which would attribute a promise to the wrong half of the framework.
    """
    for line in block.splitlines():
        u = line.upper()
        if "OUTPUTS" in u and "OUTCOMES" in u:
            return u.index("OUTCOMES")
    for line in block.splitlines():
        u = line.upper()
        if "OUTCOMES" in u:
            return u.index("OUTCOMES")
    return None


def num(s):
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_section(block):
    """Outlay and the two indicator lists for one scheme section."""
    cut = split_column(block)
    outputs, outcomes = [], []
    outlay = None

    for line in block.splitlines():
        if outlay is None:
            m = OUTLAY_HINT.match(line)
            if m:
                v = num(m.group(1))
                if v and v >= 1:
                    outlay = v

        left, right = (line[:cut], line[cut:]) if cut else (line, "")
        for side, bucket in ((left, outputs), (right, outcomes)):
            m = INDICATOR.search(side)
            if m:
                bucket.append({"ref": m.group(1),
                               "indicator": re.sub(r"\s+", " ", m.group(2)).strip()[:180],
                               "target": num(m.group(3))})
    return outlay, outputs, outcomes


def run(year):
    gz = os.path.join(ROOT, "archive", "budget", str(year), "outcome.pdf.gz")
    if not os.path.exists(gz):
        raise SystemExit(f"no archived Outcome Budget at {gz}")
    text = to_text(gz)
    pages = text.split("\f")

    marks = []
    for pno, page in enumerate(pages, 1):
        for m in HEADER.finditer(page):
            marks.append({"page": pno, "index": int(m.group(1)),
                          "name": re.sub(r"\s+", " ", m.group(2)).strip(),
                          "classification": m.group(3), "pos": (pno, m.start())})

    flat = "\f".join(pages)
    offsets = []
    base = 0
    for pno, page in enumerate(pages, 1):
        offsets.append(base)
        base += len(page) + 1

    starts = []
    for mk in marks:
        pno, off = mk["pos"]
        starts.append(offsets[pno - 1] + off)

    schemes = []
    for i, mk in enumerate(marks):
        block = flat[starts[i]: starts[i + 1] if i + 1 < len(starts) else len(flat)]
        outlay, outputs, outcomes = parse_section(block)
        schemes.append({
            "name": mk["name"], "classification": mk["classification"],
            "page": mk["page"], "index_in_ministry": mk["index"],
            "outlay_cr": outlay,
            "output_indicators": len(outputs), "outcome_indicators": len(outcomes),
            "outputs": outputs[:40], "outcomes": outcomes[:40],
        })

    with_targets = sum(1 for s in schemes if s["outputs"] or s["outcomes"])
    write_json(f"data/outcome/{year}.json", {
        "cycle": f"{year}-{str(year + 1)[2:]}",
        "source": f"Union Budget Outcome Budget {year}-{str(year+1)[2:]}, "
                  "Output Outcome Monitoring Framework",
        "pages": len(pages),
        "schemes_found": len(schemes),
        "schemes_with_targets": with_targets,
        "caveat": ("Targets only. The framework states what each scheme promises to "
                   "deliver in the coming year and carries no achieved-versus-promised "
                   "column for any scheme, so nothing here says whether last year's "
                   "targets were met. Indicator text is the first line of a wrapped "
                   "cell; target values are complete."),
        "schemes": schemes,
    })
    return schemes, with_targets


def main():
    ap = argparse.ArgumentParser(description="Parse the archived Outcome Budget.")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    schemes, wt = run(a.year)
    tgt = sum(len(s["outputs"]) + len(s["outcomes"]) for s in schemes)
    outl = sum(1 for s in schemes if s["outlay_cr"])
    print(f"Outcome Budget {a.year}-{str(a.year+1)[2:]}")
    print(f"  scheme sections   {len(schemes)}")
    print(f"  with an outlay    {outl}")
    print(f"  with any target   {wt}")
    print(f"  targets extracted {tgt}")


if __name__ == "__main__":
    main()
