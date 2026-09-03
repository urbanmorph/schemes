"""
Parse the archived Haryana Plan Memo into data/haryana/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY HARYANA YIELDS, AND WHAT IT SETTLES. `Explanatory Memorandum on Welfare & Development
Schemes` is English throughout with a scheme code, a name column and a printed total at
every level, so it passes the test in docs/state-sources.md on the first page. What makes
it worth the effort is the count: it names 970 schemes against the 249 Haryana schemes
myScheme lists and DBT Bharat's 171. Haryana was picked as the state where the portal
might be AHEAD of the state, because it is one of only three where myScheme claims more
than DBT counts. It is not ahead. It is behind by a factor of four.

THE BOOK HAS THREE HALVES, and they use three different units.

  1. A `Summary of Budget Estimate 2026-27` per department, headed `(Amount in ₹ )`,
     printing FULL RUPEES to eleven digits: 33,71,50,00,000.
  2. A `LIST OF SCHEMES BUDGET ESTIMATE 2026-27` per department, headed `(₹ In Lakhs)`:

        Scheme Code No              Name of the Scheme      Central   State     Total  ...
        P-01-10-2401-51-105-96-51   Scheme for Quality          ...  300.00    300.00
                                    Control on Agriculture
                                    Inputs

  3. A narrative entry for most schemes, whose `Outlay` line is full rupees again:

        Code No.            1-15-2230-01-102-93-51
        Name of the Scheme  Providing of Mobile Vans for Facilitating the Health Care of
                            the Workers Working in Factories
        Outlay              `30,00,000/-
                The objective of the scheme is focused on providing Mobile vans ...

Read as one unit, every figure in this file would be out by a factor of 100,000, which is
the Kerala trap in a different book. The unit is therefore read from each page's own
header and a page that does not print `(₹ In Lakhs)` is not read as a scheme table at all.
That rule earns its keep on page 110, which prints the words `LIST OF SCHEMES BUDGET
ESTIMATE 2026-27` over a table of major heads in rupees.

The narrative code is the table code with its `P-0` prefix removed, which is how the two
halves join: `P-01-15-2230-01-102-93-51` and `1-15-2230-01-102-93-51` are one scheme.

THREE THINGS ABOUT THE BOOK A READER HAS TO KNOW, all found by reconciling it:

  A CONTINUATION PAGE PRINTS NO HEADER, AND IS NOT ALIGNED WITH THE PAGE BEFORE IT.
  Page 112 carries seven scheme rows and three Part totals with no column header at all,
  and its five columns end 8, 8, 13, 10 and 15 characters right of page 111's, so neither
  requiring a header nor shifting the previous one by a constant works. The page's own
  figures are clustered by where they end and the clusters are matched to the five named
  columns by the book's own arithmetic: the mapping under which the most rows satisfy
  Total = Central + State wins. A wrong mapping breaks that identity on nearly every row,
  which is what makes the choice checkable rather than a guess.

  A COLUMN CAN BE BLANK RATHER THAN NIL. Most rows print `...` for a nil cell, so counting
  figures inward from the right end of the line works for 956 of 970 rows and puts the
  money in the wrong column for the other 14, all in Community Development & Panchayats,
  where Establishment and Works are simply left empty. Cells are therefore assigned by
  position, never by order.

  ONE PAGE IS HEADED 2025-26. The Community Development & Panchayats scheme table is
  headed `LISTOFSCHEMESBUDGETESTIMATE2025-26`, spaces and all missing, inside a 2026-27
  book, and the summary page facing it is headed LIST OF SCHEMES over a table of major
  heads in rupees. The figures are 2026-27: that department's three Part totals equal its
  own rupee summary to the rupee under check 3 below. The stale heading is recorded in
  banners_read rather than smoothed over.

RECONCILIATION, three checks, all hard errors, and on the 2026-27 book all three close:

  1. Total = Central + State on every scheme row. 970 of 970.
  2. Every printed `Total Part-I(State Schemes)`, `Total Part-II` and `Total Part-III`
     against the rows read beneath it, in all five money columns. 192 of 192.
  3. THE UNITS CHECK. Each department's Summary prints the same Part totals in full
     rupees. Those are compared with the table's totals in lakh, times 100,000, to within
     500 rupees, which is what rounding a lakh to two decimals costs. 117 of 117. A parser
     that had read the wrong unit anywhere would be out by five orders of magnitude and
     could not fail this quietly. The 75 Part totals with no Summary line to check are
     Parts a department's summary does not itemise, and are counted as not-checkable
     rather than as passing.
"""

