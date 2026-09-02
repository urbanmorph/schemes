"""
Parse the archived Odisha Demand for Grants books into data/odisha/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY ODISHA YIELDS. Every scheme row in these books is printed twice, once in English and
once in Odia, on consecutive lines. The Odia is proper Unicode in the U+0B00 block, not a
legacy font, so the two scripts separate on character range alone and the English name
never has to be told apart from anything else. That is the same property that made Kerala
work and it is the whole reason this parser is short.

THE HIERARCHY, which is Odisha's own and is what the register keys on:

    2875/60/190        major head / sub-major head / minor head, printed at the top of
                       every detail page, so a page always says where it is
      0070-  Assistance to PSUS & Other undertakings          a 4-digit SCHEME
       22125- Plug and Play Industrial Parks-DPIIT            a 5-digit sub-scheme
         073-  Infrastructural Assets      ..    1    1    1  a 3-digit object head
       TOTAL- 22125 Plug and Play Industrial Parks-DPIIT      printed sub-scheme total
      TOTAL- 0070 Assistance to PSUS & Other undertakings     printed scheme total

The 4-digit code is Odisha's scheme identifier and is the same code the Gender Budget
prints beside each scheme name, which is why the register keys on it. The same code
recurs under several demands when several departments fund the same scheme; those rows
are added and every demand that funds it is recorded.

RECONCILIATION, and this book gives an unusually strong one because it prints a total at
every level of its own tree. Three checks, all hard errors:

  1. Every printed "TOTAL- <5-digit>" against the sum of the object heads beneath it.
  2. Every printed "TOTAL- <4-digit>" against the sum of the sub-scheme totals and any
     object heads hanging directly off the scheme.
  3. Every book's own printed cycle, read off its cover page. A book that does not say
     2026-2027 is EXCLUDED and named, not quietly merged. This is not hypothetical: the
     state's budget portal at budget.odisha.gov.in links the 2025-2026 book for Demand 34
     while the 2026-2027 one sits on the server unlinked, which is why the collector reads
     the Finance Department's publication page instead.

UNITS. Every detail page prints "IN THOUSANDS OF RUPEES" and nothing else does: 820
markers across the six books measured and not one naming another unit. The figures are
converted to LAKH here so the number is comparable with Karnataka, Kerala, Tamil Nadu and
Maharashtra, and the conversion is stated in the output. A page naming any other unit is
a hard error rather than a conversion, because Kerala prints lakh and thousands in the
same header block on 333 of 491 pages and reading one as the other publishes every
allocation at 100 times its value while looking entirely plausible.

Odisha writes its figures in Indian digit grouping with the LAST group of two, so
"1124,49,92" is 1,12,44,992 thousands of rupees, or Rs 1,124.4992 crore, and ".." is nil.
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

# The Odia block plus the two joiners. Anything matching this is "not English", which is
# the only judgement this parser needs to make about a line.
ODIA = re.compile(r"[଀-୿‌‍]")

# One money cell: ".." for nil, or Indian digit grouping whose groups after the first are
# always two digits. A provision can be negative (a recovery head), so the sign is kept.
MONEY = re.compile(r"^(?:\.\.|-?\d{1,5}(?:,\d{2})*)$")
# The page's own statement of where it is: major / sub-major / minor head.
PAGE_HEAD = re.compile(r"^\s*(\d{4})/(\d{2})/(\d{3})\s*$", re.M)
UNIT = re.compile(r"IN\s+([A-Z]+)\s+OF\s+RUPEES", re.I)
CYCLE = re.compile(r"\b(20\d\d-20\d\d)\b")
RULER = re.compile(r"^\s*\(1\)\s+\(2\)\s+\(3\)")
CODE = re.compile(r"^(\d{3,5})-\s*(.*)$")
TOTAL = re.compile(r"^TOTAL\s*-\s*(\d{3,5})\s+(.*)$")

CYCLE_WANTED = "2026-2027"


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


def thousands(tok):
    """A money cell as a number of THOUSANDS of rupees. '..' is nil."""
    if tok == "..":
        return 0.0
    return float(tok.replace(",", ""))


def joined(parts):
    """Join wrapped name fragments. A fragment ending in a hyphen against a letter is one
    word broken over a line and must not gain a space. Same rule as parse/andhra.py."""
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


# Odisha votes some provisions and charges others on the Consolidated Fund, and prints
# the two separately. A CHARGED object head carries the word in the Voted/Charged column,
# and a scheme's printed TOTAL line is its VOTED total with the CHARGED total following
# on its own unlabelled line:
#
#     TOTAL- 0124  Chief Electoral Officer's Estt.   16,76,69  17,86,30  18,25,60  18,06,69
#                                            CHARGED       ..         1         1         1
#
# Read without this distinction the charged rows are added into the voted total and 60 of
# 17,799 printed totals fail to reconcile, most of them by a single thousand rupees, which
# is small enough to look like a rounding artefact and is not one.
CHARGED = "CHARGED"
VOTED = "VOTED"


class Node:
    """One code in the book's tree: a scheme, a sub-scheme or an object head."""

    __slots__ = ("code", "parts", "figures", "charged_figures", "children",
                 "printed_total", "printed_charged", "hoa", "demand")

    def __init__(self, code, hoa, demand):
        self.code, self.hoa, self.demand = code, hoa, demand
        self.parts, self.figures, self.charged_figures = [], None, None
        self.children = []
        self.printed_total = self.printed_charged = None

    @property
    def name(self):
        return joined(self.parts)

    def total(self, charged=False):
        own = self.charged_figures if charged else self.figures
        if own is not None or (self.figures is None and self.charged_figures is None
                               and not self.children):
            return list(own or [0.0, 0.0, 0.0, 0.0])
        t = [0.0, 0.0, 0.0, 0.0]
        for c in self.children:
            for i, v in enumerate(c.total(charged)):
                t[i] = round(t[i] + v, 3)
        return t


