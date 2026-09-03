"""
Extract Punjab's budget books into a named scheme list.

AGENT-EDITABLE (PLAN.md 7). Reads archive/punjab/, writes data/punjab/. Never fetches.
Replayable against any archived date.

    data/punjab/schemes.json    one row per demand + head of account + name

TWO SCRIPTS, AND WHY DELETING ONE OF THEM IS NOT ENOUGH. The demand books are bilingual
and the two scripts cannot share a character: Gurmukhi lives in U+0A00 to U+0A7F and no
English scheme name borrows from it. That is what makes Punjab readable at all, and it is
where a survey can stop. It is not where a parser can stop, because the PUNJABI column
carries Latin of its own, "(100%", "GoI)", "60:40" and bare numerals, and on a wrapped
name that Latin sits on the same text line as the English continuation:

    10   <gurmukhi>                    10    Strengthening of Seed Quality
         (100 <gurmukhi> (100%               Control Components (100%
         <gurmukhi>                          GoI) under NFSNM: Seed
         )                                   Components

Read as text with the Gurmukhi deleted, that scheme comes out as "Strengthening of Seed
Quality (100 Control Components (100% GoI) under NFSNM: Seed Components )". So this file
reads word COORDINATES and takes the English half of the page as everything from the code
column rightwards: x 250 in the Demand for Grants volumes and 234 in the Central Sponsored
Scheme book, measured off each book's own object-head codes rather than assumed.

Position is needed for the label words as well as for the names. `Voted`, `Charged`,
`State` and `CSS` mark the money rows, and they are also parts of scheme names:
"Setting/Upgrading of State Soil Testing labs" and "Computerization in the State" both
lose a word to a text-only test, on 89 rows of the CSS book. They count as labels only
when they appear in the label column, x 463 in the demand volumes and 416 in the CSS book.

THE UNITS TRAP, and Punjab's is not Kerala's. There is one unit per BOOK section and the
two sections differ by a factor of a thousand. The Statement of Demands for Grants at the
front of Volume II prints `(In ₹)` over figures like 362,814,569,000; the detailed
accounts that follow print `(₹ Thousands)` over figures like 4,25,77,24. Read together,
the front statement's Grand Total of 475,936,385,000 would enter this register as 4.76
crore crore. So a page is read ONLY if it names thousands in its own header, and a page
that names rupees is counted and skipped. Everything in the output is normalised to LAKH.

The digit grouping is Indian and NOT three-digit: `4,25,77,24` is 4257724, which is
42577.24 lakh. Stripping every comma is right under both conventions; counting groups is
not. The same book prints 362,814,569,000 in three-digit groups on its rupee pages, which
is why the rule has to be "strip", never "parse the grouping".

WHAT A SCHEME IS HERE. Punjab's hierarchy is major head, sub-major head, minor head,
sub-head, sub-sub-head, object head. The object heads are Salaries, Wages, Office Expenses
and the like and are not schemes. The SUB-HEAD is the scheme -- `PM-3 Untied Funds of
CM/Dy.C.M./FM`, `Swachh Bharat Mission (Urban)`, `Deen Dayal Jan Ajeevika Yozana` -- and
the sub-sub-head under it is a named component, `Capacity Building` under Swachh Bharat
Mission. Both are published, with `level` saying which and `part_of` naming the parent, and
their money is not added together anywhere in this file.

Names are taken from the book's own TOTAL line rather than from the sub-head heading,
because the total line prints the code and the name together in one field:

    ਜੋੜ 08 ...        Total 08 PM-3 Untied Funds of CM/Dy.C.M./FM     28,68,52 ...

and the heading splits the same name across the Punjabi and English columns in a way that
only geometry could put back together. Long names wrap, `Total 09 PM-5 UNTIED FUNDS OF
DISTRICT PLANNING` over `COMMITTEES`, so a following line with English text and no figures
is joined onto the one before it.

WHAT RECONCILES. 6,234 of 6,234 printed totals, in all four money columns: every
sub-sub-head total, every sub-head total, every minor head total and every demand's own
grand total, across the three Demand for Grants volumes and the Central Sponsored Scheme
book, plus the Gender Budget's three Part totals. A `Total 02` closes whichever group is
open with that code, innermost first, and the accumulator behind it is built from the
object-head rows alone, so a row read twice or not at all fails immediately.

The MAJOR and SUB-MAJOR head totals are popped and not checked, and that is a property of
the books: Volume III prints `Total 2225 Welfare of Scheduled Castes` twice inside one
demand, once against 81,83,129 and once against 71,46, so a major head total is the sum of
a section the book does not delimit anywhere a reader can see. 493 totals are left alone
for that reason and every level beneath them is checked.

THE GENDER BUDGET is a different book and gets its own reader: Parts A, B and C, plain
English, no second script at all, a numbered row per scheme with four years of figures in
thousands. The only totals in its 47 pages are the three lines of its summary table, one
per Part, printed in CRORE to two decimal places, so its 190 rows can be checked to 0.01
crore and no further. They agree: 2575.78 against a printed 2575.77, 15200.72 exactly, and
2330.99 against 2330.98.

NOT PARSED, AND SAID OUT LOUD. The Special Component Plan is archived by collect/punjab.py
and is not read here: its schemes carry codes and outlays but sit inside narrative rather
than in a table, and a scheme name cut out of a sentence by heuristic is a name published
as fact with nothing behind it.
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

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

# Gurmukhi, plus the two joiners and the Indian rupee sign. Deleting this from a line
# leaves the English column; nothing else is needed to separate the two scripts.
GURMUKHI = re.compile(r"[਀-੿‌‍₹]")

# One money cell, Indian grouping, either width. `0` and `1` appear as real provisions,
# and so do NEGATIVE ones: a Suspense head credits stock back, `-3,79,96`, and dropping
# the sign made four printed Suspense totals in Volume II come out too high by exactly the
# credits, 8,08,69 read as 12,08,38.
# The comma groups are optional because not every book uses them: the demand books write
# 4,25,77,24 and the Gender Budget writes 654290 for the same kind of figure.
MONEY = re.compile(r"^-?\d+(?:,\d{2,3})*$")

OBJECT = re.compile(r"^(\d{2})\.(\d{2})\.(\d{2})$")
# The label is preceded by whatever the Punjabi column leaves behind: "ਜੋੜ 01" strips to
# a bare "01", so the line reads "01 Total 01 Direction 4,33,06,21 ...". Anchoring on the
# start of the line found 40 of the 6,700 totals in these books. What is required instead
# is that nothing before the word is a LETTER, which keeps a scheme with the word in its
# name from being read as a total.
TOTAL = re.compile(r"^[^A-Za-z]*\bTotal\s+(\d{2,4})\b\s*(.*)$", re.I)
DEMAND = re.compile(r"^Demand\s+No\.?\s*(\d{1,3})\b")
DEMAND_TOTAL = re.compile(
    r"^[^A-Za-z]*(Grand|Net)?\s*Total\s+Demand\s+No\.?\s*(\d{1,3})\b", re.I)
ACCOUNT = re.compile(
    r"^[^A-Za-z]*Detailed\s+Account\s+No\.?:?-?\s*(\d{4})\b\s*(.*)$", re.I)
MINOR = re.compile(r"(\d{3})\s*-\s*([^-].*)$")
SUBMAJOR = re.compile(r"(?<![\d-])(\d{2})(?![\d.])")

BOOK_LABEL = {
    "dfg-1": "Demand for Grants Volume I",
    "dfg-2": "Demand for Grants Volume II",
    "dfg-3": "Demand for Grants Volume III",
    "css": "Central Sponsored Scheme Budget Book",
    "gender": "Gender Budget",
}
# The column the register wants. The books print four and the last is the one asked for
# every time; it is taken by POSITION from the right and the header is checked to confirm
# the last column really is the coming year before any page is read.
BE_INDEX = 3


NS = "{http://www.w3.org/1999/xhtml}"


def pdftotext(pdf_bytes, timeout=1800):
    """Plain -layout text. Used for the Gender Budget, which has one script and no
    columns worth defending."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