import argparse
import glob
import gzip
import itertools
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

# The scheme table's column header. Its five words are the anchors every figure on the
# page is assigned to.
TABLE_HEADER = re.compile(r"Scheme\s+Code\s+No.*?Central\s+State\s+Total\s+"
                          r"Establishment\s+Works")
COLUMN_WORD = re.compile(r"Central|State|Total|Establishment|Works")
COLUMNS = ("central", "state", "total", "establishment", "works")

LAKH_UNIT = re.compile(r"\(\s*₹\s*In\s+Lakhs?\s*\)", re.I)
RUPEE_UNIT = re.compile(r"\(\s*Amount\s+in\s+₹\s*\)", re.I)

# Haryana prints the banner with its spaces intact on 96 pages and with every space
# dropped on two, so the cycle is read from the page with the spaces squeezed out.
LIST_BANNER = re.compile(r"LISTOFSCHEMESBUDGETESTIMATE(\d{4}-\d{2})")
SUMMARY_BANNER = re.compile(r"SummaryofBudgetEstimate(\d{4}-\d{2})", re.I)

# P-01-10-2401-51-105-96-51, the state's own scheme code: part, department, major head,
# sub-major, minor, scheme serial, object head.
TABLE_CODE = re.compile(r"^\s*(P-\d{2}-\d{2}-\d{4}-\d{2}-\d{3}-\d{2}-\d{2,3})\s")
# One money cell. `...` is the nil marker; a few cells print four dots.
CELL = re.compile(r"\.{2,}|[\d,]*\d\.\d{2}")

PART = re.compile(r"^\s*Part-(I{1,3})\b\s*(.*)$")
PART_TOTAL = re.compile(r"^\s*Total\s+Part-(I{1,3})\b")

# The narrative half. Haryana writes the labels four ways ("Code No.", "Code No.:",
# "Name of the Scheme", "Name of the scheme:"), so the colon and the case are optional.
N_CODE = re.compile(r"^\s*Code\s+No\.?\s*:?\s+(\d-\d{2}-\d{4}-\d{2}-\d{3}-\d{2}-\d{2,3})\s*$",
                    re.I)
N_NAME = re.compile(r"^\s*Name\s+of\s+the\s+[Ss]cheme\.?\s*:?\s+(\S.*)$")
N_OUTLAY = re.compile(r"^\s*Outlay\.?\s*:?\s*(\S.*)?$", re.I)
N_ITEM = re.compile(r"^\s*\(\d{1,4}\)\s*$")
PAGE_MARK = re.compile(r"^\s*\[\d{1,4}\]\s*$")

ROMAN = {"I": 1, "II": 2, "III": 3}
PART_NAME = {1: "Part-I State Scheme",
             2: "Part-II Central Scheme (sharing basis)",
             3: "Part-III Centrally Sponsored Scheme (100%)"}


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


def rupees(s):
    """A full-rupee figure in Indian digit grouping, or None."""
    s = s.strip()
    if not re.fullmatch(r"[\d,]*\d", s):
        return None
    return float(s.replace(",", ""))


def cells(line, start, ends):
    """{column: value or None} for one table row, assigned by position.

    Each figure goes to the header word whose end is nearest its own end, because the
    figures are right-aligned under their headings. Counting from the right instead works
    for 956 of 970 rows and silently shifts the money one column left on the other 14,
    which are the rows that leave Establishment and Works blank rather than printing `...`.
    """
    out = {}
    for m in CELL.finditer(line, start):
        j = min(range(len(ends)), key=lambda k: abs(ends[k] - m.end()))
        out[COLUMNS[j]] = None if m.group(0).startswith("..") else \
            round(float(m.group(0).replace(",", "")), 2)
    return out


