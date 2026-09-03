"""
Parse the archived Jharkhand Demand for Grants books into data/jharkhand/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches. A parser bug costs a rerun,
never a snapshot.

WHY JHARKHAND YIELDS. Every scheme in these books opens with a banner line printed in
English capitals with the state's own 4-digit scheme code in brackets at the end:

    STATE SCHEME        MINORITY HOSTEL NUTRITION SCHEME(2073)
    STATE SCHEME        REPAIR AND RENOVATION OF BUILDING BUILT UNDER DEPARTMENT AS
                        HAJ HOUSE, KADRU, RANCHI MINORITY RESIDENTIAL SCHOOL ETC.(2231)

The closing bracket is the terminator the field test asks for: a banner that wraps runs
on to the next line and the code closes it, so a wrapped name is never truncated and a
name is never run into the head of account. Below the banner the head-of-account tree is
printed as `<Hindi> / <English>` on every line, which is Karnataka's bilingual slash.

The Devanagari extracts DAMAGED and nothing is read from it. `pdftotext` drops matras and
collapses conjuncts, so "स्थापना व्यय" arrives as "थापना यय" and "विस्तृत" splits across
two lines. That is Rajasthan's lossy-font problem, and here it costs nothing, because
every name this parser publishes comes from the English half.

WHAT IS READ. The three scheme statements, STATE SCHEMES, CENTRAL ASSISTANCE SCHEMES and
CENTRAL SECTOR SCHEMES. ESTABLISHMENT EXPENDITURE is counted and NOT read: it is the
department's own salaries, travel and office expenses under a demand, not a scheme
anybody can apply to, and folding it in would put "Motor Vehicle Fuel and Repair" in a
register of schemes.

TWO CODES FOR ONE SCHEME. Under CENTRAL ASSISTANCE SCHEMES a scheme is printed twice,

    STATE SCHEME                 PRADHAN MANTRI JAN VIKAS KARYAKARAM(0907)
    CENTER SCHEME                PRADHAN MANTRI JAN VIKAS KARYAKARAM(3674)

once for the state's share and once for the centre's, with a code each. The rows below
carry the fund letter in their own bill code, `30-S-...` against `30-C-...`, so the split
is read from the rows and not guessed: an S row is the state share, a C row the central
share. Both codes are kept, because both are the state's own identifiers and a reader
comparing against DBT Bharat needs to see the pair.

THE DOUBLE-COUNTING TRAP, and it is a real one. An object head that is broken down by
sub-scheme prints its own total first with `**` in the sub-scheme position, then the word
"In Which", then one row per sub-scheme:

    49 Cash Relief  30-S-4225-80-277-02-**-06-49   9,49.86  17,00.00  18,00.00  17,00.00
    In Which -
      Sub Scheme Head - 01 - CYCLE SCHEME (22000565)
      49 Cash Relief  30-S-4225-80-277-02-01-06-49     ---  17,00.00  17,00.00  17,00.00
    Total minor head 277 Education                  9,49.86  17,00.00  18,00.00  17,00.00

The printed minor-head total agrees with the `**` row alone. Adding both would publish
this scheme at nearly twice its provision and the printed totals would have said so, which
is exactly what the reconciliation below is for. Rows are therefore grouped by object head
IGNORING the sub-scheme position, and a group carrying a `**` row uses that row alone.

RECONCILIATION, and the one thing about these books a reader has to know. Every total
the books print with four money columns is checked against the sum of the rows read
beneath it, in all four columns, at major head, sub major head, minor head and sub head.
Four rules had to be measured rather than assumed, and reading any of them the obvious way
publishes wrong numbers that look entirely plausible:

  1. A printed total covers the rows since the LAST TIME THAT SAME TOTAL WAS PRINTED, not
     everything read so far. Minor head 796 under 2225-02 in the Welfare book is totalled
     at 7,98.49 and then again at 93,63.07, and the second figure is the rows between the
     two prints. Read as cumulative, 202 of 308 checks fail.
  2. A SUB HEAD total spans minor heads. Scheme 0158's sub head total is 3,87.53, which is
     its general-education row (90.46) plus its Tribal Area Sub-Plan row (2,97.07). A sub
     head IS the scheme, and the same scheme is funded under both minor heads, so its
     accumulator drops the minor head from the key.
  3. A DEDUCT belongs beside a scheme's provision and not inside it. Minor heads in the
     9xx block (901, 902, 911) are the Deduct heads of the List of Major and Minor Heads,
     printed under a section headed "घटायी गई वसूलियाँ / Deducted Recoveries", and the
     Contents page's allocation is gross expenditure. They are published as
     `deduct_lakh`, separately.
  4. A NEGATIVE is written "(-)7,20,00.00", with the sign in brackets and no minus sign
     anywhere, and a signed zero as "(0.00)". Read without the bracket, the State Disaster
     Response Fund's deduct head arrives as +Rs 720 crore instead of -Rs 720 crore.

A SECOND, INDEPENDENT CHECK. The Contents pages at the front of every book print one
Budget Estimate 2026-27 total per demand per statement, and they name the statements in
English, so the check can be made without reading a word of the damaged Devanagari:

    योग / Total - राज्य स्कीम STATE SCHEME                          2,94,12.99   18
    योग / Total - केंद्र प्रायोजित स्कीम CENTRAL ASSISTANCE SCHEMES   80,00.00   20
    योग/Total -30 Scheduled Tribe, Scheduled Caste, ...             3,79,97.63   23

That is a separately typeset statement of the same money and it is worth more than any
sum this parser takes of its own reading. It earned its keep twice: it found the deduct
rule and it found the bracketed minus sign, neither of which the internal totals could
see, because the internal totals contain both errors symmetrically.

UNITS. Every detail page prints "लाख रुपये में / In Lakhs of Rupees" and no page in the
books measured names any other unit. That is checked per page and a page naming a
different unit is a hard error, because the Kerala Annual Plan prints lakh and THOUSANDS
in the same header block on 333 of 491 pages and reading one as the other publishes every
allocation at 100 times its value while looking entirely plausible. Jharkhand writes its
figures in Indian digit grouping with a two-decimal tail, so "2,94,12.99" is 29,412.99
lakh, and "---" is nil.

THE FOUR MONEY COLUMNS, named by the books' own header row: Actual 2024-25, Budget
Estimate 2025-26, Revised Estimate 2025-26, Budget Estimate 2026-27.
"""