def parse_book(text, demand, stats):
    """Read one demand book. Returns (cycle, schemes, checks).

    schemes is a list of the 4-digit Nodes in the order met. checks is a list of
    (level, code, printed, computed) for every printed TOTAL that could be compared.
    """
    pages = text.split("\f")
    cycles = sorted(set(CYCLE.findall(pages[0]))) if pages else []
    cycle = cycles[0] if len(cycles) == 1 else None

    schemes, checks = [], []
    scheme = sub = None            # current 4-digit and 5-digit nodes
    target = None                  # the node whose name is still being collected
    last_total = None              # the node whose printed TOTAL line was just read
    last_total_level = None
    hoa = None

    for pno, page in enumerate(pages, 1):
        h = PAGE_HEAD.search(page)
        if not h:
            stats["pages_not_detail"] += 1
            continue
        u = UNIT.search(page)
        if not u:
            stats["detail_pages_with_no_unit_marker"] += 1
            continue
        unit = u.group(1).upper()
        if unit != "THOUSANDS":
            # Hard error rather than a conversion. See UNITS in the module docstring.
            raise SystemExit(f"demand {demand} page {pno} says the unit is {unit!r}, "
                             f"not THOUSANDS; refusing to publish")
        stats["detail_pages"] += 1
        hoa = f"{h.group(1)}-{h.group(2)}-{h.group(3)}"
        minor = h.group(3)

        body = False
        for raw in page.split("\n"):
            if not raw.strip():
                continue
            if RULER.match(raw):
                body = True
                continue
            if not body:
                continue
            # The Odia half of every row. Dropping it is the whole trick.
            if ODIA.search(raw):
                continue
            s = raw.strip()
            toks = s.split()
            tail = []
            while toks and MONEY.match(toks[-1]):
                tail.insert(0, toks.pop())
            # A row can end in more than four money-shaped tokens when a name ends in a
            # number. The four columns are the LAST four; anything before them belongs to
            # the name.
            if len(tail) > 4:
                toks.extend(tail[:-4])
                tail = tail[-4:]
            # The Voted/Charged column. Removed from the token list before anything else
            # reads it, and remembered, because it decides which of the node's two
            # figure vectors the row belongs to.
            charged = CHARGED in toks
            toks = [t for t in toks if t not in (CHARGED, VOTED)]
            rest = " ".join(toks)

            # The charged half of a printed total, which the book puts on its own line
            # under the TOTAL line with nothing but the word CHARGED to identify it.
            if charged and not rest and len(tail) == 4:
                if last_total is not None:
                    last_total.printed_charged = [thousands(t) for t in tail]
                    checks.append({"level": last_total_level, "voted": False,
                                   "demand": demand, "hoa": last_total.hoa,
                                   "code": last_total.code,
                                   "printed": last_total.printed_charged,
                                   "computed": last_total.total(charged=True)})
                else:
                    stats["charged_totals_above_the_scheme"] += 1
                target = None
                continue

            m = TOTAL.match(rest)
            if m and len(tail) == 4:
                code, frag = m.group(1), m.group(2)
                node = None
                if sub is not None and code == sub.code:
                    node = sub
                elif scheme is not None and code == scheme.code:
                    node = scheme
                if node is None:
                    # A total for a level this parser does not model: the minor head,
                    # the account, the demand. Counted, not read.
                    stats["printed_totals_above_the_scheme"] += 1
                    target = last_total = None
                    continue
                # A TOTAL line carries the word CHARGED itself when the whole sub-tree is
                # charged on the Consolidated Fund, which is the ordinary case for the
                # High Court and the Governor. Then it is the charged total, not the
                # voted one, and comparing it against the voted sum reports the whole of
                # Administration of Justice as a mismatch.
                figs = [thousands(t) for t in tail]
                level = "sub-scheme" if node is sub else "scheme"
                if charged:
                    node.printed_charged = figs
                else:
                    node.printed_total = figs
                checks.append({"level": level, "voted": not charged,
                               "demand": demand, "hoa": node.hoa, "code": code,
                               "printed": figs,
                               "computed": node.total(charged=charged)})
                last_total, last_total_level = node, level
                if node is sub:
                    sub = None
                else:
                    scheme = sub = None
                target = None
                continue
            if rest.upper().startswith("TOTAL") or rest.upper().startswith("GRAND TOTAL"):
                stats["printed_totals_above_the_scheme"] += 1
                target = last_total = None
                continue

            m = CODE.match(rest)
            if m:
                code, frag = m.group(1), m.group(2)
                if len(code) == 4:
                    # The major head is printed the same way as a scheme and is not one.
                    if code == h.group(1):
                        target = None
                        continue
                    scheme = Node(code, hoa, demand)
                    scheme.parts.append(frag)
                    sub = None
                    schemes.append(scheme)
                    target = scheme
                    stats["scheme_rows"] += 1
                elif len(code) == 5:
                    if scheme is None:
                        stats["sub_scheme_rows_with_no_scheme"] += 1
                        target = None
                        continue
                    sub = Node(code, hoa, demand)
                    sub.parts.append(frag)
                    scheme.children.append(sub)
                    target = sub
                    stats["sub_scheme_rows"] += 1
                else:
                    # Three digits. The minor head is printed like an object head and
                    # carries no figures; the page header names it, so it is known.
                    if code == minor and len(tail) != 4:
                        target = None
                        continue
                    if len(tail) != 4:
                        stats["three_digit_rows_with_no_figures"] += 1
                        target = None
                        continue
                    parent = sub if sub is not None else scheme
                    if parent is None:
                        stats["object_rows_with_no_scheme"] += 1
                        target = None
                        continue
                    obj = Node(code, hoa, demand)
                    obj.parts.append(frag)
                    if charged:
                        obj.charged_figures = [thousands(t) for t in tail]
                        stats["charged_object_rows"] += 1
                    else:
                        obj.figures = [thousands(t) for t in tail]
                    parent.children.append(obj)
                    target = obj
                    stats["object_rows"] += 1
                continue

            if len(tail) == 4:
                stats["figure_rows_with_no_code"] += 1
                target = None
                continue
            # Everything else is a wrapped name.
            if target is not None:
                target.parts.append(rest)
                stats["name_continuation_rows"] += 1
            else:
                stats["text_rows_outside_a_row"] += 1
    return cycle, schemes, checks


