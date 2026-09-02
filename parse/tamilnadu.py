"""
Extract Tamil Nadu's per-department Demand Books into a named scheme list.

AGENT-EDITABLE (PLAN.md SS7). Reads archive/tamilnadu/, writes data/tamilnadu/. Never
fetches. Replayable against any archived date.

    data/tamilnadu/schemes.json    one row per head of account

WHICH BUDGET THIS IS. Tamil Nadu presented two budgets for 2026-27, because it is an
assembly election year: an Interim Budget Estimate on 13 February 2026 and a Revised
Budget Estimate on 5 August 2026. collect/tamilnadu.py archives the RBE set and records
why. Both are budget estimates FOR 2026-27, so `be_lakh` here is the same kind of number
as Karnataka's, Kerala's and Andhra Pradesh's 2026-27 budget estimates and not a mid-year
revision of 2025-26. The interim February figure is published alongside it as
`interim_be_lakh` so a reader can see the difference rather than take this parser's word
that the two are comparable.

WHAT A ROW IS, and the trap that decides it. A Demand Book page is a five-level tree and
only ONE of those levels is a scheme:

    277 Education                                        minor head
      AB Upgradation of Adi Dravidar Welfare Hostels     SUB-HEAD, the scheme
        416 Major Works    71,75,73 ... 4225 01 277 AB 41600      object head
          01 Major Works   71,75,73 ... 4225 01 277 AB 41601      detailed head
        Total AB           71,75,73 ...                          the scheme's own total

`416 Major Works` and `01 Major Works` are what the money is spent ON, not what it is
spent on FOR. Publishing them would put "Major Works", "Salaries" and "Motor Vehicles"
into a register of welfare schemes 52,346 times, which is the same trap Karnataka and
Andhra Pradesh each had a version of.

The level is decided from the head of account and never from indentation, because minor
heads, object heads and sub-heads are all printed at almost the same x. Every row carries
its full head of account in the last column, `4225 01 277 AB 41600`, and the rule is
self-verifying: a row is a SCHEME when the code printed in front of its English name
equals the sub-head field of its own head of account. `AB` == `AB` is a scheme; `416`
against `AB` and `01` against `AB` are not. Measured on the 2026-27 books, all 6,244
scheme rows so identified carry a detailed head of 30000, 40000 or 50000, which is the
placeholder Tamil Nadu prints on a sub-head line, and all 6,244 sub-head codes are exactly
two capital letters. Neither fact is assumed; both are asserted at parse time.

The key is therefore `4225 01 277 AB`, major head, sub-major, minor head and sub-head.
That is Tamil Nadu's own identifier for the provision and survives the retyping every name
suffers. It also keeps a scheme's revenue head and its capital head apart, which is what
the state does: they are separate provisions voted separately.

THE UNITS. Kerala printed one column in lakh and another in thousands inside the same
header block, on 333 of 491 pages, and reading it wrong would have published every
allocation at 100 times its value. Tamil Nadu is simpler and is still read rather than
assumed: every one of the 3,154 table pages in the 55 books prints `(Rupees in Thousands)`
in its own header, no page names any other unit, and a page whose header names one is a
hard error here rather than a silent conversion. Everything in the output is normalised to
LAKH, by dividing by 100, so it is comparable with Karnataka, Kerala and Andhra Pradesh.

Three checks that this is right, all measured on the 2026-27 books:

  1. The book's own arithmetic. Demand 04, sub-head 4225 01 277 JB, prints object heads
     416 Major Works `6,02,54` and 464 Lands `63,42` and a Total JB of `6,65,96`.
     60254 + 6342 = 66596, so the commas are cosmetic grouping and the figure is a plain
     integer of thousands. That check is not done once by hand, it is done for every one
     of the 6,244 sub-heads in all four money columns.
  2. The demand's own total. Demand 04's front page prints DEMAND FOR GRANT-Voted
     `3,917,58,96` and APPROPRIATION-Charged `20,00,53`, which is 39,375,949 thousand, or
     Rs 3,937.59 crore for the Social Justice Department. The 213 sub-head totals parsed
     out of that book sum to 39,375,949 exactly.
  3. An outside number. Magalir Urimai Thogai appears under three heads of demand 53 and
     totals 144,138,001 thousand, which is Rs 14,413.80 crore. Tamil Nadu's own public
     statements put that scheme at about Rs 14,000 crore. Read as lakh it would have been
     Rs 1.44 lakh crore, a third of the whole state budget, and read as rupees it would
     have been Rs 14 crore. Only thousands lands anywhere near the truth.

WHICH COLUMN. The detail pages print four money columns and label them only `(3) (4) (5)
(6)`. What those four are is printed once, on the demand's front `Net Expenditure` page,
and is READ there rather than assumed: the four column headings are recovered by
horizontal position and must come back as Accounts 2024-2025, Revised Estimate 2025-2026,
Interim Budget Estimate 2026-2027 and Revised Budget Estimate 2026-2027. All 55 books
agree. This matters because the INTERIM book's four columns are Accounts 2024-25, Budget
Estimate 2025-26, Revised Estimate 2025-26 and Budget Estimate 2026-27: the fourth column
means the same thing in both sets but the second and third do not, so a parser that
assumed positions rather than reading them would silently mislabel two columns the moment
it was pointed at the other set.

TWO RECONCILIATIONS, both against figures the documents print about themselves.

  Per sub-head. The book prints `Total AB` under every sub-head. That must equal the sum
  of the sub-head's object heads, in all four columns. 6,244 of 6,244 reconcile.

  Per major head. The demand's front page prints a net-expenditure figure for every major
  head it touches. That must equal the sum of the sub-head totals under it, in all four
  columns. 484 of 484 reconcile across the 55 books.

Either failing exits 1, as parse/andhra.py does, because a page silently dropped by a
layout change is exactly what turns into a headline about a state deleting schemes.

ONE PROVISION UNDER TWO EXECUTING OFFICES, and why the two rows are added rather than
taken once. Demand 27, Industries, prints 24 heads of account TWICE. Pages 22 to 37 are
headed `027 02 Commissionerate of Industries and Commerce` and pages 38 to 52
`027 03 Commissionerate of Investment Promotion and Facilitation`, and the pairs look like
duplicates because the name and the head of account are identical in both.

They are not duplicates. The figures are COMPLEMENTARY. `2852 80 800 BC`, Investment
Promotion Subsidy for Industries, prints 1,000,00,00 and 1,300,00,01 in the accounts and
revised-estimate columns under 027 02 and `...` in both 2026-27 columns, and exactly the
mirror image under 027 03. Every one of the 23 pairs whose totals could be read straight
off an independent text dump is complementary, with no column carrying a figure on both
sides. The provision changed office between the years and the book prints each office's
slice of it.

So the two rows are added and the entry keeps the head of account once. Taking the first
row instead would publish a 2026-27 allocation of ZERO for all 24, including Rs 2,000
crore of Investment Promotion Subsidy, and it would look entirely plausible. Adding rows
that were not complementary would double count, so this is not left to judgement: the
demand's own major-head control totals decide it. Counting each row separately puts demand
27's major heads at exactly twice the printed figure; adding the slices and counting the
head once reconciles all 484 control totals in the corpus.

WHERE THE NAMES COME FROM, and the wrap. The English name sits in its own column beside
the Tamil, which is typeset in a legacy font that extracts as ASCII punctuation soup in 54
of the 55 books and as real Unicode Tamil in demand 22. Neither can be told from English
by character range alone, which is why this reads coordinates rather than text. Names wrap
over up to nine lines, and a continuation line is accepted only when it starts at or right
of the x where the scheme's own name began. Without that test the label of the next object
head is appended to the name and 150 schemes come out called things like "Land cost
Investment Incentive 351 Compensation" and "Pay of Speaker and Deputy Speaker 301
Salaries", which read as plausible scheme names and are exactly what makes the bug
dangerous. That is Karnataka's "Helpers" and Andhra Pradesh's 350 truncated names in a
third costume.

WHAT THIS LIST IS NOT. A sub-head is Tamil Nadu's scheme-level unit, but the state files
establishment and works provisions at the same level: "Directorate of Public Libraries",
"Headquarters Staff", "District Police" and 184 "Deduct - Recoveries" heads are sub-heads
too. They are kept, because the state files them here and dropping them would mean this
parser deciding what counts as a scheme, but they are counted and flagged so a reader can
discount them. See `caveat` and `counts` in the output.
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
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

NS = "{http://www.w3.org/1999/xhtml}"

# One money cell. Tamil Nadu prints a nil provision as "..." and writes figures in the
# Indian style, 3,016,24,99, where the commas are cosmetic grouping of a plain integer of
# thousands: demand 04's 6,02,54 plus 63,42 is printed as 6,65,96, which is 60254 + 6342.
# Negative provisions are real and numerous, because a recovery head is a sub-head like
# any other: 2225 01 911 UC is -7,34,78.
MONEY = re.compile(r"^-?(?:\.{3,}|[\d,]*\d)$")

# The head of account, as five separate words at the right of the row:
# 4225 01 277 AB 41600 is major head, sub-major, minor head, sub-head, detailed head.
# The sub-head is allowed to be alphanumeric here and then ASSERTED to be two capital
# letters, because a numeric sub-head would silently change what a scheme row looks like.
HOA_WORDS = [re.compile(r"^\d{4}$"), re.compile(r"^\d{2}$"), re.compile(r"^\d{3}$"),
             re.compile(r"^[A-Z0-9]{2}$"), re.compile(r"^\d{5}$")]
SUB_CODE = re.compile(r"^[A-Z]{2}$")
# The placeholder detailed head printed on a sub-head line. 3 for the revenue section,
# 4 for capital, 5 for loans. Asserted, not assumed.
SUB_DETAIL = re.compile(r"^[0-9]0000$")

# The sub-head's own total line, printed under its object heads. Numeric codes after
# "Total" are sub-major, minor and major head totals and are deliberately not matched.
TOTAL = re.compile(r"^Total\s+([A-Z]{2})$")
# A sub-head total, an object head or a major head can be split into its charged and voted
# halves on the two lines below the label, each carrying its own four figures.
VOTE = re.compile(r"^(Charged|Voted)$")

STRIP = re.compile(r"^\((\d{1,2})\)$")
YEAR = re.compile(r"^\d{4}-\d{4}$")
MAJOR = re.compile(r"^\d{4}$")
# The executing office banner at the top of every detail page, "004 02 Directorate of Adi
# Dravidar Welfare", printed once in Tamil and once in English.
BANNER = re.compile(r"^(\d{3})\s+(\d{2})\s+(\S.*)$")
COLUMN_WORDS = ("Accounts", "Revised", "Interim", "Budget", "Estimate")

# The unit marker every table page prints in its own header. Read, never assumed.
UNIT = re.compile(r"[Rr][Uu]?[Pp][Ee][Ee][Ss]\s+[Ii][Nn]\s+([A-Za-z]+)")

# Rows are merged into table rows at 4.0 points. Measured: the line pitch inside a wrapped
# name is 9.4 points and between table rows 11 to 13, while the Tamil half of a row and its
# English half can differ by 2.7 points where the Tamil is real Unicode (demand 22) and by
# up to 4.3 where a long Tamil name drifts against a short English one. At 2.5 points 266
# of 2,383 sub-head totals in a sample of eleven books failed to reconcile, because the
# "Total AB" label separated from its own figures. The reconciliation is flat from 3.5
# through 6.5, so 4.0 sits in the middle of a measured plateau rather than at an edge.
ROW_TOL = 4.0


# ------------------------------------------------------------------ pdf geometry

def pdf_pages(pdf_bytes, tol=ROW_TOL, timeout=900):
    """Yield one list of rows per page, from pdftotext -bbox-layout.

    A row is [top, bottom, [(left, right, word), ...]] in reading order. Poppler's lines
    are runs of adjacent words and NOT table rows: the Tamil half of a row, its English
    half, each figure and the head of account all arrive as separate lines.
    """
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        x = os.path.join(d, "b.xml")
        r = subprocess.run(["pdftotext", "-bbox-layout", p, x],
                           capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise SystemExit("pdftotext failed: %r" % r.stderr[:200])
        for page in _pages_of(x, tol):
            yield page


def _pages_of(path, tol):
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != NS + "page":
            continue
        lines = []
        for ln in el.iter(NS + "line"):
            ws = [(float(w.get("xMin")), float(w.get("xMax")),
                   float(w.get("yMin")), float(w.get("yMax")), w.text or "")
                  for w in ln.iter(NS + "word")]
            if ws:
                lines.append([min(w[2] for w in ws), max(w[3] for w in ws),
                              [(w[0], w[1], w[4]) for w in ws]])
        lines.sort(key=lambda t: (t[0], t[2][0][0]))
        rows = []
        for a, b, cells in lines:
            if rows and abs(rows[-1][0] - a) <= tol:
                rows[-1][1] = max(rows[-1][1], b)
                rows[-1][2].extend(cells)
            else:
                rows.append([a, b, list(cells)])
        for r in rows:
            r[2].sort(key=lambda c: c[0])
        yield rows
        el.clear()


def text_of(row):
    return re.sub(r"\s+", " ", " ".join(c[2] for c in row[2])).strip()


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" .,;:-")


def joined(parts):
    """Join wrapped fragments. A fragment ending in a hyphen against a letter is one word
    broken over the line and must not gain a space; a hyphen used as punctuation keeps its
    spaces. Same distinction as parse/andhra.py and parse/kerala.py."""
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


def money(tok):
    """One figure cell to a number. `...` is how these books print a nil provision."""
    return 0.0 if tok.startswith("...") else float(tok.replace(",", ""))


def to_lakh(v):
    """Thousands to lakh. The only unit conversion in this file, and the header of every
    page is checked to say `Thousands` before it is applied."""
    return None if v is None else v / 100.0


# ------------------------------------------------------------------ page structure

def strip_row(rows):
    """The `(1) (2) (3) ...` column-number strip printed under every table header.

    It is the only thing on the page that says how many columns this table has, which is
    what separates a seven-column DETAIL page, whose last column is the head of account,
    from a six-column SUMMARY page, which has no head of account and lists minor heads
    rather than schemes. Reading schemes off a summary page would publish minor-head
    names such as "Education" and "Direction and Administration" as if they were schemes.
    """
    for i, row in enumerate(rows):
        cs = row[2]
        if len(cs) < 5:
            continue
        nums = [STRIP.match(c[2]) for c in cs]
        if all(nums) and [int(m.group(1)) for m in nums] == list(range(1, len(cs) + 1)):
            return i, row
    return None, None


def unit_of(rows, upto):
    """The unit named in this page's own header, lower-cased, or None if it names none."""
    txt = " ".join(text_of(r) for r in rows[:upto])
    m = UNIT.search(txt)
    return m.group(1).lower() if m else None


