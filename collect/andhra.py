"""
Andhra Pradesh state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md §7 before editing.

Why a state budget at all: see collect/karnataka.py. DBT Bharat publishes a per-state
count and no list, so /divergence can say that myScheme lists 51 schemes for Andhra
Pradesh and cannot name one of the ones it does not list. A count is an argument, a name
is a fact.

Andhra Pradesh puts 36 volumes on one page, all in English, and six of them are
scheme-wise cuts of the same budget rather than alternatives to each other:

    Gender-Budget      every scheme with a women-oriented allocation
    Child-Budget       every scheme with a child-oriented allocation
    Backward-Classes   allocations to Backward Classes, department-wise
    Minorites          allocations to Minorities, department-wise
    Volume-VII-3       Scheduled Castes Component, formerly the SC Sub-Plan
    Volume-VII-2       Scheduled Tribes Component, formerly the Tribal Sub-Plan

Each is a two-column table of department, scheme name and one allocation, which is the
same shape of curated, benefit-delivering list that myScheme claims to cover. The 17
per-department detailed volumes (Volume-III-1 to III-17) and the Outcome Budget are more
complete and much noisier, mixing establishment and works heads with schemes; they are
deliberately not collected, for the reason recorded in collect/karnataka.py: a
comprehensive-but-noisy source needs a classifier before it can be published, and these
six do not.

`Minorites.pdf` is spelled that way on the site. The typo is theirs, and correcting it
here would mean guessing at an address rather than reading one.

    archive/andhra/D/home.html.gz     the homepage, where the budget page URL is found
    archive/andhra/D/index.html.gz    the budget page, where the PDF URLs are found
    archive/andhra/D/<book>.pdf.gz    raw bytes, byte-identical to what was served
    archive/andhra/D/_manifest.json

Two saved pages rather than Karnataka's one, because AP takes two hops to address and
the first hop is the unguessable one. The budget page URL is literally

    https://apfinance.gov.in/...Bud@et26-27/

with three leading dots and an `@`. No naming convention produces that, so it is read off
the homepage every run and the homepage is archived as the evidence that it was. The
documents then sit at `<that page>/documents/<Name>.pdf`, which is guessable, but the
hrefs are still read off the page: a file that moves should surface as a book missing
from the index, not as a 404 on an address we invented.

The same six PDFs also exist on the S3 bucket the site is served from
(s3.ap-south-1.amazonaws.com/apfinance.gov.in/...), which returns 403 to anonymous GETs.
Measured, not assumed: the apfinance.gov.in URLs are the only ones that serve.
"""

import argparse
import gzip
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://apfinance.gov.in"

# Books wanted, by the filename stem the site serves them under. The value is what the
# book is, recorded here so the archive is readable without this file.
BOOKS = {
    "Gender-Budget": "Gender Budget, department-wise scheme allocations for women",
    "Child-Budget": "Child Budget, department-wise scheme allocations for children",
    "Backward-Classes": "Budget allocations to Backward Classes, department-wise",
    "Minorites": "Budget allocations to Minorities, department-wise (site's spelling)",
    "Volume-VII-3": "Scheduled Castes Component, formerly the SC Sub-Plan",
    "Volume-VII-2": "Scheduled Tribes Component, formerly the Tribal Sub-Plan",
}


def short_cycle(cycle):
    """2026-27 is how this repo names a cycle; the AP page writes it 26-27."""
    m = re.match(r"^\d{2}(\d{2}-\d{2})$", cycle)
    return m.group(1) if m else cycle


def absolute(href, page):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return page.rstrip("/") + "/" + href


def discover(cycle, pace):
    """Find this cycle's budget page and its PDF URLs.

    Returns (home_bytes, index_bytes, page_url, {book: url}, error).
    """
    home = fetch(BASE + "/", pace=pace)
    if not home.ok:
        return None, None, None, {}, f"homepage http {home.status}"
    body = home.body.decode("utf-8", "replace")

    # The homepage links every past cycle's page (Bud@et24-25 is still there), so match
    # on the cycle rather than on the first Bud@et href.
    want = ("bud@et" + short_cycle(cycle)).lower()
    page_url = None
    for href in re.findall(r'href="([^"]+)"', body, re.I):
        if want in href.lower():
            page_url = absolute(href, BASE)
            break
    if not page_url:
        return home.body, None, None, {}, f"no href matching Bud@et{short_cycle(cycle)}"

    index = fetch(page_url, pace=pace)
    if not index.ok:
        return home.body, None, page_url, {}, f"budget page http {index.status}"
    ibody = index.body.decode("utf-8", "replace")

    urls = {}
    for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', ibody, re.I):
        url = absolute(href, page_url)
        stem = url.rsplit("/", 1)[-1].split("?")[0]
        stem = stem[:-4] if stem.lower().endswith(".pdf") else stem
        # Exact stem, not a prefix. "Volume-VII-2" is a prefix of nothing here, but
        # "Volume-I-1" and "Volume-I-2" show that prefix matching on these names is one
        # renamed file away from silently collecting the wrong volume.
        if stem in BOOKS:
            urls.setdefault(stem, url)
    return home.body, index.body, page_url, urls, None


def collect(cycle, date=None, pace=1.5):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "andhra", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "andhra", "started": utcnow(), "base": BASE, "cycle": cycle,
           "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    home_body, index_body, page_url, urls, err = discover(cycle, pace)
    if home_body:
        with gzip.open(os.path.join(out_dir, "home.html.gz"), "wb") as fh:
            fh.write(home_body)
        man["home_bytes"] = len(home_body)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
    man["page_url"] = page_url
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/andhra/{date}/_manifest.json", man)
        return man
    man["urls"] = urls

    for book in sorted(BOOKS):
        url = urls.get(book)
        if not url:
            man["errors"].append({"stage": book, "why": "not linked on the budget page"})
            continue
        r = fetch(url, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        # A PDF that is really an error page is a valid write and the failure mode that
        # matters, so check the magic bytes here rather than trusting the status.
        if not r.body.startswith(b"%PDF"):
            man["errors"].append({"stage": book, "why": "response is not a PDF"})
            continue
        bad = looks_like_error(r.body[:4096])
        if bad:
            man["errors"].append({"stage": book, "why": str(bad)})
            continue
        with gzip.open(os.path.join(out_dir, f"{book}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["books"][book] = {"url": url, "bytes": len(r.body), "what": BOOKS[book]}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/andhra/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Andhra Pradesh scheme-wise budget books.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.cycle, a.date, a.pace)
    print(f"andhra {a.cycle}: {man.get('books_collected', 0)} of "
          f"{len(BOOKS)} books archived")
    if man.get("page_url"):
        print(f"    page {man['page_url']}")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<18}{d['bytes']:>10,} bytes   {d['what']}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
