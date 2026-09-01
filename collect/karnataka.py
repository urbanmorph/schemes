"""
Karnataka state budget collector — raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md §7 before editing.

Why a state budget at all. The register could name 66 central schemes that are funded and
never announced because the Union Budget publishes an independent list of names to check
myScheme against. No such list existed for any state, so /divergence could report that
DBT counts 501 schemes in Karnataka where myScheme lists 56 and could not name one of the
missing 445. A count is an argument; a name is a fact. This collector is the first half
of turning one into the other.

Karnataka publishes several scheme-wise cuts of the same budget, and they are not
alternatives to each other:

    GB       Gender Budget, every scheme with a women-oriented allocation
    CB       Child Budget, every scheme with a child-oriented allocation
    SCSPTSP  Scheduled Caste and Tribal Sub Plan allocations, scheme-wise by statute

Each is a curated list of schemes that deliver a benefit to people, which is exactly the
population myScheme claims to cover, and each carries a head of account, the English
scheme name, four years of allocation and often a one-line statement of purpose. The
detailed expenditure volumes (EXPVOL1-7) are more complete and much noisier, mixing
establishment and works heads with schemes; they are deliberately not collected yet,
because the union-level lesson was that a comprehensive-but-noisy source needs a
classifier before it can be published, and these three do not.

    archive/karnataka/D/index.html.gz    the volumes page, so URL discovery is auditable
    archive/karnataka/D/<book>.pdf.gz    raw bytes, byte-identical to what was served
    archive/karnataka/D/_manifest.json

The PDF filenames carry a cache-busting timestamp (GB2026-27_1772789013.pdf) and the
index URL carries the financial year, so both are discovered from the volumes page rather
than hardcoded. Discovering where a document lives is not the same as adapting to what is
inside it: the first is addressing, the second is the thing collect/ must never do.
"""

import argparse
import gzip
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://finance.karnataka.gov.in"
INDEX = f"{BASE}/192/budget-volumes-{{cycle}}/en"

# Books wanted, by the prefix their filename starts with. The value is what the book is,
# recorded here so the archive is readable without this file.
BOOKS = {
    "GB": "Gender Budget, women-oriented schemes with allocations",
    "CB": "Child Budget, child-oriented schemes with allocations",
    "SCSPTSP": "Scheduled Caste Sub Plan and Tribal Sub Plan allocations, scheme-wise",
}


def discover(cycle, pace):
    """Find this cycle's PDF URLs from the volumes page. Returns (index_bytes, {book: url})."""
    r = fetch(INDEX.format(cycle=cycle), pace=pace)
    if not r.ok:
        return None, {}, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    urls = {}
    for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', body, re.I):
        if not href.startswith("http"):
            href = BASE + ("" if href.startswith("/") else "/") + href.lstrip("/")
        base = href.rsplit("/", 1)[-1]
        for book in BOOKS:
            # SCSPTSP must be tested before CB and GB or "SCSPTSP2026-27.pdf" is never
            # reached; startswith on the shorter keys does not collide here, but the sort
            # makes that independent of dictionary order.
            if base.upper().startswith(book):
                urls.setdefault(book, href)
    return r.body, urls, None


def collect(cycle, date=None, pace=1.5):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "karnataka", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "karnataka", "started": utcnow(), "base": BASE, "cycle": cycle,
           "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, urls, err = discover(cycle, pace)
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/karnataka/{date}/_manifest.json", man)
        return man
    with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
        fh.write(index_body)
    man["index_bytes"] = len(index_body)
    man["urls"] = urls

    for book in sorted(BOOKS):
        url = urls.get(book)
        if not url:
            man["errors"].append({"stage": book, "why": "not linked on the volumes page"})
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
        man["books"][book] = {"url": url, "bytes": len(r.body),
                              "what": BOOKS[book]}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/karnataka/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(description="Archive the Karnataka scheme-wise budget books.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.cycle, a.date, a.pace)
    print(f"karnataka {a.cycle}: {man.get('books_collected', 0)} of "
          f"{len(BOOKS)} books archived")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<9}{d['bytes']:>10,} bytes   {d['what']}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
