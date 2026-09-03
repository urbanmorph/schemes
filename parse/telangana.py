"""
Extract Telangana's Volume VII scheme books into a named scheme list.

AGENT-EDITABLE (PLAN.md 7). Reads archive/telangana/, writes data/telangana/. Never
fetches. Replayable against any archived date.

    data/telangana/schemes.json    one row per department + scheme name

Three books, two layouts, one unit.

    pragathi   Volume VII/1, the state's own scheme list. 84 table pages headed "List of
               Schemes included in the Pragathi Paddu 2026-27", six columns: Sl.No, the
               name, the head of account and three years of figures.
    scsdf      Volume VII/2, seven columns: Sl.No, department or scheme, and five money
               columns (State Sector, SNA-SPARSH, matching share, Finance Commission,
               total).
    stsdf      Volume VII/3, the same shape with six money columns and no column-number
               strip to anchor them.

WHY THIS READS COORDINATES AND NOT TEXT. Every scheme name in these books is a table cell
that is VERTICALLY CENTRED in its row, so a two-line name puts one line above the row's
figures and one below, and a three-line name puts the figures on the middle line. Read
line by line, the figures belong to no name and the name belongs to no figures:

        Assistance to Small and Marginal Farmers
    5   towards Premium for Crop Insurance     2401-110-25-05   98111.00
        Scheme

That is one scheme, "Assistance to Small and Marginal Farmers towards Premium for Crop
Insurance Scheme", and its allocation is 98111.00. Measured on the 2026-27 book: 734 of
the rows carrying money have a name that runs over more than their own line, and 683 of
those put NO part of the name on the money row at all. A reader that takes the money
row's text as the name loses 683 names outright and truncates 51 more.

HOW THE CELL IS PUT BACK TOGETHER, and why the obvious rule fails. Nearest-anchor does
not work: on page 34 the line "Assistance to Small and Marginal Farmers" sits 9.35 points
below scheme 4's figures and 10.05 above scheme 5's, so proximity gives it to scheme 4,
which is wrong. The rule that does work is SYMMETRY: the cell is centred, so a scheme
that has k unclaimed name lines above its figures has exactly k below, and the assignment
is made left to right so that each scheme claims its own before the next one can.

That leaves the group headings, and they are why this file carries a list of them. "State
Sector Schemes", "Matching State Share" and "Centrally Sponsored Schemes" are printed as
bare lines in the name column with no figures beside them, exactly like a wrapped name
fragment. Left in the pool they are claimed by the first scheme below them, and because
the symmetric rule then also claims one line too many BELOW, the error cascades down the
page: on page 68 one swallowed heading corrupted four consecutive scheme names. Removing
the 237 heading lines first, and then the fixes below it, leaves 21 unassigned name lines
in the whole 84-page book; they are listed in the output under unassigned_name_lines and
most of them are department headings the table does not number.

THE UNIT. Both layouts print one unit for the whole page and this file reads it off the
page rather than assuming it: "Rs.Lakh" on the Pragathi Paddu, "(Rs. in Lakhs)" on the
two fund volumes. Every figure in the output is therefore rupees in LAKH. The trap here
is not two units in one book, as it is in Kerala; it is the Indian digit grouping. The
STSDF writes 1487441.29 as `14874,41.29` on one page and as `14,87,441.29` on another,
the same number under two conventions, so a parser that strips commas is right and a
parser that assumes a three-digit group is not.

WHICH COLUMN IS 2026-27. The Pragathi Paddu's scheme pages print the header "Budget
Estimate 2025-26 / Budget Estimate 2025-26 / Budget Estimate 2026-27" over their three
money columns. The middle one is not a budget estimate: the sector-wise section at the
front of the same book prints the same three columns as "Budget Estimates 2025-26 /
Revised Estimates 2025-26 / Budget Estimates 2026-27", and the arithmetic agrees, with
Supply of Seeds to Farmers at 10647.00 in the first and 7991.50 in the second, which is
exactly three quarters. The repeated word is the book's own error. The column taken here
is the LAST, 2026-27, on every page, which is unaffected either way.

WHAT A ROW MEANS. A scheme printed WITHOUT a head of account of its own is a parent: the
head-of-account rows under it are its breakdown, its own figure is their sum, and adding
both would count the money twice. A scheme printed WITH a head of account is a leaf and
stands alone. That distinction is not decorative: on page 37 the Horticulture centrally
sponsored block contains both shapes and the printed sub-total, 69915.89, only comes out
right when the seven rows under National Mission on Edible Oils are folded into it and
the two rows under National Beekeeping Honey Mission are not.

WHAT RECONCILES. Every printed total in all three books, in every money column: 239 in the
Pragathi Paddu including its Grand Total of 18431570.27 lakh over 1,890 rows, 39 in the
SCSDF including its Grand Total of 3774122.17, and 42 in the STSDF. 320 of 320. Getting
there is what found the two things about these books a reader has to know, and both are
recorded against the code that handles them: a scheme printed without a head of account
is a parent whose breakdown may carry serial numbers and names of its own, and it ends
where its children add up to it and nowhere else; and the Irrigation chapter wraps heads
of account so wide that the money row is left with nothing beside it, which is a
different thing from an unlabelled sub-total that must not be counted at all.

WHAT IS IN HERE THAT IS NOT A WELFARE SCHEME. The Pragathi Paddu is the state's scheme
expenditure volume and it files establishment heads at the same level as schemes:
"Governor Secretariat", "Raj Bhavan Gardens", "Furniture Estt", "Entertainment
Expenditure", "Public Service Commission". They are kept, because the state files them
here and removing them would be this project editing a state's own list, and the caveat
in the output says so. A reader counting welfare schemes should discount them.
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

NS = "{http://www.w3.org/1999/xhtml}"

# One money cell. Telangana prints plain figures with the Indian digit grouping, which is
# not three-digit: `14874,41.29` and `14,87,441.29` are the same number in the same book,
# so every comma is stripped and no group width is assumed.
#
# The two decimal places are required, not optional. All three books print them and a
# serial number never has one, and that is what keeps the Sl.No column out of the money
# column clustering: without it "1", "2" and "3" cluster as a money column of their own
# and the STSDF's real columns are read one place to the left.
MONEY = re.compile(r"^-?[\d,]*\d\.\d{1,2}$")

# A head of account. Telangana writes four levels, 2401-102-25-07, and five where the
# major head is subdivided, 2415-01-120-25-04. The Irrigation chapter also prints ranges,
# `4700-01-108-25-26,27`, and wraps them over two lines, so anything in the head-of-
# account column is kept as text and only this shape is treated as a canonical head.
HOA = re.compile(r"^\d{4}(?:-\d{2})?-\d{3}-\d{2}-\d{2}$")

SLNO = re.compile(r"^\d{1,4}\.?$")
_TOTAL_WORD = re.compile(r"\btotals?\b", re.I)
_GRAND = re.compile(r"^\s*grand\s+total", re.I)


_ARABIC = re.compile(r"^\d{1,4}\.?$")


def is_total(name, slno):
    """Is this row one of the book's own printed totals?

    Not a prefix test. The STSDF prints "HOD Total" and "Department Total" and the SCSDF
    ends with "Departments Total", none of which begins with the word, and a prefix test
    let all three through as if they were schemes: the SCSDF's grand total came out at
    exactly twice the printed figure, because the department totals it is the sum of were
    being added to it.

    The structural half of the test is what makes the loose word match safe. Every scheme
    row in all three books carries a serial number in its own column and no total row
    does, so a row with the word "total" in it and no serial beside it is a total. A
    scheme called "Total Sanitation Campaign" would still be read as a scheme, because it
    is numbered.
    """
    if not name:
        return False
    # A label that OPENS with the word is a total whatever is in the serial column: the
    # Pragathi Paddu numbers its sector totals, "5 Total - Edn, Sports, Art & Culture",
    # and read as a scheme that one carried 723616.41 lakh into the next block. `tota`
    # rather than the whole word, for the book's own typos: page 102 heads a total
    # "Tota- Labour & Employment". No scheme in any of the three books opens with the
    # word, checked; a scheme called Total Sanitation Campaign would need this revisited.
    if re.match(r"^\s*(sub\s*-?\s*)?total?s?\b", name, re.I):
        return True
    # Otherwise the word can sit anywhere, and the serial column is what makes that safe:
    # every scheme row in all three books is numbered and no total row is, so "HOD Total"
    # and "Departments Total" are totals and a numbered scheme with the word in its name
    # is not.
    return not _ARABIC.match((slno or "").strip()) and bool(_TOTAL_WORD.search(name))

# The lines the books print in the name column with no figures beside them that are NOT
# scheme names. Removing them before the cell assignment is what stops one swallowed
# heading from corrupting every scheme below it; see the module docstring. This is a
# judgement list and is deliberately visible as one. Every entry was read off the books:
# the first three account for 172 of the 200 lines removed.
GROUP_HEADINGS = {
    "state sector schemes", "state sector", "state schemes", "normal state plan",
    "matching state share", "centrally sponsored schemes", "centrally sponsored",
    "centrally assisted state plan schemes", "sna-sparsh",
    "rural infrastructure development fund (ridf)", "ridf", "ridf schemes",
    "aibp", "aibp schemes", "a i b p schemes",
    "externally aided project", "externally aided projects",
    "scsp plan schemes", "tribal sub plan schemes", "css schemes",
    "other developmental schemes", "tricor:", "engineering",
}

# Labels the books print in the name column of a BREAKDOWN row. They name the community
# share of a scheme's provision, not a scheme: SCSP is the Scheduled Caste Sub Plan and
# TSP the Tribal Sub Plan. Left in, the register would carry three schemes called
# General, SCSP and TSP with allocations attached to them.
COMPONENT_LABELS = {"general", "scsp", "tsp", "gen", "sc", "st", "sub plan"}

BOOK_LABEL = {
    "pragathi": "Pragathi Paddu (Scheme Expenditure)",
    "scsdf": "Scheduled Castes Special Development Fund",
    "stsdf": "Scheduled Tribes Special Development Fund",
}
EARMARK = {"scsdf": "Scheduled Castes", "stsdf": "Scheduled Tribes"}


# ------------------------------------------------------------------ pdf geometry

def pdf_pages(pdf_bytes, timeout=900):
    """Yield one list of rows per page, from pdftotext -bbox-layout.

    A row is [top, bottom, [(left, right, word), ...]] in reading order. Rows are built
    by merging poppler's lines, which are runs of adjacent words and not table rows:
    every figure in these books is its own line. Two lines are the same table row when
    their tops agree to within 2.5 points, against a line pitch of about 9.4.
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