import argparse
import collections
import glob
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

CYCLE_WANTED = "2026-27"

# The bill code, which is Jharkhand's head of account in full:
#   demand - fund - major - sub major - minor - sub head - sub scheme - detail - object
# The sub-scheme position is `**` on a row that totals its own sub-scheme breakdown, and
# the sub-head position takes letters as well as digits (A0 to AM in the Welfare book), so
# neither segment can be assumed numeric.
# The leading guard is (?<!\d) and NOT \b, because the books run the code straight into
# the object head's name when the name fills its column: "Rent, Rate, Tax03-S-2059-80-001
# -17-00-03-16". With \b that row is invisible and its 6.56 lakh goes missing from three
# printed totals in the Building Construction book. This is Maharashtra's
# "1101010028World Agriculture Census" in another state's typesetting.
BILL = re.compile(r"(?<!\d)(\d{2})-([A-Z]{1,3})-(\d{4})-([0-9A-Z*]{2})-([0-9A-Z*]{3})"
                  r"-([0-9A-Z*]{2})-([0-9A-Z*]{2})-([0-9A-Z*]{2})-([0-9A-Z*]{2})\b")
# The left half of a bill code, where the column is narrow enough that it wraps. The rest
# of the code lands on the following line and is joined back on.
BILL_HEAD = re.compile(r"(\d{2}-[A-Z]{1,3}-[0-9A-Z*-]*-)\s*$")
# The tail sits at the END of the following line, after whatever remains of the wrapped
# object-head name ("Relief          796-02-01-06-49"), so it is anchored right and not
# left. Anchored left it misses every one of the 56 wrapped rows in the Welfare book.
BILL_TAIL = re.compile(r"([0-9A-Z*]{2,4}(?:-[0-9A-Z*]{2,4}){1,6})\s*$")

# One money cell. "---" is nil. A NEGATIVE is written "(-)7,20,00.00", with the sign in
# brackets before the figure and no minus anywhere, and a signed zero is written "(0.00)".
# Read without the bracketed sign, the State Disaster Response Fund's deduct head in the
# Home, Jail and Disaster Management book comes out as +7,20,00.00 lakh instead of
# -7,20,00.00, which is Rs 720 crore with the wrong sign, and the Contents page's total
# for that demand's centrally assisted schemes misses by exactly twice that amount.
MONEY = re.compile(r"(?:\(-\)\s*)?-?[\d,]*\d\.\d{2}|---")

# The statement a detail page belongs to, printed in English beside the Hindi.
SECTION = re.compile(r"/\s*(ESTABLISHMENT EXPENDITURE|STATE SCHEMES|"
                     r"CENTRAL ASSISTANCE SCHEMES|CENTRAL SECTOR SCHEMES)\s*\(DETAILS\)")
# Only two banner words appear in these books, measured over the whole set.
BANNER = re.compile(r"^\s*(STATE SCHEME|CENTER SCHEME)\s\s+(\S.*)$")
BANNER_CODE = re.compile(r"\((\d{3,5})\)\s*$")
DEMAND = re.compile(r"Demand No\.\s*(\d+)")
# The cover prints "DETAILS OF DEMANDS FOR GRANTS / 2026 - 2027" in English, with spaces
# around the dash and the century written out. Normalised to 2026-27 for comparison.
CYCLE = re.compile(r"\b(20\d\d)\s*[-\u2013]\s*(?:20)?(\d\d)\b")
UNIT = re.compile(r"In\s+(\w+)\s+of\s+Rupees", re.I)
# Sub Scheme Head - 01 - <Hindi> / CYCLE SCHEME (22000565). The label is printed in
# English in these books even though everything around it is bilingual.
SUB_SCHEME = re.compile(r"Sub Scheme Head\s*-\s*([0-9A-Z*]{2})\s*-\s*(.*)$")
SUB_SCHEME_CODE = re.compile(r"\((\d{6,10})\)\s*$")