def hoa_of(cells):
    """Split the head of account off the right of a row. Returns (hoa, remaining cells).

    Matched on shape and position rather than on the column boundary, because the head of
    account is the one field on the page whose form cannot be anything else, and because
    it is the field every other decision here depends on.
    """
    if len(cells) >= 5:
        tail = cells[-5:]
        if tail[0][0] >= 450 and all(r.match(c[2]) for r, c in zip(HOA_WORDS, tail)):
            return " ".join(c[2] for c in tail), cells[:-5]
    return None, cells


def money_anchors(centres, body, lo=10.0, hi=30.0, default=20.0):
    """The right edge of each of the four money columns, from the page's own ink.

    Right edges rather than a column boundary, because these figures are right aligned and
    a nil `...` is four points wide against a widest figure of forty four. The midpoint
    between two column centres is not the boundary either: on page 106 of demand 43 the
    widest blank run between the name column's centre and the first money column's centre
    falls at x 276, while the word "Charged" in the name column reaches x 291, so a
    boundary taken from the whitespace cuts that word out of its own row and loses the
    sub-head total it labels.

    The anchor is the modal right edge inside a window that cannot reach a neighbouring
    column: the four columns are 45 points apart and the window is 20 wide.
    """
    out = []
    for c in centres[2:6]:
        h = collections.Counter()
        for row in body:
            for cell in row[2]:
                if MONEY.match(cell[2]) and c + lo <= cell[1] <= c + hi:
                    h[round(cell[1], 1)] += 1
        out.append(h.most_common(1)[0][0] if h else c + default)
    return out