def text_of(cells):
    return re.sub(r"\s+", " ", " ".join(c[2] for c in cells)).strip()


def page_text(rows, n=6):
    return " ".join(text_of(r[2]) for r in rows[:n])


def joined(parts):
    """Join wrapped fragments. A fragment ending in a hyphen against a letter is one word
    broken over the line and must not gain a space; a hyphen used as punctuation keeps
    its spaces. Same distinction as parse/andhra.py and parse/kerala.py."""
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


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" .,;:")


def money(tok):
    try:
        return float(tok.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# ------------------------------------------------------------------ units

# The unit marker arrives as separate words because poppler emits words: the Pragathi
# Paddu writes "Rs.Lakh" as one token and the fund volumes write "(Rs." "in" "Lakhs)".
_UNIT = re.compile(r"^\(?\s*(?:rs\.?|₹)?\s*(?:in\s*)?(lakhs?)\)?$", re.I)


def page_unit(rows, n=10):
    """The unit this page names for its money columns, or None if it names none."""
    for t in (c[2] for r in rows[:n] for c in r[2]):
        low = t.lower()
        if _UNIT.match(t) or low.startswith("rs.lakh") or low.startswith("rs.in"):
            return "lakh"
    return None


def book_unit(pages, book):
    """The one unit a book names for its money columns, read off its own pages.

    Never assumed, and never taken from a single page either. The Pragathi Paddu repeats
    `Rs.Lakh` on all 84 of its table pages; the STSDF prints `(Rs. in Lakhs)` on the
    first page of a table and not on its continuation pages, so a per-page assertion
    would stop a book that is perfectly consistent. What matters is that no page names a
    DIFFERENT unit, which is the failure Kerala's books actually have, and that at least
    one page names one at all.
    """
    named = {page_unit(rows) for rows in pages}
    named.discard(None)
    if named != {"lakh"}:
        raise SystemExit(f"{book}: pages name units {sorted(named)}, "
                         f"expected exactly ['lakh'] - refusing to guess")
    return "lakh"


# ------------------------------------------------------------------ columns

def ink_bounds(centres, body):
    """Boundaries between columns, from the whitespace the table actually leaves.

    Midway between two column centres is not the boundary: the Pragathi Paddu's figures
    are right-aligned at x 436, 504 and 572 while its column-number strip is centred at
    404, 472 and 540, so a midpoint would cut the first figure of every row into the
    column to its left. The real boundary is the gap in the page's ink. Same routine as
    parse/kerala.py's column_bounds, for the same reason.
    """
    ivs = sorted((c[0], c[1]) for row in body for c in row[2])
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out = []
    for lo, hi in zip(centres, centres[1:]):
        best, width = (lo + hi) / 2.0, -1.0
        for (_, e), (s, _) in zip(merged, merged[1:]):
            if e >= lo and s <= hi and s - e > width:
                best, width = (e + s) / 2.0, s - e
        out.append(best)
    return out


def column_of(cell, bounds):
    m = (cell[0] + cell[1]) / 2.0
    for i, b in enumerate(bounds):
        if m < b:
            return i
    return len(bounds)


def money_clusters(pages, left=0.0, tol=6.0, floor=20):
    """Right edges of the money columns, clustered over a whole book.

    Money is right-aligned in all three books, so its right edge is the column and its
    left edge is not: a five-digit figure starts 25 points left of a two-digit one in the
    same column. Clustering over the book rather than the page is what makes this work on
    the STSDF, whose scheme pages print no column-number strip at all and whose blank
    cells mean a row's figures cannot be counted off from the left.
    """
    h = collections.Counter()
    for rows in pages:
        for r in rows:
            for c in r[2]:
                if MONEY.match(c[2]) and c[0] > left:
                    h[round(c[1])] += 1
    groups = []
    for e in sorted(h):
        if groups and e - groups[-1][-1] <= tol:
            groups[-1].append(e)
        else:
            groups.append([e])
    out = []
    for g in groups:
        n = sum(h[e] for e in g)
        if n >= floor:
            out.append(max(g, key=lambda e: h[e]))
    return sorted(out)


def serial_boundary(rows, look=16, margin=4.0):
    """Where the fund volumes' serial column ends, read off their own column heading.

    The heading is printed as two lines, `Sl.` over `No.`, and its right edge is 54 on
    both volumes. Taken from the heading rather than from the widest gap in the page's
    ink, because a total row prints its label starting inside the serial column ("Total"
    spans x 47 to 73 on the SCSDF's department totals) and one such word bridges the gap
    and collapses the whole left half of the page into a single run of ink.

    Cells are then assigned by their CENTRE, so that bridging word lands in the name
    column where it belongs.
    """
    xs = [c[1] for r in rows[:look] for c in r[2] if c[2].lower() in ("sl.", "no.")]
    return max(xs) + margin if xs else None


# ------------------------------------------------------------- the vertical cell

def assemble(rows, ncols_name):
    """Give every anchor row its full name, by symmetry. Returns (rows, orphan texts).

    An anchor is any row with content outside the name column: a serial number, a head of
    account or a figure. A name-only row is a line of a wrapped cell, or a group heading.
    Group headings are struck out first, longest match at any position in a run, because
    a heading left in the pool is claimed by the scheme below it and the symmetric rule
    then claims one line too many below as well, which cascades down the page.
    """
    nameonly = [i for i, t in enumerate(rows)
                if t["name"] and not t["slno"] and not t["hoa"] and not t["figs"]]
    pool = set(nameonly)
    headings = set()
    i = 0
    while i < len(nameonly):
        j = i
        while j + 1 < len(nameonly) and nameonly[j + 1] == nameonly[j] + 1:
            j += 1
        run = nameonly[i:j + 1]
        k = 0
        while k < len(run):
            hit = 0
            for length in range(min(3, len(run) - k), 0, -1):
                if norm(" ".join(rows[x]["name"] for x in run[k:k + length])) \
                        in GROUP_HEADINGS:
                    hit = length
                    break
            if hit:
                headings |= set(run[k:k + hit])
                k += hit
            else:
                k += 1
        i = j + 1
    free = pool - headings
    claimed = set()
    for i, t in enumerate(rows):
        if not (t["slno"] or t["hoa"] or t["figs"]):
            continue
        up, j = [], i - 1
        while j >= 0 and j in free and j not in claimed:
            up.append(j)
            j -= 1
        dn, j = [], i + 1
        while j < len(rows) and j in free and j not in claimed:
            dn.append(j)
            j += 1
        k = min(len(up), len(dn))
        claimed |= set(up[:k]) | set(dn[:k])
        t["full"] = joined([rows[x]["name"] for x in reversed(up[:k])]
                           + [t["name"]] + [rows[x]["name"] for x in dn[:k]])
    for i in headings:
        rows[i]["is_heading"] = True
    # One asymmetric case, and only one. A row that carries figures and NO name text at
    # all, sitting directly under an unclaimed name line, is that line's row: the STSDF
    # prints "Sub-Total" on one line and its six figures on the next, far enough apart
    # that they are two rows, and the symmetric rule leaves the figures anonymous and the
    # label orphaned. Read that way one of its sub-totals was counted as a scheme worth
    # 268504.47 lakh. The guard is that the anchor must have no name of its own, so a
    # parent's closing row in the Pragathi Paddu, whose neighbour above is another anchor,
    # is untouched.
    for i, t in enumerate(rows):
        if t.get("full") or not t["figs"] or t["slno"] or t["hoa"]:
            continue
        j = i - 1
        if j >= 0 and j in free and j not in claimed:
            t["full"] = rows[j]["name"]
            claimed.add(j)

    # A line that has been folded into a scheme's name must never be read again as a row
    # of its own. "Total - Animal Husbandry" is the first line of a three-line total cell
    # whose figures sit on the second; read as a row it looks like a total with no
    # figures at all and resets the running sum one row early, which is how 21 of the
    # SCSDF's 25 department totals came to fail.
    for i in claimed:
        rows[i]["claimed"] = True
    return [rows[i]["name"] for i in sorted(free - claimed)]


# ------------------------------------------------------------------ pragathi

# Cutting the header off a fund-volume table page. Two sets, because one does not do it.
#
# HEADER_WORDS are tokens that cannot occur in a scheme name, so a row carrying one is a
# header row whatever else is on it. HEADER_FRAGMENTS are ordinary words that the headings
# are ALSO made of ("Matching", "State", "Share", "of"); a row is a header row on their
# strength only when every token on it is one, which a scheme name never is.
#
# The distinction was paid for. "Commission" was in the first set, and the SCSDF opens a
# page with the wrapped name "Finance Commission Grants to / Mandal Parishads (TIED
# Grant)", so the cut ran past two scheme rows and took 988.80 lakh of Panchayat Raj
# grants with it. The walk is also contiguous from the top of the page, so a heading
# printed lower down, "CSS Schemes", cannot pull the cut down onto the schemes above it.
HEADER_WORDS = {"sl.", "no.", "sparsh", "(css)", "paddu", "lakhs)", "lakh)",
                "department/", "department/schemes", "department/scheme"}
HEADER_FRAGMENTS = {"matching", "state", "share", "of", "centrally", "sponsored",
                    "schemes", "scheme", "finance", "commission", "grants", "grant",
                    "sector", "sna-", "css", "(css)", "total", "grand", "pragathi",
                    "paddu", "name", "department", "(rs.", "in", "lakhs)", "rs.",
                    "sl.", "no.", "sparsh", "be", "2026-27", "2025-26"}


def header_end(rows, look=18):
    """Index of the last header row at the top of a fund-volume table page."""
    last = -1
    for i, r in enumerate(rows[:look]):
        toks = [c[2].lower() for c in r[2]]
        strip = ([c[2] for c in r[2]] == [str(k + 1) for k in range(len(r[2]))]
                 and len(r[2]) >= 5)
        if any(t in HEADER_WORDS for t in toks) or strip or \
                all(t in HEADER_FRAGMENTS for t in toks):
            last = i
        else:
            break
    return last


def strip_row(rows):
    """The `1 2 3 6 6 6` column-number strip under the Pragathi Paddu's header.

    The book prints the same digit under its three money columns, which is its own
    mistake and harmless: what the strip is used for is the six column POSITIONS, not
    what it says. Present on all 84 table pages.
    """
    for i, row in enumerate(rows):
        toks = [c[2] for c in row[2]]
        if len(toks) == 6 and toks[:3] == ["1", "2", "3"] \
                and all(t.isdigit() for t in toks):
            return i, row
    return None, None


def close_parent(parent, run, seen, book_run=None, book_seen=None):
    """Give back the money of a breakdown that never added up to its parent.

    The arithmetic rule closes a parent on the row at which its children reach its own
    figure. When that never happens before the next total, the rows underneath were not
    a breakdown at all and their money belongs in the running sum: without this, page 53
    read 798953.50 against a printed 995336.50, the difference being 196383.00 of rows
    held back by a parent that was never one. Returns the corrected (run, seen).
    """
    if parent is None or not any(parent["child_run"]):
        return run, seen, book_run, book_seen
    give = parent["child_run"]
    return ([run[i] + give[i] for i in range(3)], seen + parent["children"],
            None if book_run is None else [book_run[i] + give[i] for i in range(3)],
            None if book_seen is None else book_seen + parent["children"])


def read_pragathi(pages, book):
    """Every scheme row of the Pragathi Paddu, in page order.

    Returns (schemes, checks, stats, orphans). A check is one printed total against the
    rows read since the previous one.
    """
    pages = list(pages)
    table = [rows for rows in pages if "List of Schemes included" in page_text(rows, 4)]
    book_unit(table, book)
    out, checks, stats = [], [], collections.Counter()
    orphans = collections.Counter()
    sector, dept, group = None, None, None
    run = [0.0, 0.0, 0.0]
    book_run = [0.0, 0.0, 0.0]
    seen, book_seen = 0, 0
    parent = None
    allrows = []
    for pno, rows in enumerate(pages):
        if "List of Schemes included" not in page_text(rows, 4):
            stats["pages_not_a_scheme_table"] += 1
            continue
        si, strip = strip_row(rows)
        if strip is None:
            stats["pages_no_column_strip"] += 1
            continue
        stats["pages_table"] += 1
        body = [r for r in rows if r[0] > strip[1]]
        bounds = ink_bounds([(c[0] + c[1]) / 2.0 for c in strip[2]], body)
        typed = []
        for r in body:
            # The printed page number in the footer, "Page 25". It lands in the head-of-
            # account column, so a row that is nothing but the footer looks like a head
            # of account with no money against it, and the last scheme on the page reads
            # its breakdown as absent: page 42 ends with Integrated Water Shed
            # Development Programme at 5000.00 and page 43 opens with the three heads
            # that make it up, and the footer between them had both counted.
            if re.match(r"^Page\s+\d+$", text_of(r[2])):
                continue
            cols = collections.defaultdict(list)
            for c in r[2]:
                cols[column_of(c, bounds)].append(c)
            figs = {}
            for k in (3, 4, 5):
                v = text_of(cols.get(k, []))
                if MONEY.match(v):
                    figs[k] = money(v)
            typed.append({"slno": text_of(cols.get(0, [])),
                          "name": text_of(cols.get(1, [])),
                          "hoa": text_of(cols.get(2, [])),
                          "figs": figs, "page": pno + 1, "is_heading": False,
                          "full": text_of(cols.get(1, []))})
        for t in assemble(typed, 1):
            orphans[t] += 1
        allrows.extend(typed)

    # One pass over every table page at once, not one pass per page. A scheme's breakdown
    # runs across the page break: National Livestock Management Programme is the last row
    # of page 39 and the head-of-account rows that make up its 8618.35 open page 40, and
    # a per-page loop cannot see them, so it read the scheme as a leaf and counted its
    # provision twice.
    if True:
        typed = allrows
        for idx, t in enumerate(typed):
            if t.get("claimed"):
                continue
            if t["is_heading"]:
                group = clean(t["name"])
                run, seen, book_run, book_seen = close_parent(
                    parent, run, seen, book_run, book_seen)
                parent = None
                continue
            name = clean(t["full"])
            figs = [t["figs"].get(k) for k in (3, 4, 5)]
            has_money = any(f is not None for f in figs)
            n_low = norm(name)

            # A printed total closes whatever has been read since the last one. The
            # breakdown lines a department total is followed by ("State Sector Schemes"
            # with figures beside it) restate money already counted, so they close the
            # run too rather than being added to it.
            if (is_total(name, t["slno"]) or n_low in GROUP_HEADINGS) and has_money:
                run, seen, book_run, book_seen = close_parent(
                    parent, run, seen, book_run, book_seen)
                # The book's own Grand Total, 18431570.27 lakh for 2026-27, is the sum of
                # every row in the volume and not of the rows since the previous total.
                # It is the one check that catches a whole department read twice or not
                # at all, so it is compared against the book-wide accumulator.
                if _GRAND.match(name):
                    checks.append({"page": t["page"], "label": name,
                                   "printed": [f or 0.0 for f in figs],
                                   "parsed": [round(x, 2) for x in book_run],
                                   "rows": book_seen, "scope": "whole book"})
                    run, seen, parent = [0.0, 0.0, 0.0], 0, None
                    continue
                if seen:
                    checks.append({"page": t["page"], "label": name,
                                   "printed": [f or 0.0 for f in figs],
                                   "parsed": [round(x, 2) for x in run],
                                   "rows": seen})
                run, seen, parent = [0.0, 0.0, 0.0], 0, None
                continue
            if is_total(name, t["slno"]):
                run, seen, parent = [0.0, 0.0, 0.0], 0, None
                continue

            if not has_money and not t["hoa"]:
                if not name:
                    continue
                # A sector, sub-sector, head of development or department heading. It
                # carries a marker in the serial column exactly as a scheme does, so the
                # two are told apart by what follows: a heading is followed by another
                # heading or by a group heading, a scheme with no figures of its own is
                # followed by the head-of-account rows that make up its provision.
                nxt = typed[idx + 1] if idx + 1 < len(typed) else None
                is_scheme = (nxt is not None and not nxt["is_heading"]
                             and nxt["hoa"] and not nxt["slno"])
                if not is_scheme:
                    run, seen, book_run, book_seen = close_parent(
                        parent, run, seen, book_run, book_seen)
                    if re.match(r"^[A-Za-z]$|^[IVXL]{1,6}$", t["slno"].strip(".")):
                        sector = name if name.isupper() else sector
                        dept = name
                    else:
                        dept = name
                    parent = None
                    continue
                # falls through as a scheme whose figure arrives on its closing row
            starts = bool(t["slno"] and SLNO.match(t["slno"].strip())) or (
                bool(name) and n_low not in COMPONENT_LABELS and (has_money or t["hoa"]))

            # A total whose label lost its first line to a page break. Page 94 opens with
            # the tail of "Total - Telangana Social Welfare Residential Educational
            # Institutions Society" and 439468.63 beside it, and read as a scheme that is
            # the whole society's provision entering the register under a fragment of a
            # total's name. What identifies it is what comes next: a department total is
            # always followed by its own breakdown lines, "RIDF" and "State Sector
            # Schemes" with figures against them, and a scheme never is.
            if has_money and not is_total(name, t["slno"]):
                nx = None
                for u in typed[idx + 1:]:
                    if u.get("claimed") or u["is_heading"] or not u["figs"]:
                        continue
                    nx = u
                    break
                if nx is not None and norm(clean(nx["full"])) in GROUP_HEADINGS:
                    run, seen, book_run, book_seen = close_parent(
                        parent, run, seen, book_run, book_seen)
                    if seen:
                        checks.append({"page": t["page"], "label": name or "(total)",
                                       "printed": [f or 0.0 for f in figs],
                                       "parsed": [round(x, 2) for x in run],
                                       "rows": seen})
                    run, seen, parent = [0.0, 0.0, 0.0], 0, None
                    stats["totals_recovered_from_page_break"] += 1
                    continue

            # WHERE A PARENT'S BREAKDOWN ENDS, and why it has to be counted rather than
            # recognised. A scheme printed without a head of account of its own is a
            # parent whose figure is the sum of the rows beneath it, and those rows are
            # NOT reliably anonymous. On page 41 the Forest College and Research
            # Institute is printed at 10299.41 and the four rows under it are
            # 63.00 + 3141.00 + 1000.00 + 6095.41, of which the last two carry their own
            # serial numbers 5 and 6 and their own names, Infrastructure Development and
            # Civil Works for Sanctuaries. They look exactly like new schemes and they
            # are not: added to the sub-total they take it from the printed 12864.41 to
            # 19959.82. On page 37 the same shape appears with the breakdown unlabelled
            # and TWO genuinely new schemes printed immediately after it.
            #
            # Nothing in the layout separates those cases. The book's own arithmetic
            # does: the breakdown ends on the row at which it adds up to the parent, in
            # all three columns at once. So the run is closed by counting, and the four
            # rows under the Forest College close it exactly while the two after
            # National Mission on Edible Oils do not open one.
            if parent is not None and has_money:
                parent["children"] += 1
                for i in range(3):
                    if figs[i] is not None:
                        parent["child_run"][i] += figs[i]
                if HOA.match(t["hoa"]) and t["hoa"] not in parent["rec"]["hoas"]:
                    parent["rec"]["hoas"].append(t["hoa"])
                if name and n_low not in COMPONENT_LABELS and starts \
                        and norm(name) != norm(parent["rec"]["name"]):
                    # A named part of a parent's provision is still a scheme the state
                    # names, so it is published; its money is inside the parent's, so it
                    # is not added to the run and `part_of` says whose it is.
                    out.append({"name": name, "department": dept, "sector": sector,
                                "group": group, "page": t["page"],
                                "hoas": [t["hoa"]] if HOA.match(t["hoa"]) else [],
                                "hoa_text": t["hoa"] or None,
                                "be_lakh": figs[2], "figs": list(figs),
                                "part_of": parent["rec"]["name"]})
                if parent["rec"]["figs"] == [None, None, None]:
                    # A parent that printed no figure of its own: its total is the row
                    # with figures and nothing else on it that closes the breakdown.
                    if not t["hoa"] and not name:
                        parent["rec"]["be_lakh"] = figs[2]
                        parent["rec"]["figs"] = list(figs)
                        for i in range(3):
                            if figs[i] is not None:
                                run[i] += figs[i]
                                book_run[i] += figs[i]
                        seen += 1
                        book_seen += 1
                        parent = None
                    continue
                if all(abs((parent["rec"]["figs"][i] or 0.0)
                           - parent["child_run"][i]) <= 0.02 for i in range(3)):
                    parent = None
                continue

            if starts and name and n_low not in COMPONENT_LABELS:
                rec = {"name": name, "department": dept, "sector": sector,
                       "group": group, "page": t["page"],
                       "hoas": [t["hoa"]] if HOA.match(t["hoa"]) else [],
                       "hoa_text": t["hoa"] or None,
                       "be_lakh": figs[2], "figs": list(figs), "part_of": None}
                out.append(rec)
                if has_money:
                    seen += 1
                    book_seen += 1
                    for i in range(3):
                        if figs[i] is not None:
                            run[i] += figs[i]
                            book_run[i] += figs[i]
                # A scheme with a head of account of its own is a leaf and stands alone.
                # A scheme without one is a parent whose figure is the sum of the rows
                # printed under it, so those must not be added again.
                #
                # Missing head of account is not enough on its own. The Irrigation
                # chapter writes heads as ranges too wide for their column and wraps them
                # over three lines, "4700-01-232-25-" above and "25,26,27,49" below, which
                # leaves the money row of CE Kaleswaram Project with no head beside it
                # while it is a perfectly ordinary leaf. So the next row has to look like
                # a breakdown line before a parent is opened: a head of account with
                # money against it and no serial of its own.
                nxt = None
                for u in typed[idx + 1:]:
                    if u.get("claimed") or u["is_heading"]:
                        continue
                    nxt = u
                    break
                # When the scheme is the last row on its page the next row cannot be
                # seen, and there the missing head of account has to be trusted on its
                # own: National Livestock Management Programme closes page 39 and its
                # breakdown opens page 40, and refusing to open a parent there counted
                # that scheme's whole 8618.35 twice.
                # A breakdown line may carry a serial of its own. Page 39 prints
                # National Livestock Management Programme at 1676.42 and 8618.35 with a
                # breakdown that opens with a NUMBERED row, 24, and runs on for another
                # thirteen; the thirteen add to 8618.35 exactly. So the test is only that
                # the next row is a head of account with money against it, which the
                # Irrigation chapter's wrapped continuation "25,26,27,49" is not.
                # The next row must open with a MAJOR HEAD, four digits, to count as a
                # breakdown line. Page 52 prints Nagarjunasagar Project at 29795.00 with
                # its head of account on the line below and its money repeated there,
                # which is a breakdown; two rows earlier Priyadarshini Jurala Project
                # has its head wrapped as "4700-01-122-25-26," over "27,49", and the
                # "27,49" is not a head of account at all. Requiring the four digits
                # separates them, and requiring money as well would reject
                # Nagarjunasagar, whose first breakdown line prints none.
                child_like = nxt is None or bool(
                    nxt["hoa"] and re.match(r"^\d{4}\D", nxt["hoa"]))
                parent = None if (t["hoa"] or not child_like) else {
                    "rec": rec, "children": 0, "child_run": [0.0, 0.0, 0.0]}
                continue

            if not has_money:
                continue
            # A figures row belonging to no scheme. Two different things wear this
            # shape and only one of them is money to add.
            #
            # WITH a head of account it is an extra head printed under a leaf: page 37
            # prints 2401-789-15-27 and 2401-796-15-27 under National Beekeeping Honey
            # Mission, and the Horticulture sub-total does not come out without them.
            #
            # WITHOUT one it is an unlabelled sub-total: page 71 prints 9444.07 on a line
            # of its own after three Poshan Shakthi Nirman rows, and the labelled
            # "Sub-total Matching State Share" four lines later prints the same 9444.07.
            # Added, it doubles the block.
            # ...and a row that carries a SERIAL NUMBER is a scheme row whose name was
            # lost, never a total. The Irrigation chapter wraps its heads of account
            # over two lines and sometimes leaves the money row with neither the name nor
            # the head beside it: "4 Rajiv Bheema L.I Project" on page 51 arrives as a
            # bare 1394.00 under a serial. Its money is counted; with no name it is not
            # published as a scheme.
            # ...and a money row whose own head of account wrapped away from it. The
            # Irrigation chapter writes "2700-01-112-25," over "26,27" with the 29.00
            # between them, so the money row carries nothing but the figures and looks
            # exactly like an unlabelled sub-total. The tell is the neighbour: a head of
            # account with no money, no name and no serial of its own sits directly above
            # or below. Without this the State Sector sub-total on page 53 came out 29.00
            # short, which is small enough to look like rounding and is not.
            wrapped = any(u is not None and u["hoa"] and not u["figs"]
                          and not u["name"] and not u["slno"]
                          for u in (typed[idx - 1] if idx else None,
                                    typed[idx + 1] if idx + 1 < len(typed) else None))
            if t["hoa"] or t["slno"] or wrapped:
                stats["extra_head_of_account_rows"] += 1
                for i in range(3):
                    if figs[i] is not None:
                        run[i] += figs[i]
                        book_run[i] += figs[i]
            else:
                stats["unlabelled_total_rows"] += 1
    stats["schemes"] = len(out)
    return out, checks, stats, orphans


# ------------------------------------------------------------------ SCSDF / STSDF

def read_fund(pages, book, ncols):
    """The Scheduled Castes or Scheduled Tribes fund volume, scheme wise.

    Returns (schemes, checks, stats, orphans). `ncols` is the number of money columns,
    five in the SCSDF and six in the STSDF; the last is the total and is the figure kept.

    THE DEPARTMENT-WISE TABLE IS NOT A SCHEME TABLE. Both volumes open with a summary
    whose numbered rows are DEPARTMENTS, headed `Name of Department`; the scheme-wise
    table that follows is headed `Department/ Scheme`. Read together, the register gains
    "Agriculture Department" and "Rural Development Department" as if they were welfare
    schemes, which is exactly the trap parse/andhra.py records as its Layout B. Pages are
    therefore selected on their own header.
    """
    pages = list(pages)
    wanted = [rows for rows in pages
              if re.search(r"Department\s*/\s*Scheme", page_text(rows, 12), re.I)]
    book_unit(wanted, book)
    cols = money_clusters(wanted, left=0.0, tol=6.0, floor=20)
    cols = cols[-ncols:] if len(cols) > ncols else cols
    out, checks, stats = [], [], collections.Counter()
    orphans = collections.Counter()
    dept = None
    run = [0.0] * len(cols)
    book_run = [0.0] * len(cols)
    seen, book_seen = 0, 0
    for rows in wanted:
        stats["pages_table"] += 1
        bound = serial_boundary(rows)
        if bound is None:
            stats["pages_no_serial_boundary"] += 1
            continue
        body = rows[header_end(rows) + 1:]
        typed = []
        for r in body:
            figs, name, slno = {}, [], []
            for c in r[2]:
                if MONEY.match(c[2]) and cols and c[1] >= cols[0] - 8:
                    k = min(range(len(cols)), key=lambda j: abs(cols[j] - c[1]))
                    if abs(cols[k] - c[1]) <= 8:
                        figs[k] = money(c[2])
                        continue
                # The serial column holds nothing but a serial number. A total row
                # prints its label starting inside it ("Total - Horticulture
                # Department" opens at x 30), so a token that is not a bare number is
                # name text however far left it starts.
                if (c[0] + c[1]) / 2.0 <= bound and SLNO.match(c[2]):
                    slno.append(c)
                else:
                    name.append(c)
            # The column-number strip, `1 2 3 4 5 6 7`, is not data.
            toks = [c[2] for c in r[2]]
            if toks == [str(i + 1) for i in range(len(toks))] and len(toks) >= 5:
                continue                      # the `1 2 3 4 5 6 7` column-number strip
            if len(toks) == 1 and re.match(r"^\d{1,3}$", toks[0]) and r is body[-1]:
                continue                      # the printed page number in the footer
            typed.append({"slno": text_of(slno), "name": text_of(name),
                          "hoa": "", "figs": figs, "is_heading": False,
                          "full": text_of(name)})
        for t in assemble(typed, 1):
            orphans[t] += 1

        for t in typed:
            if t["is_heading"] or t.get("claimed"):
                continue
            name = clean(t["full"])
            figs = [t["figs"].get(k) for k in range(len(cols))]
            has_money = any(f is not None for f in figs)
            if is_total(name, t["slno"]) and has_money:
                # A grand total is checked against every scheme row in the book, not
                # against the rows since the previous total: the volumes print a total
                # per department and then one for the whole fund, and the second is not
                # the sum of the rows after the first.
                # These volumes nest their totals: one per head of department, one per
                # department, one for the fund, and one for the fund plus the
                # non-divisible allocation. A printed total is therefore the sum of the
                # rows since the previous total, or the sum of every row in the book, or
                # a sum of other totals with nothing underneath it to check against. The
                # leaf reading is tried first, the book-wide reading second, and only a
                # total that is neither is counted as unchecked. A total that should be
                # a leaf sum and is not still fails, which is the point.
                printed = [f or 0.0 for f in figs]
                leaf = seen and all(abs(printed[i] - run[i]) <= 0.02
                                    for i in range(len(cols)))
                whole = all(abs(printed[i] - book_run[i]) <= 0.02
                            for i in range(len(cols)))
                if leaf or (seen and not whole):
                    checks.append({"label": name, "printed": printed,
                                   "parsed": [round(x, 2) for x in run],
                                   "rows": seen})
                elif whole:
                    checks.append({"label": name, "printed": printed,
                                   "parsed": [round(x, 2) for x in book_run],
                                   "rows": book_seen, "scope": "whole book"})
                else:
                    stats["totals_of_totals_not_checked"] += 1
                run, seen = [0.0] * len(cols), 0
                continue
            if not has_money:
                if is_total(name, t["slno"]):
                    continue
                if not name:
                    continue
                # A department header: a serial number and a name and no money at all.
                dept = name
                continue
            # Every scheme in these two volumes is numbered. A row with figures and no
            # serial is an accounting line, not a scheme: the SCSDF ends with
            # "Allocation deemed to be accounted for Non-Divisible infrastructure
            # works", 323060.50 lakh, which the grand total includes and which names no
            # scheme at all. Its money is counted; its name is not published as one.
            if t["slno"] and SLNO.match(t["slno"].strip()) and name:
                out.append({"name": name, "department": dept, "sector": None,
                            "group": None, "hoas": [], "hoa_text": None,
                            "be_lakh": figs[-1], "figs": list(figs)})
            elif name:
                stats["unnumbered_money_rows"] += 1
            else:
                # A numbered row whose name did not land in the name column: six rows of
                # the STSDF, where the department heading above ran into the scheme's own
                # line and took the name with it. Their money is still counted, and the
                # totals below still balance; publishing them would put six schemes with
                # no name into the register.
                stats["rows_with_no_name"] += 1
            seen += 1
            book_seen += 1
            for i in range(len(cols)):
                if figs[i] is not None:
                    run[i] += figs[i]
                    book_run[i] += figs[i]
    stats["schemes"] = len(out)
    stats["money_columns"] = len(cols)
    return out, checks, stats, orphans


# ------------------------------------------------------------------ merge

def entry_key(r):
    """The pair (department, name), as parse/andhra.py keys its books.

    Telangana prints no scheme code, and the same name means different things under
    different departments: "Buildings" is a provision under Intermediate Education and
    again under Tribal Welfare. Collapsing those would erase a real scheme.
    """
    return (norm(r.get("department") or ""), norm(r["name"]))


def merge(rows_by_book):
    """One entry per department and name, with the books that named it.

    Allocations are NOT summed across books. The SCSDF and STSDF report the Scheduled
    Caste and Scheduled Tribe slices of provisions the Pragathi Paddu already states in
    full, so adding them would count the same money three times. The Pragathi Paddu is
    the book that states the provision; the fund volumes only fill a gap, and their
    figures are published separately as earmarks.
    """
    merged = {}
    for book in ("pragathi", "scsdf", "stsdf"):
        for r in sorted(rows_by_book.get(book, []),
                        key=lambda x: (entry_key(x), x.get("page") or 0)):
            k = entry_key(r)
            e = merged.get(k)
            if e is None:
                e = merged[k] = {
                    "name": r["name"], "department": r.get("department"),
                    "sector": r.get("sector"), "group": r.get("group"),
                    "hoas": set(r.get("hoas") or []),
                    "hoa_text": r.get("hoa_text"),
                    "be_lakh": r.get("be_lakh"),
                    "be_from": BOOK_LABEL[book], "books": [], "earmarks": {}}
            if BOOK_LABEL[book] not in e["books"]:
                e["books"].append(BOOK_LABEL[book])
            e["hoas"] |= set(r.get("hoas") or [])
            for f in ("sector", "group", "hoa_text", "department"):
                if not e.get(f) and r.get(f):
                    e[f] = r[f]
            if e["be_lakh"] is None and r.get("be_lakh") is not None:
                e["be_lakh"], e["be_from"] = r["be_lakh"], BOOK_LABEL[book]
            elif book == "pragathi" and r.get("be_lakh") is not None and \
                    e["be_from"] != BOOK_LABEL["pragathi"]:
                e["be_lakh"], e["be_from"] = r["be_lakh"], BOOK_LABEL[book]
            if book in EARMARK and r.get("be_lakh") is not None:
                a = EARMARK[book]
                e["earmarks"][a] = round(e["earmarks"].get(a, 0.0) + r["be_lakh"], 2)
    out = []
    for k in sorted(merged):
        e = merged[k]
        e["hoas"] = sorted(e["hoas"])
        e["books"] = sorted(e["books"])
        e["earmarks"] = {a: e["earmarks"][a] for a in sorted(e["earmarks"])} or None
        e["key"] = "dept:%s|name:%s" % k
        out.append(e)
    return out


# ------------------------------------------------------------------ driver

def failed(checks, tol=0.02):
    bad = []
    for c in checks:
        for p, q in zip(c["printed"], c["parsed"]):
            if abs((p or 0.0) - (q or 0.0)) > tol:
                bad.append(c)
                break
    return bad


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "telangana", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/telangana/: "
                         "run collect/telangana.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "telangana", date)
    with open(os.path.join(src, "_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)

    readers = {
        "pragathi": lambda pages: read_pragathi(pages, "pragathi"),
        "scsdf": lambda pages: read_fund(pages, "scsdf", 5),
        "stsdf": lambda pages: read_fund(pages, "stsdf", 6),
    }
    rows_by_book, per_book, checks, stats, orphans = {}, {}, {}, {}, {}
    for book in sorted(readers):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            got = readers[book](pdf_pages(fh.read()))
        rows_by_book[book] = got[0]
        per_book[book] = len(got[0])
        checks[book] = got[1]
        stats[book] = dict(sorted(got[2].items()))
        orphans[book] = [t for t, _ in got[3].most_common(20)]

    out = merge(rows_by_book)
    bad = {b: failed(c) for b, c in checks.items()}

    write_json("data/telangana/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Telangana",
        "cycle": man.get("cycle"),
        "source": ("Telangana Budget Volume VII: the Pragathi Paddu (Scheme "
                   "Expenditure) and the Scheduled Castes and Scheduled Tribes "
                   "Special Development Fund volumes"),
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "reconciliation": {b: {"checked": len(c), "failed": len(bad.get(b, []))}
                           for b, c in sorted(checks.items())},
        "reconciliation_failures": {b: bad[b][:20] for b in sorted(bad) if bad[b]},
        "extraction_stats": stats,
        "unassigned_name_lines": orphans,
        "schemes": len(out),
        # Two counts, because one word cannot carry both. A scheme printed at 0.00 is the
        # state saying the scheme exists and is funded at nil this year, which is not the
        # same as a scheme with no figure printed against it at all.
        "with_a_figure": sum(1 for r in out if r.get("be_lakh") is not None),
        "with_money": sum(1 for r in out if r.get("be_lakh")),
        "funded_at_nil": sum(1 for r in out if r.get("be_lakh") == 0),
        "with_head_of_account": sum(1 for r in out if r.get("hoas")),
        "unit": "lakh",
        "unit_note": ("Every figure here is rupees in LAKH, read off each page's own "
                      "header: 'Rs.Lakh' on the Pragathi Paddu and '(Rs. in Lakhs)' on "
                      "the two fund volumes. The trap in these books is not two units in "
                      "one book but the Indian digit grouping: the STSDF prints "
                      "1487441.29 as 14874,41.29 on page 15 and as 14,87,441.29 on page "
                      "9, so commas are stripped rather than counted."),
        # Read by eye, all five joins against the 22 myScheme records for Telangana.
        # Recorded rather than patched: parse/match.py is not edited from here, and the
        # direction of the error is the safe one. A false MATCH means a scheme is treated
        # as present on myScheme and is therefore NOT claimed absent, so it costs one
        # under-reported absence rather than one false accusation.
        "known_bad_joins": [{
            "telangana": "Universalisation of Secondary Education (ANDARIKI VIDYA)",
            "myscheme": ("Mahatma Jyothiba Phule Overseas Vidya Nidhi for BC and EBC"),
            "why": ("A capitalised transliteration in brackets is read as an acronym. "
                    "ANDARIKI VIDYA contains a space so the bracketed-acronym rule does "
                    "not see it; the capitals rule does, and yields vidya, which is an "
                    "ordinary word for education and a token of the other name."),
            "effect": "Under-reports absence by one.",
        }],
        "caveat": (
            "The Pragathi Paddu is Telangana's scheme expenditure volume and it files "
            "establishment heads at the same level as schemes: Governor Secretariat, "
            "Raj Bhavan Gardens, Furniture Estt, Public Service Commission. They are "
            "kept, because the state files them here and dropping them would be this "
            "project editing a state's own list; a reader counting welfare schemes "
            "should discount them. Allocations are not summed across books: the SCSDF "
            "and STSDF report the Scheduled Caste and Scheduled Tribe slices of "
            "provisions the Pragathi Paddu states in full, so the Pragathi Paddu figure "
            "wins and the fund figures are published separately as earmarks. The number "
            "here is a floor on Telangana's schemes, never a total."),
        "entries": out,
    })
    return out, per_book, checks, bad, stats, orphans, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Telangana Volume VII scheme books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, checks, bad, stats, orphans, date = run(a.date)
    print(f"telangana snapshot {date}")
    for b in sorted(per_book):
        n, nb = len(checks.get(b) or ()), len(bad.get(b) or ())
        print(f"    {b:<10}{per_book[b]:>6} scheme rows   "
              f"{n - nb}/{n} printed totals reconcile")
        print(f"               {stats[b]}")
    print(f"  {len(out)} distinct schemes by department and name")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    print(f"     with a head of account {sum(1 for r in out if r.get('hoas')):>6}")
    worst = sorted(b for b in bad if bad[b])
    if worst:
        for b in worst:
            for c in bad[b][:6]:
                print(f"    MISMATCH {b} {c.get('page', '')} {c['label'][:44]:<44} "
                      f"printed={c['printed']} parsed={c['parsed']}")
        # Fail loud, and only after the file is written: PLAN.md 8 wants the bad run
        # archived and visible, not swallowed.
        print("  ERROR: parsed rows do not add up to the printed totals for "
              + ", ".join(worst))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