YOG = "योग"          # योग, "total"
# The four total levels, as pdftotext renders them from this font. The Devanagari is
# damaged in a fixed, reproducible way (मुख्य -> मु य), so these are the strings the
# extractor actually produces and not the strings the book means. A label outside this
# table is counted in extraction_stats rather than guessed at; if a future year's font
# changes, that counter rises and the run fails on the reconciliation rather than
# silently reading fewer totals.
TOTAL_LEVEL = {
    "मु य शीष": 1,               # मु य शीष, major head
    "उप मु य शीष": 2,  # उप मु य शीष, sub major
    "लघु शीष": 3,                # लघु शीष, minor head
    "उप शीष": 4,                      # उप शीष, sub head
}
# A total line is `योग <label> - <code> - <name>`, except where it is not. The books use a
# hyphen, an en dash and an em dash interchangeably (the Agriculture book prints
# "योग उप शीष – 62 –"), and where the label is long the code is pushed off the line
# entirely, leaving "योग लघु शीष   क्रेडिट सहकारी समितियों को". Both shapes are read: the
# label is matched by longest prefix against TOTAL_LEVEL, and a total with no code on its
# line is placed by the head of account of the row most recently read, which is the same
# rule that disambiguates the ones that do carry a code.
DASH = "[-\u2010-\u2015]"
TOTAL = re.compile(YOG + r"\s*(.*?)\s*" + DASH + r"?\s*([0-9A-Z]{2,4})\s*" + DASH)

# "राज्यांश / State Share" and "केंद्रांश / Central Share", which repeat the row above
# split by who pays. They carry no bill code and are never rows; recognised so that
# four_column_lines_not_attributed counts only lines this parser genuinely cannot place.
SHARE_ECHO = re.compile(r"/\s*(?:State|Central)\s+Share\s*$")

# THE SECOND RECONCILIATION. The Contents pages at the front of every book print, for
# each demand, one Budget Estimate 2026-27 total per statement and then a total for the
# whole demand:
#
#     योग / Total - राज्य स्कीम STATE SCHEME                   2,94,12.99   18
#     योग / Total - केंद्र प्रायोजित स्कीम CENTRAL ASSISTANCE SCHEMES  80,00.00   20
#     योग / Total - केंद्रीय सेक्टर स्कीम / CENTRAL SECTOR SCHEMES      1,00.00   22
#     योग/Total -30 Scheduled Tribe, Scheduled Caste, ...      3,79,97.63   23
#
# This is a separately typeset statement of the same money and it names its statements in
# English, so it can be read without touching the damaged Devanagari. Checked against the
# scheme rows read out of the detail pages, per demand and per statement, it is worth more
# than any sum the parser takes of its own reading.
CONTENTS_STATEMENT = re.compile(
    r"योग\s*/?\s*Total\s*[-\u2010-\u2015]\s*.*?"
    r"(ESTABLISHMENT EXPENDITURE|STATE SCHEME|CENTRAL ASSISTANCE SCHEMES?"
    r"|CENTRAL SECTOR SCHEMES?)\s+(-?[\d,]*\d\.\d{2})\s+\d+\s*$")
CONTENTS_DEMAND = re.compile(
    r"योग\s*/?\s*Total\s*[-\u2010-\u2015]\s*(\d{1,2})[.\s]")


def pdftotext(pdf_bytes, timeout=900):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


def money(tok):
    if tok == "---":
        return 0.0
    neg = tok.startswith("(-)")
    v = float(tok.replace("(-)", "").replace(",", "").strip())
    return -v if neg else v


def joined(parts):
    """Join wrapped name fragments. A fragment ending in a hyphen against a letter is one
    word broken over a line and must not gain a space; a hyphen used as punctuation keeps
    its spaces. Same rule as parse/andhra.py, parse/kerala.py and parse/odisha.py."""
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not out:
            out = p
        elif re.search(r"\w-$", out):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


class Block:
    """One scheme block: the banner or pair of banners, and the rows beneath them.

    A block holds up to two codes because a centrally assisted scheme is printed once for
    the state's share and once for the centre's. Which code a row belongs to is decided by
    the fund letter in the row's own bill code, never by proximity.
    """

    __slots__ = ("codes", "name", "statement", "demand")

    def __init__(self, statement, demand):
        self.codes = {}
        self.name = None
        self.statement = statement
        self.demand = demand

    def code_for(self, fund):
        if fund in self.codes:
            return self.codes[fund]
        # Five fund letters appear across the 36 books: S 7,829 rows, C 620, X 102, U 3
        # and T 3. Only S and C have a banner of their own. An X row sits inside a block
        # that already carries both an S and a C code, so it is neither share on its own;
        # measured, all 102 of them are in STATE/CENTER pairs. They are filed under the
        # scheme's STATE code, which is the identity the state gives the scheme, and the
        # fund letter is published in `funds` so a reader can see that the state/central
        # split of that row is not being claimed. Dropping them instead would take 39
        # rows' provision out of the register while leaving it inside every printed total.
        if "S" in self.codes:
            return self.codes["S"]
        if len(self.codes) == 1:
            return next(iter(self.codes.values()))
        return None


