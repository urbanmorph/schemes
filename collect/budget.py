"""
Union Budget collector — the PDFs, as bytes, before they are overwritten.

FROZEN CODE. Read PLAN.md §7 before editing.

indiabudget.gov.in replaces these files in place every February at the same URLs, and
does not archive the previous year anywhere discoverable. Whatever is not captured before
the next Budget is gone. That is the entire argument for running this annually and
committing the bytes.

    archive/budget/<year>/stat4a.pdf.gz     Statement 4A — Centrally Sponsored Schemes
    archive/budget/<year>/stat4b.pdf.gz     Statement 4B — Central Sector Schemes
    archive/budget/<year>/outcome.pdf.gz    Outcome Budget
    archive/budget/<year>/_manifest.json

Two things this file exists to respect, both measured 2026-08-30:

  A browser User-Agent is required. Plain curl gets 403.

  Never HEAD to test existence. stat4b.pdf returns 404 to HEAD and 200 to GET. A
  collector that probed before fetching would conclude half the Budget is missing.
"""

import argparse
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, utcnow, write_json  # noqa: E402

BASE = "https://www.indiabudget.gov.in"

DOCS = {
    "stat4a": f"{BASE}/doc/eb/stat4a.pdf",
    "stat4b": f"{BASE}/doc/eb/stat4b.pdf",
    # The Outcome Budget filename carries the year, so it needs formatting per cycle.
    "outcome": f"{BASE}/doc/OutcomeBudgetE{{y0}}_{{y1}}.pdf",
}


def collect(year, pace=2.0):
    """`year` is the first year of the Budget cycle: 2026 -> Budget 2026-27."""
    out_dir = os.path.join(ROOT, "archive", "budget", str(year))
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "budget", "cycle": f"{year}-{str(year + 1)[2:]}",
           "started": utcnow(), "docs": {}, "errors": []}

    for name, tmpl in DOCS.items():
        url = tmpl.format(y0=year, y1=year + 1)
        r = fetch(url, timeout=180, pace=pace)
        if not r.ok or not r.body.startswith(b"%PDF"):
            man["errors"].append({"doc": name, "url": url,
                                  "why": f"status {r.status}, "
                                         f"{'not a PDF' if r.body[:4] != b'%PDF' else 'no body'}"})
            print(f"  {name}: FAILED ({r.status})")
            continue
        with gzip.open(os.path.join(out_dir, f"{name}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["docs"][name] = {"url": url, "bytes": len(r.body), "sha256": r.sha256}
        print(f"  {name}: {len(r.body):,} bytes  sha256 {r.sha256[:12]}…")

    man["finished"] = utcnow()
    man["error_count"] = len(man["errors"])
    write_json(f"archive/budget/{year}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(description="Archive the Union Budget scheme statements.")
    ap.add_argument("--year", type=int, default=2026,
                    help="first year of the cycle (2026 = Budget 2026-27)")
    ap.add_argument("--pace", type=float, default=2.0)
    args = ap.parse_args()
    print(f"Union Budget {args.year}-{str(args.year + 1)[2:]}")
    m = collect(args.year, args.pace)
    print(f"  archived {len(m['docs'])}/3 documents")


if __name__ == "__main__":
    main()