def split_row(row, name_left, anchors, tol=2.0):
    """One row into (head of account, four figures or None, name cells, figures seen).

    A figure belongs to a money column when its right edge sits on that column's anchor.
    Anything that is not a figure and not the head of account, and starts right of the
    Tamil column, is name. A row is a figures row only when all four columns are present,
    which every money-bearing row in the 55 books is.
    """
    hoa, rest = hoa_of(row[2])
    figs, used = [None] * 4, set()
    for i, cell in enumerate(rest):
        if not MONEY.match(cell[2]):
            continue
        for k, a in enumerate(anchors):
            if abs(cell[1] - a) <= tol and figs[k] is None:
                figs[k] = money(cell[2])
                used.add(i)
                break
    name = [c for i, c in enumerate(rest) if i not in used and c[0] >= name_left]
    seen = sum(1 for f in figs if f is not None)
    return hoa, (figs if seen == 4 else None), name, seen


def english_banner(header):
    """The executing office, "004 02 Directorate of Adi Dravidar Welfare".

    Printed twice at the top of every detail page, once in Tamil and once in English, and
    the two cannot be told apart by character range: 54 of the 55 books typeset the Tamil
    in a legacy font that extracts as ASCII punctuation soup, so an is-this-ASCII test
    passes it, while demand 22 uses real Unicode Tamil and fails the same test. The tell
    that works for both is the proportion of the line that is Latin letters and spaces.
    """
    best, score = None, 0.0
    for row in header:
        m = BANNER.match(text_of(row))
        if not m:
            continue
        s = m.group(3)
        r = sum(1 for ch in s if ch.isalpha() and ch.isascii() or ch == " ") / max(len(s), 1)
        if r > score:
            best, score = "%s %s %s" % (m.group(1), m.group(2), clean(s)), r
    return best if score >= 0.6 else None


