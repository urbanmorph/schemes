"""
Comptroller and Auditor General audit-report CATALOGUE collector — raw HTML only.

FROZEN CODE. Read PLAN.md §7 before editing.

What this is for. Which schemes have been audited is genuinely hard to look up. The CAG
publishes every report it has tabled since 2001 on one paginated index, and nowhere else
is that list available as a list. This collects the INDEX, which is a catalogue of what
was audited, when, of what type and where the PDF sits. It does not collect the reports.

What this is NOT for. This register is about *the data about* schemes, never about
whether a scheme works. The audit findings are the CAG's to publish and are none of this
project's business, so the PDFs are deliberately not downloaded, not read and not
summarised anywhere downstream. The catalogue is the whole deliverable: an audit exists,
on this subject, on this date, and here is where to read it for yourself.

    archive/cag/D/page-000.html.gz  .. page-NNN.html.gz   one index page each
    archive/cag/D/_manifest.json

The index is SERVER-RENDERED, which is the only reason this is a 281-request job rather
than a 3,000-request one. Measured 2026-09-02: the per-report detail pages at
/en/audit-report/details/<id> are JavaScript-driven and arrive effectively empty to a
fetcher, so nothing can be read from them and there is no reason to fetch them. Every
field this project wants is already on the index page.

Pagination, measured 2026-09-02:

    ?page=0    "Page 1 of 280, showing 10 records out of 2,798 total"   10 detail links
    ?page=279  "Page 280 of 280, showing 10 records out of 2,798 total" 10 detail links
    ?page=280  "Page 280 of 280, showing 8 records out of 2,798 total"   8 detail links
    ?page=281  HTTP 404, 0 detail links

So the page parameter is zero-based, one past the last numbered page still serves the
tail of 8, and the first page past the end 404s. 279*10 + 8 = 2,798, which is the
headline total exactly. That arithmetic is the completeness assertion: the crawl walks
until a page yields no detail links, and the manifest records the count found on every
page, the page it stopped at, and the site's own claimed total to check the sum against.

Counting `href="/en/audit-report/details/N"` is deliberately the only thing read out of
the bytes here, and it is read as a COUNT, never as a field. A collector that cannot tell
whether it reached the end of a catalogue cannot be verified at all, and the alternative
is a hard-coded page count that would silently truncate the month the catalogue grows.
The pdf link on the same listing uses a different path, so this pattern matches exactly
one occurrence per report and page counts of 10 are a check on that.

Politeness. This is one machine walking a whole catalogue, so the default pace is 2.0s
between requests: roughly 12 minutes for the full walk, against an index that changes a
few times a month. robots.txt is served as a 404 HTML page (measured 2026-09-02), so
there is no crawl-delay to honour and the conservative default stands in for one.
"""

import argparse
import gzip
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://cag.gov.in"
INDEX = BASE + "/en/audit-report"

# One occurrence per report listing. The "Download Full Report" anchor beside it points
# at /webroot/uploads/download_audit_report/..., so it cannot be caught by this.
DETAIL_LINK = re.compile(rb'href="/en/audit-report/details/(\d+)"')

# The index prints its own record count. Kept as a completeness cross-check in the
# manifest and nowhere else: it is evidence about the crawl, not a field about a report.
TOTAL_CLAIMED = re.compile(rb"showing\s+[\d,]+\s+records?\s+out\s+of\s+([\d,]+)\s+total",
                           re.I)

# A bound on the walk so a site that starts serving a valid page for every integer cannot
# turn this into an unbounded crawl. 281 pages measured 2026-09-02; 400 leaves room for
# about a decade of reports at the current rate before anyone has to think about it.
MAX_PAGES = 400


