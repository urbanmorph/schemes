"""
Delhi (NCT) budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY DELHI. myScheme lists 53 Delhi state schemes against DBT Bharat's 114, so the portal
is behind by a factor of about two. Delhi is also the smallest jurisdiction in this
register and publishes accordingly: there are no per-department demand volumes to walk,
and the whole scheme-wise budget is one 131-page file.

THE DOCUMENT. `Scheme-wise Budget 2026-27` is headed
`SCHEME/PROGRAMME/PROJECTS WISE OUTLAY 2026-27` and is a plain English table, sector by
department by scheme, with four years of figures in `(₹ in Lakh)` and a printed subtotal
at every level up to a Grand Total. There is no second script anywhere in it.

WHERE IT LIVES, AND WHERE IT DOES NOT. The Finance Department's own site,
finance.delhi.gov.in, has pages titled `Demand for Grants year 2026-27` and
`Detailed Demands for Grants` and both are EMPTY: they carry the site's boilerplate PDF
and nothing else. The budget documents are published by the Planning Department at
delhiplanning.delhi.gov.in/planning/2026-27, which is where this collector reads.

A NAME THAT LIES ABOUT ITS YEAR. The served file is `scheme_wise_6.pdf` and its PDF
/Title is `Scheme Wise 2025-26 10.03.2026 1.58 PM.xlsx`, while every page of the document
itself is headed 2026-27 and its columns run to `Budget Outlay 2026-27`. The cycle is
therefore read from the page header by parse/delhi.py and never from the filename or the
metadata, and a document whose pages say anything else is a hard error.

    archive/delhi/D/index.html.gz    the planning-department year page
    archive/delhi/D/<book>.pdf.gz    raw bytes as served
    archive/delhi/D/_manifest.json
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
INDEX = f"https://delhiplanning.delhi.gov.in/planning/{CYCLE}"

BOOKS = {
    "scheme-wise": (
        ("scheme-wise budget", CYCLE),
        "Scheme-wise Budget 2026-27: SCHEME/PROGRAMME/PROJECTS WISE OUTLAY, sector by "
        "department by scheme, four years of figures in lakh with a printed subtotal at "
        "every level and a Grand Total"),
}

SKIPPED = {
    "Budget Highlights 2026-27 (English and Hindi), budget speech, budget graph": "prose "
    "and summary",
    "finance.delhi.gov.in/finance/demand-grants-year-2026-27 and "
    "finance.delhi.gov.in/finance/detailed-demands-grants-0": (
        "the Finance Department's own Demand for Grants pages, checked 2026-09-03 and "
        "carrying no document at all"),
    "finance.delhi.gov.in/finance/gender-budget and /finance/css-statement": (
        "both list documents, the newest named for 2025-26. Not collected in this round "
        "because the Scheme-wise Budget already covers 2026-27 and mixing a 2025-26 "
        "gender statement into it would put last year's figures in a 2026-27 register"),
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
    out_dir = os.path.join(ROOT, "archive", "delhi", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "delhi", "started": utcnow(), "base": index_url,
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
        write_json(f"archive/delhi/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates
    man["books_expected"] = sorted(BOOKS)

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
    write_json(f"archive/delhi/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Delhi Scheme-wise Budget.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"delhi: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
