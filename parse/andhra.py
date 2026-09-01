"""
Extract Andhra Pradesh's scheme-wise budget books into a named scheme list.

AGENT-EDITABLE (PLAN.md §7). Reads archive/andhra/, writes data/andhra/. Never fetches.
Replayable against any archived date.

    data/andhra/schemes.json    one row per department + scheme name

What a row is. AP prints no scheme code beside the name in four of the six books, so
unlike Karnataka there is no head of account to key on. The key here is the pair
(department, scheme name), because the same name means different things under different
departments: "Subsidy on Domestic LPG Scheme" is a separate provision under Backward
Classes Welfare, EWS Welfare, Minorities Welfare, Social Welfare and Tribal Welfare, and
collapsing those five into one would erase four real schemes.

The six books use two different table layouts, and a single parser reads zero rows from
one of them. Both are plain English throughout, with no second script to separate, which
is why AP is the easiest state surveyed so far.

    LAYOUT A, the Gender and Child budgets:

         XIII Women Development and Child Welfare Department
            1 Anganwadi cum Creches under Palna scheme                      4,16.45
            2 Assistance to A.P. Women Co-operative Finance Corporation    10,27.50

    LAYOUT C, the annexure of the Backward Classes, Minorities, SC and ST books:

        AGC02-Agriculture Department
        1   2401-00-105-27-52-310-312-V   PM RKVY - Soil Health [AP324]     3,07.78

Five traps in these layouts, each of which produced a wrong answer before it was fixed:

Layout B is not a scheme table. The Backward Classes, Minorities, SC and ST books open
with a Chapter 2 headed `S.No | Department | BE 2026-27` whose numbered rows are
DEPARTMENTS, not schemes. Read as schemes it adds "Agriculture Department" and
"Horticulture Department" to the register as if they were welfare schemes. Pages are
therefore classified by their column header and only A and C pages are read: across the
six books that is 21 layout A pages and 221 layout C pages, with 10 layout B pages among
the 279 skipped.

The roman numeral is a department, not a scheme. A layout A line beginning with a roman
numeral is a department header whose name is carried down onto every scheme row that
follows. The numerals run past X (XXII appears), and the arabic S.No restarts at 1 inside
each department, which is why the numeral has to be read rather than the row counted.

Names wrap, and the wrap comes AFTER the figure. This is the bug parse/karnataka.py
documents in its own layout: reading only the line that carries the money truncates
"...ACT 1989 - INTERCASTE MARRIAGES[AP198]" to "...ACT 1989 - INTERCASTE", the same shape
of error as Karnataka's "Helpers". Here the continuation is the following line, indented
to the name column and carrying no figure of its own, so it is accumulated onto the row
above it. 350 of the 2,471 rows read, one in seven, are wrapped.

The wrap can straddle a page break. 16 names end on one page and finish on the next,
after the repeated banner and column header. A reader that resets at the page boundary
records "Pradhan Mantri Janjati Adivasi Nyaya Maha Abhiyan (PM-" as a scheme and drops
"JANMAN)", and files "Human Resources for Health and Medical Education -" without
"Establishment of New Medical Colleges [AP73]". Both look like real scheme names, which
is why this had to be hunted rather than waited for. The unfinished row is therefore
carried over the break and offered the first content line of the next page.

The BE 2026-27 column is not in a fixed position. Backward Classes and Minorities print
one figure column; the SC and ST volumes print four (ACCTS 2024-25, BE 2025-26, RE
2025-26, BE 2026-27). Taking the first figure would report 2024-25 actuals as next year's
allocation for two of the six books. The last figure is the one wanted, and the page
header is checked to confirm the last column really is 2026-27 before any row on that
page is read.

Money is written in the Indian style, `28,15.01` meaning 2815.01 lakh, and a nil
provision prints as `..`.

On adding up. Within one book, the annexure lists the same scheme under several heads of
account (a general head, the -789 SC head, the -796 ST head, revenue and capital), and
those are additive parts of that book's provision, so they are summed, keyed on the head
of account so that a repeated page header can never double count. ACROSS books they are
NOT summed: the Gender, Child, BC, Minorities, SC and ST books each report the slice of
one provision attributable to their own group, so adding them double counts. The largest
slice is kept, which makes be_lakh a floor on what the scheme gets and never a total.
`books` records which of the six named the scheme, exactly as the Karnataka parser does.
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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402

BOOK_LABEL = {
    "Gender-Budget": "Gender Budget",
    "Child-Budget": "Child Budget",
    "Backward-Classes": "Backward Classes Component",
    "Minorites": "Minorities Component",
    "Volume-VII-3": "Scheduled Castes Component",
    "Volume-VII-2": "Scheduled Tribes Component",
}

# One table cell that holds a figure. `..` is the only nil marker these books use, 2,087
# times across the table pages of the six; a bare dash never appears, so it is not
# accepted here and a lone "-" stays part of whatever name it sits in.
MONEY = re.compile(r"^(?:\.{2,}|[\d,]*\d\.\d{2})$")

# Roman numerals 1 to 39, which covers the XXII that appears in the Gender Budget with
# room to spare. Deliberately excludes L, C, D and M so that an English word can never be
# read as a department number: only I, V and X are allowed, and no word is spelled from
# those three letters alone.
ROMAN = re.compile(r"^(X{0,3}(?:IX|IV|V?I{0,3}))\s+(\S.*)$")

# Layout A scheme row: the S.No, then the name, then the figure.
A_ROW = re.compile(r"^(\d{1,3})\s+(\S.*)$")

# Layout C scheme row: the S.No, the head of account, the name, then the figures.
# 2401-00-105-27-52-310-312-V and 4401-00-119-27-07-530-531-V are the shapes seen.
C_ROW = re.compile(r"^(\d{1,4})\s+(\d{4}-\d{2}-\d{3}(?:-\d+)+-[A-Z]{1,3})\s+(\S.*)$")

# Layout C department line: the department's own code, then its name.
C_DEPT = re.compile(r"^([A-Z]{2,5}\d{2})\s*-\s*(\S.*)$")

# Page furniture that must never be read as a scheme name or a continuation. Anchored on
# whole cells where the word is also an ordinary English word: "Scheme" alone is the
# annexure's column header, but "Schemes for setting up of Womens Training Centres" is a
# real row and a `Scheme\b` prefix test would delete it.
JUNK = re.compile(
    r"^(?:S\.?\s*No|Dept$|Head of Account|Scheme$|Name of the Department|"
    r"Amount allocated|FY \d{4}-\d{2}|\(?Rupees in|(?:in\s+)?Lakhs\)$|"
    r"BE \d{4}-\d{2}|RE \d{4}-\d{2}|ACCTS \d{4}-\d{2}|Total\b|Grand Total|"
    r"DEPARTMENT WISE|"
    r"Revenue$|Capital$|PART\s*-?\s*[AB]\b|Chapter\b|An amount of Rs)", re.I)

# A line with no letters in it: the page number in the footer, or the "1 2 3 4"
# column-number strip printed under every annexure header. Both sit far to the right of
# the name column and carry no figure, so without this they would be appended to the last
# scheme on the page as if they were part of its name.
NUMERIC_ONLY = re.compile(r"^[\d\s.,\-|]+$")

# The control figures each book prints about itself, which are what makes this parser
# checkable rather than merely plausible (PLAN.md §8, assertion 3). The BC, Minorities,
# SC and ST books print one Grand Total; the Gender and Child budgets instead announce
# each Part's total in a sentence above the table and repeat it in a Total row.
GRAND_TOTAL = re.compile(r"^\s*Grand Total\s+([\d,]+\.\d{2})\s*$", re.M)
PART_TOTAL = re.compile(
    r"An amount of Rs\.?\s*([\d,]+\.\d{2})\s*Lakhs is provided under Part\s*[AB]")


def pdftotext(pdf_bytes):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, timeout=900)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" .,;:-")


def flat(s):
    """Whitespace only. Kept separate from clean() because a name that is still being
    accumulated must keep its trailing hyphen: clean() would eat the one in "Nadu-"."""
    return re.sub(r"\s+", " ", s or "").strip()


def key(s):
    """Dedup key. Strict on purpose: case and punctuation only.

    A looser key would merge names the books keep apart. "NATIONAL RURAL LIVELIHOOD
    MISSION [AP168]" and "National Rural Livelihood Mission (NRLM) - SVEP [AP365]" are two
    schemes with two allocations, and any normaliser that folds them loses one of them.
    """
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def amount(cell):
    """One figure cell to lakh. `28,15.01` is 2815.01: the commas are Indian grouping."""
    if not cell or cell.startswith(".") or cell.startswith("-"):
        return None
    try:
        return float(cell.replace(",", ""))
    except ValueError:
        return None


def cells(s):
    """Split a laid-out row into its columns. pdftotext -layout separates them by runs
    of spaces; a single space is inside a cell."""
    return [c for c in re.split(r"\s{2,}", s.strip()) if c]


def split_figures(rest):
    """Return (name, figures) for the part of a row after its S.No and head of account."""
    parts = cells(rest)
    n = len(parts)
    while n > 0 and MONEY.match(parts[n - 1]):
        n -= 1
    return " ".join(parts[:n]), parts[n:]


def indent(line):
    return len(line) - len(line.lstrip())


def layout_of(page):
    """Which table, if any, this page carries. Decided from the column header alone.

    The header is also the check that the LAST figure column is 2026-27, which is what
    every row reader here assumes. Backward Classes prints one figure column and the SC
    volume prints four, so the assumption has to be verified per page rather than per book.
    """
    # 20 lines, not 5: on the first page of each Part the column header sits under a
    # banner and a two-line "An amount of Rs. ... is provided under Part A" note, which
    # pushed it to line 11 in the Gender Budget and made a 9-line window classify a real
    # table page as prose.
    head = page.splitlines()[:20]
    for ln in head:
        if "Name of the Department and Scheme" in ln:
            # Layout A's header wraps over three lines, so look at the block.
            return "A" if "2026-27" in "\n".join(head) else None
        if "Head of Account" in ln:
            cols = cells(ln)
            return "C" if cols and "2026-27" in cols[-1] else None
    return None


def parse_layout_a(lines, book, dept=None, pending=None):
    """Gender and Child budgets: roman-numeral departments, then numbered scheme rows.

    `dept` comes in from the previous page and goes back out, because a department's rows
    run over the page break: page 7 of the Gender Budget opens with "3 Thallikivandanam",
    whose department header "VIII Minorities Welfare Department" is on page 6. Resetting
    per page left 82 of the Gender Budget's 284 rows and 22 of the Child Budget's 122
    with no department at all.
    """
    rows, prev = [], None
    for raw in lines:
        s = raw.strip()
        # A blank line does NOT end a row. pdftotext renders these PDFs double-spaced, so
        # every wrapped name is separated from the row it belongs to by an empty line, and
        # dropping the pending row on a blank line truncated all 350 wrapped names: it left
        # "Development of Sericulture Industries for the benefit of" with no beneficiary
        # and "Livestock Health and Disease Control Programme - ASCAD" with no component.
        # Both read as plausible scheme names, which is what makes the bug dangerous.
        if not s:
            continue
        if NUMERIC_ONLY.match(s) or JUNK.match(s):
            prev = None
            continue

        m = A_ROW.match(s)
        if m:
            name, figs = split_figures(m.group(2))
            # No figure on the line means this is not a scheme row: in these books every
            # scheme row carries its allocation on the same line as its name.
            if not figs or len(clean(name)) < 3:
                prev = None
                continue
            row = {"department": dept, "name": flat(name),
                   "be_lakh": amount(figs[-1]), "hoa": None,
                   "name_col": indent(raw) + len(m.group(1)) + 1, "book": book}
            rows.append(row)
            prev, pending = row, None
            continue

        m = ROMAN.match(s)
        if m and m.group(1) and not split_figures(m.group(2))[1]:
            # The department name wraps too, not just the scheme name: "XXVI Department
            # for Welfare of Differently Abled, Transgender and Senior" / "Citizens",
            # twice in the Gender Budget and four times in the Child Budget. Left unjoined
            # it split that one department into two, filing 12 schemes under "...and
            # Senior" and 15 under the same department's full name.
            prev = {"name": flat(m.group(2)), "is_dept": True,
                    "name_col": indent(raw) + len(m.group(1)) + 1}
            dept, pending = clean(prev["name"]), None
            continue

        if prev is None and pending is not None:
            # First content line of a new page, and the previous page ended mid-name.
            _continue(pending, raw, s)
            pending = None
            continue

        prev = _continue(prev, raw, s)
        if prev is not None and prev.get("is_dept"):
            dept = clean(prev["name"])
    return rows, dept, rows[-1] if rows else None


def parse_layout_c(lines, book, dept=None, pending=None):
    """Annexure of the BC, Minorities, SC and ST books: coded departments, HoA rows.

    Same carry-over as layout A, and it matters far more here: one `AGC02-Agriculture
    Department` line heads dozens of rows spread over several pages. Resetting per page
    left 774 of the Backward Classes book's 913 rows with no department.
    """
    rows, prev = [], None
    for raw in lines:
        s = raw.strip()
        # A blank line does not end a row here either, for the reason in parse_layout_a.
        if not s:
            continue
        if NUMERIC_ONLY.match(s) or JUNK.match(s):
            prev = None
            continue

        m = C_ROW.match(s)
        if m:
            name, figs = split_figures(m.group(3))
            if not figs or len(clean(name)) < 3:
                prev = None
                continue
            row = {"department": dept, "name": flat(name),
                   "be_lakh": amount(figs[-1]), "hoa": m.group(2),
                   "name_col": raw.index(m.group(2)) + len(m.group(2)) + 1, "book": book}
            rows.append(row)
            prev, pending = row, None
            continue

        m = C_DEPT.match(s)
        if m:
            prev = {"name": flat(m.group(2)), "is_dept": True,
                    "name_col": raw.index(m.group(1)) + len(m.group(1)) + 1}
            dept, pending = clean(prev["name"]), None
            continue

        if prev is None and pending is not None:
            # First content line of a new page, and the previous page ended mid-name.
            _continue(pending, raw, s)
            pending = None
            continue

        prev = _continue(prev, raw, s)
        if prev is not None and prev.get("is_dept"):
            dept = clean(prev["name"])
    return rows, dept, rows[-1] if rows else None


def _continue(prev, raw, s):
    """Append a wrapped name fragment to the row above it, or drop the line.

    The fragment has to sit at or right of the name column of the row it continues.
    Without that test the page-number footer, which is far to the right and carries no
    figure, is appended to the last scheme on every page.
    """
    if prev is None or split_figures(s)[1]:
        return None
    if indent(raw) < prev["name_col"] - 4:
        return None
    # A trailing hyphen means two different things and both appear in these books.
    # "...under Nadu-" / "Nedu" is one hyphenated word broken over the line and rejoins
    # as "Nadu-Nedu"; "...Programme - ASCAD -" / "Grant for training" is a dash used as
    # punctuation and keeps its spaces. The tell is whether a letter sits against the
    # hyphen. Joining both the same way produced "Nadu Nedu" and "ASCAD Grant".
    head = prev["name"]
    prev["name"] = head + flat(s) if re.search(r"\w-$", head) else head + " " + flat(s)
    return prev


def printed_total(text):
    """The book's own figure for everything in its tables, or None if it prints none."""
    g = GRAND_TOTAL.findall(text)
    if g:
        return sum(float(v.replace(",", "")) for v in g)
    p = PART_TOTAL.findall(text)
    if p:
        return sum(float(v.replace(",", "")) for v in p)
    return None