class Scheme:
    __slots__ = ("code", "name", "department", "part", "page", "figs",
                 "outlay_rupees", "purpose")

    def __init__(self, code, name, department, part, page, figs):
        self.code, self.name, self.department = code, name, department
        self.part, self.page, self.figs = part, page, figs
        self.outlay_rupees = self.purpose = None

    def add_name(self, more):
        self.name = (self.name + " " + more).strip() if self.name else more


FAR = 10 ** 6


def _clusters(lines, tol=5):
    """The character positions where this page's figure columns end."""
    ends = []
    for l in lines:
        m = TABLE_CODE.match(l) or PART_TOTAL.match(l)
        if m:
            ends += [c.end() for c in CELL.finditer(l, m.end())]
    ends.sort()
    out = []
    for e in ends:
        if out and e - out[-1][-1] <= tol:
            out[-1].append(e)
        else:
            out.append([e])
    return [sum(g) / len(g) for g in out]


def _continuation_columns(lines, header_ends):
    """Where the five columns are on a page that printed no header of its own.

    A continuation page is not typeset at the same character positions as the page before
    it, and it is not shifted by a constant either: page 112's five columns sit 8, 8, 13,
    10 and 15 characters right of page 111's, so no single offset puts them all back.

    So the page's own figures are clustered by where they end, and the clusters are matched
    to the five named columns in order, with the assignment chosen by the book's own
    arithmetic: whichever mapping makes the most rows satisfy Total = Central + State
    wins, ties going to the mapping closest to the last printed header. A column with no
    cluster is placed out of reach so no figure can land in it. A wrong mapping breaks the
    identity on nearly every row, which is what makes the choice safe rather than a guess.
    """
    cl = _clusters(lines)
    if not cl:
        return list(header_ends)
    if len(cl) > len(COLUMNS):
        # More clusters than columns means the page is not the table this parser knows.
        # Fall back to the header and let the reconciliation report the damage.
        return list(header_ends)
    rows = [l for l in lines if TABLE_CODE.match(l)]
    best, best_key = list(header_ends), None
    for combo in itertools.combinations(range(len(COLUMNS)), len(cl)):
        ends = [FAR] * len(COLUMNS)
        for slot, centre in zip(combo, cl):
            ends[slot] = centre
        score = 0
        for l in rows:
            m = TABLE_CODE.match(l)
            v = cells(l, m.end(), ends)
            t = v.get("total")
            if t is not None and abs((v.get("central") or 0.0) +
                                     (v.get("state") or 0.0) - t) <= 0.011:
                score += 1
        near = sum(abs(ends[i] - header_ends[i]) for i in combo)
        key = (-score, near, combo)
        if best_key is None or key < best_key:
            best, best_key = ends, key
    return best


