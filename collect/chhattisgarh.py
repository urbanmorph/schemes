"""
Chhattisgarh state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY THESE DOCUMENTS AND NOT THE OTHER ONES. Chhattisgarh publishes 44 department scheme
books, S-NN.pdf, holding 2,562 scheme rows between them, and this collector does not take
them. Their names are set in Chanakya, a legacy font whose embedded encoding maps its codes
to standard LATIN glyph names with Devanagari outlines drawn in the slots, so the font
cannot decode itself and neither can anything in the PDF. Deriving that table is unfinished
work recorded in parse/chanakya_derive.py; until it is done those 2,562 names cannot be
read, and a name this register cannot read is a name it will not publish.

What it takes instead is the Outcome, Gender, Youth and Child budgets, which 33 departments
publish and which are set in KRUTI DEV. Kruti Dev is pure ASCII and its table is fixed,
published and checked in parse/krutidev.py against the state's own Unicode department index.
Those books carry fewer schemes and more about each one: the name, the objective, the
provision, and the quantifiable deliverable.

    archive/chhattisgarh/<date>/index.html.gz      the outcome index, so discovery is auditable
    archive/chhattisgarh/<date>/<kind>-<NN>.pdf.gz raw bytes, byte-identical to what was served
    archive/chhattisgarh/<date>/_manifest.json

SKIPPED, recorded rather than silently dropped, because a document missing from the archive
is otherwise indistinguishable from a collector that failed to find it.
"""

import argparse
import gzip
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://finance.cg.gov.in/budget_doc/"
INDEX = BASE + "outcome.asp?year1={year}"

SKIPPED = {
    "Demands for Grants, 44 department books (B/T/S/N/P per department)": (
        "the S books name 2,562 schemes and set every name in Chanakya, whose encoding "
        "cannot be recovered from the PDF. The B books use it too. The T books are a "
        "grant-wise summary with no scheme names and the P books are prose. Worth "
        "collecting the day parse/chanakya_derive.py converges, and not before: bytes "
        "whose characters this register cannot read are not evidence it can publish"),
    "Annual Financial Statement, Receipt Budget, Headwise Breakup of Grants": (
        "aggregate and receipts documents. None names a scheme"),
    "Budget Speech, Key to Budget, Press Note, FRBM statements": "prose and aggregates",
}


def index_urls(body):
    """(kind, department number) -> absolute URL, from the outcome index."""
    out = {}
    for m in re.finditer(r'href=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', body, re.I):
        h = html.unescape(m.group(1) or m.group(2) or m.group(3) or "")
        mm = re.search(r"(outcome/department|gender/department|youth|child)/(\d+)\.pdf",
                       h, re.I)
        if mm:
            kind = mm.group(1).split("/")[0].lower()
            out[(kind, mm.group(2))] = BASE + urllib.parse.quote(h.lstrip("./"), safe="/:%")
    return out


def collect(cycle="2026-27", date=None, pace=1.5):
    date = date or today()
    year = cycle.split("-")[0]
    out_dir = os.path.join(ROOT, "archive", "chhattisgarh", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"started": utcnow(), "state": "Chhattisgarh", "cycle": cycle, "date": date,
           "source": ("Chhattisgarh Budget " + cycle + ", Outcome, Gender, Youth and Child "
                      "budgets, one set per department"),
           "index": INDEX.format(year=year), "books": {}, "errors": [], "skipped": SKIPPED}

    r = fetch(man["index"], pace=pace)
    if not r.ok:
        man["errors"].append({"stage": "index", "why": f"http {r.status}"})
        write_json(f"archive/chhattisgarh/{date}/_manifest.json", man)
        return man
    body = r.body.decode("utf-8", "replace")
    with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
        fh.write(r.body)
    man["index_bytes"] = len(r.body)

    urls = index_urls(body)
    man["urls_found"] = len(urls)
    for (kind, dep), url in sorted(urls.items()):
        name = f"{kind}-{dep}"
        rr = fetch(url, pace=pace)
        if not rr.ok:
            man["errors"].append({"stage": name, "why": f"http {rr.status}"}); continue
        # A PDF that is really an error page is a valid write and the failure that matters.
        if not rr.body.startswith(b"%PDF"):
            man["errors"].append({"stage": name, "why": "response is not a PDF"}); continue
        bad = looks_like_error(rr.body[:4096])
        if bad:
            man["errors"].append({"stage": name, "why": str(bad)}); continue
        with gzip.open(os.path.join(out_dir, f"{name}.pdf.gz"), "wb") as fh:
            fh.write(rr.body)
        man["books"][name] = {"url": url, "bytes": len(rr.body), "kind": kind,
                              "department": dep}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    man["departments"] = len({v["department"] for v in man["books"].values()})
    write_json(f"archive/chhattisgarh/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(description="Archive Chhattisgarh's outcome budget books.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.cycle, a.date, a.pace)
    print(f"chhattisgarh {a.cycle}: {man.get('books_collected', 0)} of "
          f"{man.get('urls_found', 0)} documents archived, "
          f"{man.get('departments', 0)} departments")
    for e in man.get("errors", [])[:8]:
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
