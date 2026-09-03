"""
Uttarakhand state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY UTTARAKHAND, AND WHY IT IS AN AWKWARD CASE FOR THE REGISTER. myScheme lists 446
Uttarakhand state schemes against DBT Bharat's 225, and 446 is the second highest count
of any state on the portal despite Uttarakhand being a tenth of Uttar Pradesh by
population. If the portal is ever ahead of a state's own books, this is where.

WHAT SAVED IT, AND IT WAS NOT THE OBVIOUS DOCUMENT. Uttarakhand writes its budget in
Hindi and typesets it in KrutiDev. `pdffonts` on Volume 2 and on the Gender Budget shows
`Kruti Dev 010` and `Kruti Dev 016` in WinAnsi with no ToUnicode, which is exactly the
Madhya Pradesh failure recorded in docs/state-sources.md, and Volume 2's opening pages
extract as `o"kZ 2026&27` where the state wrote 2026-27.

Volume 5, `Head wise details of accounts`, is a different book. It prints EVERY line of
the detailed estimates twice, the Hindi first and the English underneath it:

    2215          जल पपरत तथन सफनई
                  Water Supply and Sanitation
     01           जलपपरत
                  Water Supply
      001         वनददशन तथन पशनसन
                  Direction and Administration
       04         रद न सनकर हनसरससकग हदतन अननदनन
                  Grant for rainwater harvesting

The Hindi is damaged in the way Uttarakhand's typesetting damages everything, and it does
not matter: it is Devanagari Unicode, so it cannot share a line with the Latin, and the
English line beneath is clean. That is the Odisha property arriving by a different route.

THE CODE. Concatenating the five printed levels gives the state's own 13-digit scheme
code, which Volume 5's own front matter prints as `Scheme Code` beside a `Scheme Name`
column: 2215 01 001 04 is scheme 2215010010 4. Keying on it is what lets the four parts
of Volume 5 be read as one book.

FOUR PARTS, AND ALL FOUR ARE NEEDED. Volume 5 is split into Part 1 to Part 4 by grant
number, so collecting three of them silently drops whole departments. The collector
records all four as expected and a missing one is an error, not a shorter book.

    archive/uttarakhand/D/index.html.gz   the budget-2026-27 page
    archive/uttarakhand/D/<book>.pdf.gz   raw bytes as served
    archive/uttarakhand/D/_manifest.json
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
INDEX = f"https://budget.uk.gov.in/budget-{CYCLE}/"

BOOKS = {
    "vol5-part1": (("volume 5", "part 1"),
                   "Volume 5, Head wise details of accounts, Part 1: the detailed "
                   "estimates with the English name printed under the Hindi at every "
                   "level, in thousands of rupees"),
    "vol5-part2": (("volume 5", "part 2"), "Volume 5, Head wise details, Part 2"),
    "vol5-part3": (("volume 5", "part 3"), "Volume 5, Head wise details, Part 3"),
    "vol5-part4": (("volume 5", "part 4"), "Volume 5, Head wise details, Part 4"),
    "gender": (("gender budget",),
               "Gender Budget: the same detailed estimates annotated with a Group I / "
               "Group II women-benefit classification per scheme"),
}

SKIPPED = {
    "Volume 2 (Annual Financial Statements) Part 1 and Part 2": (
        "the Annual Financial Statement. Its preface and notes are KrutiDev with no "
        "ToUnicode and extract as garbage; its statement pages carry English but only "
        "down to the minor head, so it names no scheme Volume 5 does not"),
    "Volume 3 (New items of Expenditure)": (
        "not measured in this round. It is the one document that would say which schemes "
        "are NEW this cycle and is worth a look next time"),
    "Volume 4 (Detailed Estimates of Receipts)": "receipts, not expenditure",
    "Volume 6 (Post Description)": "sanctioned posts, not schemes",
    "Details related to urban local bodies and Panchayati Raj Institutions": (
        "transfers to bodies rather than schemes"),
    "Volume 1 (Budget Speech), Budget at a Glance, Budget Ek Drishti": "prose and summary",
}

# The year page is a WordPress table whose document links are icons with no anchor text;
# the human-readable name sits in the first cell of the same row. So the row is the unit
# of discovery, not the anchor.
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
HREF = re.compile(r'href="([^"]+\.pdf[^"]*)"', re.I)


def labelled_pdfs(body, page_url):
    """[(row label, absolute url)] one entry per (row, distinct url) pair."""
    out = []
    for m in ROW.finditer(body):
        row = m.group(1)
        urls = sorted({html.unescape(u).strip() for u in HREF.findall(row)})
        if not urls:
            continue
        label = re.sub(r"<[^>]+>", " ", row)
        label = re.sub(r"\s+", " ", html.unescape(label)).strip()
        for u in urls:
            out.append((label, urllib.parse.urljoin(page_url, u)))
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
                               "no row whose label contains " + ", ".join(words)})
        else:
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} links match, refusing to guess: "
                               + ", ".join(u.rsplit("/", 1)[-1] for u in hits[:4])})
    return r.body, books, alternates, len(pdfs), None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "uttarakhand", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "uttarakhand", "started": utcnow(), "base": index_url,
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
        write_json(f"archive/uttarakhand/{date}/_manifest.json", man)
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
    write_json(f"archive/uttarakhand/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Uttarakhand Volume 5 head-wise details and Gender Budget.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"uttarakhand: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDF rows on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