def read_tables(pages):
    """Every scheme row and every printed Part total in the scheme tables.

    Returns (schemes, part_totals, table_pages, banners, departments).
    """
    schemes, part_totals, table_pages, banners = [], [], 0, {}
    ends, department, part, current = None, None, None, None
    header_ends = None

    for pi, page in enumerate(pages):
        lines = page.split("\n")
        head = "\n".join(lines[:14])
        squeezed = head.replace(" ", "")
        banner = LIST_BANNER.search(squeezed)
        hi = next((i for i, l in enumerate(lines[:14]) if TABLE_HEADER.search(l)), None)

        if banner and hi is not None:
            if not LAKH_UNIT.search(head):
                # A page that calls itself a list of schemes and does not print the lakh
                # unit is not one. Page 110 does exactly this over a table of major heads
                # in full rupees.
                continue
            table_pages += 1
            banners[banner.group(1)] = banners.get(banner.group(1), 0) + 1
            ends = [m.end() for m in COLUMN_WORD.finditer(lines[hi])]
            header_ends = list(ends)
            # The department is printed on the line above the banner.
            was = department
            for l in reversed(lines[:hi]):
                if l.strip() and not PAGE_MARK.match(l) and "LIST" not in l \
                        and "₹" not in l:
                    department = re.sub(r"\s+", " ", l).strip()
                    break
            current = None
            # The Part is reset only when the department changes, never merely because a
            # new page began. Haryana repeats the column header on every page of a long
            # table but prints "Part-I State Scheme" only once, so resetting per page left
            # every row after the first page of Crop Husbandry with no Part and lost
            # 82,000 lakh from its printed Part-I total.
            if department != was:
                part = None
        elif ends is not None and any(TABLE_CODE.match(l) for l in lines):
            # A continuation page. Haryana prints no header on it and no banner either;
            # page 112 carries seven scheme rows this way. The columns of the last header
            # still apply, shifted by however much this page's name column has moved:
            # page 112 indents its names two characters further right than page 111, which
            # was enough to read State as Establishment and lose three Totals entirely.
            table_pages += 1
            ends = _continuation_columns(lines, header_ends)
            current = None
        else:
            continue

        for line in lines:
            m = PART.match(line)
            if m and not PART_TOTAL.match(line):
                part, current = ROMAN[m.group(1)], None
                continue
            mt = PART_TOTAL.match(line)
            if mt:
                part_totals.append({
                    "department": department, "part": ROMAN[mt.group(1)],
                    "page": pi, "figs": cells(line, mt.end(), ends)})
                current = None
                continue
            mc = TABLE_CODE.match(line)
            if mc:
                figs = cells(line, mc.end(), ends)
                # The name runs from the end of the code to the first figure on the line.
                first = CELL.search(line, mc.end())
                name = line[mc.end():first.start() if first else len(line)].strip()
                current = Scheme(mc.group(1), name, department, part, pi, figs)
                schemes.append(current)
                continue
            if current is not None and line.strip() and not CELL.search(line) \
                    and not PAGE_MARK.match(line):
                # A wrapped name. It carries no figure of its own and is indented into the
                # name column; anything with a figure on it has already been handled.
                current.add_name(re.sub(r"\s+", " ", line).strip())
            elif not line.strip():
                current = None
    return schemes, part_totals, table_pages, banners, department


