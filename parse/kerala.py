"""
Extract Kerala's scheme-wise budget books into a named scheme list.

AGENT-EDITABLE (PLAN.md §7). Reads archive/kerala/, writes data/kerala/. Never fetches.
Replayable against any archived date.

    data/kerala/schemes.json    one row per scheme code

THE UNITS TRAP, and it is the whole reason this file reads coordinates rather than text.
The Annual Plan's Statement IV prints SIX money columns and they are NOT in the same unit.
The header carries `(Rs. in Lakh)` over the accounts and revised-estimate columns and
`(Rs. in Thousands)` over the last one, Budget Estimate 2026-2027, which is the column
anyone actually wants. Read the last column as lakh and every Kerala allocation is
published inflated one hundred fold, and it looks entirely plausible: Kerala Agricultural
University would be Rs 7,800 crore instead of Rs 78 crore.

So the unit of every money column is READ OFF THE HEADER by position, never assumed. Each
`(Rs. in X)` marker is located by its horizontal centre and applies to its own column and
to every column to its left back to the previous marker. Three checks that this is right,
all of them measured on the 2026-27 books:

  1. Continuity. AGR 005 Coconut Development is 7300.00 in the Budget Estimate 2025-26
     column and 730000 in Budget Estimate 2026-27; AGR 114 Rice Development is 9360.00
     and 936000. Both are exactly 100x, which is lakh against thousand.
  2. A second document. The Environment Budget prints AGR001's total budget outlay as
     7800.00 with its own header `(Rs in lakh)`, where the Annual Plan prints 780000.
     Two documents, one figure, and the ratio is 100.
  3. The book's own arithmetic. Statement IV A totals the local government plan at
     103490000 in the thousands column, and Statement II lists the same provision as
     1034900 in a table headed `( Rs in Lakh )`.

Statement V, VI and V A, the centrally sponsored schemes, print a SINGLE `(Rs. in Lakh)`
and their Budget Estimate 2026-27 column is in lakh. The trap is therefore not "Kerala
uses thousands", it is "Kerala uses both, in the same book, in the same column position".
Everything in the output is normalised to LAKH and the unit is named in the file.

WHY COORDINATES. Karnataka separates its two scripts with a slash and Andhra Pradesh has
only one script. Kerala's Annual Plan puts the Malayalam name and the English name in two
sub-columns of one column, and pdftotext -layout collapses the gap between them to a
single space when the Malayalam is long: `AGR 012 <malayalam> Farm Information`. Splitting
that on whitespace merges the two names, and splitting at a fixed character offset cuts
the English one in half. The gap is 7 points on the page and 0 characters in the text
dump, so this parser reads `pdftotext -bbox-layout` and uses the real x of every word. The
Malayalam sub-column ends at x 242 and the English begins at x 249 on all 334 Statement IV
pages, measured, and 7,971 English words start at exactly 249.

The Malayalam is Unicode, but only mostly: a large minority of glyphs land in the Private
Use Area (U+E000..U+F8FF) rather than the Malayalam block. That does not matter here
because both are equally not-Latin, which is all the script test needs, but it does mean
no Malayalam string in these books can be matched by literal text, so the unit markers are
read from the English `(Rs. in ...)` and never from the Malayalam beside it.

FOUR BOOKS, THREE LAYOUTS.

    annual-plan   Statements IV, IV A, V, V A and VI. Statement IV has nine columns and a
                  separate English name column; V, V A and VI have twelve and stack the
                  English name UNDER the Malayalam in one column. The number of columns is
                  read off the `(1) (2) (3) ...` strip the book prints under every header,
                  which is also what says how many money columns to expect.
    gender-child  Four statements (Gender Part A, Gender Part B, Transgender, Child) in
                  one eight-column layout with an Objectives column in English.
    elderly       The same eight-column layout, with an elderly earmark.
    environment   Collected and archived but NOT parsed here. See the note below.

THE SUB-ITEM, and why the key is not the bare code. Kerala's own identifier is the scheme
code, `AGR 011`, and the docs recorded 1,808 rows against 1,639 codes. The difference is
that one code often covers several separately named and separately funded components,
which the book numbers itself: AGR 114 is `(1) Rice Development`, `(2) Vegetable
Development` and `(4) Vegetable Development - Support to VFPCK`, three schemes, three
heads of account, three allocations. Keying on the bare code merges them and publishes one
name where the state published three, which is the same class of error as truncating a
wrapped name. The key here is therefore the code AND the sub-item number where the book
prints one, `AGR 114 (2)`, which is still Kerala's own identifier and not ours. The count
of distinct bare codes is published alongside so both numbers are visible.

WHAT A MERGED CELL MEANS. The Gender, Child and Elderly books wrap the scheme name and the
Objectives sentence over many lines, and vertically centre each cell in its row, so a
cell's text starts above its own row and ends below it. Worse, an Objectives cell is
sometimes MERGED across two schemes: GEN 221 and GEN 337 share one sentence about
infrastructure in schools, printed once across both rows. Assigning each line of text to
the nearest scheme splits that sentence in half and gives each half to the wrong scheme.
So text is grouped into cells first, by vertical adjacency, and a cell is then given to
every scheme row it overlaps. A merged cell therefore produces the same objective on both
schemes, which is what the page says.

NOT PARSED, AND SAID OUT LOUD. The Environment Budget carries a real scheme table with
codes, heads of account and a justification paragraph, and it IS archived by
collect/kerala.py so it can be parsed later without a new fetch. It is not parsed here
because its column boundaries move between pages by up to 25 points and it prints no
column-number strip to anchor them, so the split between its two wide text columns has to
be inferred from whitespace and cannot be verified the way the other three can. Publishing
a justification against the wrong scheme is exactly the error this project exists to avoid.
Its codes are in any case a subset of the Annual Plan's, so nothing is missing from the
scheme list because of this; what is missing is one more sentence of description.
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

# Malayalam block, plus the Private Use Area the typesetter spills into, plus the two
# joiners. Anything matching this is "not English", which is the only judgement needed.
MAL = re.compile(r"[ഀ-ൿ-‌‍]")
LATIN = re.compile(r"[A-Za-z]")

# One money cell. Kerala prints plain figures with no thousands separator and no nil
# marker: a zero provision is "0.00" or "0". Negative provisions are real and appear as
# reductions of a claim already made, e.g. -117.00 under 2403-00-113-92 (04).
MONEY = re.compile(r"^-?[\d,]*\d(?:\.\d+)?$")

CODE_TWO = re.compile(r"^[A-Z]{2,4}$")
CODE_NUM = re.compile(r"^\d{3}$")
CODE_ONE = re.compile(r"^([A-Z]{2,4})\s?(\d{3})$")
SUBITEM = re.compile(r"^\((\d{1,2})\)$")
DEMAND = re.compile(r"^\[[IVXL]{1,7}\]$")
HOA = re.compile(r"^\d{4}-\d{2}-\d{3}-\d{2}$")
HOA_SUB = re.compile(r"^\((\d{2})\)$")
SECTOR = re.compile(r"^\d{1,2}\.\d{1,2}$")
ROMAN = re.compile(r"^[IVX]{1,6}$")

BOOK_LABEL = {
    "annual-plan": "Annual Plan Statements",
    "gender-child": "Gender & Child Budget",
    "elderly": "Elderly Budget",
}


# ------------------------------------------------------------------ pdf geometry

def pdf_pages(pdf_bytes, timeout=900):
    """Yield one list of rows per page, from pdftotext -bbox-layout.

    A row is [top, bottom, [(left, right, word), ...]] in reading order, with the page's
    rotation normalised away: the Gender, Child and Elderly statements are typeset
    sideways on a portrait page, so their word coordinates arrive transposed.

    Rows are built by merging poppler's lines, which are runs of adjacent words and NOT
    table rows: every figure in the Annual Plan is its own line. Two lines are the same
    table row when their tops agree to within 2.5 points, which is tight enough to keep a
    vertically centred Objectives cell out of the row it overlaps and loose enough to
    hold a Malayalam word and a Latin word typeset in different fonts.
    """
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        x = os.path.join(d, "b.xml")
        r = subprocess.run(["pdftotext", "-bbox-layout", p, x],
                           capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        for page in _pages_of(x):
            yield page


def _pages_of(path, tol=2.5):
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != NS + "page":
            continue
        height = float(el.get("height"))
        raw = []
        for ln in el.iter(NS + "line"):
            ws = [(float(w.get("xMin")), float(w.get("xMax")),
                   float(w.get("yMin")), float(w.get("yMax")), w.text or "")
                  for w in ln.iter(NS + "word")]
            if ws:
                raw.append(ws)
        # A sideways page shows up as lines that are taller than they are wide. Deciding
        # per page rather than per document because the Gender & Child book mixes upright
        # prose chapters with sideways statement pages.
        tall = sum(1 for ws in raw
                   if max(w[3] for w in ws) - min(w[2] for w in ws) >
                      max(w[1] for w in ws) - min(w[0] for w in ws))
        rot = bool(raw) and tall * 2 > len(raw)
        lines = []
        for ws in raw:
            if rot:
                cells = [(height - w[3], height - w[2], w[4]) for w in ws]
                a, b = min(w[0] for w in ws), max(w[1] for w in ws)
            else:
                cells = [(w[0], w[1], w[4]) for w in ws]
                a, b = min(w[2] for w in ws), max(w[3] for w in ws)
            cells.sort(key=lambda c: c[0])
            lines.append([a, b, cells])
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


def words(row):
    return [c[2] for c in row[2]]


def text_of(cells):
    return re.sub(r"\s+", " ", " ".join(c[2] for c in cells)).strip()


def joined(parts):
    """Join wrapped fragments. A fragment ending in a hyphen against a letter is one word
    broken over the line, `Nadu-` + `Nedu`, and must not gain a space; a hyphen used as
    punctuation keeps its spaces. Same distinction as parse/andhra.py."""
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


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" .,;:-")


# ------------------------------------------------------------------ units

# The unit marker arrives as separate words because poppler emits words, not phrases:
# the Annual Plan writes "(Rs." "in" "Lakh)" and the Gender, Child and Elderly books
# write "(in" "₹" "lakh)". So the anchor is the unit word, with an "in" required within
# the two tokens before it. Requiring the "in" is what stops the word Lakh inside an
# ordinary sentence of the Major Highlights chapter from being read as a column header.
_UNIT_WORD = re.compile(r"^\(?(lakh|lakhs|thousand|thousands)\)?$", re.I)
_IN = re.compile(r"^\(?in$", re.I)
_RS = re.compile(r"^\(?\s*(rs\.?|₹)$", re.I)


def unit_markers(rows):
    """Every `(Rs in <unit>)` marker in a header, as (centre, unit).

    Returned in left-to-right order. The unit of a money column is then the marker
    nearest it that is not to its right, which is how these headers are laid out: one
    marker sits over the last lakh column and another over the thousands column.
    """
    out = []
    for row in rows:
        cs = row[2]
        for i, c in enumerate(cs):
            if not _UNIT_WORD.match(c[2]):
                continue
            back = [j for j in (i - 1, i - 2) if j >= 0 and _IN.match(cs[j][2])]
            if not back:
                continue
            start = min(cs[j][0] for j in back)
            j = min(back) - 1
            if j >= 0 and _RS.match(cs[j][2]):
                start = min(start, cs[j][0])
            unit = "thousand" if c[2].lower().strip("(").startswith("thousand") else "lakh"
            out.append(((start + c[1]) / 2.0, unit))
    return sorted(out)


def column_units(centres, markers, slack=12.0):
    """The unit of each money column, by position. Raises if the header names none.

    `slack` is half a digit group: a marker centred over a column can sit a few points
    right of the column's own centre, as `(Rs. in Lakh)` does over column 8 of Statement
    IV at 657 against the column's 652.
    """
    if not markers:
        raise ValueError("no (Rs. in ...) marker in the header")
    units = []
    for c in centres:
        left = [m for m in markers if m[0] <= c + slack]
        units.append((left[-1] if left else markers[0])[1])
    return units


def to_lakh(value, unit):
    if value is None:
        return None
    return value / 100.0 if unit == "thousand" else value


def money(tok):
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


# ------------------------------------------------------------------ annual plan

STRIP = re.compile(r"^\((\d{1,2})\)$")


def strip_row(rows):
    """The `(1) (2) (3) ...` column-number strip the Annual Plan prints under its header.

    It is the only thing on the page that says how many columns this table has, which is
    what separates the nine-column State Plan statement from the twelve-column centrally
    sponsored ones, and those two need different readers and carry different units.
    """
    for i, row in enumerate(rows):
        cs = row[2]
        if len(cs) < 5:
            continue
        nums = [STRIP.match(c[2]) for c in cs]
        if all(nums) and [int(m.group(1)) for m in nums] == list(range(1, len(cs) + 1)):
            return i, row
    return None, None


def annual_regions(body, want):
    """Where the code, name, demand and money columns of an Annual Plan page begin.

    Every boundary is read off the page's own contents rather than off the column-number
    strip, because the strip's markers are centred under the column HEADINGS and are up to
    50 points away from where the column's ink actually starts.

    name_left  the leftmost Malayalam word. Every scheme carries its name in Malayalam, so
               this is the left edge of the name column and therefore the right edge of
               the code column, which is the only thing left of it.
    demand     the bracketed demand and the head of account can be nothing else, so their
               own extent is the column. It can be ABSENT: the Kerala State Electricity
               Board's 200-odd projects in sector 5.1 carry neither, because KSEB is a
               company and not a demand for grants, and six pages read zero rows when the
               demand column was assumed to exist.
    money      the left edge of the run of figures, taken from rows that carry the full
               set. Right-aligned figures make the run's own left edge vary by the width
               of the widest figure, so the minimum over the page is the column edge.
    """
    mal = [c[0] for row in body for c in row[2] if MAL.search(c[2])]
    name_left = min(mal) if mal else None
    dem = [(c[0], c[1]) for row in body for c in row[2]
           if DEMAND.match(c[2]) or HOA.match(c[2])]
    dleft = min(x[0] for x in dem) if dem else None
    dright = max(x[1] for x in dem) if dem else None
    xs = []
    for row in body:
        cs = row[2]
        k = len(cs)
        while k > 0 and MONEY.match(cs[k - 1][2]):
            k -= 1
        run = cs[k:]
        # Exactly the full set, and far enough right that a scheme name ending in a
        # number cannot be mistaken for the first figure of a short row.
        if len(run) == want and name_left is not None and run[0][0] > name_left + 80:
            xs.append(run[0][0])
    return name_left, dleft, dright, (min(xs) if xs else None)


def english_left(body, name_left, right):
    """Where the English name sub-column starts, on a nine-column page.

    The mode over the page, not a constant: it is 249 on every one of the 334 Statement IV
    pages measured, but a mode computed per page is a check on that rather than an
    assumption, and it costs nothing.
    """
    h = collections.Counter()
    for row in body:
        for c in row[2]:
            if (c[0] >= name_left - 2 and c[1] <= right
                    and not MAL.search(c[2]) and LATIN.search(c[2])):
                h[round(c[0])] += 1
    return h.most_common(1)[0][0] if h else None


def heading_text(row, body, ri, split, skip):
    """The English of a sector or sub-sector heading.

    Read from the WHOLE row and not from the name column, because a long heading runs
    clear across the table: "9.11 Welfare of SC/ST, OBC, Minorities and other Backward
    Communities" reaches x 556, well past the name column's right edge at 341, and a
    heading read from the name column alone comes back empty and leaves the previous
    sector's label attached to 200 schemes. Statement IV prints the English beside the
    Malayalam and Statements V, VI and V A print it on the line below, so a heading with
    no English of its own borrows the next line's.
    """
    txt = clean(" ".join(c[2] for c in row[2][skip:] if not MAL.search(c[2])))
    if not txt and ri + 1 < len(body):
        n2 = split(body[ri + 1])[1]
        if n2 and not any(MAL.search(c[2]) for c in n2):
            txt = clean(" ".join(c[2] for c in n2))
    return txt


def parse_annual(pages, book):
    """Every scheme row of the Annual Plan, in page order.

    Returns (rows, checks, stats). A row is one scheme: its code, its sub-item number if
    the book prints one, its English name, its heads of account and its 2026-27 budget
    estimate normalised to lakh.
    """
    out, checks, stats = [], [], collections.Counter()
    unattached = []
    sector, subsector = None, None
    last_code, run, cur, last_cols = None, 0.0, None, None
    for pno, rows in enumerate(pages):
        i, strip = strip_row(rows)
        if strip is None:
            stats["pages_no_table"] += 1
            continue
        ncols = len(strip[2])
        if ncols not in (9, 12):
            stats["pages_other_table"] += 1
            continue
        centres = [(c[0] + c[1]) / 2.0 for c in strip[2]]
        header = rows[:i]
        head_text = " ".join(text_of(r[2]) for r in header)
        # Statement IV A is the plan of the local self governments, five rows naming
        # Corporations, Municipalities and the three tiers of panchayat. They carry no
        # code, no head of account and no scheme name, so they are tiers of government
        # rather than schemes and reading them would add five inventions to the register.
        if re.search(r"STATEMENT\s+IV\s+A", head_text):
            stats["pages_statement_iv_a"] += 1
            cur, last_code = None, None
            continue
        body = [r for r in rows if r[0] > strip[1]]
        try:
            units = column_units(centres[3:], unit_markers(header))
        except ValueError as e:
            raise SystemExit(f"{book} page {pno + 1}: {e}")
        be_unit = units[-1] if ncols == 9 else units[5]
        # Statement IV's last column is the 2026-27 estimate; V, VI and V A put three
        # more columns of anticipated central assistance after it, so the wanted column
        # is the sixth of the nine and never the last.
        be_index = (ncols - 3) - 1 if ncols == 9 else 5
        stats["pages_cols%d" % ncols] += 1
        stats["unit_" + be_unit] += 1

        name_left, dleft, dright, mleft = annual_regions(body, ncols - 3)
        if name_left is None or mleft is None:
            stats["pages_no_columns"] += 1
            continue
        name_right = (dleft if dleft is not None else mleft) - 1
        eleft = english_left(body, name_left, name_right) if ncols == 9 else None
        if ncols == 9 and eleft is None:
            stats["pages_no_english_column"] += 1
            continue

        def split(row):
            code_cs = [c for c in row[2] if c[1] <= name_left - 2]
            name_cs = [c for c in row[2]
                       if c[0] >= name_left - 2 and c[1] <= name_right]
            dem_cs = ([] if dleft is None else
                      [c for c in row[2] if c[0] >= dleft - 1 and c[1] <= dright + 1])
            mon_cs = [c for c in row[2] if c[0] >= mleft - 2 and MONEY.match(c[2])]
            return code_cs, name_cs, dem_cs, mon_cs

        # `cur` survives the page break. A scheme's second and third heads of account
        # routinely open the next page with no name and no code beside them: page 45
        # begins with eight such rows under 2401-00-789-79 and the like, all of them
        # belonging to the scheme whose name is on page 44. Resetting per page loses
        # their money and breaks the sector total.
        if last_cols != ncols:
            cur, last_code = None, None
        last_cols = ncols
        for ri, row in enumerate(body):
            code_cs, name_cs, dem_cs, mon_cs = split(row)
            figures = mon_cs if len(mon_cs) == ncols - 3 else []
            has_demand = any(DEMAND.match(c[2]) for c in dem_cs)

            # A sector heading, "1.1 Agriculture", ends whatever record was open: the
            # next scheme belongs to the new sector and never continues the old name.
            # It is also printed as a banner at the top of every continuation page, so
            # the code carried over a page break is only dropped when the sector really
            # changes. Dropping it on the banner too would orphan the 170 Statement IV
            # sub-items and 148 Statement V sub-items whose parent code is on the page
            # before, and they would be published with no code at all.
            if name_cs and SECTOR.match(name_cs[0][2]) and not figures:
                new = heading_text(row, body, ri, split, 1)
                if new and new != sector:
                    sector, subsector, last_code, cur = new, None, None, None
                continue

            # A sub-sector heading, "II Crop Husbandry". It closes the record above it,
            # and it must be recognised rather than fallen through: its English would
            # otherwise be appended to the last scheme's name, which is how a scheme
            # comes to be called "... Crop Husbandry". Like the sector heading it is
            # reprinted as a banner on every continuation page, so the open record is
            # only closed when the sub-sector actually changes.
            if name_cs and ROMAN.match(name_cs[0][2]) and not figures:
                new = heading_text(row, body, ri, split, 1)
                if new and new != subsector:
                    subsector, cur = new, None
                continue

            code, sub, rest = None, None, name_cs
            if len(code_cs) >= 2 and CODE_TWO.match(code_cs[0][2]) \
                    and CODE_NUM.match(code_cs[1][2]):
                code = f"{code_cs[0][2]} {code_cs[1][2]}"
            elif code_cs and CODE_ONE.match(code_cs[0][2]):
                m = CODE_ONE.match(code_cs[0][2])
                code = f"{m.group(1)} {m.group(2)}"
            elif len(code_cs) == 1 and CODE_TWO.match(code_cs[0][2]) \
                    and ri + 1 < len(body):
                # The code column is narrow and the code wraps inside it: KSEB's 200-odd
                # power projects print "POW" on the scheme's own line and "009" on the
                # line below. Read as two rows they lose their identifier entirely.
                n2 = split(body[ri + 1])[0]
                if n2 and CODE_NUM.match(n2[0][2]) and abs(n2[0][0] - code_cs[0][0]) < 20:
                    code = f"{code_cs[0][2]} {n2[0][2]}"
            if rest and SUBITEM.match(rest[0][2]):
                sub, rest = rest[0][2], rest[1:]

            starts = code is not None or (sub is not None and bool(figures))

            if figures and not starts and not has_demand:
                # A printed total. The English word for it is on the line BELOW the
                # figures, not beside them: the cell holds "ആെക" over "TOTAL", and only
                # the Malayalam shares the money row. So the label is read from the next
                # line, and it is the label that decides what the figure means.
                # `TOTAL` closes a sector and is the control figure that the rows since
                # the previous one must add up to; `Sub Total` is an interior subtotal;
                # anything else is a sector-group total, which restates money already
                # counted and is skipped.
                #
                # The test is "no code AND no demand", and the code has to be read first
                # for it to work. KSEB's sector 5.1 prints neither a demand nor a head of
                # account against any of its projects, because the Board is a company and
                # not a demand for grants, so on a demand test alone every one of its
                # schemes reads as a total row. That mistake dropped 104,218 lakh, the
                # whole of the Board's own contribution to the plan, and it dropped it
                # silently: the schemes simply were not there.
                label = clean(" ".join(c[2] for c in name_cs if not MAL.search(c[2])))
                if not label and ri + 1 < len(body):
                    n2, m2 = split(body[ri + 1])[1], split(body[ri + 1])[3]
                    if len(m2) != ncols - 3:
                        label = clean(" ".join(c[2] for c in n2
                                               if not MAL.search(c[2])))
                val = to_lakh(money(figures[be_index][2]), be_unit)
                if label.lower() == "total":
                    checks.append({"book": book, "page": pno + 1, "sector": sector,
                                   "printed": round(val or 0.0, 2),
                                   "parsed": round(run, 2)})
                    run = 0.0
                cur = None
                continue
            if starts:
                last_code = code or last_code
                cur = {"code": last_code, "sub": sub,
                       "name_parts": [], "hoas": [], "be_lakh": None,
                       "sector": sector, "book": book,
                       "statement": "IV" if ncols == 9 else "V"}
                out.append(cur)
            if cur is None:
                # A figures row belonging to no scheme. Counted rather than ignored: it
                # is money the book prints that this parser has not attributed, and the
                # sector totals below are what say whether that matters.
                if figures:
                    stats["figure_rows_unattached"] += 1
                    unattached.append((pno + 1, sector,
                                       to_lakh(money(figures[be_index][2]), be_unit),
                                       text_of(row[2])[:110]))
                continue

            # The name. On nine-column pages the English sits in its own sub-column and
            # is taken by position; on twelve-column pages it is stacked under the
            # Malayalam in one column, so a line is English only if nothing on it is not.
            if ncols == 9:
                eng = [c[2] for c in rest if c[0] >= eleft - 2 and not MAL.search(c[2])]
            else:
                eng = ([c[2] for c in rest] if rest and
                       not any(MAL.search(c[2]) for c in rest) else [])
            if eng:
                cur["name_parts"].append(" ".join(eng))

            for c in dem_cs:
                if HOA.match(c[2]):
                    cur["hoas"].append(c[2])
                elif HOA_SUB.match(c[2]) and cur["hoas"]:
                    # The two-digit sub-head is printed under its head of account and
                    # belongs to it. Keeping them joined is what lets a Gender Budget row,
                    # which prints 2501-06-198-48-04 in one piece, find the same provision.
                    cur["hoas"][-1] = cur["hoas"][-1] + "-" + HOA_SUB.match(c[2]).group(1)
            if figures:
                v = to_lakh(money(figures[be_index][2]), be_unit)
                if v is not None:
                    # Additive parts of one provision: the revenue head and the capital
                    # head of the same scheme are two rows and one allocation.
                    cur["be_lakh"] = v if cur["be_lakh"] is None else cur["be_lakh"] + v
                    run += v
                    stats["figure_rows"] += 1

    rows = []
    for r in out:
        name = clean(joined(r["name_parts"]))
        if not name or not r["code"]:
            stats["dropped_no_name_or_code"] += 1
            continue
        rows.append({"code": r["code"] + (" " + r["sub"] if r["sub"] else ""),
                     "base_code": r["code"], "name": name,
                     "hoas": sorted(set(r["hoas"])), "be_lakh": r["be_lakh"],
                     "sector": r["sector"], "objectives": None,
                     "book": r["book"], "statement": r["statement"]})
    return rows, checks, stats, unattached


# ------------------------------------------------- eight-column statement books

def num_strip(rows):
    """The `1 2 3 4 5 6 7 8` strip under the header of the Gender, Child and Elderly
    statements. Same job as the Annual Plan's bracketed strip, without the brackets."""
    for i, row in enumerate(rows):
        cs = row[2]
        if len(cs) < 6:
            continue
        try:
            nums = [int(c[2]) for c in cs]
        except ValueError:
            continue
        if nums == list(range(1, len(cs) + 1)):
            return i, row
    return None, None