def collect(date=None, pace=2.0, max_pages=MAX_PAGES):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "cag", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "cag", "started": utcnow(), "base": BASE, "index": INDEX,
           "pace": pace, "max_pages": max_pages, "pages": [], "errors": [],
           "status_histogram": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    total_claimed = None
    links_total = 0
    seen_ids = set()
    pages_written = 0
    stopped_at = None
    stop_reason = None

    for page in range(max_pages):
        r = fetch(f"{INDEX}?page={page}", pace=pace)
        note(r.status)

        if not r.ok:
            # 404 is how the site says "past the end", so it is a stop and not an error.
            # Anything else is a fetch that failed, and stopping on it would truncate the
            # catalogue while leaving a manifest that looks perfectly plausible. So the
            # walk carries on and the mismatch against total_claimed is what fails.
            if r.status == 404:
                stopped_at, stop_reason = page, f"http 404 at page {page}"
                break
            man["errors"].append({"page": page, "why": f"http {r.status}"})
            print(f"  page {page:>3}: http {r.status}")
            continue

        bad = looks_like_error(r.body)
        if bad:
            man["errors"].append({"page": page, "why": str(bad)})
            print(f"  page {page:>3}: {bad}")
            continue

        ids = DETAIL_LINK.findall(r.body)
        n = len(ids)
        if n == 0:
            stopped_at, stop_reason = page, f"0 detail links at page {page}"
            break

        if total_claimed is None:
            m = TOTAL_CLAIMED.search(r.body)
            if m:
                total_claimed = int(m.group(1).replace(b",", b""))

        name = f"page-{page:03d}.html.gz"
        with gzip.open(os.path.join(out_dir, name), "wb") as fh:
            fh.write(r.body)
        pages_written += 1
        links_total += n
        seen_ids.update(ids)
        man["pages"].append({"page": page, "status": r.status, "links": n,
                             "bytes": len(r.body), "sha256": r.sha256})
        if page % 20 == 0:
            print(f"  page {page:>3}: {n:>2} reports  ({links_total:,} so far)")
    else:
        stop_reason = f"hit max_pages={max_pages} without reaching the end"
        man["errors"].append({"page": max_pages, "why": stop_reason})

    man.update(finished=utcnow(), pages_written=pages_written,
               detail_links=links_total, distinct_reports=len(seen_ids),
               duplicate_listings=links_total - len(seen_ids), stopped_at=stopped_at,
               stop_reason=stop_reason, total_claimed=total_claimed,
               error_count=len(man["errors"]))
    # The assertion counts DISTINCT report ids, not links. Counting links called the first
    # complete walk incomplete: 2,808 links against a claimed 2,798, which looks like ten
    # reports too many and is actually ?page=0 serving the same ten rows as ?page=1,
    # because this pagination is one-based and page zero aliases to the first page.
    #
    # myScheme taught the same lesson from the other side. Paging it under an unstable sort
    # returned 4,772 records but 4,735 distinct slugs, and there the duplicates meant 37
    # schemes had never been served at all. So a duplicate is never dismissable on sight:
    # it means either a harmless alias or a silent loss, and only counting distinct
    # identities against the source's own total tells you which. Here distinct ids equal
    # the claimed total exactly, so nothing was missed.
    #
    # Recorded rather than raised, so the snapshot is still archived and still inspectable.
    man["complete"] = bool(total_claimed is not None
                           and len(seen_ids) == total_claimed
                           and not man["errors"])
    write_json(f"archive/cag/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the CAG audit-report index (catalogue only, no PDFs).")
    ap.add_argument("--date", default=today())
    ap.add_argument("--pace", type=float, default=2.0)
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    a = ap.parse_args()
    print(f"CAG audit-report catalogue snapshot {a.date}")
    man = collect(a.date, a.pace, a.max_pages)
    print(f"  pages written : {man['pages_written']}")
    print(f"  detail links  : {man['detail_links']:,}")
    print(f"  distinct      : {man['distinct_reports']:,} "
          f"({man['duplicate_listings']} listed more than once)")
    print(f"  site claims   : {man['total_claimed']}")
    print(f"  stopped       : {man['stop_reason']}")
    print(f"  complete      : {man['complete']}")
    for e in man["errors"]:
        print(f"    ERROR page {e['page']}: {e['why']}")


if __name__ == "__main__":
    main()
