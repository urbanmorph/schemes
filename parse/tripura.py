"""
Parse the archived Tripura CSS & SLS Budget Overview into data/tripura/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY TRIPURA MATTERS AND WHAT THIS BOOK ANSWERS. myScheme lists 37 state schemes for
Tripura against DBT Bharat's 209, the widest ratio in the register at 5.6 to one. DBT
publishes that 209 as a bare number with no list, so the question has never been which
schemes it counts. This book is very probably the answer: `Details of Centrally Sponsored
Schemes onboarded on SNS SPARSH 2026-27` names **74 distinct Centrally Sponsored
Scheme codes and 134 State Level Scheme codes, 208 together**, against DBT's 209. SNS is
the Single Nodal Agency system DBT counts through, so the near-identity is not a
coincidence worth ignoring.
It is not proof, and this file does not claim it is; it is the closest a state document
has come to reproducing a DBT count.

THE SHAPE, which is a clean three-level tree with a printed total at every level:

    10              Home (Police)                                <- demand and department
    CSS 3194          MODERNISATION OF POLICE FORCES             <- central scheme
    SLS      TR89           ASUMP Main Plan Tripura              <- the state's scheme
      Major  Sub    Minor  Sub    Detail  Object   Budget Estimate
      Head   Major  Head   Head   Head    Head     (Amount in Lakhs) 2026-27
     4055     00     207    90      48      60          23.1300
     4055     00     207    91      48      60         208.0000
          SLS   TR89    Total :                        231.1300
              CSS   3194     Total :                   231.1300
                    Grand Total for Demand no. 10      231.1300

Everything is English and every line matches one of six shapes, so nothing here is
guessed: 658 head-of-account rows, 134 SLS totals, 76 CSS
total lines over 74 distinct codes, and 30 demand totals account for every non-header line
in the book.

The register keys on the **SLS code**, `TR89`, because that is Tripura's own identifier
for its own scheme and the thing a later year can be compared against. The CSS code and
the central scheme's name are carried alongside, and a scheme funded under more than one
demand has all of them recorded.

WHY THE GENDER BUDGET IS COLLECTED AND NOT PARSED. `Gender Budget 2026-27` is the only
other Tripura document that names schemes with their department, and its names cannot be
published. Its text stream carries spaces INSIDE words, so the scheme Tripura calls
Mukhyamantri SATH extracts as

    Mukhya Mantri Scholars hip for Achiecer s Towards Higher Educatio n-CM SATH

and `Academi c Excellen ce`, `Examina tion` and `Minister’ s` come out the same way. It is
not a `pdftotext -layout` artefact: `-raw` and the default mode return the identical
breaks, so the spaces are in the PDF. A name like that cannot be matched against myScheme
and publishing it would put a garbled name beside a real allocation. The book is archived
because the finding needs its evidence, and it is not read here.

RECONCILIATION, three checks over the book's own tree, all hard errors:

  1. Every printed `SLS <code> Total` against the head-of-account rows beneath it.
  2. Every printed `CSS <code> Total` against the SLS totals beneath it.
  3. Every printed `Grand Total for Demand no. N` against the CSS totals beneath it.

plus the unit and the cycle, both read from every page's own column header and never
assumed.
"""

import argparse
import glob
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, read_json, utcnow, write_json  # noqa: E402

CYCLE_WANTED = "2026-27"

# The six line shapes this book is made of. The Total forms are tested BEFORE the name
# forms, because "CSS 3194 Total : 231.1300" also matches the name pattern with the name
# reading "Total : 231.1300".
CSS_TOTAL = re.compile(r"^\s*CSS\s+(\d{3,5})\s+Total\s*:\s*([\d,]*\d\.\d+)\s*$")
SLS_TOTAL = re.compile(r"^\s*SLS\s+(TR\d+)\s+Total\s*:\s*([\d,]*\d\.\d+)\s*$")
CSS_NAME = re.compile(r"^\s*CSS\s+(\d{3,5})\s+(\S.*?)\s*$")
SLS_NAME = re.compile(r"^\s*SLS\s+(TR\d+)\s+(\S.*?)\s*$")
# Major, Sub Major, Minor, Sub Head, Detail Head, Object Head, then the provision.
HOA = re.compile(r"^\s*(\d{4})\s+(\d{2})\s+(\d{3})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+"
                 r"([\d,]*\d\.\d+)\s*$")
DEMAND_TOTAL = re.compile(r"^\s*Grand Total for Demand no\.\s*(\d+)\s+"
                          r"([\d,]*\d\.\d+)\s*$")
DEMAND_HEAD = re.compile(r"^\s*(?:Continued\s+)?Demand No\s*[:.]?\s*(\d+)\s*$")
# The department is printed with the demand number in front of it on every detail page.
DEPT_HEAD = re.compile(r"^\s*(\d{1,2})\s{2,}(\S.*?)\s*$")