def parse_book(text, stats):
    """Read one department book. Returns (cycle, rows, sub_schemes, checks, units)."""
    pages = text.split("\f")
    cycle = None
    m = CYCLE.search(pages[0] if pages else "")
    if m:
        cycle = m.group(1) + "-" + m.group(2)

    units = collections.Counter()
    rows = []            # one per object head, after the ** rule is applied
    deducts = []         # rows under a Deduct minor head, kept apart from the provision
    # Budget Estimate 2026-27 by (demand, statement): what the Contents page prints, and
    # what the detail pages add up to.
    printed_statement = {}
    pending_contents = []
    read_statement = collections.defaultdict(float)
    sub_schemes = {}     # 8-digit sub-scheme code -> English name
    checks = []
    demand = None
    statement = None
    scope = None         # (demand, statement); the accumulator resets when this changes
    block = None
    pending_banner = None
    pending_sub = None
    last_parts = None    # the head of account of the row most recently read
    sums = collections.defaultdict(lambda: [0.0] * 4)

    def take(blk, hoa, fig, parts, deduct):
        # A deduct row still feeds the accumulator, because the totals the books print DO
        # include it, but it is kept out of the scheme's provision and published beside it.
        (deducts if deduct else rows).append((blk, hoa, fig))
        # Keyed on (level, path), where the path is the bill code prefix down to that
        # level: (3, '2225-04-796'). The level is part of the key because minor head 796
        # and sub head 96 would otherwise be indistinguishable by their last segment.
        for n in range(1, 5):
            prefix = (n, parts[n - 1])
            for i in range(4):
                sums[prefix][i] = round(sums[prefix][i] + fig[i], 4)

    def open_block(kind, text_with_code):
        """Start or extend a scheme block from one closed banner."""
        nonlocal block
        code = BANNER_CODE.search(text_with_code).group(1)
        name = BANNER_CODE.sub("", text_with_code).strip()
        fund = "S" if kind == "STATE SCHEME" else "C"
        # A STATE SCHEME banner always opens a new block. A CENTER SCHEME banner extends
        # the block above it when there is one, because a centrally assisted scheme is
        # printed as a STATE/CENTER pair naming the same scheme twice.
        if fund == "S" or block is None or block.codes.get("C"):
            block = Block(statement, demand)
        block.codes[fund] = code
        block.name = block.name or name
        stats["banners"] += 1

    for page in pages:
        for u in UNIT.finditer(page):
            units[u.group(1).lower()] += 1
        d = DEMAND.search(page)
        if d:
            demand = int(d.group(1))
        if SECTION.search(page) is None:
            # A Contents page. Statement totals come first and the demand total closes
            # the block, so the statement lines are held until the demand names itself.
            for line in page.split("\n"):
                cm = CONTENTS_STATEMENT.search(line.rstrip())
                if cm:
                    pending_contents.append((cm.group(1), money(cm.group(2))))
                    continue
                dm = CONTENTS_DEMAND.search(line)
                if dm and pending_contents:
                    for st_, amt in pending_contents:
                        printed_statement[(int(dm.group(1)), st_)] = amt
                    pending_contents = []
        s = SECTION.search(page)
        if not s:
            continue
        if (demand, s.group(1)) != scope:
            scope = (demand, s.group(1))
            statement = s.group(1)
            block = None
            sums.clear()

        lines = page.split("\n")
        for i, line in enumerate(lines):
            # ---- a banner, possibly wrapped, possibly a second banner for the same block
            if pending_banner is not None:
                kind, parts = pending_banner
                parts.append(line.strip())
                if BANNER_CODE.search(line):
                    open_block(kind, joined(parts))
                    pending_banner = None
                elif len(parts) > 5:
                    stats["banner_never_closed"] += 1
                    pending_banner = None
                continue
            b = BANNER.match(line)
            if b:
                if BANNER_CODE.search(line):
                    open_block(b.group(1), b.group(2).strip())
                else:
                    pending_banner = (b.group(1), [b.group(2).strip()])
                continue

            # ---- a sub-scheme head, which carries an 8-digit code of its own
            if pending_sub is not None:
                pending_sub.append(line.strip())
                cm = SUB_SCHEME_CODE.search(line)
                if cm:
                    txt = SUB_SCHEME_CODE.sub("", joined(pending_sub)).strip()
                    eng = txt.split("/")[-1].strip()
                    if eng:
                        sub_schemes[cm.group(1)] = eng
                    pending_sub = None
                elif len(pending_sub) > 8:
                    stats["sub_scheme_never_closed"] += 1
                    pending_sub = None
                continue
            sm = SUB_SCHEME.search(line)
            if sm:
                pending_sub = [sm.group(2).strip()]
                cm = SUB_SCHEME_CODE.search(line)
                if cm:
                    txt = SUB_SCHEME_CODE.sub("", sm.group(2)).strip()
                    eng = txt.split("/")[-1].strip()
                    if eng:
                        sub_schemes[cm.group(1)] = eng
                    pending_sub = None
                continue

            nums = MONEY.findall(line)
            if len(nums) != 4:
                continue
            left = line[:MONEY.search(line).start()]

            # ---- an object-head row
            bm = BILL.search(left)
            if bm is None:
                hm = BILL_HEAD.search(left)
                if hm and i + 1 < len(lines):
                    tm = BILL_TAIL.search(lines[i + 1].strip())
                    if tm:
                        bm = BILL.search(hm.group(1) + tm.group(1))
                        if bm:
                            stats["bill_codes_rejoined_across_lines"] += 1
            if bm:
                g = bm.groups()
                fig = [money(x) for x in nums]
                if statement == "ESTABLISHMENT EXPENDITURE":
                    stats["establishment_rows"] += 1
                    continue
                if block is None:
                    stats["rows_before_any_banner"] += 1
                    continue
                # THE ** RULE. The sub-scheme position is `00` on an object head with
                # no breakdown, `**` on one that has a breakdown and is printing its own
                # total, and 01, 02, ... on the breakdown rows themselves. Counting the
                # breakdown rows as well as their ** total publishes the scheme at nearly
                # twice its provision. Measured over the archived books: every unwrapped
                # bill code carries either 00 or **, and the numbered rows always arrive
                # indented under the word "In Which" with the code wrapped over two lines.
                #
                # An earlier version grouped by object head and let a ** row win inside
                # the group. It failed on the Health book: page 36 prints a minor-head
                # total in the middle of a breakdown and page 37 repeats the breakdown
                # from the top, so the second copy formed a fresh group with no ** in it
                # and was counted, putting sub head 23 at exactly twice its provision in
                # three of four columns. Dropping the numbered rows outright has no seam.
                if g[6] not in ("00", "**"):
                    stats["sub_scheme_breakdown_rows_skipped"] += 1
                    continue
                # The four levels the books total, as bill-code paths. Note that the
                # SUB HEAD level drops the minor head: measured on the Welfare book, the
                # sub head total for scheme 0158 is 3,87.53, which is its 277 row (90.46)
                # plus its 796 row (2,97.07). A sub head is the scheme, and the same
                # scheme is funded under the general minor head and under the Tribal Area
                # Sub-Plan one, so its total spans both.
                parts = [g[2], g[2] + "-" + g[3], g[2] + "-" + g[3] + "-" + g[4],
                         g[2] + "-" + g[3] + "-" + g[5]]
                # A minor head in the 9xx block is a Deduct head in the List of Major
                # and Minor Heads: 901 "Deduct - Amount met from ...", 902, and 911
                # "Deduct - Recoveries of Overpayments". These books print them under a
                # section headed "घटायी गई वसूलियाँ / Deducted Recoveries" with every
                # figure bracketed negative. The Contents page's allocation is GROSS
                # expenditure, and the demand's own summary page prints Gross, Deduct and
                # Net as three separate lines, so a deduct belongs beside a scheme's
                # provision and not inside it. Counted in, the Home, Jail and Disaster
                # Management book's centrally assisted total comes out at 18,000 lakh
                # against the 90,000 the Contents page prints.
                deduct = g[4].startswith("9")
                take(block, "-".join(g), fig, parts, deduct)
                # Accumulated here and NOT before the ** filter above: counted earlier it
                # picks up the sub-scheme breakdown rows as well as their ** total and
                # every Contents-page check comes out at twice the printed figure, which
                # is how that filter was found to be load-bearing a second time.
                if not deduct:
                    read_statement[(demand, statement)] = round(
                        read_statement[(demand, statement)] + fig[3], 4)
                last_parts = parts
                stats["scheme_rows"] += 1
                continue

            # ---- the per-share echo lines that repeat the row above, once for the
            # state's share and once for the centre's. They carry no bill code, so they
            # are never counted as rows; they are recognised here only so that the
            # unattributed counter below means what it says.
            if SHARE_ECHO.search(left):
                stats["share_echo_lines"] += 1
                continue

            # ---- a printed total. The label may sit on this line or on the line above,
            # because a long Hindi label pushes the figures on to their own line.
            # The label can sit above the figures OR BELOW them. The Agriculture book
            # prints the code fragment "- 107 -" on one line, the four figures on the
            # next and "योग लघु शीष ..." on the one after that, so an upward-only search
            # misses the total and, with it, the reset that keeps the accumulator honest:
            # three minor-head totals in that book then fail by exactly the provision of
            # the scheme above them.
            label_src = line
            if YOG not in line:
                for off in (-1, 1, -2, 2):
                    j = i + off
                    if 0 <= j < len(lines) and YOG in lines[j]:
                        label_src = lines[j]
                        break
            if YOG not in label_src:
                stats["four_column_lines_not_attributed"] += 1
                continue
            norm = re.sub(r"\s+", " ", label_src.strip())
            tm = TOTAL.search(norm)
            lvl = TOTAL_LEVEL.get(tm.group(1)) if tm else None
            code = tm.group(2) if tm else None
            if lvl is None:
                # No code on the line, or a label the code regex could not isolate. Take
                # the level by longest matching prefix and place the total by position.
                rest = norm[norm.index(YOG) + len(YOG):].strip()
                lvl = next((v for k, v in sorted(TOTAL_LEVEL.items(),
                                                 key=lambda kv: -len(kv[0]))
                            if rest.startswith(k)), None)
                code = None
                if lvl is None:
                    stats["total_label_unparsed"] += 1
                    continue
                stats["totals_placed_without_a_printed_code"] += 1
            if statement == "ESTABLISHMENT EXPENDITURE":
                continue
            # Which subtree the total covers is taken from the head of account of the row
            # most recently read, because a total is always printed at the end of the
            # subtree it closes. Minor head 796 exists under both 2225-04 and 4225-80 in
            # the same statement, so searching the accumulator by the printed code alone
            # is ambiguous and loses the check; the reading position is not.
            key = None
            if last_parts and len(last_parts) >= lvl:
                cand = last_parts[lvl - 1]
                if (code is None or cand.rsplit("-", 1)[-1] == code) and (lvl, cand) in sums:
                    key = (lvl, cand)
            if key is None and code is None:
                stats["total_without_a_position"] += 1
                continue
            if key is None:
                cands = [k for k in sums
                         if k[0] == lvl and k[1].rsplit("-", 1)[-1] == code]
                if len(cands) != 1:
                    stats["total_without_a_unique_prefix"] += 1
                    continue
                key = cands[0]
            checks.append({"statement": statement, "demand": demand,
                           "level": lvl, "code": code,
                           "printed": [money(x) for x in nums],
                           "computed": list(sums[key])})
            # A printed total covers the rows since the LAST time that same total was
            # printed, not everything read so far. Measured on the Welfare book: minor
            # head 796 under 2225-02 is totalled at 7,98.49 and again at 93,63.07, and the
            # second figure is the rows between the two prints, not the whole minor head.
            # Reading these as cumulative fails 202 of 308 checks.
            sums[key] = [0.0, 0.0, 0.0, 0.0]
    contents = []
    for (d_, st_), amt in sorted(printed_statement.items()):
        if st_ == "ESTABLISHMENT EXPENDITURE":
            continue
        # The Contents page writes the statement in the singular ("STATE SCHEME") and the
        # detail pages in the plural ("STATE SCHEMES (DETAILS)"), so they are matched on
        # the singular stem rather than on the string.
        key = next((k for k in read_statement
                    if k[0] == d_ and k[1].rstrip("S").rstrip() == st_.rstrip("S").rstrip()),
                   None)
        contents.append({"demand": d_, "statement": st_,
                         "printed_be_lakh": amt,
                         "computed_be_lakh": round(read_statement.get(key, 0.0), 4)})
    return cycle, rows, deducts, sub_schemes, checks, units, contents