# ------------------------------------------------------- the front control table

def front_table(rows):
    """The demand's own net-expenditure figures per major head, and its column headings.

    Returns ({major head: [four figures]}, [four years], [four labels]). Only pages whose
    text carries `Net Expenditure` are offered here, because the SUMMARY chapter that
    follows repeats major head codes against four figures in the same shape and would
    overwrite the control totals with sub-totals. Demand 27 is where that showed: its
    summary begins on a page with no column-number strip, and reading it as a control table
    put every major head of that book out by a factor of two.

    The table can also run over two pages. Demand 05 touches 22 major heads and prints the
    last eight on a second page under the same banner, so the caller accumulates.
    """
    ctl, anchors = {}, []
    for row in rows:
        cs = row[2]
        k = len(cs)
        while k > 0 and MONEY.match(cs[k - 1][2]):
            k -= 1
        run = cs[k:]
        if len(run) == 4 and cs and MAJOR.match(cs[0][2]) and cs[0][0] < 80:
            ctl[cs[0][2]] = [money(c[2]) for c in run]
            anchors.append([c[1] for c in run])
    if not anchors:
        return {}, None, None
    right = [sum(a[j] for a in anchors) / len(anchors) for j in range(4)]
    years, words = [None] * 4, [[] for _ in range(4)]
    for row in rows:
        for c in row[2]:
            if YEAR.match(c[2]):
                j = min(range(4), key=lambda i: abs(c[1] - right[i]))
                if abs(c[1] - right[j]) < 12:
                    years[j] = c[2]
    centres = [r - 20 for r in right]
    for row in rows:
        for c in row[2]:
            if c[2] in COLUMN_WORDS:
                mid = (c[0] + c[1]) / 2.0
                j = min(range(4), key=lambda i: abs(mid - centres[i]))
                if abs(mid - centres[j]) < 24:
                    words[j].append((row[0], c[0], c[2]))
    labels = [" ".join(w[2] for w in sorted(ws)) for ws in words]
    return ctl, years, labels


# ------------------------------------------------------------------ one book

