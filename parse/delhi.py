"""
Parse the archived Delhi Scheme-wise Budget into data/delhi/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY DELHI YIELDS. `SCHEME/PROGRAMME/PROJECTS WISE OUTLAY 2026-27` is plain English with
no second script anywhere in it, and its scheme name has its own column. That alone
passes the test in docs/state-sources.md. What makes it parseable rather than merely
readable is a strip of column numbers printed under the header of all 131 table pages:

    1              2              3    4      5      6    7  ...  13     14      15

Those fifteen markers are the only reliable geometry in the document. `pdftotext -bbox`
and `-bbox-layout` both CRASH on this file (poppler 25.x, `std::out_of_range` in
basic_string, zero words returned), so the real x of a word is not available and the
character columns of `-layout` are all there is. The markers move by up to five
characters between pages, so they are read per page and never assumed.

HOW A ROW IS PUT BACK TOGETHER. One logical row is spread over up to three printed lines,
and the money is not on the line with the name:

    b        Assistance to States for Control of Animal Diseases        150.00   150.00
                              9.05      9.05   30.00   30.00  25.00   25.00
             (Animal Disease Control) CSS

The 2026-27 columns (13 to 15) sit on the first line, the twelve older columns on the
second, and the rest of the name on the third. So the parser accumulates: a line with a
serial number in the first eight characters opens a row, and every following line adds
its name text and its figures to that row until the next serial arrives.

The serial is taken by character position and not by splitting on whitespace, because 46
of them carry an internal space: "10 a", "13 (a)", "42. a", "4.3.1 b". Split on the first
gap, "34 a   Sakhi Niwas-Mission Shakti CSS" becomes serial 34 and scheme "a Sakhi
Niwas".

THE ONE RULE THAT COST THE MOST TO GET RIGHT. A line with no serial number, sitting in the
name column, is a continuation of the row above it EXCEPT when a blank line separates
them, in which case it is a heading:

              TOURISM                <- sector
                                     <- blank
              Tourism Infrastructure <- heading, not the tail of the last Tourism scheme
                                     <- blank
    1         Other Tourism Infrastructure GIA-Capital

Without the blank-line rule `AGRICULTURE & ALLIED ACTIVITIES` is appended to the last
scheme of the previous sector, which is exactly the Karnataka "Helpers" failure. Measured
on the 2026-27 book: 1,156 name-column lines follow content and are continuations, and
134 follow a blank line and are headings. Read by eye, about ten of those 134 are really
nil-provision scheme rows (`Ground Water Recharge & Water Conservation`, `Tourism
Infrastructure development`) and are published here as headings rather than as schemes.
That direction is deliberate: this register's claim is that a state funds something
myScheme does not list, and dropping a row can only weaken that claim, never invent one.

UNITS. One unit throughout, `(₹ in Lakh)`, printed in the header of every table page and
checked on every one of them. There is no second unit in this document, which makes it
the only book in this round where that is true.

RECONCILIATION, and this is the one place Delhi is weaker than the other states in the
register, because its book does not fully balance to itself.

  1. HARD. Every scheme row's own arithmetic: Total = Revenue + Capital/Loan, in all four
     year blocks. 1,577 of 1,578 pass; the one failure is a printed "Sub Total" on page 38
     where Delhi's own two columns add to 105,908.97 and its total says 105,844.11.
  2. REPORTED. Every printed total in the book, from "Sub Total" up to the Grand Total,
     against the longest run of items directly above it that adds up to it in all four
     year blocks at once. Delhi never says how deep a total reaches, so the depth is
     recovered arithmetically rather than read. 263 of 282 resolve.
  3. REPORTED. The Grand Total against every scheme row: 62,55,000.00 lakh printed against
     64,55,956.00 lakh summed, 3.2 per cent over.

The gap in 3 is partly identified and partly not, and saying so is the point. Delhi prints
`OAS(Other than Minorities)` directly under `TOTAL [OTHER ADMN. SERVICES]` as a
restatement of part of it, with no word in its name to mark it as a total, so it is read
as a scheme and its 1,14,031.00 lakh is counted twice. The rest of the gap sits in
Transport, General Education and Urban Development, where the book also prints
cross-cutting subtotals that no contiguous rule can capture: page 41 closes with a
"Sub -Total (GIA General to Degree College)" and a "Sub -Total (GIA Salary to Degree
College)" that each sum every OTHER row of an interleaved list.

So the money here is sound at the row level and approximate in aggregate, and the counts
are what this register actually uses.

Delhi's own file also carries three cells Excel could not render, printed as `####` and
`#VALUE!`, all on total lines, plus one figure clipped to `129` on page 66. Those are
recorded as unreadable and any check touching one says so, so a failure there reads as
the state's defect and not as this parser's.
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

# The column-number strip printed under every table header. The whole geometry of this
# parser hangs off it, so the match is anchored and exact: a page without it is not a
# table page and is skipped.
STRIP = re.compile(r"^\s*1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9\s+10\s+11\s+12\s+13\s+14\s+"
                   r"15\s*$")

BANNER = re.compile(r"SCHEME\s*/\s*PROGRAMME\s*/\s*PROJECTS\s+WISE\s+OUTLAY\s+"
                    r"(\d{4}-\d{2})")
UNIT = re.compile(r"\(\s*₹\s*in\s+Lakh\s*\)", re.I)

# One money cell. Every figure in this book is written this way; the only other tokens to
# the right of the name column are the R/C/L section flags and four broken cells.
MONEY = re.compile(r"[\d,]+\.\d{1,2}")
UNREADABLE = re.compile(r"#{3,}|#VALUE!|#REF!|#DIV/0!")

SNO_WIDTH = 8

# A printed total. The word is at the start of most of them and at the end of a few
# ("S.P.C.A.- Total"), so the test is for the word anywhere in the cell.
TOTAL_WORD = re.compile(r"\btotals?\b", re.I)
# A sector total names its own sector in brackets: "TOTAL [OTHER ADMN. SERVICES]".
SECTOR_TOTAL = re.compile(r"^\s*TOTAL\s*\[(.+?)\]\s*$", re.I)
GRAND_TOTAL = re.compile(r"^\s*Grand\s+Total\s*$", re.I)

BLOCKS = ("actual 2024-25", "be 2025-26", "mre 2025-26", "be 2026-27")

# The R/C/L section flag, which sits in column 3 and sometimes drifts left of where the
# column-number strip says column 3 begins, landing inside the name. Stripped from the end
# of a name, never from the middle: no Delhi scheme name ends in a bare capital R, C or L,
# and 40-odd of them were being published as "National Law University, Delhi GIA-Salary R".
TRAILING_FLAG = re.compile(r"\s+(?:R|C|L|R/C|R/L|C/L|C/R)$")


def pdftotext(pdf_bytes):
    """pdftotext -layout on raw bytes, via a temp file."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout


def markers(strip_line):
    """Centre of each of the fifteen column-number markers, in characters."""
    return [(m.start() + m.end()) / 2.0 for m in re.finditer(r"\d+", strip_line)]


def cells(text, mk, offset):
    """{column number: value} for the figures in one line's figure region.

    `offset` is where that region starts in the full line. The marker positions are
    absolute page columns, so a figure's position has to be made absolute too before it
    is compared with them; measuring it inside the slice put every figure in column 4 and
    left the 2026-27 block empty.
    """
    out = {}
    for m in MONEY.finditer(text):
        centre = offset + (m.start() + m.end()) / 2.0
        # Nearest marker among columns 4 to 15. Columns 1 to 3 are the serial, the name
        # and the R/C/L flag and never hold a figure.
        col = min(range(3, 15), key=lambda k: abs(mk[k] - centre)) + 1
        out[col] = round(float(m.group(0).replace(",", "")), 2)
    return out


class Row:
    __slots__ = ("sno", "name", "figs", "page", "unreadable", "sector", "group")

    def __init__(self, sno, name, page):
        self.sno, self.name, self.page = sno, name, page
        self.figs, self.unreadable = {}, False
        self.sector = self.group = None

    def add_name(self, more):
        # A wrapped name has its own spacing already; joining with a single space is what
        # the document means. "Improvement of Veterinary Services and Control of" +
        # "Contagious Diseases".
        self.name = (self.name + " " + more).strip() if self.name else more

    def add_figs(self, d):
        for k, v in d.items():
            # A repeated column on a later line of the same row would mean the row was
            # split wrongly. Keep the first; the arithmetic check is what catches a bad
            # split, and it would be hidden by overwriting.
            self.figs.setdefault(k, v)

    def block(self, i):
        """(revenue, capital_or_loan, total) for year block i in 0..3."""
        base = 4 + 3 * i
        return (self.figs.get(base), self.figs.get(base + 1), self.figs.get(base + 2))

    def total(self, i):
        rev, cap, tot = self.block(i)
        if tot is not None:
            return tot
        if rev is None and cap is None:
            return None
        return round((rev or 0.0) + (cap or 0.0), 2)