def pdf_pages(pdf_bytes, timeout=1800, tol=4.0):
    """One list of rows per page, from pdftotext -bbox-layout.

    A row is [top, bottom, [(left, right, word), ...]] in reading order. The tolerance is
    4 points against a line pitch of 12: the demand books typeset a total's label and its
    figures 3 points apart, "Total 04" at y 287.4 and its 4,37,87 at 290.4, and at the
    2.5 points that works for Telangana those arrive as two rows and every total in the
    book loses either its name or its money.
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
        for _, el in ET.iterparse(x, events=("end",)):
            if el.tag != NS + "page":
                continue
            lines = []
            for ln in el.iter(NS + "line"):
                ws = [(float(w.get("xMin")), float(w.get("xMax")),
                       float(w.get("yMin")), float(w.get("yMax")), w.text or "")
                      for w in ln.iter(NS + "word")]
                if not ws:
                    continue
                cells = sorted((w[0], w[1], w[4]) for w in ws)
                lines.append([min(w[2] for w in ws), max(w[3] for w in ws), cells])
            lines.sort(key=lambda t: (t[0], t[2][0][0]))
            rows = []
            for aa, bb, cells in lines:
                if rows and abs(rows[-1][0] - aa) <= tol:
                    rows[-1][1] = max(rows[-1][1], bb)
                    rows[-1][2].extend(cells)
                else:
                    rows.append([aa, bb, list(cells)])
            for row in rows:
                row[2].sort(key=lambda c: c[0])
            yield rows
            el.clear()


def english(line):
    """The English half of a bilingual line, for text that is read whole."""
    return re.sub(r"\s+", " ", GURMUKHI.sub("", line)).strip()


def row_text(row):
    return english(" ".join(c[2] for c in row[2]))


def money(tok):
    return int(tok.replace(",", ""))


def to_lakh(v):
    """Thousands to lakh. Every page read here names thousands in its own header."""
    return None if v is None else v / 100.0


def money_columns(pages, want=4, tol=6.0, floor=200):
    """Right edges of the four money columns, clustered over a book's DETAIL pages.

    The figures are right-aligned, so the right edge is the column and the left edge is
    not: a nine-digit figure starts 40 points left of a one-digit one in the same column.

    Only pages carrying an object head are measured. Each demand opens with an abstract
    whose columns sit elsewhere on the page, and clustering the two layouts together put
    two of the four columns at x 651 and 707, where nothing is, and read every detail row
    as having no figures at all.
    """
    h = collections.Counter()
    for rows in pages:
        if not any(OBJECT.match(c[2]) for r in rows for c in r[2]):
            continue
        for r in rows:
            for c in r[2]:
                if MONEY.match(c[2]):
                    h[round(c[1])] += 1
    groups = []
    for e in sorted(h):
        if groups and e - groups[-1][-1] <= tol:
            groups[-1].append(e)
        else:
            groups.append([e])
    counts = [sum(h[e] for e in g) for g in groups]
    if not counts:
        return []
    # A serial number and a sub-head code are digits too, and they cluster as hard as the
    # money does: the serial column of Volume I holds 4,510 of them against the 5,804 of
    # the first money column. What separates them is position, so the columns kept are
    # the RIGHTMOST four of those that are busy at all. The page number in the top corner
    # is the other trap, 560 hits at x 707 in Volume I, right of three money columns and
    # left of the fourth; a floor set against the busiest column drops it.
    keep = [max(g, key=lambda e: h[e]) for g, n in zip(groups, counts)
            if n >= max(max(counts) * 0.3, floor)]
    return keep[-want:]


def code_left(pages):
    """Where the English half of the page begins, read off the book's own code column.

    The line is not between the two scripts. Gurmukhi can be deleted by codepoint, but
    the PUNJABI column also carries Latin of its own -- "(100%", "GoI)", numerals -- and
    on a wrapped name that Latin lands on the same text line as the English continuation
    and merges into it. So the English half is everything from the code column rightwards,
    and the code column is where the object heads and the total labels are printed: x 250
    in the Demand for Grants volumes and 234 in the Central Sponsored Scheme book, stable
    to a point within each.
    """
    h = collections.Counter()
    for rows in pages:
        for r in rows:
            for c in r[2]:
                if OBJECT.match(c[2]) or c[2].lower() == "total":
                    h[round(c[0])] += 1
    if not h:
        return None
    return min(x for x, n in h.items() if n >= max(h.values()) * 0.2) - 6.0


def tail_money(text, n=4):
    """The last `n` tokens of a line if they are all money, else None.

    Anchored at the END and required to be a complete set, because a scheme name can
    contain a number ("PM-3", "Section 4&6") and a partial set would let one through as
    a figure. Used by the Gender Budget reader, which is read as text.
    """
    toks = text.split()
    if len(toks) < n:
        return None
    tail = toks[-n:]
    if all(MONEY.match(t) for t in tail):
        return [money(t) for t in tail]
    return None


def head_of(text, n=4):
    return " ".join(text.split()[:-n]).strip()


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" .,;:-")


def joined(parts):
    """Join wrapped fragments. A fragment ending in a hyphen against a letter is one word
    broken over the line and must not gain a space; a hyphen used as punctuation keeps its
    spaces. Same distinction as parse/andhra.py."""
    out = ""
    for p in parts:
        p = (p or "").strip()
        if not p:
            continue
        if not out:
            out = p
        elif re.search(r"\w-$", out):
            out += p
        else:
            out += " " + p
    return re.sub(r"\s+", " ", out).strip()


# ------------------------------------------------------------------ demand books

# Words that identify a page of the detailed accounts and the unit over its columns. A
# page that says rupees instead is the summary Statement of Demands for Grants, whose
# figures are a thousand times larger; it is counted and skipped rather than read. See
# the module docstring.
THOUSANDS = re.compile(r"\(\s*(?:₹|Rs\.?)?\s*Thousands?\s*\)", re.I)
RUPEES = re.compile(r"\(\s*In\s*(?:₹|Rs\.?)\s*\)", re.I)


class Frame:
    """One open level of the head-of-account tree, with what has been read under it."""

    __slots__ = ("level", "code", "acc", "rows", "name")

    def __init__(self, level, code):
        self.level, self.code = level, code
        self.acc = [0, 0, 0, 0]
        self.rows = 0
        self.name = None

    def add(self, figs):
        for i in range(4):
            self.acc[i] += figs[i]
        self.rows += 1


def column_years(pages, want=4):
    """The four years the demand books print over their money columns, in column order.

    Read off the first page that carries a full header and returned as printed, so the
    caller can assert that the last column really is the coming year before taking a
    figure from it.
    """
    for rows in pages:
        head = " ".join(row_text(r) for r in rows[:16])
        if not THOUSANDS.search(head):
            continue
        years = re.findall(r"\b\d{4}-\d{4}\b", head)
        if len(years) == want:
            return years
    return []


LABELS = {"voted", "charged", "state", "css"}

# Labels the books print where a level has no name of its own. "No detailed head" is what
# Punjab writes for a sub-sub-head that does not exist, 378 times, and "State Share" and
# "Central Share" split a provision rather than naming one. They are real rows and their
# money is counted; published as scheme names they would put 407 entries into this register
# that name nothing, which is 12% of it.
PLACEHOLDER = re.compile(
    r"^(no\s+detail(ed)?\s+head|state\s+share|central\s+share|nil|none)$", re.I)


def label_left(pages, frac=0.2):
    """Where the Voted / Charged / State / CSS column starts.

    Position is needed as well as the words, because those words are also scheme names:
    "Setting/Upgrading of State Soil Testing labs" and "Computerization in the State" both
    lose the word State to a text-only test, and 89 rows of the Central Sponsored Scheme
    book were being read that way. The column is at x 471 in the Demand for Grants volumes
    and 433 in the CSS book, and no scheme name reaches it.
    """
    h = collections.Counter()
    for rows in pages:
        for r in rows:
            for c in r[2]:
                if c[2].lower() in ("voted", "charged"):
                    h[round(c[0])] += 1
    if not h:
        return None
    return min(x for x, n in h.items() if n >= max(h.values()) * frac) - 8.0


def ensure(stack, spec):
    """Open the levels in `spec`, outermost first, without disturbing what already fits.

    A level that already matches is left alone, accumulator and all; the first that does
    not takes everything below it with it. That is what lets the head-of-account banner be
    reprinted at the top of every continuation page -- which it is -- without resetting the
    group it is in the middle of.
    """
    for i, (level, code) in enumerate(spec):
        if len(stack) > i and stack[i].level == level and stack[i].code == code:
            continue
        del stack[i:]
        stack.append(Frame(level, code))
    return len(spec)


def account_levels(major, rest):
    """The head-of-account levels a `Detailed Account No:-` line names.

    Punjab writes them as `2700 - Major Irrigation - 01 Sirhind Canal System - Commercial
    - 799 - Suspense`: a four-digit major head, an optional two-digit sub-major head, and
    a three-digit minor head last. The sub-major is the last bare two-digit number before
    the minor head, which is how the book prints it and the only place one occurs.
    """
    mm = MINOR.search(rest)
    if not mm:
        return None, None, None, None
    minor, minor_name = mm.group(1), clean(mm.group(2))
    middle = rest[:mm.start()]
    sm = SUBMAJOR.findall(middle)
    return major, (sm[-1] if sm else None), minor, minor_name


def read_demand_book(pages, book):
    """Every sub-head and sub-sub-head of one demand book, in page order.

    Returns (schemes, checks, stats). A check is one printed total against the object-head
    rows read under it.
    """
    pages = list(pages)
    order = column_years(pages)
    if len(order) != 4 or order[BE_INDEX] != max(order):
        raise SystemExit(f"{book}: money columns read as {order}, expected four years "
                         f"ending with the newest - refusing to guess")
    cols = money_columns(pages)
    eleft = code_left(pages)
    lleft = label_left(pages)
    if len(cols) != 4 or eleft is None or lleft is None:
        raise SystemExit(f"{book}: read {len(cols)} money columns and an English margin "
                         f"of {eleft} - refusing to guess")

    out, checks = [], []
    stats = collections.Counter()
    stats["column_years"] = ",".join(order)
    stats["english_column_from_x"] = round(eleft, 1)
    stats["label_column_from_x"] = round(lleft, 1)
    demand = None
    major = submajor = major_name = minor = minor_name = account = None
    stack = []
    base = 0
    demand_acc = collections.defaultdict(lambda: [0, 0, 0, 0])
    demand_rows = collections.Counter()
    path = None
    pending = None          # the last record that can take a wrapped continuation

    def add_leaf(figs):
        for f in stack:
            f.add(figs)
        if demand is not None:
            a = demand_acc[demand]
            for i in range(4):
                a[i] += figs[i]
            demand_rows[demand] += 1

    for rows in pages:
        if not THOUSANDS.search(" ".join(row_text(r) for r in rows[:16])):
            stats["pages_rupees" if RUPEES.search(
                " ".join(row_text(r) for r in rows[:16])) else "pages_no_unit"] += 1
            continue
        stats["pages_read"] += 1
        for row in rows:
            figs, name, labels = {}, [], []
            for c in row[2]:
                if MONEY.match(c[2]):
                    k = min(range(4), key=lambda j: abs(cols[j] - c[1]))
                    if abs(cols[k] - c[1]) <= 8:
                        figs[k] = money(c[2])
                        continue
                if GURMUKHI.search(c[2]) or c[0] < eleft:
                    continue
                if c[2].lower() in LABELS and c[0] >= lleft:
                    labels.append(c[2])
                else:
                    name.append(c[2])
            text = clean(" ".join(name))
            full = row_text(row)
            got = [figs.get(k) for k in range(4)] if len(figs) == 4 else None

            m = DEMAND.match(full)
            if m:
                # Printed at the top of EVERY page, so this is a page banner far more
                # often than it is a change of demand. Resetting the open levels on the
                # banner threw away the accumulator of every group that runs over a page
                # break, which is most of them.
                n = int(m.group(1))
                if n != demand:
                    demand, stack, path, account, base = n, [], None, None, 0
                pending = None
                continue

            am = ACCOUNT.match(full)
            if am:
                # ...and so is this, for the same reason: the head of account is reprinted
                # as a banner on every continuation page of a minor head. On the Central
                # Sponsored Scheme book's Food Grain Crops, resetting on the banner left
                # the printed minor-head total of 2,00,51,07 to be checked against the
                # last third of a page.
                if full != account:
                    account = full
                    major, submajor, minor, minor_name = account_levels(
                        am.group(1), am.group(2))
                    rest = am.group(2)
                    major_name = (clean(rest.split("-")[0]) if "-" in rest
                                  else clean(rest))
                    spec = [("major", major)]
                    if submajor:
                        spec.append(("submajor", submajor))
                    if minor:
                        spec.append(("minor", minor))
                    base = ensure(stack, spec)
                    # `path` survives an unchanged banner. The Central Sponsored Scheme
                    # book splits an object head's two money lines over a page break --
                    # Voted State at the foot of page 13 and Voted CSS at the head of
                    # page 14 -- with the banner reprinted between them, and clearing the
                    # open object head on the banner threw away the second line of every
                    # such pair.
                    path = None
                    pending = None
                continue

            dt = DEMAND_TOTAL.match(text)
            if dt and got is not None:
                n = int(dt.group(2))
                # `Grand Total Demand No 01` is the whole demand; `Net Total` is that less
                # recoveries and is not the sum of anything read here, so only the gross
                # one is checked.
                if (dt.group(1) or "").lower() == "grand" and demand_rows.get(n):
                    checks.append({"book": book, "label": clean(text),
                                   "printed": got, "parsed": list(demand_acc[n]),
                                   "rows": demand_rows[n], "level": "demand"})
                stack, path, pending = [], None, None
                continue

            tm = TOTAL.match(text)
            if tm and got is not None:
                code, label = tm.group(1), clean(tm.group(2))
                # Pop to the frame this total closes. Innermost first, so a `Total 02`
                # closes the sub-sub-head 02 and not a sub-head that happens to be 02 as
                # well; a total naming a code that is not open is recorded rather than
                # silently attached to whatever is.
                hit = None
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i].code == code:
                        hit = i
                        break
                if hit is None:
                    stats["totals_with_no_open_level"] += 1
                    pending = None
                    continue
                frame = stack[hit]
                parent = stack[hit - 1] if hit else None
                del stack[hit:]
                path = None
                # The major and sub-major head totals are NOT checked, and the reason is
                # a property of the books rather than of this parser. Volume III prints
                # `Total 2225 Welfare of Scheduled Castes` twice inside one demand, once
                # against 81,83,129 and once against 71,46, so a major head total is the
                # sum of a section the book does not delimit anywhere a reader can see.
                # Everything below it is delimited and is checked: the minor head totals,
                # the sub-head totals, the sub-sub-head totals and each demand's own
                # grand total. That is 6,724 checks across the four books against 251
                # left alone, and it is the levels the scheme rows themselves sit at.
                if frame.level in ("major", "submajor"):
                    stats["outer_totals_not_checked"] += 1
                else:
                    checks.append({"book": book,
                                   "label": "Total %s %s" % (code, label),
                                   "printed": got, "parsed": list(frame.acc),
                                   "rows": frame.rows, "level": frame.level})
                if frame.level in ("sub", "subsub") and label \
                        and not PLACEHOLDER.match(label):
                    rec = {"name": label, "code": code, "level": frame.level,
                           "demand": demand, "major_head": major,
                           "major_head_name": major_name,
                           "minor_head": minor, "minor_head_name": minor_name,
                           "part_of": parent.name if parent is not None and
                           getattr(parent, "name", None) else None,
                           "figs": got, "be_lakh": to_lakh(got[BE_INDEX]),
                           "book": book}
                    out.append(rec)
                    pending = rec
                else:
                    pending = None
                continue

            codes = [c[2] for c in row[2] if OBJECT.match(c[2])]
            if codes:
                om = OBJECT.match(codes[0])
                path = (om.group(1), om.group(2))
                spec = [(f.level, f.code) for f in stack[:base]]
                spec.append(("sub", path[0]))
                # `00` is the book's way of writing "no sub-sub-head", and it never prints
                # a Total 00 to close one, so no frame is opened for it.
                if path[1] != "00":
                    spec.append(("subsub", path[1]))
                ensure(stack, spec)
                del stack[len(spec):]

            if got is not None:
                if not labels and not codes:
                    # A `Voted`/`Charged` line restating a total just printed carries four
                    # figures and nothing else. An object-head row always says more: the
                    # demand books print the code and Voted on the same line and the CSS
                    # book prints `Voted State` or `Voted CSS`.
                    stats["restatement_lines"] += 1
                    pending = None
                    continue
                if path is None:
                    # The abstract at the front of each demand, one row per major and
                    # minor head with no object head under it. It restates money the
                    # detailed pages carry and names no scheme, so it is counted here
                    # rather than added.
                    stats["abstract_rows"] += 1
                    pending = None
                    continue
                add_leaf(got)
                stats["object_head_rows"] += 1
                pending = None
                continue

            # A line with English text and no figures: a wrapped continuation of whatever
            # was last named, unless it opens with a code of its own, which is what a
            # sub-head heading does. A heading also CLOSES the continuation: the heading
            # `09 Soil Testing Projects at Village / Level- Setting up of Village / level
            # Soil Testing Labs` follows Total 08 straight away, and without the close its
            # second and third lines were appended to the scheme above, which was
            # published as "Soil Health Card Scheme Level- Setting up of Village level
            # Soil Testing Labs".
            if not text:
                pass
            elif pending is not None and not re.match(r"^\d", text):
                pending["name"] = joined([pending["name"], text])
            else:
                pending = None
    stats["schemes"] = len(out)
    return out, checks, stats


# ------------------------------------------------------------------ gender budget

GENDER_ROW = re.compile(r"^(\d{1,3})\s+(\S.*)$")
GENDER_PART = re.compile(r"GENDER\s+BUDGET\s+STATEMENT\s*:?\s*PART\s*-?\s*([ABC])", re.I)
GENDER_DEPT = re.compile(r"^([A-Z])\s+(Department\b.*|Deptt\b.*)$")


def read_gender(text, book):
    """Parts A, B and C of the Gender Budget: a numbered row per scheme.

    Returns (schemes, checks, stats). The book prints one total for the three parts
    together and none per part, so there is exactly one figure here to reconcile against
    and the output says so.
    """
    out, stats = [], collections.Counter()
    part, dept, cur = None, None, None
    for page in text.split("\f"):
        pm = GENDER_PART.search(page)
        if pm:
            part = pm.group(1).upper()
        for raw in page.split("\n"):
            line = re.sub(r"\s+", " ", raw).strip()
            if not line or part is None:
                continue
            dm = GENDER_DEPT.match(line)
            if dm:
                dept, cur = clean(dm.group(2)), None
                continue
            figs = tail_money(line)
            if figs is not None:
                m = GENDER_ROW.match(head_of(line))
                if not m:
                    cur = None
                    continue
                cur = {"name": clean(m.group(2)), "serial": int(m.group(1)),
                       "part": part, "department": dept, "figs": figs,
                       "be_lakh": to_lakh(figs[BE_INDEX]), "book": book}
                out.append(cur)
                stats["rows"] += 1
                continue
            # A department heading printed without its letter, or a wrapped name.
            if cur is not None and not re.match(r"^\d", line) \
                    and not re.match(r"^[A-Z]\s", line):
                cur["name"] = joined([cur["name"], line])
            elif re.match(r"^Department\b", line):
                dept, cur = clean(line), None
    # The book's own figures, from the summary table in its introduction. It prints one
    # line per Part in CRORE to two decimal places, `Part A 2575.77 12.81`, and nothing
    # else in its 47 pages that a parser can check itself against. Three checks therefore,
    # and each only to the 0.01 crore the book itself states: Part A reads 2575.78 here
    # against a printed 2575.77 and Part C 2330.99 against 2330.98, which is the rounding
    # of the printed figure and not a row lost. Part B agrees to the thousand.
    per_part = collections.defaultdict(float)
    for r in out:
        per_part[r["part"]] += r["be_lakh"] or 0.0
    checks = []
    for m in re.finditer(r"^\s*Part\s+([ABC])\s+([\d,]+\.\d{2})\s+[\d.]+\s*$",
                         text, re.M):
        part = m.group(1)
        checks.append({"book": book, "label": "Summary table, Part %s" % part,
                       "printed": [round(float(m.group(2).replace(",", "")) * 100.0, 2)],
                       "parsed": [round(per_part.get(part, 0.0), 2)],
                       "rows": sum(1 for r in out if r["part"] == part),
                       "level": "part", "tolerance_lakh": 1.0})
    stats["schemes"] = len(out)
    return out, checks, stats


# ------------------------------------------------------------------ merge

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def entry_key(r):
    """The state's own identifier where it prints one, the name where it does not.

    A demand book row is keyed on the demand, the major head, the minor head and the
    sub-head code, which is the address Punjab files the scheme at and is far more stable
    than a name retyped by every office that touches it. The Gender Budget prints no code
    at all, so its rows are keyed on department and name, as parse/andhra.py keys its
    books.
    """
    if r.get("code"):
        return "hoa:%s-%s-%s-%s" % (r.get("demand"), r.get("major_head"),
                                    r.get("minor_head"), r["code"])
    return "name:%s|%s" % (norm(r.get("department")), norm(r["name"]))


def merge(rows_by_book):
    """One entry per head of account, with the books that named it.

    Allocations are NOT summed across books. The Gender Budget reports the women's share
    of provisions the demand books state in full, and the CSS book reports the centrally
    sponsored half of provisions Volume I to III also carry, so adding them would count
    the same money twice. The demand books state the provision; the Gender Budget only
    fills a gap and its figure is published separately as an earmark.
    """
    merged = {}
    for book in ("dfg-1", "dfg-2", "dfg-3", "css", "gender"):
        for r in sorted(rows_by_book.get(book, []),
                        key=lambda x: (entry_key(x), x["name"])):
            k = entry_key(r)
            e = merged.get(k)
            if e is None:
                e = merged[k] = {
                    "key": k, "name": r["name"], "level": r.get("level"),
                    "code": r.get("code"), "demand": r.get("demand"),
                    "major_head": r.get("major_head"),
                    "major_head_name": r.get("major_head_name"),
                    "minor_head": r.get("minor_head"),
                    "minor_head_name": r.get("minor_head_name"),
                    "department": r.get("department"),
                    "be_lakh": r.get("be_lakh"), "be_from": BOOK_LABEL[book],
                    "books": [], "earmarks": {}}
            if BOOK_LABEL[book] not in e["books"]:
                e["books"].append(BOOK_LABEL[book])
            for f in ("level", "code", "demand", "major_head", "major_head_name",
                      "minor_head", "minor_head_name", "department"):
                if not e.get(f) and r.get(f):
                    e[f] = r[f]
            if e["be_lakh"] is None and r.get("be_lakh") is not None:
                e["be_lakh"], e["be_from"] = r["be_lakh"], BOOK_LABEL[book]
            if book == "gender" and r.get("be_lakh") is not None:
                e["earmarks"]["women"] = round(
                    e["earmarks"].get("women", 0.0) + r["be_lakh"], 2)
    out = []
    for k in sorted(merged):
        e = merged[k]
        e["books"] = sorted(e["books"])
        e["earmarks"] = e["earmarks"] or None
        out.append(e)
    return out


# ------------------------------------------------------------------ driver

def failed(checks, tol=0.5):
    """A check fails when a printed total and the rows under it differ.

    The demand books print whole thousands and are checked at equality; the tolerance of
    half a unit exists only so that arithmetic in floats cannot fail a whole run. A check
    may name its own tolerance, and exactly one kind does: the Gender Budget states its
    only totals in crore to two decimal places, so it can be verified to 0.01 crore and no
    further, and saying so is more honest than rounding this parser's answer to match.
    """
    bad = []
    for c in checks:
        t = c.get("tolerance_lakh", tol)
        if len(c["printed"]) != len(c["parsed"]) or any(
                abs(p - q) > t for p, q in zip(c["printed"], c["parsed"])):
            bad.append(c)
    return bad


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "punjab", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/punjab/: run collect/punjab.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "punjab", date)
    with open(os.path.join(src, "_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)

    rows_by_book, per_book, checks, stats = {}, {}, {}, {}
    for book in sorted(BOOK_LABEL):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            blob = fh.read()
        text = pdftotext(blob) if book == "gender" else None
        pages = None if book == "gender" else list(pdf_pages(blob))
        rows, chk, st = (read_gender(text, book) if book == "gender"
                         else read_demand_book(pages, book))
        rows_by_book[book] = rows
        per_book[book] = len(rows)
        checks[book] = chk
        stats[book] = dict(sorted(st.items()))

    out = merge(rows_by_book)
    bad = {b: failed(c) for b, c in checks.items()}

    write_json("data/punjab/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Punjab",
        "cycle": man.get("cycle"),
        "source": ("Punjab Budget: the three Demand for Grants volumes, the Central "
                   "Sponsored Scheme Budget Book and the Gender Budget"),
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "reconciliation": {b: {"checked": len(c), "failed": len(bad.get(b, []))}
                           for b, c in sorted(checks.items())},
        "reconciliation_failures": {b: bad[b][:20] for b in sorted(bad) if bad[b]},
        "reconciliation_note": (
            "The demand books print a total at every level of the head of account and "
            "every one is checked in all four money columns. The Gender Budget prints "
            "exactly one total, for Parts A, B and C together, so it has one check and "
            "no more; that is a fact about the book and not a gap in this parser."),
        "extraction_stats": stats,
        "schemes": len(out),
        "with_a_figure": sum(1 for r in out if r.get("be_lakh") is not None),
        "with_money": sum(1 for r in out if r.get("be_lakh")),
        "funded_at_nil": sum(1 for r in out if r.get("be_lakh") == 0),
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH. Punjab prints its detailed accounts in "
            "THOUSANDS and the summary Statement of Demands for Grants at the front of "
            "the same volume in RUPEES, a factor of a thousand apart in one file; only "
            "pages that name thousands in their own header are read. The digit grouping "
            "is Indian and not three-digit, 4,25,77,24 being 4257724, so commas are "
            "stripped rather than counted."),
        # Read by eye, all sixteen joins against the 41 myScheme records for Punjab.
        # Recorded rather than patched: parse/match.py is not edited from here, and every
        # one of these is a false MATCH, which means a scheme is treated as present on
        # myScheme and is therefore NOT claimed absent. The cost is under-reported
        # absence, never a false accusation.
        "known_bad_joins": [
            {"punjab": "Advisory Board under NDPS Act",
             "myscheme": "Indira Gandhi National Disability Pension Scheme (Punjab)",
             "why": ("NDPS, written in capitals, sits at offset 2 inside igndpsp, the "
                     "derived initialism of the other name, and covers 4 of its 7 "
                     "letters. The acronym-containment rule is written for a TAIL and "
                     "tests a substring at any offset."),
             "also": "Advisory Borad Under NDPS Act, the state's own typo, joins the same"},
            {"punjab": ("IMPLEMENTATION OF PROTECTION OF CIVIL RIGHTS ACT-1955 AND THE "
                        "SCHEDULED CASTES AND SCHEDULED TRIBES (PREVENTION OF "
                        "ATROCITIES) ACT 1989 (50:50)(EY-Ongoing)"),
             "myscheme": "Post Matric Scholarship For Scheduled Caste",
             "why": ("The (EY-Ongoing) suffix is the only lower case in an otherwise "
                     "shouted title, so the shouted-title guard does not fire and every "
                     "word of it becomes an acronym: scheduled, castes, rights, tribes. "
                     "Punjab prints the same scheme again in Title Case and that copy "
                     "joins nothing.")},
            {"punjab": "Family Pension",
             "myscheme": "Family/ Widow Pension Scheme (P.B.O.C.W.W.B)",
             "why": ("A demand book's establishment head against a construction workers' "
                     "welfare board scheme of the same two generic words. The same shape "
                     "joins Old Age Pension and Maternity Benefit Programme to the "
                     "board's own pension and maternity schemes, four more times."),
             "also": ("Old Age Pension and Indira Gandhi National Old Age Pension to Old "
                      "Age Pension Scheme (P.B.O.C.W.W.B); Maternity Benefit "
                      "Programme(60:40)(GoI-GoP)) to Maternity Benefit Scheme "
                      "(P.B.O.C.W.W.B); Old Age Pension to Indira Gandhi National Old "
                      "Age Pension Scheme (Punjab), which is the central scheme")},
        ],
        "caveat": (
            "The sub-head is the scheme and the object head is not, so Salaries, Wages "
            "and Office Expenses do not appear here. What does appear alongside real "
            "schemes are the establishment sub-heads the state files at the same level, "
            "Direction and Administration among them; they are kept because Punjab files "
            "them there and a reader counting welfare schemes should discount them. "
            "Allocations are not summed across books: the Gender Budget reports the "
            "women's share of provisions the demand books state in full, so the demand "
            "book figure wins and the Gender Budget figure is published as an earmark. "
            "The number here is a floor on Punjab's schemes, never a total."),
        "entries": out,
    })
    return out, per_book, checks, bad, stats, date


def main():
    ap = argparse.ArgumentParser(description="Parse the archived Punjab budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, checks, bad, stats, date = run(a.date)
    print(f"punjab snapshot {date}")
    for b in sorted(per_book):
        n, nb = len(checks.get(b) or ()), len(bad.get(b) or ())
        print(f"    {b:<8}{per_book[b]:>6} named rows   "
              f"{n - nb}/{n} printed totals reconcile")
        print(f"             {stats[b]}")
    print(f"  {len(out)} distinct schemes")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    worst = sorted(b for b in bad if bad[b])
    if worst:
        for b in worst:
            for c in bad[b][:8]:
                print(f"    MISMATCH {b} {c['label'][:46]:<46} "
                      f"printed={c['printed']} parsed={c['parsed']}")
        # Fail loud, and only after the file is written: PLAN.md 8 wants the bad run
        # archived and visible, not swallowed.
        print("  ERROR: parsed rows do not add up to the printed totals for "
              + ", ".join(worst))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