def parse_book(pages, book):
    """Every sub-head of one Demand Book, with the checks the book prints about itself.

    Returns (rows, per_scheme_checks, control, years, labels, stats).
    """
    pgs = list(pages)
    st = collections.Counter()

    control, years, labels = {}, None, None
    for rows in pgs:
        # The whole page, not its first few rows: the banner sits fifteen rows down on
        # demand 04's front page, under the demand title, the estimate sentence, the
        # variant heading and the voted-and-charged block.
        if "Net Expenditure" not in " ".join(text_of(r) for r in rows):
            continue
        ctl, y, lab = front_table(rows)
        control.update(ctl)
        if y and y[0]:
            years, labels = y, lab

    out, order = [], []
    by_key = {}
    objsum = collections.defaultdict(lambda: [0.0] * 4)
    totals = collections.defaultdict(list)
    office = None
    cur, pend = None, None

    for pno, rows in enumerate(pgs):
        i, strip = strip_row(rows)
        if strip is None:
            st["pages_no_table"] += 1
            continue
        if len(strip[2]) != 7:
            # A six-column SUMMARY page. Real and numerous, 1,107 of the 4,261 table
            # pages, and it lists minor heads rather than schemes.
            st["pages_summary"] += 1
            continue
        header = rows[:i]
        unit = unit_of(rows, i)
        if unit is None:
            raise SystemExit("%s page %d: no (Rupees in ...) marker in the header"
                             % (book, pno + 1))
        if not unit.startswith("thousand"):
            raise SystemExit("%s page %d: header says rupees in %r, not thousands"
                             % (book, pno + 1, unit))
        st["unit_" + unit] += 1
        st["pages_detail"] += 1
        banner = english_banner(header)
        if banner:
            office = banner

        centres = [(c[0] + c[1]) / 2.0 for c in strip[2]]
        body = [r for r in rows if r[0] > strip[1]]
        # The Tamil column ends and the English begins at the midpoint of the two label
        # columns' centres. There is 8 points of clear page either side of it on every
        # page measured, which is why this one boundary can be a midpoint where the
        # name-to-money boundary cannot.
        name_left = (centres[0] + centres[1]) / 2.0
        anchors = money_anchors(centres, body)

        for row in body:
            hoa, figs, name, seen = split_row(row, name_left, anchors)
            if figs is None and seen:
                st["partial_money_rows"] += 1
            txt = " ".join(c[2] for c in name).strip()
            lead = name[0][2] if name else None

            # The page number in the footer. It sits inside the money band, carries no
            # head of account and matches no column anchor, and it must not be allowed to
            # close an open record: a sub-head total routinely prints its label as the
            # last line of a page and its charged and voted figures as the first lines of
            # the next, with the footer in between. Measured: with the footer allowed to
            # close the record, 7 sub-head totals and 10 major-head control totals failed
            # to reconcile; with it skipped, none do.
            if hoa is None and figs is None and len(name) == 1 and lead.isdigit():
                st["page_number_rows"] += 1
                continue

            if hoa:
                f = hoa.split()
                sub, detail = f[3], f[4]
                key = " ".join(f[:4])
                if lead == sub:
                    if not SUB_CODE.match(sub):
                        raise SystemExit("%s page %d: sub-head %r is not two capital "
                                         "letters" % (book, pno + 1, sub))
                    if not SUB_DETAIL.match(detail):
                        raise SystemExit("%s page %d: sub-head line %s carries detailed "
                                         "head %s, expected a X0000 placeholder"
                                         % (book, pno + 1, key, detail))
                    st["scheme_rows"] += 1
                    # The scheme's own name starts here, and a continuation line is only
                    # a continuation if it starts at or right of this x. Object head and
                    # minor head labels sit 15 points left of it, which is the whole
                    # defence against a scheme called "... 301 Salaries".
                    nx = name[1][0] if len(name) > 1 else name[0][1] + 3
                    cur = {"key": key, "code": sub, "major": f[0], "hoa": key,
                           "office": office, "page": pno + 1, "name_x": nx,
                           "parts": [" ".join(c[2] for c in name[1:])]}
                    out.append(cur)
                    order.append(key)
                    by_key.setdefault(key, cur)
                    pend = None
                    continue
                cur = None
                if detail.endswith("00") and not SUB_DETAIL.match(detail):
                    st["object_rows"] += 1
                    if figs:
                        for j in range(4):
                            objsum[key][j] += figs[j]
                        pend = None
                    else:
                        # An object head split into charged and voted lines below its
                        # label, "351 Compensation" over "Charged ... 1 1 1".
                        pend = ("object", key)
                else:
                    st["detail_rows"] += 1
                    pend = None
                continue

            m = TOTAL.match(txt)
            if m:
                cur = None
                st["total_rows"] += 1
                key = next((k for k in reversed(order) if k.split()[-1] == m.group(1)),
                           None)
                if key is None:
                    st["total_orphan"] += 1
                    pend = None
                    continue
                if figs:
                    totals[key].append(figs)
                    pend = None
                else:
                    totals.setdefault(key, [])
                    pend = ("total", key)
                continue

            if figs and VOTE.match(txt) and pend:
                st["vote_rows"] += 1
                if pend[0] == "total":
                    totals[pend[1]].append(figs)
                else:
                    for j in range(4):
                        objsum[pend[1]][j] += figs[j]
                continue

            pend = None
            if figs:
                # A higher-level total: "Total 102", "State's Expenditure Total",
                # "Total 2225". They restate money already counted and are skipped, but
                # they do close whatever record was open.
                cur = None
                st["higher_total_rows"] += 1
                continue
            if cur is not None and txt and name[0][0] >= cur["name_x"] - 1:
                cur["parts"].append(txt)
                st["name_continuation_rows"] += 1

    checks = []
    for r in out:
        printed = ([sum(f[j] for f in totals[r["key"]]) for j in range(4)]
                   if r["key"] in totals else None)
        summed = objsum.get(r["key"], [0.0] * 4)
        r["figures"] = printed
        checks.append({"key": r["key"], "page": r["page"], "printed": printed,
                       "summed": summed,
                       "ok": printed is not None
                       and all(abs(printed[j] - summed[j]) < 0.001 for j in range(4))})

    rows = []
    for r in out:
        name = clean(joined(r["parts"]))
        if not name:
            st["dropped_no_name"] += 1
            continue
        rows.append({"key": r["key"], "code": r["code"], "hoa": r["hoa"],
                     "major_head": r["major"], "name": name, "office": r["office"],
                     "page": r["page"], "figures": r["figures"], "book": book})
    return rows, checks, control, years, labels, st


def control_check(rows, control):
    """Sum the DISTINCT sub-head totals per major head and compare with the printed one.

    Distinct, because 24 heads of account in demand 27 are printed under two executing
    offices and parse_book has already added the two slices into one figure for each. See
    the module docstring: counting the row twice puts that book's major heads at exactly
    twice the printed control total, and counting the head once reconciles all 484.
    """
    by, seen = collections.defaultdict(lambda: [0.0] * 4), set()
    for r in rows:
        if r["key"] in seen or r["figures"] is None:
            continue
        seen.add(r["key"])
        for j in range(4):
            by[r["major_head"]][j] += r["figures"][j]
    out = []
    for m in sorted(set(list(by) + list(control))):
        a, b = by.get(m), control.get(m)
        out.append({"major_head": m, "parsed": a, "printed": b,
                    "ok": bool(a and b
                               and all(abs(a[j] - b[j]) < 0.001 for j in range(4)))})
    return out


# ------------------------------------------------------------------ merge