def run(date=None, verbose=False):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "jharkhand", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/jharkhand/: run collect/jharkhand.py")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "jharkhand", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    stats = collections.Counter()
    merged, per_book, all_checks, wrong_cycle = {}, {}, [], []
    all_contents = []
    all_units = collections.Counter()
    sub_scheme_names = {}

    for book in sorted(man.get("books", {})):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        dept = man["books"][book].get("department") or book
        (cycle, rows, deducts, subs, checks,
         units, contents) = parse_book(text, stats)
        if cycle != CYCLE_WANTED:
            # Excluded and named rather than quietly merged. A supplementary book or a
            # left-over year on the index would otherwise publish a figure that is not
            # the 2026-27 Budget Estimate.
            wrong_cycle.append({"book": book, "department": dept,
                                "cycle_printed_on_its_cover": cycle})
            continue
        # A page naming any unit but lakh is a hard error, not a conversion.
        other = {u: n for u, n in units.items() if u != "lakhs"}
        if other:
            raise SystemExit(f"{book}: unit markers other than lakhs: {other}")
        all_units.update(units)
        sub_scheme_names.update(subs)
        seen_here = set()
        for is_deduct, group in ((False, rows), (True, deducts)):
            for blk, hoa, fig in group:
                fund = hoa.split("-")[1]
                code = blk.code_for(fund)
                if code is None:
                    stats["rows_with_no_code_for_their_fund"] += 1
                    continue
                e = merged.get(code)
                if e is None:
                    e = merged[code] = {
                        "code": code, "names": set(), "statements": set(),
                        "departments": set(), "demands": set(), "hoas": set(),
                        "funds": set(), "paired": set(),
                        "fig": [0.0] * 4, "deduct": [0.0] * 4}
                if blk.name:
                    e["names"].add(blk.name)
                e["statements"].add(blk.statement)
                e["departments"].add(dept)
                if blk.demand is not None:
                    e["demands"].add(blk.demand)
                e["hoas"].add(hoa)
                e["funds"].add(fund)
                for other_code in blk.codes.values():
                    if other_code != code:
                        e["paired"].add(other_code)
                key = "deduct" if is_deduct else "fig"
                for i in range(4):
                    e[key][i] = round(e[key][i] + fig[i], 4)
                seen_here.add(code)
        per_book[book] = len(seen_here)
        all_checks.extend(checks)
        for c in contents:
            all_contents.append(dict(c, book=book))

    failed = [c for c in all_checks
              if any(abs(a - b) > 0.005 for a, b in zip(c["printed"], c["computed"]))]
    failed_contents = [c for c in all_contents
                       if abs(c["printed_be_lakh"] - c["computed_be_lakh"]) > 0.005]

    out = []
    for code in sorted(merged):
        e = merged[code]
        names = sorted(e["names"])
        out.append({
            "code": code,
            "name": names[0] if names else None,
            "also_named": names[1:] or None,
            "statements": sorted(e["statements"]),
            "departments": sorted(e["departments"]),
            "demands": sorted(e["demands"]),
            "funds": sorted(e["funds"]),
            "paired_codes": sorted(e["paired"]) or None,
            "hoas": sorted(e["hoas"]),
            "actual_2024_25_lakh": e["fig"][0],
            "be_2025_26_lakh": e["fig"][1],
            "re_2025_26_lakh": e["fig"][2],
            "be_lakh": e["fig"][3],
            "deduct_lakh": e["deduct"][3] or None,
        })

    write_json("data/jharkhand/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Jharkhand",
        "cycle": CYCLE_WANTED,
        "source": ("Jharkhand Budget, the per-department Detailed Demands for Grants "
                   "books 2026-27"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH exactly as the books print them, "
            "converted by nothing. The unit is read from each page's own "
            "'लाख रुपये में / In Lakhs of Rupees' marker and a page naming any other "
            "unit is a hard error, because the Kerala Annual Plan prints lakh and "
            "THOUSANDS in the same header block on 333 of 491 pages and reading one as "
            "the other publishes every allocation at 100 times its value while looking "
            "entirely plausible. Jharkhand writes its figures in Indian digit grouping "
            "with a two-decimal tail, so 2,94,12.99 is 29,412.99 lakh, and '---' is nil. "
            "be_lakh is the Budget Estimate 2026-27, the last of the four money columns "
            "the books print; Actual 2024-25, Budget Estimate 2025-26 and Revised "
            "Estimate 2025-26 are published beside it."),
        "variant": "Budget Estimate 2026-27",
        "variant_note": (
            "The main budget, as laid before the Assembly in February 2026. The 1st "
            "Supplementary Book 2026-27 on the same index page is NOT read: a "
            "supplementary demand is voted after the main budget and mixing the two "
            "publishes a figure that is neither the budget estimate nor the final grant. "
            "Each book's own cover is read for the cycle and a book printing anything "
            "else is excluded and named in cycle_excluded."),
        "caveat": (
            "This is a floor on Jharkhand's schemes and never a total. It counts what the "
            "36 demand books print under STATE SCHEMES, CENTRAL ASSISTANCE SCHEMES and "
            "CENTRAL SECTOR SCHEMES; a benefit paid from a welfare board's own fund "
            "rather than from a demand does not appear. In the other direction some rows "
            "here are heads of expenditure rather than schemes a citizen can apply to, "
            "which is why the count is stated with the source and not as a headline."),
        "entries": out,
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "books_read": len(per_book),
            "with_a_positive_be": sum(1 for r in out if r["be_lakh"] > 0),
            "funded_at_nil": sum(1 for r in out if r["be_lakh"] == 0),
            "state_share_codes": sum(1 for r in out if "S" in r["funds"]),
            "central_share_codes": sum(1 for r in out if "C" in r["funds"]),
            "paired_state_and_central_codes": sum(
                1 for r in out if r["paired_codes"]),
            "in_more_than_one_department": sum(
                1 for r in out if len(r["departments"]) > 1),
            "sub_scheme_codes": len(sub_scheme_names),
            "schemes_per_book": per_book,
        },
        "sub_schemes": {k: sub_scheme_names[k] for k in sorted(sub_scheme_names)} or None,
        # The join against myScheme, run once by hand on the 2026-09-03 snapshot and read
        # line by line, all 45 of them. Recorded here rather than recomputed on every run
        # because the classification is a human reading, not a rule. parse/match.py is NOT
        # edited to fix any of these; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_jharkhand_records": 96,
            "joins_produced": 45,
            "joins_sound_on_inspection": 31,
            "joins_wrong_on_inspection": 14,
            "myscheme_records_with_any_join": 29,
            "myscheme_records_with_a_sound_join": 26,
            "scheme_codes_with_a_sound_join": 29,
            "how": ("myScheme records whose beneficiaryState names Jharkhand and whose "
                    "level is not Central; indexed on match.tokens, match.skeleton and "
                    "match.acronyms, then match.probably_same on every candidate pair, "
                    "then every join read by eye"),
            "read_this_carefully": (
                "26 of myScheme's 96 Jharkhand records were found in books that name 852 "
                "schemes, and that is not evidence the other 70 are invented. Several are "
                "benefits paid from a board's or a corporation's own fund rather than "
                "from a demand, and several are central schemes myScheme files under the "
                "state. In the other direction this register is a superset and some of "
                "its rows, 'ROADS' and 'TRANSMISSION' among them, are heads of "
                "expenditure rather than schemes a citizen can apply to."),
        },
        "myscheme_join_defects": [
            {"defect": ("AN ALL-CAPS NAME HAS EVERY ONE OF ITS WORDS READ AS AN ACRONYM. "
                        "Jharkhand prints every scheme banner in capitals, so "
                        "match.acronyms('KIYOSK CONSTRUCTION') returns "
                        "['construction', 'kiyosk'] while match.acronyms('Kiyosk "
                        "Construction') returns []. The same pair of names therefore "
                        "matches or does not match according to the case the state "
                        "typeset them in: probably_same('Rearing Pond Construction "
                        "Scheme', 'KIYOSK CONSTRUCTION') is (True, 'acronym match: "
                        "construction') and probably_same('Rearing Pond Construction "
                        "Scheme', 'Kiyosk Construction') is (False, 'no match')."),
             "joins": 6,
             "reason_strings": ["acronym match: construction", "acronym match: block",
                                "acronym match: institute", "acronym match: procurement"],
             "example_myscheme": "Rearing Pond Construction Scheme",
             "example_register": "0299 KIYOSK CONSTRUCTION",
             "note": ("this is Odisha's 'SWACHHA ODISHA' defect with an A/B pair beside "
                      "it. Six of the fourteen wrong joins are this one: two to KIYOSK "
                      "CONSTRUCTION, two to BLOCK JEEPS and BLOCK ADMINISTRATION, one to "
                      "PHARMACY INSTITUTE and one to E-PROCUREMENT.")},
            {"defect": ("A WRITTEN ACRONYM MATCHES ANY NAME CARRYING ONE WORD OF ITS "
                        "EXPANSION. myScheme's 'Block Level Institute for Rural Skill "
                        "Acquisition (BIRSA)' yields acronyms ['birsa', 'blifrsa', "
                        "'blirsa'], and 'birsa' is a content token of a dozen unrelated "
                        "Jharkhand schemes because Birsa Munda's name is on them."),
             "joins": 7,
             "reason_strings": ["acronym match: birsa"],
             "example_myscheme": "Block Level Institute for Rural Skill Acquisition (BIRSA)",
             "example_register": "2098 BIRSA IRRIGATION WELL ENRICHMENT MISSION",
             "note": ("that one myScheme record produced ten joins and every one is "
                      "wrong: BIRSA AGRICULTURE UNIVERSITY, BIRSA AWAS YOJANA, BIRSA "
                      "VISHIST JANJATI VIKASH YOJNA, INTEGRATED BIRSA VILLAGE "
                      "DEVELOPMENT SCHEME, BIRSA SEED PRODUCTION, BIRSA IRRIGATION WELL "
                      "ENRICHMENT MISSION and a second grants-in-aid line to the "
                      "university, plus the three above from the all-caps defect. A "
                      "person's name is the least discriminating token in an Indian "
                      "scheme register and is being used as the most discriminating "
                      "one.")},
            {"defect": ("'ALL N CONTENT WORDS OF THE SHORTER NAME ARE PRESENT' WITH N=2 "
                        "LETS A HEAD OF EXPENDITURE SWALLOW A SCHEME. 'EXTENSION - "
                        "TRAINING' is an object head, and both of its content words "
                        "appear in 'Fish Extension, Research, and Training Scheme', so "
                        "the two join at full confidence."),
             "joins": 1,
             "reason_strings": ["all 2 content words of the shorter name are present"],
             "example_myscheme": "Fish Extension, Research, and Training Scheme",
             "example_register": "0798 EXTENSION - TRAINING",
             "note": ("the same myScheme record also joins correctly to 0564 FISHERIES "
                      "EXTENSION, RESEARCH AND TRAINING SCHEME, so the defect costs "
                      "precision and not recall here.")},
            {"defect": ("NOT A MATCHER DEFECT, recorded so it is not mistaken for one. "
                        "myScheme lists 'Scheme Of Coaching & Allied For Scheduled "
                        "Castes' and 'Scheme Of Coaching & Allied For Scheduled Tribes' "
                        "separately, and Jharkhand prints both register rows as plain "
                        "'COACHING & ALLIED' and 'COACHING AND ALLIED' with no SC or ST "
                        "in the name. All four joins are produced and two of them must "
                        "be wrong; nothing in the register's own text says which."),
             "joins": 4,
             "reason_strings": ["all 2 content words of the shorter name are present"],
             "example_myscheme": "Scheme Of Coaching & Allied For Scheduled Castes",
             "example_register": "0174 COACHING & ALLIED",
             "note": ("counted as sound above, because the scheme is real and the "
                      "ambiguity is the register's, not the matcher's. The demand each "
                      "row sits under settles it and the joiner does not look at "
                      "that.")},
        ],
        "extraction_stats": dict(stats),
        "unit_markers": dict(all_units),
        "cycle_excluded": wrong_cycle or None,
        "reconciliation": {
            "printed_totals": {
                "checked": len(all_checks), "failed": len(failed),
                "failures": failed[:20] or None,
                "what": ("every total the books print with four money columns, at major "
                         "head, sub major head, minor head and sub head, against the sum "
                         "of the rows read beneath it in all four columns. The scope is "
                         "cumulative within a statement, so a minor head total covers "
                         "every scheme under it and not only the scheme it follows")},
            "contents_page_statement_totals": {
                "checked": len(all_contents), "failed": len(failed_contents),
                "failures": failed_contents[:20] or None,
                "what": ("the Budget Estimate 2026-27 total the Contents page at the "
                         "front of each book prints for each demand and each statement, "
                         "against the scheme rows read out of that statement's detail "
                         "pages. A separately typeset statement of the same money, so it "
                         "is worth more than any internal sum, and it named its statements "
                         "in English so no Devanagari had to be read to use it")},
        },
    })
    if failed or failed_contents:
        print(f"jharkhand: {len(failed)} of {len(all_checks)} printed totals and "
              f"{len(failed_contents)} of {len(all_contents)} Contents-page totals FAILED")
        for c in (failed + failed_contents)[:10]:
            print("   ", c)
        return 1
    print(f"jharkhand: {len(out)} schemes from {len(per_book)} books, "
          f"{len(all_checks)} printed totals and {len(all_contents)} Contents-page "
          f"statement totals reconciled, "
          f"{sum(1 for r in out if r['be_lakh'] > 0)} with a positive BE")
    if verbose:
        print("   stats:", dict(stats))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Jharkhand demand books.")
    ap.add_argument("--date")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    raise SystemExit(run(a.date, a.verbose))


if __name__ == "__main__":
    main()