def column_bounds(centres, body):
    """Boundaries between columns, from the whitespace the table actually leaves.

    Midway between two column CENTRES is not the boundary: column 3 of the Child Budget
    holds the scheme name and runs 124 points wide against column 4's 82, so a midpoint
    cuts the last word of every long name into the head-of-account column. The real
    boundary is the gap in the page's ink, so this looks for the widest run of blank page
    between each pair of centres and puts the boundary in the middle of it.
    """
    ivs = sorted((c[0], c[1]) for row in body for c in row[2])
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    bounds = []
    for lo, hi in zip(centres, centres[1:]):
        best, width = (lo + hi) / 2.0, -1.0
        for (_, e), (s, _) in zip(merged, merged[1:]):
            if e >= lo and s <= hi and s - e > width:
                best, width = (e + s) / 2.0, s - e
        bounds.append(best)
    return bounds


def column_of(cell, bounds):
    c = (cell[0] + cell[1]) / 2.0
    for i, b in enumerate(bounds):
        if c < b:
            return i
    return len(bounds)


def cells_in_column(rows, bounds, col, gap=8.0):
    """Group one column's text into cells: runs of rows with no vertical break.

    A cell is [top, bottom, [(row, text), ...]]. The break threshold is 8 points against
    a line pitch of 11, so a wrapped sentence stays one cell and two schemes' cells stay
    apart. This is what keeps an Objectives cell merged across two schemes in one piece
    instead of splitting it between them.
    """
    out = []
    for row in rows:
        cs = [c for c in row[2] if column_of(c, bounds) == col]
        if not cs:
            continue
        txt = text_of(cs)
        if out and row[0] - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], row[1])
            out[-1][2].append((row, txt))
        else:
            out.append([row[0], row[1], [(row, txt)]])
    return out