def deptkey(s):
    """A department name reduced to what both halves of the book agree on.

    The Summary page writes "Community Development & Panchayats" and the scheme table
    writes "Community Development &Panchayats"; other pairs differ by a hyphen or a
    trailing bracket. Comparing the printed strings left 78 of 192 Part totals with no
    Summary to check the unit against, which is most of the check.
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def read_summaries(pages):
    """{(department key, part): rupees} from the per-department Summary of Budget
    Estimate."""
    out, department = {}, None
    for pi, page in enumerate(pages):
        lines = page.split("\n")
        head = "\n".join(lines[:14])
        # A summary page is recognised by its UNIT and its columns, not by its banner.
        # Page 110 is the Community Development & Panchayats summary and is headed
        # "LIST OF SCHEMES BUDGET ESTIMATE 2026-27" over a table of major heads in rupees,
        # so a banner test skips exactly the one department whose scheme table is headed
        # with last year's cycle and most needs an independent check.
        if not RUPEE_UNIT.search(head):
            continue
        if "Major Head" not in head or "Gross Amount" not in head:
            continue
        for i, l in enumerate(lines[:14]):
            if "Major Head" in l:
                for prev in reversed(lines[:i]):
                    t = prev.strip()
                    if not t or PAGE_MARK.match(prev) or "₹" in t or \
                            "Summary of Budget" in t or "LIST" in t.upper():
                        continue
                    department = re.sub(r"\s+", " ", t)
                    break
                break
        for l in lines:
            mt = PART_TOTAL.match(l)
            if not mt:
                continue
            # Gross, Recoveries, Net. The Net column is the last figure on the line and is
            # what the scheme table's Total column adds up to.
            nums = [rupees(x) for x in re.findall(r"[\d,]*\d", l[mt.end():])]
            nums = [n for n in nums if n is not None]
            if nums:
                out[(deptkey(department), ROMAN[mt.group(1)])] = nums[-1]
    return out


def read_narratives(pages):
    """{narrative code: {"name":.., "outlay_rupees":.., "purpose":..}}."""
    out = {}
    for page in pages:
        lines = page.split("\n")
        i = 0
        while i < len(lines):
            m = N_CODE.match(lines[i])
            if not m:
                i += 1
                continue
            code, name, outlay, body = m.group(1), None, None, []
            i += 1
            while i < len(lines):
                l = lines[i]
                if N_CODE.match(l) or N_ITEM.match(l):
                    break
                mn = N_NAME.match(l)
                if mn and name is None:
                    name = mn.group(1).strip()
                    i += 1
                    # The name wraps into the same column with no label of its own.
                    while i < len(lines) and lines[i].strip() and \
                            not N_OUTLAY.match(lines[i]) and not N_CODE.match(lines[i]):
                        name += " " + re.sub(r"\s+", " ", lines[i]).strip()
                        i += 1
                    continue
                mo = N_OUTLAY.match(l)
                if mo and outlay is None:
                    outlay = (mo.group(1) or "").strip()
                    i += 1
                    continue
                if l.strip() and not PAGE_MARK.match(l):
                    body.append(re.sub(r"\s+", " ", l).strip())
                i += 1
            # `30,00,000/- with a backtick for the rupee sign, which is what the
            # Rupeeforadian font in this book renders as.
            rup = None
            if outlay:
                mr = re.search(r"([\d,]*\d)", outlay)
                if mr:
                    rup = rupees(mr.group(1))
            purpose = " ".join(body).strip()
            if code not in out:
                out[code] = {"name": re.sub(r"\s+", " ", name).strip() if name else None,
                             "outlay_rupees": rup,
                             "purpose": purpose or None}
    return out


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "haryana", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive/haryana snapshot; run collect/haryana.py first")
    date = date or dates[-1]
    man = read_json(f"archive/haryana/{date}/_manifest.json", {}) or {}

    path = os.path.join(ROOT, "archive", "haryana", date, "plan-memo.pdf.gz")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    with gzip.open(path, "rb") as fh:
        pages = pdftotext(fh.read()).split("\f")

    schemes, part_totals, table_pages, banners, _ = read_tables(pages)
    summaries = read_summaries(pages)
    narratives = read_narratives(pages)

    if CYCLE_WANTED not in banners:
        raise SystemExit(f"haryana: no scheme table headed {CYCLE_WANTED}; "
                         f"the banners read are {banners}")

    # ------------------------------------------------------- check 1, row arithmetic
    row_fail = []
    for s in schemes:
        c, st, t = (s.figs.get("central"), s.figs.get("state"), s.figs.get("total"))
        if t is None:
            row_fail.append({"code": s.code, "page": s.page, "why": "no Total printed",
                             "figs": s.figs})
            continue
        if abs((c or 0.0) + (st or 0.0) - t) > 0.011:
            row_fail.append({"code": s.code, "page": s.page,
                             "why": "Total is not Central + State", "figs": s.figs})

    # --------------------------------------------- check 2, the printed Part totals
    by_part = {}
    for s in schemes:
        by_part.setdefault((s.department, s.part), []).append(s)
    part_checks = []
    for pt in part_totals:
        key = (pt["department"], pt["part"])
        rows = by_part.get(key, [])
        got = {c: round(sum(s.figs.get(c) or 0.0 for s in rows), 2) for c in COLUMNS}
        printed = {c: pt["figs"].get(c) for c in COLUMNS}
        ok = all(abs((printed[c] or 0.0) - got[c]) <= 0.05 for c in COLUMNS)
        part_checks.append({"department": pt["department"], "part": pt["part"],
                            "page": pt["page"], "rows": len(rows),
                            "printed": printed, "computed": got, "ok": ok})

    # ------------------------------------------------------------ check 3, the units
    unit_checks = []
    for pt in part_totals:
        rup = summaries.get((deptkey(pt["department"]), pt["part"]))
        if rup is None:
            unit_checks.append({"department": pt["department"], "part": pt["part"],
                                "ok": None, "why": "no Summary line for this part"})
            continue
        lakh = pt["figs"].get("total") or 0.0
        # A lakh is 100,000 rupees. If the scheme table had been read as rupees, or the
        # summary as lakh, this would be out by that factor and could not pass.
        # The scheme table rounds to two decimals of a lakh, which is the nearest 100
        # rupees, so the two can differ by up to 500 rupees without either being wrong:
        # Haryana Vidhan Sabha Part-II is 1,70,70,678 rupees in the Summary and 170.71
        # lakh in the table. A factor-of-100,000 mistake is five orders of magnitude
        # larger than this tolerance and cannot hide behind it.
        ok = abs(lakh * 100000.0 - rup) <= 500.5
        unit_checks.append({"department": pt["department"], "part": pt["part"],
                            "summary_rupees": rup, "table_lakh": lakh,
                            "table_lakh_as_rupees": round(lakh * 100000.0, 2),
                            "ok": ok})

    # ------------------------------------------------------------------- the entries
    joined, out = 0, []
    for s in sorted(schemes, key=lambda x: (x.code, x.page)):
        # The narrative half prints the same code without its "P-0" prefix.
        nkey = s.code[3:] if s.code.startswith("P-0") else None
        n = narratives.get(nkey) if nkey else None
        if n:
            joined += 1
        out.append({
            "code": s.code,
            "narrative_code": nkey,
            "name": re.sub(r"\s+", " ", s.name).strip(),
            "name_in_the_narrative": (n or {}).get("name"),
            "department": s.department,
            "part": PART_NAME.get(s.part),
            "purpose": (n or {}).get("purpose"),
            "outlay_rupees": (n or {}).get("outlay_rupees"),
            "central_share_lakh": s.figs.get("central"),
            "state_share_lakh": s.figs.get("state"),
            "be_lakh": s.figs.get("total"),
            "establishment_lakh": s.figs.get("establishment"),
            "works_lakh": s.figs.get("works"),
            "page": s.page,
        })

    failed_parts = [c for c in part_checks if not c["ok"]]
    failed_units = [c for c in unit_checks if c["ok"] is False]
    dup = len(out) - len({e["code"] for e in out})

    write_json("data/haryana/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Haryana",
        "cycle": CYCLE_WANTED,
        "source": ("Haryana Budget 2026-27, Explanatory Memorandum on Welfare & "
                   "Development Schemes (Plan Memo)"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "be_lakh, central_share_lakh, state_share_lakh, establishment_lakh and "
            "works_lakh are rupees in LAKH, read from the `(₹ In Lakhs)` header the "
            "scheme tables print and never assumed: this book also prints full rupees to "
            "eleven digits in its per-department Summary and again on every narrative "
            "`Outlay` line, and one page prints the words LIST OF SCHEMES over a table in "
            "rupees. outlay_rupees is that narrative figure and is left in RUPEES on "
            "purpose, so the two can be compared without a conversion hiding a mistake. "
            "The scale is checked, not asserted: each department's Summary total in "
            "rupees is compared with its scheme table's total in lakh times 100,000."),
        "variant": "Budget Estimate 2026-27",
        "variant_note": (
            "Haryana publishes one Plan Memo per cycle with no original/revised split, so "
            "there is no variant to choose. Two of its 96 scheme-table pages are headed "
            "LISTOFSCHEMESBUDGETESTIMATE2025-26, spaces and all missing, for Community "
            "Development & Panchayats. Those figures are 2026-27: that department's table "
            "totals equal its own 2026-27 rupee Summary to the rupee, which is the units "
            "check. The stale heading is recorded in banners_read."),
        "banners_read": banners,
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "distinct_codes": len({e["code"] for e in out}),
            "duplicate_code_rows": dup,
            "table_pages_read": table_pages,
            "departments": len({e["department"] for e in out if e["department"]}),
            "with_a_purpose_paragraph": sum(1 for e in out if e["purpose"]),
            "narrative_entries_read": len(narratives),
            "narrative_entries_joined": joined,
            "with_a_positive_be": sum(1 for e in out if (e["be_lakh"] or 0) > 0),
            "part_i_state": sum(1 for e in out if e["part"] == PART_NAME[1]),
            "part_ii_shared": sum(1 for e in out if e["part"] == PART_NAME[2]),
            "part_iii_central": sum(1 for e in out if e["part"] == PART_NAME[3]),
        },
        "reconciliation": {
            "row_arithmetic": {
                "checked": len(schemes), "failed": len(row_fail),
                "failures": row_fail[:20] or None,
                "what": "Total = Central Share + State Share on every scheme row"},
            "part_totals": {
                "checked": len(part_checks), "failed": len(failed_parts),
                "failures": failed_parts[:20] or None,
                "what": ("every printed Total Part-I, Total Part-II and Total Part-III "
                         "against the scheme rows read under it, in all five money "
                         "columns")},
            "units": {
                "checked": sum(1 for c in unit_checks if c["ok"] is not None),
                "failed": len(failed_units),
                "not_checkable": sum(1 for c in unit_checks if c["ok"] is None),
                "failures": failed_units[:20] or None,
                "what": ("each department's Summary of Budget Estimate total, printed in "
                         "full rupees, against the same total from the scheme table in "
                         "lakh multiplied by 100,000. This is the check that would catch "
                         "a unit read wrongly anywhere in the book")},
        },
        # The join against myScheme, run once by hand on the 2026-09-03 snapshot and all
        # 60 joins read line by line. Recorded here rather than recomputed on every run
        # because the classification is a human reading, not a rule. parse/match.py is NOT
        # edited to fix anything found; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_haryana_records": 249,
            "register_names": 970,
            "joins_produced": 60,
            "joins_sound_on_inspection": 28,
            "joins_wrong_on_inspection": 32,
            "myscheme_records_with_any_join": 53,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read by "
                    "eye"),
            "read_this_carefully": (
                "This is the state the whole exercise was picked to test. myScheme claims "
                "249 Haryana schemes against DBT Bharat's 171, one of only three states "
                "where the portal claims more than DBT counts, so the question was "
                "whether the portal is ahead of the state's own books. It is not. The "
                "Plan Memo names 970 schemes with codes and 824 with a paragraph of "
                "purpose, and a generous matcher finds only 53 of myScheme's 249 in it. "
                "Read the 32 wrong joins before reading anything into that 53: 18 of them "
                "are a single budget line for PMMSY matched to eighteen myScheme records "
                "that are components of it, which says myScheme's Haryana count is partly "
                "made of sub-schemes a budget states once."),
        },
        "myscheme_join_defects": [
            {"defect": ("A SCHEME BRAND SHARED BY MANY myScheme SUB-SCHEMES AND ONE "
                        "BUDGET LINE. myScheme lists eighteen PMMSY components for "
                        "Haryana, each named 'PMMSY: <component>'; the Plan Memo states "
                        "the whole programme once. Every one of the eighteen matches on "
                        "the written acronym, so one budget row absorbs eighteen "
                        "records"),
             "reason_string": "acronym match: pmmsy",
             "joins": 18,
             "example_myscheme": "PMMSY: Construction of New Grow Out Ponds - Haryana",
             "example_budget": ("Development of Fresh Water Aquaculture Renamed as "
                                "Pradhan Mantri Matsya Sampada Yojana"),
             "note": ("not wrong in direction, since every one of them IS funded from that "
                      "line, and useless for attribution, because the money cannot be "
                      "split eighteen ways by anything in either document.")},
            {"defect": ("a FUNDING CHANNEL read as a scheme. NSKFDC is the National Safai "
                        "Karamcharis Finance and Development Corporation, which lends to "
                        "five different myScheme schemes; the budget names it once"),
             "reason_string": "acronym match: nskfdc",
             "joins": 5,
             "example_myscheme": "Mahila Samridhi Yojana under NSKFDC- Haryana",
             "example_budget": ("Provision of Subsidy under National Safai Karmacharis "
                                "Finance Development Corporation")},
            {"defect": ("A COMMUNITY BUDGET CUT READ AS AN ACRONYM. SCSP is the Scheduled "
                        "Caste Sub Plan, a cut of a budget and never a scheme. Haryana "
                        "writes it in capitals at the end of a row name, so it is a "
                        "WRITTEN acronym; the myScheme side DERIVES an initialism from a "
                        "long name and that initialism contains it"),
             "reason_string": "acronym containment: csscsphe / scsp",
             "joins": 4,
             "example_myscheme": ("Consolidated Stipend Scheme for Scheduled Caste "
                                  "Students Pursuing Higher Education"),
             "example_budget": ("National Livestock Mission Breed Development of "
                                "Livestock & Poultry SCSP"),
             "note": ("NOT_ACRONYMS already holds sc, st, obc and vjnt because a "
                      "community is who a scheme is for and never which scheme it is. "
                      "scsp and tsp are the same axis written as a plan name and are not "
                      "on the list. Four joins here, two from csscsphe and two from "
                      "fbscsphe.")},
            {"defect": ("a DERIVED initialism equal to another DERIVED initialism, on two "
                        "names that differ in one word. Disabled and Destitute are "
                        "different children"),
             "reason_string": "acronym match: fatdc",
             "joins": 1,
             "example_myscheme": "Financial Assistance To Disabled Children (HBOCWWB)",
             "example_budget": "Financial Assistance to Destitute Children"},
            {"defect": ("a NATIONAL HONOUR read as a coined acronym. Padma is the award; "
                        "PADMA is Haryana's Programme to Accelerate Development for MSME "
                        "Advancement"),
             "reason_string": "acronym match: padma",
             "joins": 1,
             "example_myscheme": "Haryana Gaurav Samman Scheme for Padma Awardees",
             "example_budget": ("Programme to Accelerate Development for MSME Advancement "
                                "(PADMA)")},
            {"defect": ("containment on a brand shared by two sibling schemes. Haryana "
                        "runs IT Saksham Yuva and Contractor Saksham Yuva as separate "
                        "provisions and myScheme lists a bare Saksham Yuva Scheme as "
                        "well; the two content words of the shorter name sit inside the "
                        "longer"),
             "reason_string": "all 2 content words of the shorter name are present",
             "joins": 2,
             "example_myscheme": "IT Saksham Yuva Scheme",
             "example_budget": "Contractor Saksham Yuva Scheme"},
            {"defect": ("containment on a parent brand. Mukhyamantri Vivah Shagun Yojana "
                        "is the general marriage grant and Mukhyamantri Samajik Samrasta "
                        "Antarjatiya Vivah Shagun Yojana is the inter-caste one; the "
                        "budget states both and the shorter absorbed the longer"),
             "reason_string": "all 3 content words of the shorter name are present",
             "joins": 1,
             "example_myscheme": ("Mukhyamantri Samajik Samrasta Antarjatiya Vivah Shagun "
                                  "Yojana"),
             "example_budget": "Mukhyamantri Vivah Shagun Yojana--NA-",
             "note": ("the same record also joins correctly to its own name elsewhere in "
                      "the book, at similarity 0.99, so the right answer was available "
                      "and the wrong one was taken alongside it.")},
        ],
        "caveat": (
            "One row here is one line of Haryana's Plan Memo, keyed on the state's own "
            "scheme code. The book is a register of WELFARE AND DEVELOPMENT schemes and "
            "not of the whole budget, so establishment and pension heads are largely "
            "absent, which makes this a cleaner scheme list than most states publish and "
            "a smaller one than their total expenditure. purpose is Haryana's own "
            "description of the scheme, taken verbatim from the narrative half of the "
            "same book; it is present for most schemes and null for the rest."),
        "entries": out,
    })
    return out, row_fail, part_checks, failed_parts, unit_checks, failed_units, \
        banners, table_pages, joined, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Haryana Plan Memo.")
    ap.add_argument("--date")
    a = ap.parse_args()
    (out, row_fail, part_checks, failed_parts, unit_checks, failed_units,
     banners, table_pages, joined, date) = run(a.date)
    print(f"haryana snapshot {date}")
    print(f"  {table_pages} scheme-table pages, {len(out)} scheme rows, "
          f"{len({e['code'] for e in out})} distinct codes")
    print(f"     with a narrative entry   {joined:>6}, of which with a purpose "
          f"paragraph {sum(1 for e in out if e['purpose']):>6}")
    print(f"     sum of 2026-27 provisions "
          f"{sum(e['be_lakh'] or 0 for e in out):>18,.2f} lakh")
    print(f"  row arithmetic  {len(out) - len(row_fail):>6} of {len(out):<6} pass")
    print(f"  part totals     {len(part_checks) - len(failed_parts):>6} of "
          f"{len(part_checks):<6} reconcile")
    ck = sum(1 for c in unit_checks if c["ok"] is not None)
    print(f"  units check     {ck - len(failed_units):>6} of {ck:<6} agree "
          f"({sum(1 for c in unit_checks if c['ok'] is None)} with no Summary line)")
    print(f"  table banners   {banners}")
    for f in (row_fail + failed_parts + failed_units)[:10]:
        print("     MISMATCH", json.dumps(f)[:240])
    if row_fail or failed_parts or failed_units:
        print("  ERROR: the Plan Memo does not reconcile against its own printed totals")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