def merge(rows_by_book, labels_by_book):
    """One entry per head of account, with the demand books that named it.

    Nothing is added here. parse_book has already summed every row carrying a given head
    of account, which is what demand 27's two executing offices need, and every row of a
    repeated head therefore already carries the same summed figure.

    Across books there is nothing to add either: no head of account appears in more than
    one demand book. Each demand for grant is a disjoint slice of the accounts, and
    measured on 2026-27 the corpus has zero cross-book collisions. That is what makes this
    simpler than Kerala and Andhra Pradesh, where several books report overlapping cuts of
    one provision and the figures must never be added.
    """
    merged = {}
    for book in sorted(rows_by_book):
        for r in sorted(rows_by_book[book], key=lambda x: (x["key"], x["page"])):
            e = merged.get(r["key"])
            if e is None:
                e = merged[r["key"]] = {
                    "hoa": r["hoa"], "code": r["code"], "major_head": r["major_head"],
                    "name": r["name"], "department": labels_by_book[book],
                    "head_of_department": r["office"],
                    "be_lakh": to_lakh(r["figures"][3]) if r["figures"] else None,
                    "interim_be_lakh": to_lakh(r["figures"][2]) if r["figures"] else None,
                    "books": [], "names_seen": set()}
            e["names_seen"].add(r["name"])
            if labels_by_book[book] not in e["books"]:
                e["books"].append(labels_by_book[book])
    out = []
    for k in sorted(merged):
        e = merged[k]
        # A head of account printed twice with two different names would mean the key is
        # not the identifier this parser claims it is, so it is published rather than
        # hidden. Measured on 2026-27: zero.
        names = sorted(e.pop("names_seen"))
        e["also_named"] = names[1:] or None
        e["books"] = sorted(e["books"])
        out.append(e)
    return out


# ------------------------------------------------------------------ driver

# The publications page writes the variant marker with a U+2013 en dash and some rows
# use a plain hyphen, so both are accepted. They are written as escapes so no dash
# character other than the ASCII hyphen appears in this file.
DEPT = re.compile("^\\s*\\d{1,3}\\.\\s*(.*?)\\s*"
                  "(?:[-\\u2013\\u2014]\\s*\\(RBE\\)|\\(RBE\\))?\\s*$")
ESTABLISHMENT = re.compile(
    r"^(Directorate|Director of|Director-General|Headquarters|District Staff|"
    r"Secretariat|Establishment|Office of|Commissionerate|Deduct|Regional Office|"
    r"Head Office|Executive Establishment)", re.I)