def run(date=None, verbose=False):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "odisha", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/odisha/: run collect/odisha.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "odisha", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    stats = collections.Counter()
    merged, per_book, all_checks, wrong_cycle = {}, {}, [], []
    name_conflicts = []

    for book in sorted(man.get("books", {})):
        if not book.startswith("demand-"):
            continue
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        demand = man["books"][book].get("demand")
        dept = man["books"][book].get("department")
        cycle, schemes, checks = parse_book(text, demand, stats)
        if cycle != CYCLE_WANTED:
            # Excluded and named. Merging a book from another year is the failure this
            # check exists to stop; see RECONCILIATION 3 in the module docstring.
            wrong_cycle.append({"book": book, "demand": demand, "department": dept,
                                "cycle_printed_on_its_cover": cycle})
            continue
        per_book[book] = len(schemes)
        all_checks.extend(checks)
        for s in schemes:
            name = s.name
            e = merged.get(s.code)
            if e is None:
                e = merged[s.code] = {
                    "code": s.code, "name": name, "names": {name},
                    "departments": set(), "hoas": set(),
                    "figures": [0.0, 0.0, 0.0, 0.0],
                    "charged": [0.0, 0.0, 0.0, 0.0], "sub_schemes": {}}
            e["names"].add(name)
            e["departments"].add(f"{demand:02d} {dept}" if demand else str(dept))
            e["hoas"].add(s.hoa)
            for i, v in enumerate(s.total()):
                e["figures"][i] = round(e["figures"][i] + v, 3)
            for i, v in enumerate(s.total(charged=True)):
                e["charged"][i] = round(e["charged"][i] + v, 3)
            for c in s.children:
                if len(c.code) == 5:
                    e["sub_schemes"].setdefault(c.code, c.name)

    for code, e in merged.items():
        if len(e["names"]) > 1:
            name_conflicts.append({"code": code, "names": sorted(e["names"])})

    failed = [c for c in all_checks
              if any(abs(a - b) > 0.5 for a, b in zip(c["printed"], c["computed"]))]

    out = []
    for code in sorted(merged):
        e = merged[code]
        # thousands -> lakh, and voted plus charged, which is the whole provision the
        # demand carries for the scheme. The two are published separately as well,
        # because a charged provision is one the legislature does not vote on and a
        # reader may want to leave it out.
        lakh = [round((v + c) / 100.0, 4)
                for v, c in zip(e["figures"], e["charged"])]
        chg = [round(v / 100.0, 4) for v in e["charged"]]
        out.append({
            "code": code,
            "name": e["name"],
            "also_named": sorted(n for n in e["names"] if n != e["name"]) or None,
            "departments": sorted(e["departments"]),
            "hoas": sorted(e["hoas"]),
            "sub_schemes": [{"code": k, "name": v}
                            for k, v in sorted(e["sub_schemes"].items())],
            "actual_2024_25_lakh": lakh[0],
            "be_2025_26_lakh": lakh[1],
            "re_2025_26_lakh": lakh[2],
            "be_lakh": lakh[3],
            "be_charged_lakh": chg[3] or None,
        })

    write_json("data/odisha/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Odisha",
        "cycle": CYCLE_WANTED,
        "source": ("Odisha Budget, the 44 per-department Demand for Grants books "
                   "2026-2027"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH, converted from the THOUSANDS the "
            "demand books print. The unit is read from each page's own "
            "'IN THOUSANDS OF RUPEES' marker and not assumed, and a page naming any "
            "other unit is a hard error. Odisha writes its figures in Indian digit "
            "grouping with every group after the first being two digits, so 1124,49,92 "
            "is 1,12,44,992 thousands, which is Rs 1,124.4992 crore; '..' is nil. "
            "be_lakh is the Budget Estimate 2026-2027, the last of the four money "
            "columns; the Accounts 2024-2025, Budget Estimates 2025-2026 and Revised "
            "Estimates 2025-2026 columns are published beside it. Checked against the "
            "outside world as well as against the books: Subhadra Yojana comes out at "
            "10,14,520 lakh, which is Rs 10,145 crore, the figure Odisha states publicly "
            "for it; Jal Jeevan Mission at Rs 7,000 crore and Madhubabu Pension for "
            "Destitute at Rs 5,837 crore are the same order as the state's own "
            "announcements. Read as lakh without the conversion each would have been 100 "
            "times smaller."),
        "variant": "Budget Estimate 2026-2027",
        "variant_note": (
            "The books read here each print 2026-2027 on their own cover and a book "
            "printing anything else is excluded and named in cycle_excluded below. The "
            "state's own budget portal, budget.odisha.gov.in, lists all 44 demands twice, "
            "the second listing being last year's VOLUME - II, and links the 2025-2026 "
            "book for Demand 34 while the 2026-2027 one sits on the server unlinked. "
            "The collector reads the Finance Department's publication page instead, "
            "which has neither fault."),
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "demand_books_read": len(per_book),
            "with_a_positive_be": sum(1 for r in out if r["be_lakh"] > 0),
            "funded_at_nil": sum(1 for r in out if r["be_lakh"] == 0),
            "funded_in_more_than_one_department": sum(
                1 for r in out if len(r["departments"]) > 1),
            "with_a_charged_provision": sum(
                1 for r in out if r["be_charged_lakh"]),
            "sub_schemes": sum(len(r["sub_schemes"]) for r in out),
            "schemes_per_book": per_book,
        },
        "extraction_stats": dict(stats),
        "name_conflicts": sorted(name_conflicts, key=lambda c: c["code"])[:40] or None,
        "name_conflicts_total": len(name_conflicts),
        "cycle_excluded": wrong_cycle or None,
        "reconciliation": {
            "printed_totals": {
                "checked": len(all_checks), "failed": len(failed),
                "failures": failed[:20] or None,
                "what": ("every TOTAL the books print for a scheme or a sub-scheme, "
                         "against the sum of the rows read beneath it, in all four "
                         "money columns")},
        },
        # The join against myScheme, run once by hand on the 2026-09-02 snapshot and read
        # line by line, all 37 of them. Recorded here rather than recomputed on every run
        # because the classification is a human reading, not a rule. parse/match.py is
        # NOT edited to fix any of these; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_odisha_records": 83,
            "joins_produced": 37,
            "joins_sound_on_inspection": 15,
            "joins_wrong_on_inspection": 22,
            "myscheme_records_with_any_join": 27,
            "myscheme_records_with_a_sound_join": 15,
            "scheme_codes_with_a_sound_join": 12,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read "
                    "by eye"),
            "read_this_carefully": (
                "15 of myScheme's 83 Odisha records were found in a book that names "
                "1,628 schemes, and that is not evidence the other 68 are invented. "
                "Several of the 68 are components of a scheme the books do carry "
                "(myScheme lists MMKY twice, once per benefit) and several are welfare "
                "board benefits paid from a board's own fund rather than from a demand. "
                "In the other direction this register is a superset: rows like "
                "'Construction of Buildings' and 'Financial Assistance' are heads of "
                "expenditure and not schemes a citizen can apply to."),
        },
        "myscheme_join_defects": [
            {"defect": ("the STATE'S OWN NAME read as an acronym. Odisha prints "
                        "'SWACHHA ODISHA' in capitals, so acronyms() returns 'odisha' "
                        "for it, and every myScheme record with the word Odisha in its "
                        "title matches. NOT_ACRONYMS blocks india, indian and bharat and "
                        "no state name"),
             "reason_string": "acronym match: odisha",
             "joins": 6,
             "example_myscheme": ("Pension to Indigent Sportspersons of Odisha"),
             "example_budget": "SWACHHA ODISHA",
             "note": ("all 6 wrong joins are to the same register row. The fix is one "
                      "line in NOT_ACRONYMS and the hole will recur for every state that "
                      "shouts a scheme name containing its own name.")},
            {"defect": ("a coined Sanskrit word that is a programme brand on one side "
                        "and an ordinary word on the other. SAMARTHYA is bracketed and "
                        "capitalised in the budget, so it is a written acronym; it is an "
                        "ordinary token in the myScheme name"),
             "reason_string": "acronym match: samarthya",
             "joins": 4,
             "example_myscheme": "Bhima Bhoi Bhinnakshyama Samarthya Abhiyan",
             "example_budget": "Shakti Sadan (SAMARTHYA)",
             "note": ("an Odisha disability scheme matched to all four SAMARTHYA "
                      "sub-schemes of the central Mission Shakti. match.py already "
                      "records SAMARTHYA as exactly the kind of coined word a dictionary "
                      "would wrongly throw away, and this is the cost of keeping it.")},
            {"defect": ("a DERIVED initialism equal to an unrelated WRITTEN acronym. "
                        "'Semi-Commercial Duck Farming' derives scdf; the budget writes "
                        "SCDF for the SIDBI Cluster Development Fund. The containment "
                        "guard asks only that ONE side wrote its acronym, and the budget "
                        "did"),
             "reason_string": "acronym containment: scdf / scdf",
             "joins": 2,
             "example_myscheme": "Semi-Commercial Duck Farming",
             "example_budget": "SIDBI Cluster Developement Fund (SCDF)",
             "note": ("the second instance of this hole; the first was pocs / pocs on "
                      "the Tamil Nadu demand books.")},
            {"defect": ("a scheme BRAND shared by three separate budget lines, where "
                        "myScheme lists only the parent. Subhadra Yojana is the cash "
                        "transfer; Subhadra Surakhya Yojana is a Home Department scheme "
                        "and Subhadra Sambedna a separate Women and Child line"),
             "reason_string": "acronym match: subhadra",
             "joins": 2,
             "example_myscheme": "SUBHADRA",
             "example_budget": "Subhadra Surakhya Yojana",
             "note": ("the join to Subhadra Yojana itself is sound and is counted as "
                      "such; these are the two extra rows it dragged in.")},
            {"defect": ("containment on a generic domain phrase, the hole already "
                        "recorded against the Tamil Nadu demand books. Two Biju Patnaik "
                        "sports AWARDS matched the Sports Department's 'Promotion of "
                        "Sports and Games' head, which is where the department's own "
                        "promotion spending sits"),
             "reason_string": "all 3 content words of the shorter name are present",
             "joins": 2,
             "example_myscheme": ("Biju Patnaik Sports Award for Lifetime Achievement in "
                                  "Promotion of Sports & Games"),
             "example_budget": "Promotion of Sports and Games"},
            {"defect": ("the consonant skeleton firing on two generic words. Building "
                        "and construction, financial and assistance, state and fund, "
                        "safety and equipment: each pair is enough to satisfy the "
                        "two-skeleton rule and none of them names a scheme"),
             "reason_string": "transliteration variant: ['bldng', 'cnstrctn']",
             "joins": 5,
             "example_myscheme": "Building And Other Construction Scholarship",
             "example_budget": "Construction of building for Jails",
             "note": ("five joins across four reason strings: ['bldng','cnstrctn'] twice, "
                      "['fnncl','ssstnc'], ['fnd','stt'] joining the Odisha State "
                      "Treatment Fund to the State Road Fund, and ['qpmnt','sfty'] "
                      "joining a building workers' safety-equipment benefit to a "
                      "Rs 10 lakh fire safety head.")},
            {"defect": "containment on two words that are a generic domain phrase",
             "reason_string": "all 2 content words of the shorter name are present",
             "joins": 1,
             "example_myscheme": "Building And Other Construction Scholarship",
             "example_budget": "Construction of Buildings"},
        ],
        "caveat": (
            "One row here is one 4-digit SCHEME code as Odisha's demand books number "
            "them, which is the same code the state's Gender Budget prints beside each "
            "scheme name. The same code recurs under several demands when several "
            "departments fund the same scheme; those provisions are ADDED and every "
            "department is named. This list is a superset of Odisha's citizen-facing "
            "schemes and not a count of them: the books file establishment and "
            "generic heads at the same level, so rows like 'Information, Education and "
            "Communication' and 'Other Charges' sit alongside 'Mukhya Mantri Kalakara "
            "Sahayata Yojana', and a reader counting schemes should discount them. The "
            "5-digit sub-schemes beneath each code are published as sub_schemes and are "
            "not counted as schemes."),
        "entries": out,
    })
    return out, per_book, all_checks, failed, wrong_cycle, stats, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Odisha Demand for Grants books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, checks, failed, wrong_cycle, stats, date = run(a.date)
    print(f"odisha snapshot {date}")
    print(f"  {len(per_book)} demand books read, {len(out)} distinct scheme codes")
    print(f"     with a positive 2026-27 provision "
          f"{sum(1 for r in out if r['be_lakh'] > 0):>6}")
    print(f"     sum of 2026-27 provisions "
          f"{sum(r['be_lakh'] for r in out):>18,.2f} lakh")
    print(f"  printed totals  {len(checks) - len(failed):>6} of {len(checks):<6} "
          f"reconcile")
    for w in wrong_cycle:
        print(f"     EXCLUDED {w['book']} ({w['department']}): its cover says "
              f"{w['cycle_printed_on_its_cover']}")
    for k, v in sorted(stats.items()):
        print(f"     {k:<38}{v:>8}")
    if failed:
        for f in failed[:10]:
            print("     MISMATCH", json.dumps(f)[:220])
        print(f"  ERROR: {len(failed)} printed totals do not match the rows read")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
