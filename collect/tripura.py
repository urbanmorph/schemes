"""
Tripura state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY TRIPURA. It is the sharpest gap in the register: myScheme lists 37 state schemes for
Tripura against DBT Bharat's 209, a ratio of 5.6 to one, the largest of any state
measured. If the portal is behind anywhere it is behind here, and Tripura's own Finance
Department answers the question in one 154-page book.

THE DOCUMENT THAT DECIDES IT. `CSS & SLS- BUDGET OVERVIEW 2026-27` prints, per demand,
every Centrally Sponsored Scheme onboarded on SNS SPARSH and every State Level Scheme
under it, each with the state's own code:

    CSS 3690   National Mission for Safety of Women (Fast Track Spl Courts-Nirbhaya Fund)
    SLS TR157  Tripura Fastrack Special Code/National Mission Safety of Women
    2014 00 103 90 90 49    1.0000
    SLS TR157 Total :       2.0000
    CSS 3690  Total :       2.0000

Measured on the 2026-27 book: 74 distinct CSS codes and 134 distinct SLS codes, 208
together, against DBT Bharat's count of 209 for Tripura. That near-identity is the point
of collecting it: this is very likely the same list DBT counts, published with names.

The Gender Budget 2026-27 is collected alongside it because it is the only Tripura
document that prints a scheme's DEPARTMENT next to its name, and because its Part A / B /
C split says how much of each provision is women-specific.

WHICH VARIANT, AND WHY. Tripura publishes the Expenditure Budget Volume 2 twice for the
same year, once as `(B.E.)` and once as `(A.C. & B.E. & R.E)`, with near-identical
filenames. Neither is collected here (see SKIPPED) but the same trap applies to any
future addition: the two books carry different column counts for the same rows, and
taking the first match would silently mix a 2024-25 actual into a 2026-27 register.

    archive/tripura/D/index-p0.html.gz .. index-pN.html.gz  the paged listing
    archive/tripura/D/<book>.pdf.gz                         raw bytes as served
    archive/tripura/D/_manifest.json
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

# Drupal view with a plain ?page= pager and no session. Page 0 carries the current cycle;
# the walk stops at the first page with no PDF on it, measured at page 6 on 2026-09-03.
INDEX = "https://finance.tripura.gov.in/budget"
MAX_PAGES = 12

CYCLE = "2026-27"

# Matched on the label the page prints, which is also the anchor's title attribute.
# Labels rather than filenames because Tripura's filenames are URL-encoded ampersands and
# parentheses ("Budget%20for%20Scheduled%20Caste%20%28B.E.%29%202026-27.pdf") while the
# labels are plain. Every pattern carries the cycle, so a page listing several years
# cannot hand back last year's book.
BOOKS = {
    "css-sls": (
        ("css", "sls", "budget overview", CYCLE),
        "CSS & SLS Budget Overview: every Centrally Sponsored Scheme onboarded on SNS "
        "SPARSH and every State Level Scheme under it, per demand, with the state's own "
        "CSS and TR codes, the heads of account and a printed total per scheme"),
    "gender": (
        ("gender budget", CYCLE),
        "Gender Budget Statement: Part A (100% women-specific), Part B (30 to 99% women "
        "component) and Part C (below 30%), scheme-wise with the department named and a "
        "printed total per department"),
}

# On the index and deliberately not collected. Recorded here rather than in a commit
# message because a document missing from the archive is otherwise indistinguishable
# from a collector that failed to find it.
SKIPPED = {
    "Expenditure Budget 2026-27 Volume 2, both (B.E.) and (A.C. & B.E. & R.E) variants": (
        "the detailed account by object head, 664 pages in Part I alone. It is English "
        "and it reconciles, but its Detail Head level mixes schemes with establishment "
        "items: 1,338 distinct detail heads in Part I include 'Assembly Secretariat', "
        "'Electricity Charges' and 'Gardening/Beautification' beside real schemes. "
        "Publishing those as schemes would make false absence claims against myScheme. "
        "The CSS & SLS book names the schemes and says which they are"),
    "Expenditure Budget 2026-27 Volume 1 - Abstracts of Accounts": (
        "major-head abstracts, no scheme rows"),
    "Budget for Scheduled Caste and Budget for Scheduled Tribe 2026-27": (
        "collected by nobody yet: both are published in a (B.E.) and an "
        "(A.C. & R.E. & B.E.) variant for the same year and neither was measured in this "
        "round. A future round should take exactly one variant and say which"),
    "Annual Financial Statement, Budget at a Glance, Highlights, Supplementary Grants, "
    "Finance Minister's Speech, Action taken against the budget declaration": (
        "aggregate, prose or last-year documents"),
    "Output & Outcome Budget 2025-26": (
        "the only Outcome Budget on the index is last year's; there is no 2026-27 one"),
}

# <a href="/sites/default/files/X.pdf" title="LABEL" target="_blank">LABEL</a>
ANCHOR = re.compile(r'<a\s+href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def labelled_pdfs(body, page_url):
    """[(label, absolute url)] as the page prints them."""
    out = []
    for m in ANCHOR.finditer(body):
        label = re.sub(r"<[^>]+>", "", m.group(2))
        label = re.sub(r"\s+", " ", html.unescape(label)).strip()
        out.append((label, urllib.parse.urljoin(
            page_url, html.unescape(m.group(1)).strip())))
    return out


def discover(index_url, pace):
    """Walk the pager. Returns (pages, all_pdfs, books, alternates, err)."""
    pages, seen_pdfs = [], []
    for p in range(MAX_PAGES):
        url = f"{index_url}?page={p}"
        r = fetch(url, pace=pace)
        if not r.ok:
            if p == 0:
                return [], [], {}, [], f"index http {r.status}"
            break
        body = r.body.decode("utf-8", "replace")
        found = labelled_pdfs(body, url)
        pages.append((p, url, r.body, len(found)))
        if not found:
            # An empty page is the end of the pager, not a failure. Measured 2026-09-03:
            # pages 0 to 5 carry documents and page 6 carries none.
            break
        seen_pdfs.extend(found)

    books, alternates = {}, []
    for name, (words, what) in sorted(BOOKS.items()):
        hits = sorted({u for label, u in seen_pdfs
                       if label and all(w in label.lower() for w in words)})
        if len(hits) == 1:
            books[name] = {"url": hits[0], "what": what,
                           "matched_on": " + ".join(words)}
        elif not hits:
            alternates.append({"book": name, "why_not_taken":
                               "no link whose label contains " + ", ".join(words)})
        else:
            # Two links matching one pattern is the variant trap. Refuse rather than
            # guess: Tripura publishes (B.E.) and (A.C. & B.E. & R.E) editions of the
            # same book for the same year.
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} links match, refusing to guess: "
                               + ", ".join(u.rsplit("/", 1)[-1] for u in hits[:4])})
    return pages, seen_pdfs, books, alternates, None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "tripura", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "tripura", "started": utcnow(), "base": index_url,
           "cycle_wanted": CYCLE, "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    pages, pdfs, wanted, alternates, err = discover(index_url, pace)
    for p, url, body, n in pages:
        with gzip.open(os.path.join(out_dir, f"index-p{p}.html.gz"), "wb") as fh:
            fh.write(body)
    man["index_pages"] = [{"page": p, "url": u, "bytes": len(b), "pdfs": n}
                          for p, u, b, n in pages]
    man["pdfs_on_index"] = len(pdfs)
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/tripura/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates
    man["books_expected"] = sorted(wanted)

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        # 300s rather than the default 45: the Gender Budget is 17 MB over a link that
        # measured 20 seconds per megabyte, and a timeout would look like a missing book.
        r = fetch(meta["url"], timeout=300, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        # A 404 arriving as an HTML body written to a file named .pdf is the failure that
        # matters, so the magic bytes are checked rather than the status.
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
    write_json(f"archive/tripura/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Tripura CSS/SLS and Gender budget books.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*", help="archive names, for a partial re-run")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"tripura: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs across "
          f"{len(man.get('index_pages', []))} index pages, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
