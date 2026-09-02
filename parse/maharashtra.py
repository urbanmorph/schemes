"""
Parse the archived Maharashtra Annual Scheme book into data/maharashtra/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches. A parser bug costs a rerun,
never a snapshot.

WHAT THE BOOK IS. ANNUAL SCHEME 2026-2027 (Departmentwise), English edition, 752 pages,
published by the Planning Department through BEAMS. It is seven statements about the same
1,956 schemes:

    GN2  SCHEMEWISE DETAILED STATEMENT - STATE SCHEME, in three cuts, GENERAL, SCCS
         (Scheduled Caste Component) and TCS (Tribal Component). 1,952 scheme codes, one
         row each, plus a second row per additional budget code.  THE REGISTER.
    GN3  SCHEMEWISE PHYSICAL TARGETS, keyed on the same scheme code.
    GN4  SCHEMEWISE DETAILS OF CENTRALLY SPONSORED / ASSISTED SCHEMES. 502 codes, of
         which 498 are already in GN2 and 4 are not.
    GN5  EXTERNALLY AIDED PROJECTS, 31 codes, ALL of them already in GN2.
    GN6  PROJECTS FUNDED FROM DOMESTIC FINANCIAL INSTITUTIONS, 24 codes, ALL already in
         GN2.
    GN7  SCHEMES RELATED TO WOMEN AND CHILD DEVELOPMENT.
    GN8  SCHEMES RELATED TO HUMAN DEVELOPMENT.

WHY ONLY GN2 AND GN4 ARE READ, measured on the 2026-09-02 snapshot and not assumed:
GN5's 31 scheme codes and GN6's 24 are every one of them present in GN2, so parsing them
would add no scheme and would only risk a second, worse-shaped reading of the same money.
GN4 is read because 4 of its 502 codes appear nowhere else (the four NSAP pensions filed
under Tribal Sub-Plan, 1411140001 to 1411140004) and because it lets the book be checked
against itself; see RECONCILIATION below. GN7 and GN8 carry NO scheme code, only a
department and a name, so folding them in would mean matching Maharashtra's names to
Maharashtra's own names and inventing a link the state did not print. They are counted
and not merged. GN3 is not parsed here: its name column and its Target Description column
both wrap and a reading of it is a separate job, recorded as the next thing worth doing.

RECONCILIATION, two independent checks, both hard errors:

  1. Every "Sub Sector Total" the book prints, against the sum of the scheme rows read
     under that sub-sector, in ALL FOUR money columns. 382 of them.
  2. Every scheme that appears in BOTH GN2 and GN4, GN2's total against GN4's, again in
     all four columns. These are two separately typeset statements about the same money,
     so an agreement is worth more than an internal sum.

UNITS. Every detail page prints "(₹.In Lakhs)" and there is no second unit anywhere in
the book: 508 of 753 pages carry that marker and none carries any other. That is checked
per page and a page naming a different unit is a hard error, because the Kerala Annual
Plan prints lakh and THOUSANDS in the same header block on 333 of 491 pages, and read as
lakh every one of those allocations publishes at 100 times its value while looking
entirely plausible. The figure published here is therefore rupees in lakh as printed,
converted by nothing.

GEOMETRY. This book is read from `pdftotext -layout`, NOT from `-bbox-layout` as Kerala
and Tamil Nadu are. Both bbox modes abort on this file with
"terminating due to uncaught exception of type std::out_of_range" from poppler 26.04,
after emitting the opening <title> tag and before the first page, on every page tried
(1, 2, 5, 33, 700). The layout mode reads the same file without complaint. The row
grammar below is token-based rather than column-sliced, so it does not depend on the
character offsets `-layout` chooses, which move from page to page: the ruler row "1 2 3
... 9" that each page prints sits at a different offset on nearly every page.
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

# One money cell. The book prints plain two-decimal figures; a nil provision is 0.00 and
# a negative one is real (a recovery head) so the sign is kept. Commas are accepted
# because a handful of the larger totals carry them.
MONEY = re.compile(r"^-?[\d,]*\d\.\d{2}$")
SCHEME_CODE = re.compile(r"^\d{10}$")
# The budget code, which is Maharashtra's head of account in its 8-character BEAMS form.
# Two shapes on this snapshot, 1,205 of 99999999 and 741 of 9999A999, so the letter is in
# a fixed position and cannot be confused with a name word.
BUDGET_CODE = re.compile(r"^\d{4}[0-9A-Z]\d{3}$")
# Pattern of Funding, the centre-to-state share. "100", "60", "0/28", "0/100", and six
# rows in the book that split it to one decimal place: 54.5/45.5 for PMKSY (AIBP) SNA
# Sparsh and 47.1/52.9 and 31.9/68.1 for two Pradhan Mantri share capital contributions.
# Without the decimal those six rows fall out of the centrally sponsored statement
# entirely, taking three schemes out of the GN2-against-GN4 check with them. One decimal
# and not two, so a pattern can never be confused with a money cell, which the book
# always prints to exactly two.
PATTERN = re.compile(r"^\d{1,3}(?:\.\d)?(?:/\d{1,3}(?:\.\d)?)?$")
SR_NO = re.compile(r"^\d{1,4}$")
STATEMENT = re.compile(r"STATEMENT-(GN\d)")
UNIT = re.compile(r"\(\s*(?:₹|Rs)\.?\s*In\s+(\w+)\s*\)", re.I)

# Source of Fund, as the book writes it. Longest phrase wins, because "Ext. Grant/Ext.
# Loan" is three tokens and "Ext." on its own is one. An unrecognised source is recorded
# rather than guessed at, since the token before the budget code is the only thing
# separating the source from the last word of the scheme name.
SOURCES = ("Ext. Grant/Ext. Loan", "CSS-TBJ", "CSS-OBJ", "CASP", "State", "Central",
           "Others", "DFI", "EAP", "Ext.")

# The three cuts GN2 is printed in. Their scheme codes are disjoint on this snapshot
# (1,952 rows, 1,952 distinct codes), so a scheme belongs to exactly one of them and the
# SCCS and TCS provisions are separate schemes rather than slices of a general one.
GN2_CUT = re.compile(r"SCHEMEWISE DETAILED STATEMENT - STATE SCHEME,\s*(\w+)")

DEPT_GN2 = re.compile(
    r"^Department\s*:\s*(.*?)\s+Sector:\s*(.*?)(?:\s+Sub-Sector:\s*(.*))?$")
DEPT_GN4 = re.compile(
    r"^Department\s*:\s*(.*?)\s+Source of Fund\s*:\s*(.*?)"
    r"(?:\s+Umbrella Scheme:\s*(.*))?$")


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
    return float(tok.replace(",", ""))


def joined(parts):
    """Join wrapped name fragments. A fragment ending in a hyphen against a letter is one
    word broken over a line and must not gain a space; a hyphen used as punctuation keeps
    its spaces. Same rule as parse/andhra.py and parse/kerala.py."""
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
    # The book writes "( Umbrella 5 )" with spaces inside the brackets and wraps after
    # the number often enough that the closing bracket lands on its own line. Tidying the
    # spacing here rather than in the join keeps the join rule about hyphens only.
    out = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", out))
    return re.sub(r"\s+", " ", out).strip()


# The scheme code with the first word of the name run into it, with no space between
# them. This happens ONCE in the 752-page book, on page 528:
#
#     3       1101010028World Agriculture Census   24010996  Central  100  96.41 ...
#
# and it is not cosmetic. Read without this rule the row is attributed to the scheme
# above it, World Agriculture Census disappears from the register, and Improvement of
# Crop statistics is published carrying both provisions. That was the single failure of
# the GN2-against-GN4 check on the first correct run of this parser, which is exactly the
# job that check exists to do.
CODE_GLUED = re.compile(r"^(\d{10})(\D\S*)$")


def take_code(toks, stats):
    """Split (scheme code, remaining name tokens) off the front of a row."""
    if toks and SR_NO.match(toks[0]) and len(toks) >= 2 and (
            SCHEME_CODE.match(toks[1]) or CODE_GLUED.match(toks[1])):
        toks = toks[1:]
    if not toks:
        return None, toks
    if SCHEME_CODE.match(toks[0]):
        return toks[0], toks[1:]
    m = CODE_GLUED.match(toks[0])
    if m:
        stats["scheme_code_run_into_the_name"] += 1
        return m.group(1), [m.group(2)] + toks[1:]
    return None, toks


def take_source(toks):
    """Split a token list into (rest, source). Longest known phrase wins."""
    for s in sorted(SOURCES, key=len, reverse=True):
        parts = s.split()
        if len(toks) >= len(parts) and toks[-len(parts):] == parts:
            return toks[:len(toks) - len(parts)], s
    return toks, None


def parse_book(text, stats):
    """Read the annual scheme book. Returns (rows, subsector_totals, schemes).

    A row is one budget-code line: the scheme it belongs to, its source of fund, its
    8-character budget code and four figures. A scheme with two budget codes produces two
    rows, which is what the book prints and what its own Sub Sector Totals add up.

    State is carried ACROSS pages and reset only when the statement or the cut changes.
    That is not a nicety. Measured on the first run of this parser, resetting per page
    put 110 budget-code rows under no scheme at all and left 79 of 382 Sub Sector Totals
    with no department to compare against, because a sub-sector's header is printed once
    and its rows then run over the page break.
    """
    rows, totals, schemes = [], [], {}
    st = cut = dept = sector = subsector = umbrella = source_group = None
    cur = None                      # the scheme whose name is still being collected

    for pno, page in enumerate(text.split("\f"), 1):
        m = STATEMENT.search(page)
        if not m:
            stats["pages_no_statement"] += 1
            continue
        page_st = m.group(1)
        if page_st not in ("GN2", "GN4"):
            stats[f"pages_{page_st.lower()}_not_read"] += 1
            continue
        u = UNIT.search(page)
        if not u:
            stats["pages_no_unit_marker"] += 1
            continue
        unit = u.group(1).lower()
        if unit not in ("lakh", "lakhs"):
            # Hard error rather than a conversion: a unit this parser has never seen
            # means the book changed and every figure on the page is suspect.
            raise SystemExit(f"page {pno} of the annual scheme book says unit "
                             f"{unit!r}, not lakhs; refusing to publish")
        stats["pages_lakhs"] += 1
        page_cut = None
        if page_st == "GN2":
            c = GN2_CUT.search(page)
            if not c:
                stats["pages_gn2_no_cut"] += 1
                continue
            page_cut = c.group(1).upper()
        if (page_st, page_cut) != (st, cut):
            st, cut = page_st, page_cut
            dept = sector = subsector = umbrella = source_group = None
            cur = None

        lines = page.split("\n")
        # Skip the repeated column headers. Every page prints a ruler row of column
        # numbers ("1 2 3 4 5 6 7 8 9") and the body starts under it. Finding the body
        # this way rather than by a fixed line count is what keeps the four-line wrapped
        # header of GN5 and the three-line one of GN2 out of the name field.
        start = 0
        for i, line in enumerate(lines[:16]):
            t = line.split()
            if t[:6] == ["1", "2", "3", "4", "5", "6"]:
                start = i + 1
                break

        for line in lines[start:]:
            s = line.strip()
            if not s:
                continue
            d = DEPT_GN2.match(s) if st == "GN2" else DEPT_GN4.match(s)
            if d:
                cur = None
                if st == "GN2":
                    dept, sector, subsector = d.group(1), d.group(2), d.group(3)
                else:
                    dept, source_group, umbrella = d.group(1), d.group(2), d.group(3)
                continue
            toks = s.split()
            tail = []
            while toks and MONEY.match(toks[-1]):
                tail.insert(0, toks.pop())

            if len(tail) != 4:
                # A page number is a bare integer on its own line and is the one text
                # line that must not be read as a name continuation.
                if not tail and toks and cur is not None and not (
                        len(toks) == 1 and toks[0].isdigit()):
                    schemes[cur]["name_parts"].extend(toks)
                    stats["name_continuation_rows"] += 1
                elif tail:
                    stats["short_figure_rows"] += 1
                else:
                    stats["text_rows_outside_a_scheme"] += 1
                continue

            # A figure row with no budget code anywhere in it is one of the book's own
            # printed totals: Sub Sector Total, Sector Total, Grand Total, State Scheme
            # Excl CSS-TBJ, Department incl CSS-TBJ and the rest. Only Sub Sector Total
            # is used as a check; the others are counted so the shape of the page is
            # accounted for rather than silently dropped.
            if not any(BUDGET_CODE.match(t) for t in toks):
                cur = None
                if "Sub Sector Total" in s:
                    totals.append({"page": pno, "statement": st, "cut": cut,
                                   "department": dept, "sector": sector,
                                   "subsector": subsector,
                                   "figures": [money(t) for t in tail]})
                else:
                    stats["other_printed_total_rows"] += 1
                continue

            if st == "GN2":
                bcode = toks.pop() if toks and BUDGET_CODE.match(toks[-1]) else None
                toks, src = take_source(toks)
            else:
                if toks and PATTERN.match(toks[-1]):
                    toks.pop()
                toks, src = take_source(toks)
                bcode = toks.pop() if toks and BUDGET_CODE.match(toks[-1]) else None
            if bcode is None:
                stats["figure_rows_with_no_budget_code_in_position"] += 1
                continue
            if src is None:
                stats["rows_without_a_known_source"] += 1

            code, toks = take_code(toks, stats)

            if code is not None:
                cur = (st, code)
                stats["scheme_rows"] += 1
            elif cur is None:
                stats["budget_code_rows_with_no_scheme"] += 1
                continue
            else:
                stats["extra_budget_code_rows"] += 1

            e = schemes.get(cur)
            if e is None:
                e = schemes[cur] = {
                    "code": cur[1], "statement": st, "cut": cut, "name_parts": [],
                    "department": dept, "sector": sector, "subsector": subsector,
                    "umbrella": umbrella, "source_group": source_group,
                    "sources": set(), "budget_codes": set(),
                    "figures": [0.0, 0.0, 0.0, 0.0], "first_page": pno}
            if toks:
                e["name_parts"].extend(toks)
            if src:
                e["sources"].add(src)
            e["budget_codes"].add(bcode)
            figs = [money(t) for t in tail]
            for i, v in enumerate(figs):
                e["figures"][i] = round(e["figures"][i] + v, 2)
            rows.append({"statement": st, "cut": cut, "department": dept,
                         "sector": sector, "subsector": subsector, "code": cur[1],
                         "source": src, "budget_code": bcode, "figures": figs})
    return rows, totals, schemes


def fold(schemes, statement):
    """The schemes of one statement, keyed on the scheme code.

    The figures of every budget-code row were ADDED as they were read. That is what the
    book's own Sub Sector Totals add, and it is right here in a way it would not be for
    Kerala's overlapping books: two rows of one scheme are two heads of account carrying
    different halves of the same provision, most often the state and central shares of a
    centrally sponsored scheme, and neither is a slice of the other.
    """
    return {c: e for (st, c), e in schemes.items() if st == statement}


def reconcile_subsectors(rows, totals):
    """Each printed Sub Sector Total against the rows read under it, all four columns."""
    got = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for r in rows:
        k = (r["statement"], r["cut"], r["department"], r["sector"], r["subsector"])
        for i, v in enumerate(r["figures"]):
            got[k][i] = round(got[k][i] + v, 2)
    checked, failures = 0, []
    for t in totals:
        k = (t["statement"], t["cut"], t["department"], t["sector"], t["subsector"])
        mine = got.get(k)
        checked += 1
        if mine is None or any(abs(a - b) > 0.02 for a, b in zip(mine, t["figures"])):
            failures.append({"page": t["page"], "department": t["department"],
                             "sector": t["sector"], "subsector": t["subsector"],
                             "printed": t["figures"], "parsed": mine})
    return checked, failures


def reconcile_gn2_gn4(gn2, gn4):
    """Every scheme in both statements, GN2's four figures against GN4's."""
    shared = sorted(set(gn2) & set(gn4))
    failures = []
    for c in shared:
        a, b = gn2[c]["figures"], gn4[c]["figures"]
        if any(abs(x - y) > 0.02 for x, y in zip(a, b)):
            failures.append({"code": c, "name": joined(gn2[c]["name_parts"])[:70],
                             "gn2": a, "gn4": b})
    return len(shared), failures


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "maharashtra", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/maharashtra/: "
                         "run collect/maharashtra.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "maharashtra", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    book = os.path.join(src, "annual-scheme-en.pdf.gz")
    if not os.path.exists(book):
        raise SystemExit(f"{book} is missing; the register cannot be built without it")
    with gzip.open(book, "rb") as fh:
        text = pdftotext(fh.read())

    stats = collections.Counter()
    rows, totals, schemes = parse_book(text, stats)
    gn2, gn4 = fold(schemes, "GN2"), fold(schemes, "GN4")

    sub_checked, sub_fail = reconcile_subsectors(rows, totals)
    shared, cross_fail = reconcile_gn2_gn4(gn2, gn4)

    # GN2 is the register. GN4 contributes only the codes GN2 does not carry, which is 4
    # on this snapshot; taking GN4's figure for a scheme GN2 also lists would replace a
    # figure with a differently rounded copy of itself for no gain.
    merged = dict(gn2)
    gn4_only = sorted(set(gn4) - set(gn2))
    for c in gn4_only:
        merged[c] = gn4[c]

    out = []
    for c in sorted(merged):
        e = merged[c]
        name = joined(e["name_parts"])
        out.append({
            "code": c,
            "name": name,
            "department": e["department"],
            "sector": e["sector"],
            "sub_sector": e["subsector"],
            "component": e["cut"] or ("CSS" if e["statement"] == "GN4" else None),
            "statement": e["statement"],
            "sources": sorted(e["sources"]),
            "budget_codes": sorted(e["budget_codes"]),
            "actual_2024_25_lakh": e["figures"][0],
            "be_2025_26_lakh": e["figures"][1],
            "anticipated_2025_26_lakh": e["figures"][2],
            "be_lakh": e["figures"][3],
        })

    unnamed = [r["code"] for r in out if not r["name"]]
    write_json("data/maharashtra/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Maharashtra",
        "cycle": man.get("cycle"),
        "source": ("Maharashtra Budget, ANNUAL SCHEME 2026-2027 (Departmentwise), "
                   "English edition, statements GN2 and GN4"),
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH exactly as the book prints them, "
            "converted by nothing. The unit is read from each page's own "
            "(₹.In Lakhs) marker and not assumed: every detail page read carries it and "
            "a page naming any other unit is a hard error. Checked against the outside "
            "world as well as against the book: Mukhyamantri Mazi Ladaki Bahin, the "
            "state's largest single scheme, comes out at 21,00,000 lakh, which is "
            "Rs 21,000 crore, the figure Maharashtra states publicly for it. Read as "
            "thousands it would have been Rs 210 crore and as crore Rs 21 lakh crore. "
            "be_lakh is the Annual Scheme 2026-27 Proposed Fund, the last of the book's "
            "four money columns; the other three are published beside it."),
        "variant": "Budget Estimate 2026-2027",
        "variant_note": (
            "Maharashtra presents one budget for 2026-2027. Its supplementary demands "
            "are published separately on the BEAMS front page (June 2026, December 2025, "
            "February 2025) and are NOT added here, because adding them would turn a "
            "budget estimate into a part-year revised figure and stop this number being "
            "comparable with Karnataka's and Kerala's. Two errata files for 2026-2027 "
            "are archived alongside the book and are not applied; a figure here is what "
            "the book printed."),
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "gn2_scheme_codes": len(gn2),
            "gn4_scheme_codes": len(gn4),
            "gn4_only_scheme_codes": gn4_only,
            "budget_code_rows_read": len(rows),
            "with_a_positive_be": sum(1 for r in out if r["be_lakh"] > 0),
            "funded_at_nil": sum(1 for r in out if r["be_lakh"] == 0),
            "with_more_than_one_budget_code": sum(
                1 for r in out if len(r["budget_codes"]) > 1),
            "names_empty_after_reading": unnamed,
            "by_component": dict(collections.Counter(
                r["component"] for r in out)),
        },
        "extraction_stats": dict(stats),
        "reconciliation": {
            "sub_sector_totals": {
                "checked": sub_checked, "failed": len(sub_fail),
                "failures": sub_fail[:20] or None,
                "what": ("each printed Sub Sector Total against the sum of the "
                         "budget-code rows read under it, in all four money columns")},
            "gn2_against_gn4": {
                "checked": shared, "failed": len(cross_fail),
                "failures": cross_fail[:20] or None,
                "what": ("every scheme printed in both the state-scheme statement and "
                         "the centrally-sponsored statement, GN2's four figures against "
                         "GN4's; two separately typeset statements about the same "
                         "money")},
        },
        # The join against myScheme, run once by hand on the 2026-09-02 snapshot and read
        # line by line, all 167 of them. Recorded here rather than recomputed on every
        # run because the classification is a human reading, not a rule. parse/match.py
        # is NOT edited to fix any of these; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_maharashtra_records": 84,
            "joins_produced": 167,
            "joins_sound_on_inspection": 36,
            "joins_wrong_on_inspection": 131,
            "myscheme_records_with_any_join": 22,
            "myscheme_records_with_a_sound_join": 17,
            "scheme_codes_with_a_sound_join": 36,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read "
                    "by eye"),
            "read_this_carefully": (
                "17 of myScheme's 84 Maharashtra records were found in a book that names "
                "1,956 schemes. That is NOT evidence that the other 67 are invented. The "
                "Annual Scheme book is the SCHEME budget, so a provision paid from "
                "establishment or from a corporation's own funds is not in it; and this "
                "register is a superset in the other direction too, because rows like "
                "'District and Other Roads' and '4700 Capital Outlay on Major Irrigation' "
                "are heads of expenditure and not schemes a citizen can apply to. Both "
                "counts are floors, and neither supports a claim about the other without "
                "reading the pair."),
        },
        "myscheme_join_defects": [
            {"defect": ("a COMMUNITY abbreviation written in capitals on both sides is "
                        "read as a scheme acronym. VJNT is Vimukta Jati and Nomadic "
                        "Tribes, the same kind of word as SC, ST, OBC and minority, "
                        "which QUALIFIERS already knows describe a scheme rather than "
                        "name it. VJNT and SBC are in neither QUALIFIERS nor "
                        "NOT_ACRONYMS, so written_acronyms returns vjnt for both names "
                        "and the containment rule fires at a perfect ratio"),
             "reason_string": "acronym containment: vjnt / vjnt",
             "joins": 125,
             "example_myscheme": "Training Of Motor Driving To VJNT, SBS & OBC",
             "example_budget": "Tanda Vasti Sudhar Yojana For VJNT And SBC",
             "note": ("125 of the 131 wrong joins on this corpus are this one hole. Six "
                      "myScheme records each fanned out to the same 21 register rows, "
                      "which is every row in the book whose name contains VJNT.")},
            {"defect": ("the consonant skeleton silently DROPS the words that "
                        "distinguish sibling schemes, because it drops any token that "
                        "falls under three characters after the vowels come out. 'old' "
                        "becomes 'ld' and 'age' becomes 'g', so the National Old Age "
                        "Pension's skeleton set is a strict subset of the National Widow "
                        "Pension's and the two match on the three brand words they share"),
             "reason_string": "transliteration variant: ['gnd', 'ndr', 'ntnl']",
             "joins": 4,
             "example_myscheme": "Indira Gandhi National Widow Pension Scheme (Maharashtra)",
             "example_budget": "Indira Gandhi National Old Age Pension Scheme(Others 67)",
             "note": ("the three NSAP pensions share three quarters of their names and "
                      "differ only on short words. Old age, widow and disability are a "
                      "sibling axis exactly like rural and urban, and QUALIFIERS has no "
                      "entry for them.")},
            {"defect": ("the same skeleton rule, this time dropping a CLASS RANGE. Two "
                        "Savitribai Phule scholarships differ only in that one is for "
                        "5th to 7th standard and the other for VIII to X. '5th' reduces "
                        "to '5t' and 'VIII' to 'v', both under the three-character "
                        "floor, so both vanish and six generic words carry the match"),
             "reason_string": "transliteration variant: ['grl', 'sclrsp', 'stdnt']",
             "joins": 1,
             "example_myscheme": ("Savitribai Phule Scholarship For V.J.N.T. And S.B.C. "
                                  "Girl Students Studying In 5th To 7th Standard"),
             "example_budget": ("Savitribai Phule Scholarship For VJNT And SBC Girl "
                                "Students Studying In VIII To X Standard"),
             "note": ("QUALIFIERS has primary, secondary and higher but no numbered "
                      "standards, and the two sides do not even write the number the "
                      "same way, one in digits and one in Roman numerals.")},
            {"defect": ("the all-caps stand-down in acronyms() is defeated by a single "
                        "mixed-case suffix. The rule refuses to read acronyms out of a "
                        "name that shouts every word, which is right; but Maharashtra "
                        "appends '(Umbrella 27)' to its shouted names, the lowercase "
                        "'mbrella' makes letters != letters.upper(), the stand-down does "
                        "not apply, and INFRASTRUCTURE and INSTITUTION both become "
                        "acronyms"),
             "reason_string": "acronym match: institution",
             "joins": 1,
             "example_myscheme": ("Special Education And Vocational Training Through "
                                  "Government Institutions"),
             "example_budget": ("INFRASTRUCTURE DEVELOPMENT FOR SCHOOL RUN BY MINORITY "
                                "INSTITUTION (IDMI)(Umbrella 27)"),
             "note": ("a new instance of a hole already recorded against Andhra Pradesh "
                      "and Tamil Nadu, with a new mechanism: it is not that INSTITUTION "
                      "is missing from NOT_ACRONYMS, it is that the guard which should "
                      "have suppressed the whole branch was switched off by a bracketed "
                      "note the state adds to the end of the name.")},
            {"defect": ("an ordinary Hindi word in capitals read as an acronym. This one "
                        "produced a CORRECT join and is recorded anyway, because the "
                        "rule that produced it is unsound and will not be correct next "
                        "time"),
             "reason_string": "acronym match: aadmi",
             "joins": 0,
             "example_myscheme": "Aam Aadmi Bima Yojana (Maharashtra)",
             "example_budget": ("AAM AADMI VIMA YOJANA (Premium of Janshree Vima Yojana "
                                "for Unorgnised Labour)"),
             "note": ("counted as sound in the totals above because the pair really is "
                      "one scheme, so the 131 wrong joins do not include it.")},
        ],
        "caveat": (
            "One row here is one SCHEME as Maharashtra's Planning Department numbers "
            "them, keyed on the 10-digit scheme code the state prints. be_lakh is the "
            "sum of that scheme's budget-code rows, which is what the book's own Sub "
            "Sector Totals add: two rows of one scheme are two heads of account holding "
            "different halves of one provision, most often the state and central shares "
            "of a centrally sponsored scheme. The GENERAL, SCCS (Scheduled Caste "
            "Component) and TCS (Tribal Component) cuts use disjoint scheme codes on "
            "this snapshot, so a scheme belongs to exactly one of them and none is "
            "counted twice. Statements GN5 (externally aided) and GN6 (domestic "
            "financial institutions) are not read because all 31 and all 24 of their "
            "scheme codes already appear in GN2. Statements GN7 and GN8, the women and "
            "child and human development cross-cuts, carry no scheme code and are not "
            "merged, because linking them would mean matching Maharashtra's names to "
            "Maharashtra's own names and asserting a link the state did not print. "
            "Statement GN3, the physical targets, is not read yet."),
        "entries": out,
    })
    return out, stats, (sub_checked, sub_fail), (shared, cross_fail), date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Maharashtra Annual Scheme book.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, stats, (sub_checked, sub_fail), (shared, cross_fail), date = run(a.date)
    print(f"maharashtra snapshot {date}")
    print(f"  {len(out)} schemes, keyed on the state's 10-digit scheme code")
    print(f"     with a positive 2026-27 provision "
          f"{sum(1 for r in out if r['be_lakh'] > 0):>6}")
    print(f"     sum of 2026-27 provisions      "
          f"{sum(r['be_lakh'] for r in out):>14,.2f} lakh")
    print(f"  sub sector totals   {sub_checked - len(sub_fail):>5} of {sub_checked:<5} "
          f"reconcile")
    print(f"  GN2 against GN4     {shared - len(cross_fail):>5} of {shared:<5} agree")
    for k, v in sorted(stats.items()):
        print(f"     {k:<36}{v:>8}")
    bad = []
    if sub_fail:
        bad.append(f"{len(sub_fail)} sub sector totals")
    if cross_fail:
        bad.append(f"{len(cross_fail)} GN2/GN4 disagreements")
    if bad:
        for f in (sub_fail + cross_fail)[:10]:
            print("     MISMATCH", json.dumps(f)[:200])
        # Fail loud and only after the file is written: PLAN.md 8 wants the bad run
        # visible, not swallowed.
        print("  ERROR: " + ", ".join(bad))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