def assign_cells(cells, anchors):
    """Give each cell to every anchor row it overlaps, else to the nearest anchor.

    Overlap and not proximity, because these books vertically centre a cell in its row and
    MERGE a cell across two rows when two schemes share an objective. GEN 221 and GEN 337
    of the Child Budget share one sentence: by proximity its three lines split two-one
    between the schemes and the sentence is destroyed, by overlap both schemes get the
    whole sentence, which is what the page prints.
    """
    got = collections.defaultdict(list)
    orphans = 0
    for top, bot, lines in cells:
        hit = [k for k, a in enumerate(anchors) if a[0] <= bot and a[1] >= top]
        if not hit:
            orphans += 1
            if not anchors:
                continue
            mid = (top + bot) / 2.0
            hit = [min(range(len(anchors)),
                       key=lambda k: abs((anchors[k][0] + anchors[k][1]) / 2.0 - mid))]
        for k in hit:
            got[k].append(joined(t for _, t in lines))
    return got, orphans


def parse_statement(pages, book, alloc_label):
    """The Gender, Child, Transgender and Elderly statements: one eight-column layout.

    Columns are Sl.No, Scheme Code, Sector/Subsector/Scheme, Head of Account, State Plan
    outlay, the allocation earmarked for this book's group, that as a percentage, and
    Objectives. Every figure is in lakh and the header says so once.
    """
    out, stats = [], collections.Counter()
    statement, sector = None, None
    for pno, rows in enumerate(pages):
        i, strip = num_strip(rows)
        if strip is None or len(strip[2]) != 8:
            stats["pages_no_table"] += 1
            continue
        header = rows[:i]
        title = clean(" ".join(text_of(r[2]) for r in header[:2]))
        if title:
            statement = title
        body = [r for r in rows if r[0] > strip[1]]
        if not body:
            continue
        centres = [(c[0] + c[1]) / 2.0 for c in strip[2]]
        bounds = column_bounds(centres, body)
        try:
            unit = column_units(centres[4:7], unit_markers(header))[0]
        except ValueError as e:
            raise SystemExit(f"{book} page {pno + 1}: {e}")
        stats["pages_table"] += 1
        stats["unit_" + unit] += 1

        # Anchor rows: the one line of each scheme that carries its code and its figures.
        anchors, codes = [], []
        for row in rows:
            cs = [c for c in row[2] if column_of(c, bounds) == 1]
            if not cs or row[0] <= strip[1]:
                continue
            t = text_of(cs)
            m = CODE_ONE.match(t.replace(" ", "")) if t else None
            if not m:
                continue
            anchors.append((row[0], row[1]))
            codes.append(f"{m.group(1)} {m.group(2)}")
        if not anchors:
            # A sector heading page with no scheme on it. Real: the Transgender
            # statement has three pages and the Child Budget's sector headings sit alone.
            stats["pages_no_anchor"] += 1
            continue

        names, orph_n = assign_cells(cells_in_column(body, bounds, 2), anchors)
        hoas, orph_h = assign_cells(cells_in_column(body, bounds, 3), anchors)
        objs, orph_o = assign_cells(cells_in_column(body, bounds, 7), anchors)
        stats["orphan_cells"] += orph_n + orph_h + orph_o

        # A sector heading is a row in the name column with no code beside it. Kept as
        # context, exactly as parse/andhra.py keeps the department.
        for row in body:
            cs = [c for c in row[2] if column_of(c, bounds) <= 2]
            if not cs:
                continue
            if any(a[0] <= row[1] and a[1] >= row[0] for a in anchors):
                continue
            t = clean(text_of(cs))
            if t and t.upper() == t and len(t) > 3 and not any(ch.isdigit() for ch in t):
                sector = t

        for k, code in enumerate(codes):
            row = [r for r in body if r[0] == anchors[k][0]]
            figs = []
            if row:
                for c in row[0][2]:
                    col = column_of(c, bounds)
                    if col in (4, 5) and MONEY.match(c[2]):
                        figs.append((col, money(c[2])))
            outlay = next((v for col, v in figs if col == 4), None)
            alloc = next((v for col, v in figs if col == 5), None)
            hoa = [h for h in re.split(r"[,\s]+", joined(hoas.get(k, [])))
                   if re.match(r"^\d{4}-\d{2}-\d{3}-\d{2}(-\d{2})?$", h)]
            out.append({"code": code, "base_code": code,
                        "name": clean(joined(names.get(k, []))),
                        "hoas": sorted(set(hoa)),
                        "be_lakh": to_lakh(outlay, unit),
                        "earmark_lakh": to_lakh(alloc, unit),
                        "earmark_for": alloc_label,
                        "objectives": clean(joined(objs.get(k, []))) or None,
                        "sector": sector, "book": book, "statement": statement})
            stats["rows"] += 1
    return [r for r in out if r["name"]], [], stats