def parse_text(text, book):
    """Every table page of one book, in page order.

    Two things carry across the page break. The department, because a department's rows
    run over the break. And `pending`, the last row of the previous page, because 16 names
    finish on the next page: it is offered exactly one line, the first content line after
    the header block, and then dropped.

    Both are reset whenever a non-table page intervenes or the layout changes, because
    that is a new chapter and its first table row is always preceded by its own department
    header. Carrying them further would silently file the first rows of a new chapter
    under the last department of the old one.
    """
    rows, skipped, dept, last_kind, pending = [], 0, None, None, None
    for page in text.split("\f"):
        kind = layout_of(page)
        if kind is None:
            skipped += 1
            dept, last_kind, pending = None, None, None
            continue
        if kind != last_kind:
            dept, pending = None, None
        reader = parse_layout_a if kind == "A" else parse_layout_c
        got, dept, pending = reader(page.splitlines(), book, dept, pending)
        rows.extend(got)
        last_kind = kind
    for r in rows:
        r["name"] = clean(r["name"])
    return [r for r in rows if len(r["name"]) >= 3], skipped


def fold_book(rows):
    """One book's rows to {key: entry}. Sums across heads of account, never across names.

    Two rows of the same book with the same department, the same name and DIFFERENT heads
    of account are two components of one provision (the general head, the -789 SC head,
    the -796 ST head, revenue and capital), so they add. Two rows with the same head of
    account are the same line read twice and must not. Layout A has no head of account at
    all; there the larger of the two is kept, because nothing in the page proves the two
    lines are separate provisions and inventing a sum would be the expensive direction of
    error.
    """
    out = {}
    for r in rows:
        k = (key(r["department"] or ""), key(r["name"]))
        e = out.get(k)
        if e is None:
            e = out[k] = {"name": r["name"], "department": r["department"],
                          "be_lakh": None, "hoas": set()}
        amt = r["be_lakh"]
        if amt is None:
            continue
        if r["hoa"] is None:
            e["be_lakh"] = amt if e["be_lakh"] is None else max(e["be_lakh"], amt)
        elif r["hoa"] not in e["hoas"]:
            e["hoas"].add(r["hoa"])
            e["be_lakh"] = amt if e["be_lakh"] is None else e["be_lakh"] + amt
    return out


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "andhra", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/andhra/: run collect/andhra.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "andhra", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    merged, per_book, per_book_schemes, checks = {}, {}, {}, {}
    # sorted(), not dict order: a set or a dict iterated in insertion order is how
    # parse/registry.py came to manufacture false change events. Everything whose order
    # could vary is sorted before it can reach the output.
    for book in sorted(BOOK_LABEL):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        rows, _ = parse_text(text, book)
        per_book[book] = len(rows)
        # Assertion 3: the rows read must add up to the total the book prints about
        # itself. Measured on the 2026-27 snapshot, all six reconcile to the paisa
        # (Gender 1949647.34 + 7136307.04, Child 1616833.07 + 851734.24, BC 5102056.09,
        # Minorities 609045.37, SC 2064357.13, ST 918961.37). A page silently dropped by
        # a layout change is exactly the failure this catches, and a dropped page is what
        # turns into a headline about a state deleting schemes.
        want = printed_total(text)
        got = round(sum(r["be_lakh"] or 0 for r in rows), 2)
        checks[book] = {"printed": want, "parsed": got,
                        "ok": want is not None and abs(want - got) < 0.02}
        folded = fold_book(rows)
        per_book_schemes[book] = len(folded)
        label = BOOK_LABEL[book]
        for k, e in sorted(folded.items()):
            cur = merged.get(k)
            if cur is None:
                merged[k] = {"name": e["name"], "department": e["department"],
                             "be_lakh": e["be_lakh"], "books": [label],
                             "hoas": set(e["hoas"])}
                continue
            if label not in cur["books"]:
                cur["books"].append(label)
            cur["hoas"] |= e["hoas"]
            # The largest slice, never the sum. See the module docstring.
            if e["be_lakh"] is not None:
                cur["be_lakh"] = (e["be_lakh"] if cur["be_lakh"] is None
                                  else max(cur["be_lakh"], e["be_lakh"]))

    out = sorted(merged.values(),
                 key=lambda r: (key(r["department"] or ""), key(r["name"])))
    # Publish the heads of account. They were collected to decide whether two rows add
    # and then dropped, which threw away the only evidence that settles whether two
    # differently branded names are one provision. Andhra Pradesh pays social pensions
    # under "NTR Bharosa" and myScheme lists eight "INDIRAMMA" pensions; nothing in either
    # name answers whether those are the same money, and a shared head of account would.
    # Karnataka keys on the head of account for exactly this reason.
    for r in out:
        r["books"] = sorted(r["books"])
        r["hoas"] = sorted(r.pop("hoas", ()))

    # A judgement recorded rather than buried, because it decides eight absence claims.
    #
    # myScheme lists eight "INDIRAMMA" pensions for Andhra Pradesh, cut by type (old age,
    # widow, weavers, disabled) crossed with rural and urban. The budget pays social
    # pensions as "NTR Bharosa Pension Scheme" across five welfare departments plus the
    # EWS and rural development ones, Rs 27,819 cr in all. Nothing in either name says
    # whether they are the same money under two political brands.
    #
    # What the evidence here shows. INDIRAMMA appears nowhere in the Andhra Pradesh budget,
    # not once in 552 names. NTR Bharosa's heads of account run 901 to 911 and 940 to 943
    # under 2225-XX-102-11-53-900, the same block repeated in each department, which is the
    # shape of one provision subdivided by category and then cross-cut by social group.
    # Category is the axis INDIRAMMA is cut on, so the two are consistent with being one
    # scheme renamed.
    #
    # Consistent with is not the same as shown to be, so they are kept DISTINCT. Merging
    # them would erase eight named schemes from the count of what myScheme documents and
    # would assert a renaming this register cannot evidence. Keeping them apart risks the
    # milder error, counting one provision twice under two names, which is visible to any
    # reader because both names are published side by side.
    #
    # What would settle it, in order of decisiveness: the sub-head NAMES under
    # 2225-01-102-11-53-900-9xx, which are in Volume-III-12 and not in these six books, and
    # which would show whether 901 to 911 really are old age, widow, weavers and disabled;
    # a government order renaming the scheme; or a start date on the myScheme records,
    # which carry none. All eight also lack an implementing agency and a benefit amount,
    # saying only that the scale "will be notified by the Government of Andhra Pradesh",
    # and one of them describes itself as a different scheme than its own title.
    write_json("data/andhra/schemes.json", {
        "decisions": [{
            "question": ("Are myScheme's eight INDIRAMMA pensions the same provision as "
                         "the budget's NTR Bharosa Pension Scheme, renamed?"),
            "decision": "kept distinct",
            "affects": "eight absence claims",
            "for_same": ("INDIRAMMA appears nowhere in the budget; NTR Bharosa's sub-heads "
                         "901-911 and 940-943 repeat per department, the shape of one "
                         "provision cut by category, which is INDIRAMMA's own axis"),
            "for_distinct": ("no document here says one was renamed to the other, and no "
                             "head of account is shared, because myScheme publishes none"),
            "why_this_way": ("merging asserts a renaming this register cannot evidence and "
                             "erases eight named schemes; keeping them apart risks counting "
                             "one provision twice, which a reader can see, since both names "
                             "are published"),
            "would_settle_it": ("the sub-head names under 2225-01-102-11-53-900-9xx in "
                                "Volume-III-12, a government order renaming the scheme, or "
                                "a start date on the myScheme records, which carry none"),
        }],
        "snapshot": date,
        "built": utcnow(),
        "state": "Andhra Pradesh",
        "cycle": man.get("cycle"),
        "source": ("Andhra Pradesh Budget, scheme-wise books (Gender, Child, Backward "
                   "Classes, Minorities, SC Component, ST Component)"),
        "source_url": man.get("page_url") or man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "schemes": len(out),
        "with_allocation": sum(1 for r in out if r.get("be_lakh")),
        "caveat": ("These are the scheme-wise cuts of the state budget, so a scheme with "
                   "no women, child, Backward Classes, Minorities or SC/ST earmark does "
                   "not appear. The number here is a floor on Andhra Pradesh's schemes, "
                   "never a total. be_lakh is the largest single-book slice of the "
                   "provision, not the whole provision: each book reports only the part "
                   "attributable to its own group, and the books overlap, so they are "
                   "not added. Some rows are establishment heads the books list "
                   "alongside schemes (District Offices, Headquarters Office, "
                   "Buildings); they are kept because the state files them here, and a "
                   "reader counting schemes should discount them."),
        "entries": out,
    })
    return out, per_book, per_book_schemes, checks, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Andhra Pradesh budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, per_book_schemes, checks, date = run(a.date)
    print(f"andhra snapshot {date}")
    for b in sorted(per_book):
        c = checks[b]
        print(f"    {b:<18}{per_book[b]:>6} rows{per_book_schemes[b]:>7} schemes   "
              f"total {'reconciles' if c['ok'] else 'MISMATCH'} "
              f"{c['parsed']:,.2f} vs {c['printed']}")
    print(f"  {len(out)} distinct schemes by department and name")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    bad = sorted(b for b, c in checks.items() if not c["ok"])
    if bad:
        # Fail loud, and only after the file is written: PLAN.md §8 wants the bad run
        # archived and visible, not swallowed.
        print("  ERROR: parsed rows do not add up to the printed total for "
              + ", ".join(bad))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