def read_book(text):
    """Walk the book once, in document order.

    Returns (sequence, headings, pages_read, cycles, unit_pages) where sequence is a list
    of ("row"|"total", Row) exactly as printed. One walk, because the reconciliation needs
    the rows and the totals interleaved and a second walk would be a second chance to
    disagree with the first.
    """
    seq, headings = [], []
    cycles, unit_pages, pages_read = set(), 0, 0

    for pi, page in enumerate(text.split("\f")):
        lines = page.split("\n")
        strip_at = next((i for i, l in enumerate(lines) if STRIP.match(l)), None)
        if strip_at is None:
            continue
        pages_read += 1
        head = "\n".join(lines[:strip_at])
        m = BANNER.search(head)
        if m:
            cycles.add(m.group(1))
        if UNIT.search(head):
            unit_pages += 1

        mk = markers(lines[strip_at])
        # The R/C/L flag column is marker 3; the name ends two characters short of it.
        cut = max(SNO_WIDTH + 1, int(mk[2]) - 2)

        current, prev_blank = None, True
        for line in lines[strip_at + 1:]:
            if not line.strip():
                prev_blank = True
                continue
            sno = line[:SNO_WIDTH].strip()
            name = line[SNO_WIDTH:cut].strip()
            figs = cells(line[cut:], mk, cut)
            bad = bool(UNREADABLE.search(line[cut:]))

            if sno:
                current = Row(sno, name, pi)
                seq.append(("total" if TOTAL_WORD.search(name) else "row", current))
            elif name and TOTAL_WORD.search(name):
                # A printed total, and this test comes BEFORE the continuation rule
                # rather than after it. Delhi prints most of its totals with no serial and
                # no blank line above them, so the continuation rule reached them first
                # and glued them onto the last scheme: "Delhi Energy Conservation Fund
                # Total [Power Deptt.]" and "Rajiv Gandhi Swavlamban Rozgar Yojana Total"
                # were published as scheme names, each carrying its department's whole
                # provision.
                current = Row(None, name, pi)
                seq.append(("total", current))
            elif name and figs:
                # A scheme row whose serial the document omits, and it carries money on
                # its own line, so it is a row and not a tail. Delhi drops the serial for
                # every sub-row of a group: pages 37 and 38 print one serial for
                # "PM SHRI (Elementary) SS GIA-General" and none for the eleven SC, ST and
                # Capital rows under it. Read as continuations they were glued into one
                # scheme and eleven provisions were lost, which is what the printed
                # "Sub Total - PM SHRI CSS" caught.
                #
                # The discriminator is the figure. Every row in this book prints its
                # 2026-27 columns on the same line as its name and its older columns on
                # the line below, so a name line with a figure on it is a row and a name
                # line without one is a tail.
                current = Row(None, name, pi)
                seq.append(("row", current))
            elif name and prev_blank:
                # No serial, no money and a blank line above: a heading, not a tail. See
                # the module docstring.
                headings.append({"page": pi, "text": name})
                current = None
            elif current is not None:
                current.add_name(name)

            if current is not None:
                current.add_figs(figs)
                current.unreadable = current.unreadable or bad
            prev_blank = False
    return seq, headings, pages_read, cycles, unit_pages