# ------------------------------------------------------------------ merge

def norm_name(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def entry_key(r):
    """Kerala's own identifier, in the order the state itself would use it.

    The scheme code first, with the sub-item number where the book prints one, because it
    is the state's identifier and survives the retyping every name suffers. Then a head of
    account, which is an identifier too, just a coarser one. Then the name, which is all
    that is left.
    """
    if r.get("code"):
        return "code:" + r["code"]
    if r.get("hoas"):
        return "hoa:" + r["hoas"][0]
    return "name:" + norm_name(r["name"])


def merge(rows_by_book):
    """One entry per scheme, with the books that named it.

    Allocations are NOT summed across books. The Gender, Child and Elderly books each
    report the same provision, sliced by who benefits, so adding them would count one
    scheme's money three times. The Annual Plan is the book that states the provision, so
    its figure wins where it exists and the others only fill a gap.
    """
    merged = {}
    for book in sorted(rows_by_book):
        for r in sorted(rows_by_book[book], key=lambda x: (entry_key(x), x["name"])):
            k = entry_key(r)
            e = merged.get(k)
            if e is None:
                e = merged[k] = {"key": k, "code": r.get("code"),
                                 "base_code": r.get("base_code"),
                                 "name": r["name"], "objectives": r.get("objectives"),
                                 "hoas": set(r["hoas"]), "be_lakh": r.get("be_lakh"),
                                 "be_from": BOOK_LABEL[book], "sector": r.get("sector"),
                                 "books": [], "earmarks": {}}
            if BOOK_LABEL[book] not in e["books"]:
                e["books"].append(BOOK_LABEL[book])
            e["hoas"] |= set(r["hoas"])
            if not e["objectives"] and r.get("objectives"):
                e["objectives"] = r["objectives"]
            if not e["sector"] and r.get("sector"):
                e["sector"] = r.get("sector")
            if e["be_lakh"] is None and r.get("be_lakh") is not None:
                e["be_lakh"], e["be_from"] = r["be_lakh"], BOOK_LABEL[book]
            if r.get("earmark_lakh") is not None:
                e["earmarks"][r["earmark_for"]] = r["earmark_lakh"]
    out = []
    for k in sorted(merged):
        e = merged[k]
        e["hoas"] = sorted(e["hoas"])
        e["books"] = sorted(e["books"])
        e["earmarks"] = {a: e["earmarks"][a] for a in sorted(e["earmarks"])} or None
        out.append(e)
    return out


# ------------------------------------------------------------------ driver

BOOK_READER = {
    "annual-plan": lambda pages: parse_annual(pages, "annual-plan"),
    "gender-child": lambda pages: parse_statement(pages, "gender-child", "women/children"),
    "elderly": lambda pages: parse_statement(pages, "elderly", "elderly"),
}


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "kerala", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/kerala/: run collect/kerala.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "kerala", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    rows_by_book, per_book, checks, stats = {}, {}, {}, {}
    for book in sorted(BOOK_READER):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            got = BOOK_READER[book](pdf_pages(fh.read()))
            rows, chk, st = got[0], got[1], got[2]
        rows_by_book[book] = rows
        per_book[book] = len(rows)
        checks[book] = chk
        stats[book] = dict(sorted(st.items()))

    out = merge(rows_by_book)
    bad = {b: [c for c in chk if abs(c["printed"] - c["parsed"]) > 0.02]
           for b, chk in checks.items()}

    write_json("data/kerala/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Kerala",
        "cycle": man.get("cycle"),
        "source": ("Kerala Budget, Annual Plan statements and the Gender & Child and "
                   "Elderly budgets"),
        "source_url": man.get("index"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "reconciliation": {b: {"checked": len(chk), "failed": len(bad.get(b, []))}
                           for b, chk in sorted(checks.items())},
        "extraction_stats": stats,
        "schemes": len(out),
        # Two counts, because one word cannot carry both. 733 schemes are printed in the
        # plan with a figure of zero, which is the state saying the scheme exists and is
        # funded at nil this year. Calling those "with an allocation" would be true and
        # misleading, and calling them "without" would be false.
        "with_a_figure": sum(1 for r in out if r.get("be_lakh") is not None),
        "with_money": sum(1 for r in out if r.get("be_lakh")),
        "funded_at_nil": sum(1 for r in out if r.get("be_lakh") == 0),
        "with_objectives": sum(1 for r in out if r.get("objectives")),
        "unit": "lakh",
        "unit_note": ("Every figure here is rupees in LAKH. The Annual Plan prints its "
                      "earlier columns in lakh and its Budget Estimate 2026-27 column in "
                      "THOUSANDS, both labelled in the same header block, on 333 of its "
                      "491 table pages. Read as lakh, every one of those allocations would "
                      "have published at 100 times its real value and looked entirely "
                      "plausible. The unit is decided per page from that page's own header "
                      "and normalised here."),
        # One known bad join, recorded rather than patched. "Research and Development
        # Institutions under KSCSTE" matches "KSCSTE Research Fellowship" because both
        # names literally contain KSCSTE, so the acronym rule fires on a shared FUNDER
        # rather than a shared scheme. Ten of the eleven joins on this corpus are right and
        # this is the eleventh.
        #
        # Not fixed, deliberately. The only rules that would reject it also reject MGNREGA
        # against its own expansion and PMAY against PMAY Urban, which are the cases the
        # acronym rules exist for. And the direction of this error is the safe one: a false
        # MATCH means a Kerala scheme is treated as present on myScheme and is therefore
        # NOT claimed absent, so it costs one under-reported absence rather than one false
        # accusation. That is the asymmetry this project is built on.
        "known_bad_joins": [{
            "kerala": "Research and Development Institutions under KSCSTE",
            "myscheme": "KSCSTE Research Fellowship",
            "why": ("Both names contain the written acronym KSCSTE, so the match is on a "
                    "shared funding council rather than a shared scheme."),
            "effect": ("Under-reports absence by one. Left unfixed because every rule that "
                       "rejects it also rejects MGNREGA against its expansion."),
        }],
        "caveat": ("The Annual Plan is the state's plan scheme list, so a scheme funded "
                   "outside the plan does not appear. Allocations are not summed across "
                   "books: the Gender, Child and Elderly books slice the same provision by "
                   "who benefits, so the Annual Plan figure wins and the others only fill "
                   "a gap. The number here is a floor on Kerala's schemes, never a total."),
        "entries": out,
    })
    return out, per_book, checks, bad, stats, man, date


def main():
    ap = argparse.ArgumentParser(description="Parse the archived Kerala budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, checks, bad, stats, man, date = run(a.date)
    print(f"kerala snapshot {date}")
    for b in sorted(per_book):
        n = len(checks.get(b) or ())
        nb = len(bad.get(b) or ())
        print(f"    {b:<14}{per_book[b]:>6} scheme rows   "
              f"{n - nb}/{n} printed totals reconcile")
        print(f"                  {stats[b]}")
    print(f"  {len(out)} distinct schemes")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    print(f"     with objectives    {sum(1 for r in out if r.get('objectives')):>6}")


if __name__ == "__main__":
    main()