UNIT = re.compile(r"\(\s*Amount\s+in\s+Lakhs?\s*\)", re.I)
CYCLE = re.compile(r"\b(\d{4}-\d{2})\b")


def pdftotext(pdf_bytes):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout


def num(s):
    return round(float(s.replace(",", "")), 4)


def read_book(text):
    """Walk the book. Returns (blocks, checks, meta).

    A block is one SLS scheme under one CSS scheme under one demand, with its head-of
    -account rows and the total the book prints for it.
    """
    demand = department = css_code = css_name = None
    sls = None
    blocks, sls_checks, css_checks, demand_checks = [], [], [], []
    css_open, demand_open = [], []
    units, cycles, pages = 0, set(), 0

    for page in text.split("\f"):
        lines = page.split("\n")
        if not any(l.strip() for l in lines):
            continue
        pages += 1
        if UNIT.search(page):
            units += 1
            # The cycle is printed directly under the unit in the same column-header
            # block, and nowhere else on a detail page, so reading every year-shaped token
            # on a page that prints the unit yields exactly the cycles the book claims.
            for m in CYCLE.finditer(page):
                cycles.add(m.group(1))

        for line in lines:
            if not line.strip():
                continue

            m = DEMAND_TOTAL.match(line)
            if m:
                demand_checks.append({
                    "demand": int(m.group(1)), "department": department,
                    "printed": num(m.group(2)),
                    "computed": round(sum(demand_open), 4),
                    "css_blocks": len(demand_open)})
                demand_open = []
                continue

            m = CSS_TOTAL.match(line)
            if m:
                css_checks.append({
                    "css_code": m.group(1), "css_name": css_name,
                    "demand": demand, "printed": num(m.group(2)),
                    "computed": round(sum(css_open), 4),
                    "sls_blocks": len(css_open)})
                demand_open.append(num(m.group(2)))
                css_open = []
                sls = None
                continue

            m = SLS_TOTAL.match(line)
            if m:
                got = round(sum(r["amount"] for r in sls["rows"]), 4) if sls else 0.0
                sls_checks.append({
                    "sls_code": m.group(1),
                    "sls_name": sls["name"] if sls else None,
                    "css_code": css_code, "demand": demand,
                    "printed": num(m.group(2)), "computed": got,
                    "rows": len(sls["rows"]) if sls else 0})
                if sls is not None:
                    sls["printed_total"] = num(m.group(2))
                    blocks.append(sls)
                css_open.append(num(m.group(2)))
                sls = None
                continue

            m = SLS_NAME.match(line)
            if m:
                sls = {"code": m.group(1), "name": m.group(2),
                       "css_code": css_code, "css_name": css_name,
                       "demand": demand, "department": department,
                       "rows": [], "printed_total": None}
                continue

            m = CSS_NAME.match(line)
            if m:
                css_code, css_name = m.group(1), m.group(2)
                continue

            m = HOA.match(line)
            if m:
                if sls is None:
                    # A head of account outside any SLS block would mean the walk has lost
                    # its place. Nothing in the 2026-27 book does this and the checks
                    # below would fail if it did, so it is recorded rather than guessed at.
                    continue
                sls["rows"].append({
                    "hoa": "-".join(m.groups()[:6]),
                    "amount": num(m.group(7))})
                continue

            m = DEMAND_HEAD.match(line)
            if m:
                demand = int(m.group(1))
                continue

            m = DEPT_HEAD.match(line)
            if m and demand is not None and int(m.group(1)) == demand:
                department = m.group(2)
                continue

    return blocks, sls_checks, css_checks, demand_checks, units, cycles, pages


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "tripura", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive/tripura snapshot; run collect/tripura.py first")
    date = date or dates[-1]
    man = read_json(f"archive/tripura/{date}/_manifest.json", {}) or {}

    path = os.path.join(ROOT, "archive", "tripura", date, "css-sls.pdf.gz")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    with gzip.open(path, "rb") as fh:
        text = pdftotext(fh.read())

    blocks, sls_checks, css_checks, demand_checks, units, cycles, pages = \
        read_book(text)

    if CYCLE_WANTED not in cycles:
        raise SystemExit(f"tripura: the book's column headers name {sorted(cycles)}, "
                         f"not {CYCLE_WANTED}")
    other = sorted(c for c in cycles if c != CYCLE_WANTED)
    if not units:
        raise SystemExit("tripura: no page prints '(Amount in Lakhs)'; the unit cannot "
                         "be assumed")

    tol = 0.0011
    sls_failed = [c for c in sls_checks if abs(c["printed"] - c["computed"]) > tol]
    css_failed = [c for c in css_checks if abs(c["printed"] - c["computed"]) > tol]
    dem_failed = [c for c in demand_checks
                  if abs(c["printed"] - c["computed"]) > tol]

    # ------------------------------------------------------------------------- entries
    # Keyed on the SLS code, which is Tripura's own identifier for its own scheme. The
    # same code appears under more than one demand when two departments fund it, and those
    # provisions are ADDED with every demand recorded, the way parse/odisha.py treats a
    # scheme code that recurs across demand books.
    merged = {}
    for b in blocks:
        e = merged.get(b["code"])
        if e is None:
            e = merged[b["code"]] = {
                "code": b["code"], "name": b["name"], "names": {b["name"]},
                "css_codes": {}, "departments": set(), "demands": set(),
                "hoas": set(), "be_lakh": 0.0, "blocks": 0}
        e["names"].add(b["name"])
        if b["css_code"]:
            e["css_codes"][b["css_code"]] = b["css_name"]
        if b["department"]:
            e["departments"].add(b["department"])
        if b["demand"]:
            e["demands"].add(b["demand"])
        for r in b["rows"]:
            e["hoas"].add(r["hoa"])
        e["be_lakh"] = round(e["be_lakh"] + (b["printed_total"] or 0.0), 4)
        e["blocks"] += 1

    out = []
    for code in sorted(merged):
        e = merged[code]
        out.append({
            "code": code,
            "name": e["name"],
            "also_named": sorted(n for n in e["names"] if n != e["name"]) or None,
            "css_codes": [{"code": k, "name": v}
                          for k, v in sorted(e["css_codes"].items())],
            "departments": sorted(e["departments"]),
            "demands": sorted(e["demands"]),
            "hoas": sorted(e["hoas"]),
            "be_lakh": e["be_lakh"],
            "budget_lines": e["blocks"],
        })

    # The central schemes named in the same book, published separately because a CSS name
    # is the Government of India's name for the scheme and not Tripura's.
    css_out = []
    seen_css = {}
    for c in css_checks:
        k = c["css_code"]
        s = seen_css.setdefault(k, {"code": k, "name": c["css_name"],
                                    "demands": set(), "be_lakh": 0.0})
        s["demands"].add(c["demand"])
        s["be_lakh"] = round(s["be_lakh"] + c["printed"], 4)
    for k in sorted(seen_css):
        s = seen_css[k]
        css_out.append({"code": k, "name": s["name"],
                        "demands": sorted(d for d in s["demands"] if d),
                        "be_lakh": s["be_lakh"]})

    write_json("data/tripura/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Tripura",
        "cycle": CYCLE_WANTED,
        "source": ("Tripura Budget 2026-27, CSS & SLS Budget Overview: Details of "
                   "Centrally Sponsored Schemes onboarded on SNS SPARSH, with the State "
                   "Level Schemes under each"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "be_lakh is rupees in LAKH, read from the '(Amount in Lakhs)' the book prints "
            "in the column header of every detail page. Figures carry four decimals "
            "because the book does, so a provision of Rs 1,000 prints as 0.0100 and is "
            "kept as such rather than rounded to nothing. be_lakh is the Budget Estimate "
            "2026-27; this book publishes no other year, which is why there is no "
            "variant to choose."),
        "variant": "Budget Estimate 2026-27",
        "variant_note": (
            "One edition, one year, one figure per scheme. Tripura does publish its "
            "Expenditure Budget Volume 2 twice for the same cycle, as (B.E.) and as "
            "(A.C. & B.E. & R.E), and neither is read here; see collect/tripura.py."),
        "schemes": len(out),
        "counts": {
            "state_level_schemes": len(out),
            "centrally_sponsored_schemes": len(css_out),
            "state_and_central_together": len(out) + len(css_out),
            "dbt_bharat_counts_for_tripura": 209,
            "myscheme_lists_for_tripura": 37,
            "budget_lines_read": len(blocks),
            "heads_of_account_read": sum(len(e["hoas"]) for e in out),
            "demands_read": len(demand_checks),
            "pages_read": pages,
            "pages_printing_the_lakh_unit": units,
            "with_a_positive_be": sum(1 for e in out if e["be_lakh"] > 0),
            "funded_under_more_than_one_demand": sum(
                1 for e in out if len(e["demands"]) > 1),
        },
        "reconciliation": {
            "sls_totals": {
                "checked": len(sls_checks), "failed": len(sls_failed),
                "failures": sls_failed[:20] or None,
                "what": ("every printed 'SLS <code> Total' against the head-of-account "
                         "rows read beneath it")},
            "css_totals": {
                "checked": len(css_checks), "failed": len(css_failed),
                "failures": css_failed[:20] or None,
                "what": ("every printed 'CSS <code> Total' against the SLS totals read "
                         "beneath it")},
            "demand_totals": {
                "checked": len(demand_checks), "failed": len(dem_failed),
                "failures": dem_failed[:20] or None,
                "what": ("every printed 'Grand Total for Demand no. N' against the CSS "
                         "totals read beneath it")},
            "cycles_seen_in_page_headers": sorted(cycles),
            "cycles_other_than_wanted": other or None,
        },
        "centrally_sponsored_schemes": css_out,
        "gender_budget_not_read": (
            "Tripura's Gender Budget 2026-27 is archived beside this book and is not "
            "parsed. Its text stream carries spaces inside words, so Mukhyamantri SATH "
            "extracts as 'Mukhya Mantri Scholars hip for Achiecer s Towards Higher "
            "Educatio n-CM SATH', and 'Academi c Excellen ce', 'Examina tion' and "
            "'Minister’ s' come out the same way. pdftotext -raw and the default mode "
            "return the identical breaks, so the spaces are in the PDF and not in the "
            "extraction. A name in that state cannot be matched against myScheme, and "
            "publishing it would put a garbled name beside a real allocation."),
        # The join against myScheme, run once by hand on the 2026-09-03 snapshot and read
        # line by line. Recorded here rather than recomputed on every run because the
        # classification is a human reading, not a rule. parse/match.py is NOT edited to
        # fix anything found; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_tripura_records": 37,
            "register_names": 134,
            "joins_produced": 0,
            "joins_wrong_on_inspection": 0,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair"),
            "read_this_carefully": (
                "Zero. A generous matcher run over 37 myScheme records and 134 state "
                "scheme names found nothing at all, and that is a finding rather than a "
                "failure. The two lists describe different halves of Tripura's spending. "
                "myScheme's 37 are almost entirely welfare-board benefits and state "
                "pensions: Mukhyamantri Samajik Sahayata Prakalpa in four variants, six "
                "Tripura Building and Other Construction Workers Welfare Board benefits, "
                "the Tripura Journalist Health Insurance Scheme, the Lynching/Mob "
                "Violence Victim Compensation Scheme. This book is the schemes onboarded "
                "on SNS SPARSH, which is the route centrally sponsored money takes. "
                "Neither list contains the other and both are real, so Tripura's true "
                "count is at least 37 plus 208. The state schemes myScheme DOES list are "
                "named in Tripura's Gender Budget, which is archived here and cannot be "
                "read: see gender_budget_not_read."),
            "no_defects_to_report": (
                "A join count of zero produces no wrong joins, so this round adds nothing "
                "to the record of parse/match.py defects from Tripura."),
        },
        "caveat": (
            "One row here is one State Level Scheme code as Tripura's own budget system "
            "numbers them. A scheme funded under more than one demand has its provisions "
            "ADDED and every demand recorded. This book covers the schemes onboarded on "
            "SNS SPARSH, which is the single-nodal-agency route through which centrally "
            "sponsored money flows, so a purely state-funded scheme outside that route "
            "does not appear here and this is a floor on Tripura's schemes rather than a "
            "count of them. The centrally sponsored schemes are published separately "
            "under centrally_sponsored_schemes, because a CSS name is the Government of "
            "India's name for a scheme and not Tripura's."),
        "entries": out,
    })
    return out, css_out, sls_checks, sls_failed, css_checks, css_failed, \
        demand_checks, dem_failed, cycles, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Tripura CSS & SLS Budget Overview.")
    ap.add_argument("--date")
    a = ap.parse_args()
    (out, css_out, sls_checks, sls_failed, css_checks, css_failed,
     dem_checks, dem_failed, cycles, date) = run(a.date)
    print(f"tripura snapshot {date}")
    print(f"  {len(out)} state level schemes, {len(css_out)} centrally sponsored, "
          f"{len(out) + len(css_out)} together, against DBT Bharat's 209")
    print(f"     sum of 2026-27 provisions "
          f"{sum(e['be_lakh'] for e in out):>18,.4f} lakh")
    print(f"  SLS totals      {len(sls_checks) - len(sls_failed):>6} of "
          f"{len(sls_checks):<6} reconcile")
    print(f"  CSS totals      {len(css_checks) - len(css_failed):>6} of "
          f"{len(css_checks):<6} reconcile")
    print(f"  demand totals   {len(dem_checks) - len(dem_failed):>6} of "
          f"{len(dem_checks):<6} reconcile")
    print(f"  cycles in headers {sorted(cycles)}")
    for f in (sls_failed + css_failed + dem_failed)[:10]:
        print("     MISMATCH", json.dumps(f)[:220])
    if sls_failed or css_failed or dem_failed:
        print("  ERROR: the book does not reconcile against its own printed totals")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
