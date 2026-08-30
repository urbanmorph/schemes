"""
Extract scheme line items from archived Budget statements, and hold the parse to the
document's own printed Grand Total.

AGENT-EDITABLE (PLAN.md §7). Reads archive/, writes data/budget/. Never fetches.

The reconciliation is the point of this file. Measured 2026-08-30: `pdftotext -layout`
on Statement 4A yields 84 numbered rows where the document numbers 86 — items 28 and 31
vanish from the extracted text entirely, in both -layout and plain mode, with no error
raised. Row 27 is followed directly by row 29.

A parser that loses 2.3% of Centrally Sponsored Schemes and reports success is worse
than one that crashes. The printed Grand Total is the only independent witness the
document offers, so every parse is checked against it and a mismatch is fatal.

    data/budget/<year>/4a.json      line items
    data/budget/<year>/4b.json
    data/budget/_totals.json        what the verifier reads
"""

import argparse
import glob
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, write_json  # noqa: E402

# A numbered scheme row: leading spaces, an index, a dot, then the name.
ROW = re.compile(r"^\s+(\d+)\.\s+(\S.*?)\s{2,}(.*)$")
DEMAND = re.compile(r"^\s*Demand\s*No\.?\s*(\d+)", re.I)
GRAND = re.compile(r"^\s*Grand\s+Total\s+(.*)$", re.I)
NUMS = re.compile(r"-?[\d,]+\.\d{2}|\.{3}")


def to_text(gz_path):
    """pdftotext -layout on a gzipped PDF, via a temp file."""
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext not found — install poppler-utils")
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "d.pdf")
        with gzip.open(gz_path, "rb") as src, open(pdf, "wb") as dst:
            shutil.copyfileobj(src, dst)
        txt = os.path.join(td, "d.txt")
        subprocess.run(["pdftotext", "-layout", pdf, txt], check=True,
                       capture_output=True, timeout=180)
        with open(txt, encoding="utf-8", errors="replace") as fh:
            return fh.read()


def cells(tail):
    """Parse a row's numeric tail. '...' is the source's nil-mark, kept as None."""
    return [None if c == "..." else float(c.replace(",", "")) for c in NUMS.findall(tail)]


def parse_statement(text):
    """Rows, the printed grand total, and the gaps in the document's own numbering."""
    rows, demand, grand = [], None, None
    for line in text.splitlines():
        m = DEMAND.match(line)
        if m:
            demand = int(m.group(1))
            continue
        m = GRAND.match(line)
        if m:
            c = cells(m.group(1))
            # Four column-groups of Revenue/Capital/Total; the last Total is BE for the
            # coming year, which is the figure the line items sum to.
            grand = c[-1] if c else None
            continue
        m = ROW.match(line)
        if m:
            idx, name, tail = int(m.group(1)), m.group(2).strip(), m.group(3)
            c = cells(tail)
            rows.append({"index": idx, "name": name, "demand_no": demand,
                         "be_next_year": c[-1] if c else None})

    seen = {r["index"] for r in rows}
    highest = max(seen) if seen else 0
    missing = [i for i in range(1, highest + 1) if i not in seen]
    return rows, grand, missing, highest


def parse_year(year):
    src = os.path.join(ROOT, "archive", "budget", str(year))
    if not os.path.isdir(src):
        raise SystemExit(f"no archive at archive/budget/{year}")

    totals, failures = {}, []
    for stmt in ("stat4a", "stat4b"):
        gz = os.path.join(src, f"{stmt}.pdf.gz")
        if not os.path.exists(gz):
            continue
        rows, grand, missing, highest = parse_statement(to_text(gz))
        parsed_sum = round(sum(r["be_next_year"] or 0 for r in rows), 2)

        write_json(f"data/budget/{year}/{stmt}.json", {
            "cycle": f"{year}-{str(year + 1)[2:]}",
            "statement": stmt,
            "rows_extracted": len(rows),
            "highest_index_in_document": highest,
            "missing_indices": missing,
            "parsed_sum_be": parsed_sum,
            "printed_grand_total": grand,
            "items": rows,
        })

        # TWO independent assertions, because neither is sufficient alone.
        #
        # Measured 2026-08-31 on Statement 4A: 84 rows extracted where the document
        # numbers 86 — rows 28 and 31 are absent from pdftotext's output entirely, in
        # both -layout and plain mode — and yet the 84 rows sum to the printed Grand
        # Total exactly. Both lost rows carry a nil BE for this cycle, so the money
        # reconciles while the scheme list is short by two.
        #
        # The money check alone would have passed and we would have published 84
        # Centrally Sponsored Schemes as though that were the count. This project counts
        # schemes, not only rupees, so contiguity of the document's own numbering is a
        # separate and equally hard requirement.
        reconciles = grand is not None and abs(parsed_sum - grand) < 0.02
        contiguous = not missing
        ok = reconciles and contiguous

        totals[stmt] = {"parsed_sum": parsed_sum, "printed_grand_total": grand,
                        "rows": len(rows), "highest_index": highest,
                        "missing_indices": missing,
                        "reconciles": reconciles, "contiguous": contiguous, "ok": ok}

        printed = "—" if grand is None else f"{grand:,.2f}"
        print(f"  {'OK ' if reconciles else 'FAIL'} {stmt} money: "
              f"parsed {parsed_sum:,.2f} vs printed {printed} cr")
        print(f"  {'OK ' if contiguous else 'FAIL'} {stmt} rows:  "
              f"{len(rows)} extracted, document numbers up to {highest}"
              + (f" — LOST {missing}" if missing else ""))
        if not ok:
            failures.append(stmt)

    write_json("data/budget/_totals.json", totals)
    return totals, failures


def main():
    ap = argparse.ArgumentParser(description="Parse archived Budget statements.")
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()
    print(f"Union Budget {args.year}-{str(args.year + 1)[2:]}")
    totals, failures = parse_year(args.year)
    if failures:
        print(f"\n{len(failures)} statement(s) failed a check. A money mismatch means "
              f"values were misread; a row gap means the extraction lost line items that "
              f"the document itself numbers. Either way the scheme counts derived from "
              f"this statement are not publishable as a census. See PLAN.md §3.3.")
        raise SystemExit(1)
    print("\nall statements reconcile on money and are contiguous on numbering.")


if __name__ == "__main__":
    main()