class Node:
    """One item on the reconciliation stack: a scheme row, or a total and what it covers."""

    __slots__ = ("row", "vec", "children")

    def __init__(self, row, children=()):
        self.row = row
        self.children = list(children)
        self.vec = [row.total(i) or 0.0 for i in range(4)]


def _close(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def reconcile(seq, tol=0.05):
    """Resolve every printed total against the items directly beneath it.

    Delhi's totals NEST and the document never says how deep. Rows are closed by a
    "Sub Total", several Sub Totals by a "Total [Department]", several of those by a
    "TOTAL [SECTOR]", and everything by a "Grand Total"; and the labels do not say which
    is which, because "Total (ENERGY)" and "Total [Power Deptt.]" are printed alike. So
    the depth is recovered arithmetically instead of being read: a total consumes the
    LONGEST run of items immediately above it whose figures add up to its own, in all four
    year blocks at once.

    Longest rather than shortest, so that the nil-provision rows a department prints
    between two funded ones are absorbed rather than left stranded under the next total.
    Requiring all four blocks to agree is what makes the search safe: a single column can
    be matched by coincidence, four cannot.

    Returns (checks, root_items). A total that matches nothing is reported and then
    treated as covering everything still open, so the failure is contained and the rest of
    the book still reconciles.
    """
    stack, checks, ok_by_id = [], [], {}
    for kind, r in seq:
        if kind == "row":
            stack.append(Node(r))
            continue
        want = [r.total(i) or 0.0 for i in range(4)]
        # A total of nothing covers nothing. Delhi prints a few empty "Sub-Total" lines
        # under a group whose every scheme is nil, and with a minimum run of one item they
        # stole the funded row above them and cascaded a failure into every total after.
        hit = 0 if _close(want, [0.0] * 4, tol) else None
        # Walk suffixes from the longest down, so the first match found is the longest.
        for k in range(len(stack), 0, -1):
            got = [round(sum(n.vec[i] for n in stack[-k:]), 2) for i in range(4)]
            if _close(want, got, tol):
                hit = k
                break
        node = Node(r, stack[-hit:] if hit else [])
        matched = hit is not None
        checks.append({
            "label": r.name[:90], "page": r.page,
            "printed": [round(v, 2) for v in want],
            "items_covered": hit,
            "computed": ([round(sum(n.vec[i] for n in node.children), 2)
                          for i in range(4)] if node.children else [0.0] * 4),
            "ok": matched,
            "cell_unreadable_in_the_pdf": r.unreadable})
        ok_by_id[id(r)] = matched
        if matched:
            if hit:
                del stack[-hit:]
        else:
            # Nothing beneath it adds up. Take everything open so the next total is not
            # judged on this one's leftovers, and let the check above carry the failure.
            node.children = stack[:]
            stack.clear()
        # A total's own figures, not its children's, go back on the stack: that is what a
        # parent total will be compared against, and it is the state's own arithmetic that
        # is being tested.
        node.vec = [round(v, 2) for v in want]
        stack.append(node)
    return checks, stack, ok_by_id


def label_rows(roots, ok_by_id):
    """Give every scheme row the printed totals that cover it.

    The tree reconcile() builds is the hierarchy Delhi does not label, so it is also the
    only source for a row's department and sector. `group` is the innermost printed total
    directly above a row. `sector` is the outermost, and it is filled in ONLY when every
    total between the row and it reconciled: a total that did not reconcile was made to
    swallow everything still open, so its label says nothing about what is under it and
    publishing it as a sector would be a guess dressed as a fact.
    """
    def walk(node, chain, clean):
        label = re.sub(r"\s+", " ", node.row.name).strip()
        clean = clean and ok_by_id.get(id(node.row), False)
        chain = chain if GRAND_TOTAL.match(label) else chain + [label]
        for child in node.children:
            if child.children:
                walk(child, chain, clean)
            elif chain:
                child.row.group = chain[-1]
                child.row.sector = chain[0] if clean else None

    for node in roots:
        if node.children:
            walk(node, [], True)


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "delhi", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive/delhi snapshot; run collect/delhi.py first")
    date = date or dates[-1]
    man = read_json(f"archive/delhi/{date}/_manifest.json", {}) or {}

    path = os.path.join(ROOT, "archive", "delhi", date, "scheme-wise.pdf.gz")
    if not os.path.exists(path):
        raise SystemExit(f"missing {path}")
    with gzip.open(path, "rb") as fh:
        text = pdftotext(fh.read())

    seq, headings, pages_read, cycles, unit_pages = read_book(text)
    rows = [r for k, r in seq if k == "row"]
    totals = [r for k, r in seq if k == "total"]

    # The cycle is read off the page banner and never off the filename: the served file is
    # scheme_wise_6.pdf and its PDF /Title says "Scheme Wise 2025-26", while all 131 of
    # its table pages are headed 2026-27.
    if cycles != {CYCLE_WANTED}:
        raise SystemExit(
            f"delhi: pages are headed {sorted(cycles)}, wanted only {CYCLE_WANTED}")
    if unit_pages != pages_read:
        raise SystemExit(
            f"delhi: {pages_read - unit_pages} of {pages_read} table pages do not print "
            "'(₹ in Lakh)' in their header; the unit cannot be assumed")

    checks, roots, ok_by_id = reconcile(seq)
    label_rows(roots, ok_by_id)

    # ---------------------------------------------------------------- check 1, per row
    arithmetic = []
    for r in rows + totals:
        for i in range(4):
            rev, cap, tot = r.block(i)
            if tot is None or (rev is None and cap is None):
                continue
            want = round((rev or 0.0) + (cap or 0.0), 2)
            if abs(want - tot) > 0.011:
                arithmetic.append({
                    "page": r.page, "sno": r.sno, "name": r.name[:70],
                    "block": BLOCKS[i], "revenue": rev, "capital_or_loan": cap,
                    "printed_total": tot, "sum_of_the_two": want,
                    "cell_unreadable_in_the_pdf": r.unreadable})

    # ------------------------------------------------- check 2, the whole printed tree
    failed_totals = [c for c in checks if not c["ok"]]
    scheme_row_arithmetic = [f for f in arithmetic if f["sno"] is not None or
                             not TOTAL_WORD.search(f["name"])]
    # The LAST printed total in the book, which has to be the Grand Total and has to
    # cover everything left open. Taking the first match instead found the bare
    # "GRAND TOTAL" Delhi prints in the middle of General Education on page 43 and
    # reported the whole book as unreconciled.
    grand = checks[-1] if checks and GRAND_TOTAL.match(checks[-1]["label"].strip()) \
        else None

    # ------------------------------------------------------------------------- entries
    # Delhi prints no scheme code, so the key is the pair (sector, name), the choice
    # parse/andhra.py makes and for the same reason: "Improvement of Veterinary Services
    # and Control of Contagious Diseases" and its SCSP twin are two provisions under one
    # department, and collapsing every repeat would erase one of them.
    seen, out = {}, []
    for r in rows:
        name = TRAILING_FLAG.sub("", re.sub(r"\s+", " ", r.name).strip()).strip()
        if not name:
            continue
        key = f"{r.sector or 'unsectored'} | {r.group or ''} | {name}"
        e = seen.get(key)
        if e is None:
            e = seen[key] = {
                "key": key, "name": name, "sector": r.sector, "group": r.group,
                "snos": [], "pages": [], "rows_added": 0,
                "actual_2024_25_lakh": 0.0, "be_2025_26_lakh": 0.0,
                "mre_2025_26_lakh": 0.0, "be_lakh": 0.0,
                "be_revenue_lakh": 0.0, "be_capital_or_loan_lakh": 0.0}
            out.append(e)
        e["rows_added"] += 1
        if r.sno and r.sno not in e["snos"]:
            e["snos"].append(r.sno)
        if r.page not in e["pages"]:
            e["pages"].append(r.page)
        for i, k in enumerate(("actual_2024_25_lakh", "be_2025_26_lakh",
                               "mre_2025_26_lakh", "be_lakh")):
            e[k] = round(e[k] + (r.total(i) or 0.0), 2)
        rev, cap, _ = r.block(3)
        e["be_revenue_lakh"] = round(e["be_revenue_lakh"] + (rev or 0.0), 2)
        e["be_capital_or_loan_lakh"] = round(
            e["be_capital_or_loan_lakh"] + (cap or 0.0), 2)

    out.sort(key=lambda e: (e["sector"] or "~", e["group"] or "~", e["name"]))

    by_name = {}
    for e in out:
        by_name.setdefault(e["name"], set()).add(e["sector"])

    write_json("data/delhi/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Delhi",
        "cycle": CYCLE_WANTED,
        "source": ("Delhi Scheme-wise Budget 2026-27, SCHEME/PROGRAMME/PROJECTS WISE "
                   "OUTLAY, published by the Planning Department"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH, and the document prints only that one "
            "unit: '(₹ in Lakh)' appears in the header of all 131 table pages and this "
            "parser refuses a page that does not print it. Checked by hand against the "
            "book's own Grand Total for 2026-27, 62,55,000.00 lakh, which is Rs 62,550 "
            "crore, the size Delhi announced for its 2026-27 budget. be_lakh is the "
            "Budget Outlay 2026-27, the last of four year blocks; Actual 2024-25, Budget "
            "Outlay 2025-26 and Modified Revised Outlay 2025-26 are published beside it, "
            "each split into Revenue and Capital/Loan."),
        "variant": "Budget Outlay 2026-27",
        "variant_note": (
            "The served file is scheme_wise_6.pdf and its PDF /Title reads 'Scheme Wise "
            "2025-26 10.03.2026 1.58 PM.xlsx'. Every one of its table pages is headed "
            "SCHEME/PROGRAMME/PROJECTS WISE OUTLAY 2026-27 and its last column block is "
            "Budget Outlay 2026-27. The cycle is read from the page banner, and a book "
            "whose pages say anything else is a hard error, so a stale file cannot be "
            "published as a current one."),
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "table_pages_read": pages_read,
            "scheme_rows_read": len(rows),
            "printed_total_rows_read": len(totals),
            "headings_read": len(headings),
            "with_a_positive_be": sum(1 for e in out if e["be_lakh"] > 0),
            "funded_at_nil": sum(1 for e in out if e["be_lakh"] == 0),
            "rows_merged_into_an_earlier_row": sum(
                e["rows_added"] - 1 for e in out),
            "names_appearing_in_more_than_one_sector": sum(
                1 for v in by_name.values() if len(v) > 1),
            "sectors": len({e["sector"] for e in out if e["sector"]}),
        },
        "reconciliation": {
            "row_arithmetic": {
                "checked": (len(rows) + len(totals)) * 4,
                "failed": len(arithmetic),
                "failed_on_a_scheme_row": len(scheme_row_arithmetic),
                "failures": arithmetic[:20] or None,
                "what": ("Total = Revenue + Capital/Loan on every row and every printed "
                         "total, in all four year blocks")},
            "printed_totals": {
                "checked": len(checks), "failed": len(failed_totals),
                "failures": failed_totals[:20] or None,
                "checks": checks,
                "what": ("every printed total in the book, from 'Sub Total' up to the "
                         "Grand Total, against the longest run of items directly above it "
                         "that adds up to it, in all four year blocks at once. Delhi does "
                         "not label the depth of its totals, so the depth is recovered "
                         "arithmetically; see reconcile() in parse/delhi.py")},
            "grand_total": grand,
            "grand_total_against_every_scheme_row": {
                "printed": grand["printed"] if grand else None,
                "sum_of_scheme_rows": [
                    round(sum(r.total(i) or 0.0 for r in rows), 2) for i in range(4)],
                "what": ("the book's own Grand Total against every scheme row read, "
                         "which is the strictest statement of whether this parser has "
                         "double counted"),
                "read_this": (
                    "It does not close. The 2026-27 column reads 62,55,000.00 lakh "
                    "printed against 64,55,956.00 lakh summed, 3.2 per cent over, and at "
                    "least 1,14,031.00 lakh of that gap is one identified memo line: the "
                    "book prints 'OAS(Other than Minorities)' immediately under "
                    "'TOTAL [OTHER ADMN. SERVICES]' as a restatement of part of it, with "
                    "no word in its name to mark it as a total, so it is read as a "
                    "scheme. The rest of the gap sits in Transport (pages 14 to 17), "
                    "General Education (30 to 43) and Urban Development, which are also "
                    "where the nineteen unresolved printed totals are, and it has NOT "
                    "been traced to a single cause. Treat the money in this file as "
                    "sound at the row level, where 1,577 of 1,578 scheme rows satisfy "
                    "their own Total = Revenue + Capital, and as approximate in "
                    "aggregate.")},
            "unreadable_cells": (
                "Delhi's own PDF carries three cells Excel could not render, printed as "
                "'####' twice and '#VALUE!' once, and one figure clipped to '129' on "
                "page 66. All four are on total lines. Any check touching one carries "
                "cell_unreadable_in_the_pdf, so a failure there reads as the state's "
                "defect and not as this parser's."),
        },
        # The join against myScheme, run once by hand on the 2026-09-03 snapshot and all
        # 33 joins read line by line. Recorded here rather than recomputed on every run
        # because the classification is a human reading, not a rule. parse/match.py is NOT
        # edited to fix anything found; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_delhi_records": 53,
            "register_names": 1578,
            "joins_produced": 33,
            "joins_sound_on_inspection": 27,
            "joins_wrong_on_inspection": 6,
            "myscheme_records_with_any_join": 20,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read by "
                    "eye"),
            "read_this_carefully": (
                "20 of myScheme's 53 Delhi records were found in a book that names 1,578 "
                "lines, and several of the 33 joins are one myScheme record against four "
                "budget lines because Delhi splits a scheme into GIA-General, GIA-Salary, "
                "GIA-Capital and SCSP rows. In the other direction this register is a "
                "large superset and most of the excess is works and establishment rather "
                "than schemes a citizen can apply to."),
        },
        "myscheme_join_defects": [
            {"defect": ("ONE LOWER-CASE LETTER DEFEATS THE SHOUTED-NAME GUARD. "
                        "match.acronyms stands down when a name is three or more words "
                        "of unbroken capitals, on the ground that a shouted title says "
                        "nothing about which words are codes. Delhi appends GIA-General, "
                        "GIA-Salary, GIA-Capital and Dr. to shouted names constantly, and "
                        "one lower-case letter anywhere makes the guard read the name as "
                        "not shouted and turn every capitalised word into an acronym"),
             "reason_string": "acronym match: gandhi",
             "joins": 3,
             "example_myscheme": "Rajiv Gandhi Swavlamban Rojgar Yojna",
             "example_budget": ("RAJIV GANDHI SUPER SPECIALITY HOSPITAL AT TAHIR PUR "
                                "GIA-Capital"),
             "note": ("a PERSONAL NAME read as an acronym. NOT_ACRONYMS holds states, "
                      "sectors and communities and no person. The same name matched the "
                      "hospital's General, Salary and Capital rows, so one hole produced "
                      "three joins.")},
            {"defect": "a personal name read as an acronym, second instance",
             "reason_string": "acronym match: ambedkar",
             "joins": 1,
             "example_myscheme": ("Dr. B. R. Ambedkar State Award To SC/ST/OBC/Minorities "
                                  "Students"),
             "example_budget": ("Dr. Baba Saheb Ambedkar (Dr. B.R.AMBEDKAR) HOSPITAL AT "
                                "ROHINI"),
             "note": ("an award and a hospital, joined because both are named after the "
                      "same person.")},
            {"defect": ("an ordinary sector word capitalised and read as an acronym. "
                        "NOT_ACRONYMS lists health and housing and not medical or "
                        "transport"),
             "reason_string": "acronym match: medical",
             "joins": 1,
             "example_myscheme": "Medical Assistance for the Construction Workers",
             "example_budget": "Dr. BSA MEDICAL COLLEGE"},
            {"defect": "the same hole, on the word transport",
             "reason_string": "acronym match: transport",
             "joins": 1,
             "example_myscheme": "Transport Loan Scheme",
             "example_budget": "TRANSPORT DEPARTMENT",
             "note": ("department is in NOT_ACRONYMS and transport is not, so the "
                      "department name still matched a loan scheme.")},
        ],
        "headings": headings,
        "caveat": (
            "One row here is one line of Delhi's scheme-wise budget, keyed on (sector, "
            "name) because the document prints no scheme code. Rows repeating a name "
            "within one sector are ADDED, which is what the document means when it "
            "splits a scheme into GIA-General, GIA-Salary and GIA-Capital lines. This "
            "list is a superset of Delhi's citizen-facing schemes: works and "
            "establishment lines such as 'Construction of Residential Complex for "
            "Judicial Officers' sit at the same level as 'Laadli Yojana'. It is also "
            "slightly SHORT of the document: about ten nil-provision rows are read as "
            "headings by the blank-line rule described in parse/delhi.py, and appear "
            "under headings rather than under entries."),
        "entries": out,
    })
    return out, checks, failed_totals, arithmetic, scheme_row_arithmetic, grand, \
        headings, date, pages_read


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Delhi Scheme-wise Budget.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, checks, failed, arithmetic, bad_rows, grand, headings, date, pages = \
        run(a.date)
    print(f"delhi snapshot {date}")
    print(f"  {pages} table pages, {len(out)} distinct (sector, scheme) rows")
    print(f"     with a positive 2026-27 outlay "
          f"{sum(1 for r in out if r['be_lakh'] > 0):>6}")
    print(f"     sum of 2026-27 outlays "
          f"{sum(r['be_lakh'] for r in out):>18,.2f} lakh")
    if grand:
        print(f"  grand total printed {grand['printed'][3]:>16,.2f} lakh against "
              f"{sum(r['be_lakh'] for r in out):>16,.2f} summed over every scheme row "
              f"({'closes' if grand['ok'] else 'DOES NOT CLOSE, see the JSON'})")
    print(f"  printed totals  {len(checks) - len(failed):>6} of {len(checks):<6} "
          f"reconcile")
    print(f"  row arithmetic  {len(arithmetic):>6} failures, of which "
          f"{len(bad_rows)} on a scheme row rather than on a printed total")
    print(f"  headings read   {len(headings):>6}")
    for f in (failed + arithmetic)[:10]:
        print("     MISMATCH", json.dumps(f)[:240])
    if bad_rows:
        print(f"  ERROR: {len(bad_rows)} scheme rows do not satisfy "
              f"Total = Revenue + Capital/Loan")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
