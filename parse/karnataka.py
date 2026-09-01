"""
Extract Karnataka's scheme-wise budget books into a named scheme list.

AGENT-EDITABLE (PLAN.md §7). Reads archive/karnataka/, writes data/karnataka/. Never
fetches. Replayable against any archived date.

    data/karnataka/schemes.json    one row per head of account

What a row is. Karnataka's books are keyed by head of account,
`2401-00-102-0-27`, whose last field is the scheme code within a minor head. That code is
the state's own identifier for the scheme and is far more stable than the name, which is
retyped by every office that touches it. It is the join key here, and the reason the same
scheme appearing in both the Gender and Child books collapses to one row rather than two.

Three things the layout does that a naive reader gets wrong:

The name wraps. "CSS-Central Share-Training of Anganwadi Workers &" ends a line and
"Helpers / <Kannada>" begins the next, so a parser that reads the line containing the
slash records a scheme called "Helpers". 41 of 901 rows came out that way. Lines are
accumulated up to and including the slash instead.

The Kannada is not Unicode. These PDFs use a legacy font, so Kannada extracts as
Latin-range byte soup, and a plain is-this-ASCII test passes it. Latin Extended letters
are the tell: no English scheme name contains Ŵ or ĸ.

Every scheme carries a purpose line. "Free travel to all women (including girl students)
and transgenders in State Road Transport Corporation buses." That single sentence is
better than what myScheme publishes for many schemes it does list, and it is the reason
this is worth parsing rather than just counting.
"""

import argparse
import glob
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

HOA = re.compile(r"^(\d{4}-\d{2}-\d{3}-\d-\d{2})$")
# An amounts row: two or more money-shaped tokens, where "......" is how these books
# print a nil provision.
AMTS = re.compile(r"^\s*(?:[\d,]+\.\d{2}|\.{3,}|-)(?:\s+(?:[\d,]+\.\d{2}|\.{3,}|-)){1,}\s*$")
MONEY = re.compile(r"[\d,]+\.\d{2}|\.{4,}")
# Latin-1 supplement and Latin Extended-A/B. Present in the legacy-font Kannada, absent
# from any English scheme name.
LEGACY = re.compile(r"[À-ɏ]")
CTRL = re.compile(r"[\x00-\x08\x0b-\x1f]")
BOOK_LABEL = {"GB": "Gender Budget", "CB": "Child Budget",
              "SCSPTSP": "SCSP/TSP Allocations"}


def pdftotext(pdf_bytes):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, timeout=600)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


def is_english(s):
    return bool(s) and not LEGACY.search(s) and not CTRL.search(s)


def clean(s):
    return re.sub(r"\s+", " ", CTRL.sub(" ", LEGACY.sub("", s))).strip(" .,-/")


def amounts(line):
    out = []
    for tok in MONEY.findall(line):
        out.append(None if tok.startswith("..") else float(tok.replace(",", "")))
    return out


# SCSP/TSP prints the head of account and every figure on one line, prefixed SC or ST,
# and puts the Kannada name BEFORE the slash with the English after it — the opposite of
# the Gender and Child books. One parser trying to serve both read zero rows from it.
SCSP = re.compile(r"^(SC|ST)\s+(\d{4}-\d{2}-\d{3}-\d-\d{2})\s*(.*)$")


def parse_scsptsp(text, book):
    rows = []
    for page in text.split("\f"):
        lines = page.splitlines()
        for i, raw in enumerate(lines):
            m = SCSP.match(raw.strip())
            if not m:
                continue
            rest = m.group(3)
            amt = amounts(rest)
            tail = rest.split("/", 1)[1] if "/" in rest else ""
            parts = [tail] if clean(tail) else []
            for j in range(i + 1, min(i + 5, len(lines))):
                s = lines[j].strip()
                if not s or SCSP.match(s) or AMTS.match(lines[j]):
                    break
                seg = s.split("/", 1)[1] if "/" in s else s
                if clean(seg):
                    parts.append(seg)
                if MONEY.search(s):
                    break
            name = clean(MONEY.sub("", " ".join(parts)))
            if len(name) < 5:
                continue
            rows.append({"hoa": m.group(2), "name": name, "purpose": None,
                         "be_lakh": amt[0] if amt else None, "book": book})
    return rows


