"""
Haryana state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY HARYANA, AND WHY IT IS THE OPPOSITE TEST. Every state built so far had myScheme far
behind the state's own books. Haryana runs the other way: myScheme lists 249 Haryana
schemes against DBT Bharat's 171, one of only three states in the register where the
portal claims more than DBT counts. The question worth asking is whether Haryana's own
budget also exceeds 249, and the answer is on the index.

THE DOCUMENT. `Explanatory Memorandum on Welfare & Development Schemes (Plan Memo)`,
491 pages, is a scheme register in two halves per department. First a table:

    Scheme Code No              Name of the Scheme          Central   State   Total  ...
    P-01-10-2401-51-105-96-51   Scheme for Quality Control       ...  300.00  300.00
                                on Agriculture Inputs

then, for most of the same schemes, a narrative entry carrying a paragraph of purpose:

    Code No.            1-15-2230-01-102-93-51
    Name of the Scheme  Providing of Mobile Vans for Facilitating the Health Care ...
    Outlay              `30,00,000/-

Measured on the 2026-27 book: 970 distinct scheme codes in the tables and 870 narrative
entries. The narrative code is the table code with its `P-0` prefix removed, which is how
the two halves join.

THREE UNITS IN ONE BOOK, and this is the trap that would have published every figure at
the wrong scale. Each department opens with a `Summary of Budget Estimate` headed
`(Amount in ₹ )` printing full rupees to eleven digits (25,11,50,00,000); the scheme
table that follows is headed `(₹ In Lakhs)`; and the narrative `Outlay` line is full
rupees again (`30,00,000/-`). The parser reads the unit off each table's own header.

WHERE THE FILES LIVE. finhry.gov.in is WordPress; the documents are on the shared
S3-backed government CDN under an opaque numeric filename
(`.../uploads/2026/03/20260320967023201.pdf`) that carries neither the year nor the
title, so it cannot be constructed and has to be read off the year page.

    archive/haryana/D/index.html.gz    the budget-2026-27 page, so discovery is auditable
    archive/haryana/D/<book>.pdf.gz    raw bytes, byte-identical to what was served
    archive/haryana/D/_manifest.json
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

CYCLE = "2026-27"
INDEX = f"https://finhry.gov.in/budget-{CYCLE}/"

BOOKS = {
    "plan-memo": (
        ("explanatory memorandum", "welfare", "development schemes"),
        "Explanatory Memorandum on Welfare & Development Schemes (Plan Memo): every "
        "scheme with the state's own 20-character scheme code, the central and state "
        "share in lakh, and for most of them a paragraph of purpose"),
}

# On the index and deliberately not collected.
SKIPPED = {
    "Demands for Grants with Detailed Estimates of Expenditure (Volume II)": (
        "1,498 pages. English scheme names are present but the Hindi beside them is a "
        "LOSSY text layer of the Rajasthan kind, dropping consonants and matras, and the "
        "book is organised by head of account rather than by scheme. The Plan Memo "
        "carries the same schemes with a code and a description"),
    "Detailed Estimates of Capital Expenditure (Volume III), Detailed Estimates for "
    "Revenue Receipts (Volume I)": "capital works and receipts, no scheme register",
    "Budgetary Transfers to Local Bodies": (
        "26 MB of transfers to panchayats and municipalities, which are bodies and not "
        "schemes"),
    "Budget at a Glance, Finance Minister's Speech (English and Hindi), Annual Financial "
    "Statement & Explanatory Memorandum (F.S. Memo.), Haryana FRBM Act, An Introduction "
    "to Budget": "aggregate or prose documents",
}

ANCHOR = re.compile(r'<a\s[^>]*href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def labelled_pdfs(body, page_url):
    out = []
    for m in ANCHOR.finditer(body):
        label = re.sub(r"<[^>]+>", "", m.group(2))
        label = re.sub(r"\s+", " ", html.unescape(label)).strip()
        out.append((label, urllib.parse.urljoin(
            page_url, html.unescape(m.group(1)).strip())))
    return out


def discover(index_url, pace):
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, [], 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    pdfs = labelled_pdfs(body, index_url)

    books, alternates = {}, []
    for name, (words, what) in sorted(BOOKS.items()):
        hits = sorted({u for label, u in pdfs
                       if label and all(w in label.lower() for w in words)})
        if len(hits) == 1:
            books[name] = {"url": hits[0], "what": what,
                           "matched_on": " + ".join(words)}
        elif not hits:
            alternates.append({"book": name, "why_not_taken":
                               "no link whose label contains " + ", ".join(words)})
        else:
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} links match, refusing to guess: "
                               + ", ".join(u.rsplit("/", 1)[-1] for u in hits[:4])})
    return r.body, books, alternates, len(pdfs), None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "haryana", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "haryana", "started": utcnow(), "base": index_url,
           "cycle_wanted": CYCLE, "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, wanted, alternates, n_pdfs, err = discover(index_url, pace)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/haryana/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates
    man["books_expected"] = sorted(wanted)

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        r = fetch(meta["url"], timeout=300, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        if not r.body.startswith(b"%PDF"):
            man["errors"].append({"stage": book,
                                  "why": f"response is not a PDF ({len(r.body)} bytes)"})
            continue
        bad = looks_like_error(r.body[:4096])
        if bad:
            man["errors"].append({"stage": book, "why": str(bad)})
            continue
        with gzip.open(os.path.join(out_dir, f"{book}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["books"][book] = dict(meta, bytes=len(r.body), sha256=r.sha256)

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/haryana/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Haryana Plan Memo (scheme-wise Explanatory Memorandum).")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"haryana: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