def department_of(title):
    """The department, from the title the publications page prints beside the link.

    "04. SOCIAL JUSTICE DEPARTMENT - (RBE)" is the department; the leading serial is the
    demand number, which is already in the archive filename, and the trailing (RBE) is the
    variant, which is already in the manifest.
    """
    m = DEPT.match(title or "")
    return clean(m.group(1)) if m else clean(title)


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "tamilnadu", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/tamilnadu/: run collect/tamilnadu.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "tamilnadu", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    rows_by_book, labels, per_book = {}, {}, {}
    scheme_checks, control_checks, stats = {}, {}, collections.Counter()
    columns = {}
    for book in sorted(man.get("books") or {}):
        p = os.path.join(src, "%s.pdf.gz" % book)
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            rows, checks, control, years, labs, st = parse_book(pdf_pages(fh.read()), book)
        rows_by_book[book] = rows
        labels[book] = department_of(man["books"][book].get("what"))
        per_book[book] = len(rows)
        scheme_checks[book] = checks
        control_checks[book] = control_check(rows, control)
        for a, b in st.items():
            stats[a] += b
        columns[book] = {"years": years, "labels": labs}

    # Assertion: the four money columns must be the ones this parser thinks they are, and
    # they are read off each book's own front page rather than assumed from position. The
    # INTERIM books put a Budget Estimate 2025-26 where these put a Revised Estimate, so a
    # parser that skipped this check would mislabel two columns the moment it met the other
    # set of books.
    want_years = ["2024-2025", "2025-2026", man.get("cycle", "").replace("2026-27", "2026-2027"),
                  man.get("cycle", "").replace("2026-27", "2026-2027")]
    want_labels = ["Accounts", "Revised Estimate", "Interim Budget Estimate",
                   "Revised Budget Estimate"]
    column_errors = sorted(
        b for b, c in columns.items()
        if c["years"] != want_years or c["labels"] != want_labels)

    out = merge(rows_by_book, labels)

    bad_scheme = {b: [c for c in chk if not c["ok"]] for b, chk in scheme_checks.items()}
    bad_control = {b: [c for c in chk if not c["ok"]] for b, chk in control_checks.items()}
    n_scheme = sum(len(c) for c in scheme_checks.values())
    n_control = sum(len(c) for c in control_checks.values())

    dedup = sum(len(v) for v in rows_by_book.values()) - len(out)
    counts = {
        "sub_head_rows_read": sum(len(v) for v in rows_by_book.values()),
        "distinct_heads_of_account": len(out),
        # Demand 27 prints 24 heads under two executing offices, with complementary
        # figures that parse_book adds. Not a duplicate count: see the module docstring.
        "rows_merged_into_one_head": dedup,
        "distinct_names": len({r["name"].lower() for r in out}),
        "with_a_figure": sum(1 for r in out if r.get("be_lakh") is not None),
        # with_money follows parse/kerala.py and counts any non-zero provision, so the 35
        # negative recovery heads are in it; with_a_positive_allocation is the number a
        # reader counting funded schemes actually wants.
        "with_money": sum(1 for r in out if r.get("be_lakh")),
        "with_a_positive_allocation": sum(1 for r in out if (r.get("be_lakh") or 0) > 0),
        "funded_at_nil": sum(1 for r in out if r.get("be_lakh") == 0),
        "negative_recovery_heads": sum(1 for r in out if (r.get("be_lakh") or 0) < 0),
        # Indicative only, and the pattern is named so the number can be argued with. It
        # is NOT used to filter the list: deciding what counts as a scheme is the state's
        # job here, not this parser's.
        "name_starts_with_an_establishment_word": sum(
            1 for r in out if ESTABLISHMENT.match(r["name"])),
        "establishment_word_pattern": ESTABLISHMENT.pattern,
    }

    write_json("data/tamilnadu/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Tamil Nadu",
        "cycle": man.get("cycle"),
        "variant": man.get("variant"),
        "variant_note": man.get("variant_note"),
        "source": ("Tamil Nadu Budget, the 55 per-department Demand Books of the Revised "
                   "Budget Estimate 2026-2027"),
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "money_columns": {
            "read_from": ("each demand's own front Net Expenditure page, by horizontal "
                          "position; not assumed from column order"),
            "columns": want_labels,
            "years": want_years,
            "published_here": {"be_lakh": "Revised Budget Estimate 2026-2027",
                               "interim_be_lakh": "Interim Budget Estimate 2026-2027"},
            "books_disagreeing": column_errors,
        },
        "reconciliation": {
            "per_sub_head": {
                "what": ("the Total printed under each sub-head against the sum of that "
                         "sub-head's object heads, in all four money columns"),
                "checked": n_scheme,
                "failed": sum(len(v) for v in bad_scheme.values()),
                "failures": {b: v for b, v in sorted(bad_scheme.items()) if v} or None,
            },
            "per_major_head": {
                "what": ("each demand's printed net expenditure per major head against "
                         "the sum of the distinct sub-head totals under it, in all four "
                         "money columns"),
                "checked": n_control,
                "failed": sum(len(v) for v in bad_control.values()),
                "failures": {b: v for b, v in sorted(bad_control.items()) if v} or None,
            },
        },
        "extraction_stats": dict(sorted(stats.items())),
        "schemes": len(out),
        "counts": counts,
        "unit": "lakh",
        "unit_note": ("Every figure here is rupees in LAKH, converted from the thousands "
                      "the Demand Books print. The unit is read from each page's own "
                      "header and not assumed: all 3,154 detail pages of the 55 books say "
                      "(Rupees in Thousands) and a page naming any other unit is a hard "
                      "error. Three checks: the books' own arithmetic reconciles for all "
                      "6,244 sub-heads in all four columns; demand 04's parsed total of "
                      "39,375,949 thousand equals the 3,917,58,96 voted plus 20,00,53 "
                      "charged its own front page prints; and Magalir Urimai Thogai comes "
                      "out at Rs 14,413.80 crore across its three heads, against Tamil "
                      "Nadu's own public figure of about Rs 14,000 crore. Read as lakh it "
                      "would have been Rs 1.44 lakh crore."),
        # Every join this corpus produces against myScheme's 234 Tamil Nadu records was
        # read by hand: 201 joins over 56 records, of which 118 are wrong. The defects are
        # recorded here and parse/match.py is deliberately NOT changed, because it feeds
        # published absence claims elsewhere and the evidence should land before the
        # numbers move. Direction of harm matters and is not symmetric: a false match makes
        # a budget head look present on myScheme, so it UNDER-reports absence, which is the
        # safe direction; but it INFLATES the count of myScheme records found in the budget,
        # from a real 32 to an apparent 56.
        "myscheme_join_defects": [
            {"defect": "containment fires on two content words, which a generic domain "
                       "phrase supplies on its own",
             "reason_string": "all 2 content words of the shorter name are present",
             "joins": 63,
             "example_myscheme": "Animal Husbandry",
             "example_budget": "Buildings- Animal Husbandry (Administered by Chief "
                               "Engineer (Buildings))",
             "note": ("myScheme's record is an Adi Dravidar and Tribal Welfare livestock "
                      "subsidy; all 31 of its joins are to the Animal Husbandry department "
                      "instead, including recovery, buildings and loan heads.")},
            {"defect": "containment on two words across a wrong department or community",
             "reason_string": "all 2 content words of the shorter name are present",
             "joins": 13,
             "example_myscheme": "Free Education Scheme",
             "example_budget": "Reimbursement of fee claimed as per the provision of "
                               "section 12(1) (c) of Right of Children to Free and "
                               "Compulsory Education Act"},
            {"defect": "a Roman numeral is read as a written acronym; NOT_ACRONYMS has no "
                       "Roman numerals and Indian budget documents are full of them",
             "reason_string": "acronym containment: viii / viii",
             "joins": 12,
             "example_myscheme": "Scholarship (Above VIII Standard) - Tamil Nadu",
             "example_budget": "Special incentive scheme to promote literacy among "
                               "scheduled caste girls studying VI standard to VIII "
                               "standard"},
            {"defect": "containment matches a DEPARTMENT name to that department's own "
                       "secretariat establishment head",
             "reason_string": "all 5 content words of the shorter name are present",
             "joins": 10,
             "example_myscheme": "Braille Watches by Welfare of Differently Abled Persons "
                                 "Department",
             "example_budget": "Department for the Welfare of Differently Abled Persons",
             "note": "2251 00 090 BG and 2251 00 090 AP, two salary heads."},
            {"defect": "containment ignores the community axis when the shorter name names "
                       "no community, so a BC scheme matches its SC and ST siblings",
             "reason_string": "all 3 content words of the shorter name are present",
             "joins": 9,
             "example_myscheme": "Pre-Matric Scholarship Scheme",
             "example_budget": "Pre - Matric Scholarship to Scheduled Caste Students - "
                               "State Share",
             "note": ("QUALIFIERS already knows sc, st, obc and minority are one axis; the "
                      "conflict test cannot fire because myScheme's name names none of "
                      "them.")},
            {"defect": "a written acronym matches the same letters used as an ordinary "
                       "English word in the other name",
             "reason_string": "acronym match: peace",
             "joins": 4,
             "example_myscheme": "Promotion of Energy Audit and Conservation of Energy "
                                 "(PEACE): Training Programme",
             "example_budget": "Extension of Battle casuality facilities to the dependants "
                               "of those killed, disabled while performing their duties "
                               "during war and peace"},
            {"defect": "the consonant skeleton, built for Indic transliteration, folds two "
                       "unrelated ENGLISH words: administration and demonstration both "
                       "reduce to dmnstrtn",
             "reason_string": "transliteration variant: ['dmnstrtn', 'mngmnt']",
             "joins": 2,
             "example_myscheme": "Integrated Pest Management Demonstration Cum Training",
             "example_budget": "Management and Administration"},
            {"defect": "similarity clears the 0.75 floor between sibling schemes that "
                       "differ on a word no QUALIFIERS axis covers",
             "reason_string": "similarity 0.78",
             "joins": 2,
             "example_myscheme": "Maintenance Allowance to Severely Affected Persons",
             "example_budget": "Maintenance Allowance to Leprosy affected persons"},
            {"defect": "a DERIVED initialism equal to an unrelated WRITTEN acronym passes "
                       "the containment guard, because the guard asks only that one side "
                       "wrote it",
             "reason_string": "acronym containment: pocs / pocs",
             "joins": 1,
             "example_myscheme": "Production Of Certified Seeds",
             "example_budget": "Conveyance Advance to Government Servants in lieu of "
                               "Government Vehicles (POCS)"},
            {"defect": "an ordinary adjective matches a genuine acronym on the other side",
             "reason_string": "acronym match: smart",
             "joins": 1,
             "example_myscheme": "Smart Phone for Hearing and Visually Impaired Persons",
             "example_budget": "Implementation of the Scheme of Modernization and Reforms "
                               "through Technology in Public Distribution System "
                               "(SMART-PDS)"},
            {"defect": "containment ignores a narrowing qualifier the budget adds",
             "reason_string": "all 3 content words of the shorter name are present",
             "joins": 1,
             "example_myscheme": "Differently Abled Pension Scheme",
             "example_budget": "Social Security Net-Differently abled Pension for the "
                               "Srilankan Tamils staying at relief camps"},
        ],
        "myscheme_join_summary": {
            "myscheme_tamil_nadu_records": 234,
            "joins_produced": 201,
            "joins_sound_on_inspection": 83,
            "joins_wrong_on_inspection": 118,
            "myscheme_records_with_any_join": 56,
            "myscheme_records_with_a_sound_join": 32,
            "heads_of_account_with_a_sound_join": 78,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read "
                    "by eye"),
        },
        "caveat": (
            "One row here is one SUB-HEAD of a demand for grant, keyed on its head of "
            "account. That is Tamil Nadu's own scheme-level unit, and the object heads "
            "beneath it (Salaries, Major Works, Motor Vehicles) are deliberately NOT "
            "published, because they are what a scheme spends money on and not schemes. "
            "But the state also files establishment and works provisions at sub-head "
            "level: 571 of these names begin with an establishment word, 184 are "
            "\"Deduct - Recoveries\" heads and 35 carry a negative provision, so this "
            "list is a superset of Tamil Nadu's schemes "
            "and not a count of them. A scheme with a revenue head and a capital head "
            "appears twice, because the state votes them separately. Demand 27 prints "
            "24 heads under two executing offices with complementary figures, and the "
            "two slices are added. be_lakh is the "
            "Revised Budget Estimate for 2026-27, the budget in force; interim_be_lakh is "
            "the interim February estimate the same books print beside it. Demands 56 to "
            "67, Debt Charges, Public Debt Repayment, the works lists and the statements, "
            "are not collected and are not here."),
        "entries": out,
    })
    return out, per_book, scheme_checks, control_checks, bad_scheme, bad_control, \
        counts, column_errors, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Tamil Nadu Demand Books.")
    ap.add_argument("--date")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    out, per_book, schk, cchk, bad_s, bad_c, counts, col_err, date = run(a.date)
    print("tamilnadu snapshot %s" % date)
    if a.verbose:
        for b in sorted(per_book):
            print("    %-11s%6d sub-heads   %d/%d sub-head totals   %d/%d major heads"
                  % (b, per_book[b],
                     len(schk[b]) - len(bad_s.get(b, ())), len(schk[b]),
                     len(cchk[b]) - len(bad_c.get(b, ())), len(cchk[b])))
    n_s = sum(len(v) for v in schk.values())
    n_c = sum(len(v) for v in cchk.values())
    f_s = sum(len(v) for v in bad_s.values())
    f_c = sum(len(v) for v in bad_c.values())
    print("  %d books, %d sub-head rows, %d distinct heads of account"
          % (len(per_book), counts["sub_head_rows_read"],
             counts["distinct_heads_of_account"]))
    print("     printed sub-head totals reconcile %d/%d" % (n_s - f_s, n_s))
    print("     printed major head totals reconcile %d/%d" % (n_c - f_c, n_c))
    print("     with an allocation %6d" % counts["with_money"])
    print("     funded at nil      %6d" % counts["funded_at_nil"])
    print("     recovery heads     %6d" % counts["negative_recovery_heads"])
    if col_err:
        print("  ERROR: money column headings differ from the expected four in "
              + ", ".join(col_err))
    if f_s or f_c or col_err:
        # Fail loud, and only after the file is written: the bad run should be archived
        # and visible, not swallowed. Same discipline as parse/andhra.py.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