def parse_book(text, book):
    """One row per head of account. Names are accumulated across wrapped lines."""
    rows = []
    for page in text.split("\f"):
        lines = page.splitlines()
        for i, raw in enumerate(lines):
            m = HOA.match(raw.strip())
            if not m:
                continue
            amt, start = [], i + 1
            for j in range(i + 1, min(i + 3, len(lines))):
                if AMTS.match(lines[j]):
                    amt, start = amounts(lines[j]), j + 1
                    break
            # Name: everything before the first slash, accumulated over wrapped lines.
            name_parts, k, name = [], start, None
            while k < min(start + 6, len(lines)):
                s = lines[k].strip()
                if not s or AMTS.match(lines[k]) or HOA.match(s):
                    k += 1
                    continue
                if "/" in s:
                    head = s.split("/", 1)[0]
                    if clean(head) or name_parts:
                        name_parts.append(head)
                    name = clean(" ".join(name_parts))
                    k += 1
                    break
                if is_english(s):
                    name_parts.append(s)
                    k += 1
                    continue
                break
            if not name and name_parts:
                name = clean(" ".join(name_parts))
            if not name or len(name) < 5:
                continue
            # Purpose: the first fully English sentence after the name.
            desc = None
            for j in range(k, min(k + 7, len(lines))):
                s = lines[j].strip()
                if not s or AMTS.match(lines[j]):
                    continue
                # Stop rather than skip. A slash means the next scheme's name has started
                # and a Total line means the department block has ended, so anything past
                # either belongs to a different record. Skipping instead of stopping is
                # how "Subsidy for Supply of free Power to Irrigation Pumpsets" came to be
                # described as "Gruha Jyothi".
                if HOA.match(s) or re.search(r"\bTotal\s*:?\s*$|\bTotal\b\s+[\d,]", s):
                    break
                # A slash alone does not mean the next record: the Kannada continuation
                # lines carry them too. It is the next scheme's name only when there is
                # readable English in front of the slash.
                if "/" in s and len(clean(s.split("/", 1)[0])) > 3 \
                        and is_english(s.split("/", 1)[0]):
                    break
                if is_english(s) and len(s.split()) >= 4 and re.search(r"[a-z]{3}", s):
                    desc = re.sub(r"\s+", " ", s)
                    break
            rows.append({"hoa": m.group(1), "name": name, "purpose": desc,
                         "be_lakh": amt[-1] if amt else None, "book": book})
    return rows


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "karnataka", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/karnataka/ — run collect/karnataka.py")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "karnataka", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    by_hoa, per_book = {}, {}
    for book in sorted(BOOK_LABEL):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        rows = (parse_scsptsp if book == "SCSPTSP" else parse_book)(text, book)
        per_book[book] = len(rows)
        for r in rows:
            # First book wins the name; later books only fill gaps. The allocation is
            # NOT summed across books: the Gender and Child books report overlapping
            # slices of the same provision, so adding them would double-count a scheme
            # that serves women and children both.
            cur = by_hoa.get(r["hoa"])
            if cur is None:
                r["books"] = [BOOK_LABEL[book]]
                by_hoa[r["hoa"]] = r
            else:
                if BOOK_LABEL[book] not in cur["books"]:
                    cur["books"].append(BOOK_LABEL[book])
                if not cur.get("purpose") and r.get("purpose"):
                    cur["purpose"] = r["purpose"]
                if cur.get("be_lakh") in (None, 0) and r.get("be_lakh"):
                    cur["be_lakh"] = r["be_lakh"]
    out = sorted(by_hoa.values(), key=lambda r: r["hoa"])
    for r in out:
        r.pop("book", None)
    write_json("data/karnataka/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Karnataka",
        "cycle": man.get("cycle"),
        "source": "Karnataka Budget, scheme-wise books (Gender, Child, SCSP/TSP)",
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "schemes": len(out),
        "with_allocation": sum(1 for r in out if r.get("be_lakh")),
        "with_purpose": sum(1 for r in out if r.get("purpose")),
        "caveat": ("These are the scheme-wise cuts of the state budget, so a scheme with "
                   "no women, child or SC/ST earmark does not appear. The number here is "
                   "a floor on Karnataka's schemes, never a total."),
        "entries": out,
    })
    return out, per_book, date


def main():
    ap = argparse.ArgumentParser(description="Parse the archived Karnataka budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, date = run(a.date)
    print(f"karnataka snapshot {date}")
    for b, n in sorted(per_book.items()):
        print(f"    {b:<9}{n:>6} rows")
    print(f"  {len(out)} distinct schemes by head of account")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    print(f"     with a purpose     {sum(1 for r in out if r.get('purpose')):>6}")


if __name__ == "__main__":
    main()
