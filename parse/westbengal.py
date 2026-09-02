"""
Parse the archived West Bengal Detailed Demands for Grants into
data/westbengal/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY WEST BENGAL YIELDS. These books are English throughout. The only Bengali in them is
the cover, set in a legacy font that garbles into Latin punctuation ("þîyöì‹Ýþ ²Ì„þyŸ˜ ˜‚
26"), and no cover carries a scheme name. So the name field needs no separator at all:
there is nothing else in the column.

WHAT ONE ROW IS. West Bengal's scheme-level unit is the SUB-HEAD, keyed on its full head
of account, exactly as Tamil Nadu's is:

    DETAILED ACCOUNT NO. 2235-02-001 - DIRECTION AND ADMINISTRATION   the minor head
    02 - SOCIAL WELFARE                                               the sub-major head
    001- Direction and Administration                                 the minor head again
          Administrative Expenditure                                  a section label
    001- Directorate of Women Development and Social Welfare [WC]     THE SUB-HEAD
     01- Salaries                                                     an object head
          01-Pay                        2,73,98,625  2,94,16,000 ...  a detail head
                        Total - 2235-02-001-001-01   3,52,75,639 ...  printed detail total
                        Total - 2235-02-001-001      ...              PRINTED SUB-HEAD TOTAL

Note the trap in that fragment: the minor head and the sub-head are BOTH printed as
"001-" and only the name tells them apart. The DETAILED ACCOUNT NO. line names the minor
head, so a 3-digit line repeating that code AND that name is the minor head restated and
is not a scheme. Without that rule the register gains a phantom scheme called Direction
and Administration under every department that has one.

RECONCILIATION, two checks, both hard errors:

  1. Every printed "Total - <major>-<sub>-<minor>-<subhead>" against the sum of the
     figure rows read beneath that sub-head, in all four money columns. These are the
     state's own arithmetic about its own rows.
  2. Every printed "Total - <major>-<sub>-<minor>" against the sum of the sub-head totals
     under it, again in all four columns.

UNITS. These books print RUPEES, not thousands and not lakh: the column header is a bare
"Rs." and the figures run to eleven digits (50427,79,53,000 for the Women and Child
Development demand's gross revenue expenditure). They are converted to LAKH here so the
number is comparable with the other states in this register, and the conversion is stated
in the output. Nil is "..." and a negative figure is real, because "Deduct - Recoveries"
is a head in its own right.
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

# One money cell. Indian digit grouping with an UNBOUNDED first group: the largest figure
# in these books is 50427,79,53,000, whose first group is five digits. "..." is nil.
MONEY = re.compile(r"^(?:\.\.\.|-?\d+(?:,\d{2,3})*)$")
DETAIL_ACCOUNT = re.compile(
    r"DETAILED ACCOUNT NO\.\s*(\d{4})-(\d{2})-(\d{3})\s*-\s*(.+?)\s*$")
CODE3 = re.compile(r"^\s{0,2}(\d{3})-\s*(\S.*)$")
TOTAL = re.compile(r"^\s*Total\s*-\s*(\S.*?)\s*$")
HOA_SUB = re.compile(r"^(\d{4})-(\d{2})-(\d{3})-(\d{3})$")
HOA_MINOR = re.compile(r"^(\d{4})-(\d{2})-(\d{3})$")
# A total over the detail heads of ONE object head, "Total - 2235-02-001-001-01" being
# the total of the Pay, Dearness Allowance and House Rent rows under object head 01,
# Salaries. It is printed in the middle of a sub-head, not at the end of one. Read as an
# unrecognised section total it closes the sub-head early and every object head after it
# is dropped: measured on the first run of this parser, 13,386 figure rows fell outside
# any sub-head and 870 of 5,521 printed sub-head totals came out short.
HOA_OBJECT = re.compile(r"^(\d{4})-(\d{2})-(\d{3})-(\d{3})-(\d{2})$")
DEMAND = re.compile(r"^\s*DEMAND No\.\s*(\d{1,3})\s*$", re.I | re.M)
YEARS = re.compile(r"DETAILED\s+DEMANDS FOR GRANTS FOR\s+(\d{4}-\d{4})", re.I)
GLUED_LABEL = re.compile(r"\b(Voted|Charged)(?=[\d\.])")


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


def rupees(tok):
    if tok == "...":
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


# Lines that sit in the name column, are indented exactly as a wrapped name is, and are
# not part of any name: the page footer and the section label that groups the sub-heads
# beneath it. Section labels are not guessed. They are read from the book's own
# "Total - <label>" lines in a first pass, because every section the book opens it also
# closes with a total, so the book states its own vocabulary. Without this the register
# publishes schemes called "Management of Government Estates Administrative Expenditure"
# and "Other pensions [FD] ______________________".
FOOTER = re.compile(r"^(_+|[\d ]+|June, \d{4}|Budget Publication No\.\s*\d+|\.)$")


def section_labels(text):
    out = set()
    for m in re.finditer(r"^\s*Total\s*-\s*(\S.*?)\s{2,}", text, re.M):
        label = m.group(1).strip()
        if not (HOA_SUB.match(label) or HOA_MINOR.match(label)
                or HOA_OBJECT.match(label)):
            out.add(label)
    return out


def parse_book(text, stats):
    """Read one Detailed Demands volume.

    Returns (cycle, rows, sub_checks, minor_checks) where a row is one sub-head:
    its head of account, its name, the demand it sits under and four figures.
    """
    sections = section_labels(text)
    pages = text.split("\f")
    y = YEARS.search(pages[0]) if pages else None
    cycle = y.group(1) if y else None

    rows, sub_checks, minor_checks = [], [], []
    demand = None
    minor = None                # (major, submajor, minor, name)
    subheads = {}               # code -> [name parts], candidates in this minor head
    current = None              # the sub-head whose object rows are being summed
    name_target = None
    sums = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    printed_sub = {}
    order = []
    after_total = False         # see the Voted/Charged note below

    def flush_minor():
        """Emit every sub-head of the minor head just finished.

        A sub-head whose object heads run over a page break is PRINTED AGAIN at the top
        of the next page, so its name is captured more than once. The longest capture
        wins: a restatement can be cut short by the page break it sits on, and appending
        the captures instead produced names like "Old Age Pension Scheme under Jai Bangla
        (JAIBANGLA) [WC] [WC]" and a Gatidhara row carrying its own tail three times.
        """
        for hoa in order:
            caps = subheads.get(hoa.split("-")[3], [])
            name = max((joined(c) for c in caps), key=len, default="")
            rows.append({"hoa": hoa, "demand": demand,
                         "major": hoa.split("-")[0],
                         "name": name,
                         "figures": printed_sub.get(hoa) or list(sums[hoa])})
        order.clear()
        subheads.clear()
        printed_sub.clear()
        sums.clear()

    for page in pages:
        if "DETAILED ACCOUNT" not in page:
            d = DEMAND.search(page)
            if d:
                demand = int(d.group(1))
            stats["pages_not_detail"] += 1
            continue
        stats["detail_pages"] += 1
        for raw in page.split("\n"):
            s = raw.rstrip()
            if not s.strip():
                continue
            if set(s.strip()) <= {"-", " "}:
                continue

            d = DEMAND.search(s)
            if d:
                demand = int(d.group(1))
                continue
            m = DETAIL_ACCOUNT.search(s)
            if m:
                flush_minor()
                minor = (m.group(1), m.group(2), m.group(3), m.group(4).strip())
                current = name_target = None
                stats["minor_head_headers"] += 1
                continue

            # The Voted/Charged label collides with the first figure often enough to
            # matter: "Voted7,79,88,889" on the Kangsabati Reservoir capital head. The
            # row then has three money tokens rather than four, is not read at all, and
            # its sub-head total comes out at a fiftieth of the printed one. Three of the
            # 5,521 printed sub-head totals failed on exactly this before the split.
            s = GLUED_LABEL.sub(r"\1 ", s)
            toks = s.split()
            tail = []
            while toks and MONEY.match(toks[-1]):
                tail.insert(0, toks.pop())
            if len(tail) > 4:
                toks.extend(tail[:-4])
                tail = tail[-4:]
            rest = " ".join(toks)

            # A bare "Voted" or "Charged" line carrying four figures is TWO different
            # things depending on where it stands, and reading both the same way is what
            # made eight sub-head totals come out half as large again as the state's own.
            # Immediately after a Total line it is that total SPLIT into its voted and
            # charged halves, and adding it double counts. Anywhere else it is the
            # charged half of the coded row above it, which must be added.
            if rest in ("Voted", "Charged") and len(tail) == 4:
                if after_total:
                    stats["voted_charged_breakdown_of_a_total"] += 1
                    name_target = None
                    continue
                if current is not None:
                    for i, v in enumerate(rupees(x) for x in tail):
                        sums[current][i] = round(sums[current][i] + v, 2)
                    stats["voted_charged_half_rows"] += 1
                else:
                    stats["figure_rows_outside_a_sub_head"] += 1
                name_target = None
                continue

            t = TOTAL.match(rest)
            if t and len(tail) == 4:
                label = t.group(1).strip()
                figs = [rupees(x) for x in tail]
                hm = HOA_SUB.match(label)
                if hm:
                    hoa = label
                    printed_sub[hoa] = figs
                    sub_checks.append({"hoa": hoa, "demand": demand,
                                       "printed": figs,
                                       "computed": list(sums[hoa])})
                    current = name_target = None
                    after_total = True
                    continue
                if HOA_OBJECT.match(label):
                    # Already counted, row by row, and the sub-head continues.
                    stats["object_head_totals"] += 1
                    name_target = None
                    after_total = True
                    continue
                mm = HOA_MINOR.match(label)
                if mm:
                    got = [0.0, 0.0, 0.0, 0.0]
                    for hoa in order:
                        vals = printed_sub.get(hoa) or sums[hoa]
                        for i, v in enumerate(vals):
                            got[i] = round(got[i] + v, 2)
                    minor_checks.append({"hoa": label, "demand": demand,
                                         "printed": figs, "computed": got})
                    current = name_target = None
                    after_total = True
                    continue
                # Total - State Development Schemes, - Administrative Expenditure,
                # - 999 - Deduct - Recoveries, - Voted, - Charged. Section totals over
                # rows already counted; recorded and not used.
                stats["section_totals"] += 1
                current = name_target = None
                after_total = True
                continue
            if t:
                stats["total_lines_without_four_figures"] += 1
                current = name_target = None
                continue

            after_total = False
            c = CODE3.match(s)
            if c and minor is not None:
                code, frag = c.group(1), c.group(2)
                # The minor head restated. See the trap in the module docstring.
                if code == minor[2] and frag.strip().lower() == minor[3].lower():
                    stats["minor_head_restated"] += 1
                    current = name_target = None
                    continue
                hoa = f"{minor[0]}-{minor[1]}-{minor[2]}-{code}"
                if hoa not in order:
                    order.append(hoa)
                    subheads[code] = [[frag]]
                else:
                    # The same sub-head restated after a page break, which happens when
                    # its object heads run over. Each restatement is captured separately
                    # and the longest wins; see flush_minor.
                    subheads.setdefault(code, []).append([frag])
                    stats["sub_head_restated"] += 1
                current = hoa
                name_target = code
                if len(tail) == 4:
                    for i, v in enumerate(rupees(x) for x in tail):
                        sums[hoa][i] = round(sums[hoa][i] + v, 2)
                stats["sub_head_rows"] += 1
                continue

            if len(tail) == 4:
                if current is not None:
                    for i, v in enumerate(rupees(x) for x in tail):
                        sums[current][i] = round(sums[current][i] + v, 2)
                    stats["object_rows"] += 1
                else:
                    stats["figure_rows_outside_a_sub_head"] += 1
                name_target = None
                continue

            # A wrapped sub-head name. Object head names wrap too, so only lines while a
            # sub-head is the live name target are taken.
            body = s.strip()
            if name_target is not None and not re.match(r"^\s*\d{1,2}-", s) \
                    and not FOOTER.match(body) \
                    and not any(body.startswith(x) for x in sections):
                subheads[name_target][-1].append(body)
                stats["name_continuation_rows"] += 1
            else:
                stats["text_rows"] += 1
                name_target = None
    flush_minor()
    return cycle, rows, sub_checks, minor_checks


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "westbengal", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/westbengal/: "
                         "run collect/westbengal.py first")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "westbengal", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    stats = collections.Counter()
    merged, per_book, sub_checks, minor_checks, wrong_cycle = {}, {}, [], [], []
    want = man.get("cycle")

    for book in sorted(man.get("books", {})):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        cycle, rows, sc, mc = parse_book(text, stats)
        if want and cycle and cycle != want:
            wrong_cycle.append({"book": book, "cycle_printed_on_its_cover": cycle})
            continue
        per_book[book] = len(rows)
        sub_checks.extend(sc)
        minor_checks.extend(mc)
        for r in rows:
            e = merged.get(r["hoa"])
            if e is None:
                e = merged[r["hoa"]] = {"hoa": r["hoa"], "name": r["name"],
                                        "demands": set(), "books": set(),
                                        "figures": [0.0, 0.0, 0.0, 0.0]}
            elif not e["name"] and r["name"]:
                e["name"] = r["name"]
            if r["demand"]:
                e["demands"].add(r["demand"])
            e["books"].add(book)
            for i, v in enumerate(r["figures"]):
                e["figures"][i] = round(e["figures"][i] + v, 2)

    sub_failed = [c for c in sub_checks
                  if any(abs(a - b) > 1.0 for a, b in zip(c["printed"], c["computed"]))]
    minor_failed = [c for c in minor_checks
                    if any(abs(a - b) > 1.0 for a, b in zip(c["printed"], c["computed"]))]

    out = []
    for hoa in sorted(merged):
        e = merged[hoa]
        lakh = [round(v / 100000.0, 4) for v in e["figures"]]
        out.append({
            "hoa": hoa,
            "name": e["name"],
            "major_head": hoa.split("-")[0],
            "sub_head": hoa.split("-")[3],
            "demands": sorted(e["demands"]),
            "books": sorted(e["books"]),
            "actual_2024_25_lakh": lakh[0],
            "be_2025_26_lakh": lakh[1],
            "re_2025_26_lakh": lakh[2],
            "be_lakh": lakh[3],
        })

    write_json("data/westbengal/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "West Bengal",
        "cycle": want,
        "source": ("West Bengal Budget, Budget Publications 11 to 26, the Detailed "
                   "Demands for Grants for 2026-2027"),
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "unit": "lakh",
        "unit_note": (
            "Every figure here is rupees in LAKH, converted from the RUPEES the books "
            "print. These volumes do not use thousands or lakh: the column header is a "
            "bare 'Rs.' and the figures run to eleven digits, 50427,79,53,000 being the "
            "gross revenue expenditure of the Women and Child Development demand, which "
            "is Rs 50,427.7953 crore. Nil is printed '...' and a negative figure is "
            "real, because Deduct - Recoveries is a head in its own right. be_lakh is "
            "the Budget Estimate 2026-2027, the last of the four money columns; the "
            "Actuals 2024-2025, Budget Estimate 2025-2026 and Revised Estimate "
            "2025-2026 are published beside it. Checked against the outside world as "
            "well as against the books: Kanyashree Prakalpa comes out at Rs 1,609 crore "
            "across its 11 heads, Rupashree at Rs 1,006 crore, Swasthya Sathi at "
            "Rs 1,200 crore and Lakshmir Bhandar at Rs 20,400 crore, all of them the "
            "order the state announces. Read without the conversion each would have been "
            "a hundred thousand times larger."),
        "variant": "Budget Estimate 2026-2027",
        "variant_note": (
            "One budget for 2026-2027, presented in June 2026. Earlier years are behind "
            "the page's __doPostBack year selector and are not collected. Each volume's "
            "own cover states the cycle and a volume printing anything else is excluded "
            "and named."),
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "volumes_read": len(per_book),
            "with_a_positive_be": sum(1 for r in out if r["be_lakh"] > 0),
            "funded_at_nil": sum(1 for r in out if r["be_lakh"] == 0),
            "negative_recovery_heads": sum(1 for r in out if r["be_lakh"] < 0),
            "deduct_recoveries_heads": sum(
                1 for r in out if r["name"].lower().startswith("deduct")),
            "rows_per_volume": per_book,
            "names_the_state_letter_spaced": sum(
                1 for r in out if re.search(r"\b\w \w \w \w\b", r["name"])),
        },
        "extraction_stats": dict(stats),
        "cycle_excluded": wrong_cycle or None,
        "reconciliation": {
            "sub_head_totals": {
                "checked": len(sub_checks), "failed": len(sub_failed),
                "failures": sub_failed[:20] or None,
                "what": ("every printed Total for a sub-head against the sum of the "
                         "figure rows read beneath it, in all four money columns")},
            "minor_head_totals": {
                "checked": len(minor_checks), "failed": len(minor_failed),
                "failures": minor_failed[:20] or None,
                "what": ("every printed Total for a minor head against the sum of the "
                         "sub-head totals under it, in all four money columns")},
        },
        # The join against myScheme, run once by hand on the 2026-09-02 snapshot and
        # read line by line, all 126 of them. Recorded here rather than recomputed on
        # every run because the classification is a human reading, not a rule.
        # parse/match.py is NOT edited to fix any of these.
        "myscheme_join_summary": {
            "myscheme_west_bengal_records": 109,
            "joins_produced": 126,
            "joins_sound_on_inspection": 75,
            "joins_wrong_on_inspection": 51,
            "myscheme_records_with_any_join": 31,
            "myscheme_records_with_a_sound_join": 21,
            "heads_of_account_with_a_sound_join": 66,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read "
                    "by eye"),
            "uncertain": (
                "myScheme's 'Old Age Pension' record fanned out to 44 register rows and "
                "the split between right and wrong there is a JUDGEMENT, not a fact. "
                "The record is filed under the Women and Child Development and Social "
                "Welfare Department, so the 16 rows named 'Old Age Pension Scheme under "
                "Jai Bangla' tagged [WC] or [PN] are counted sound and the other 28 "
                "wrong: those are the central IGNOAPS and NOAPS shares, the Jai Johar "
                "Scheduled Tribe pension, and five separate occupational pensions for "
                "marginal farmers, fishermen, artisans, weavers and silk weavers. A "
                "reader who takes Jai Bangla to be one umbrella scheme rather than "
                "several would count differently, and the underlying question, whether "
                "West Bengal runs one old age pension or nine, is not settled by "
                "anything in these books."),
        },
        "myscheme_join_defects": [
            {"defect": ("containment on a generic domain phrase, at the largest scale "
                        "this register has seen it. 'Old Age Pension' is three content "
                        "words and every one of the 44 rows in these books whose name "
                        "contains them satisfies the rule"),
             "reason_string": "all 3 content words of the shorter name are present",
             "joins": 28,
             "example_myscheme": "Old Age Pension",
             "example_budget": ("Grant of Old-age Pension to Old and Infirm Fishermen "
                                "[FI]"),
             "note": ("the same hole already recorded against the Tamil Nadu demand "
                      "books, where a short generic phrase was swallowed by a long "
                      "specific name. Here the phrase is long enough to clear the "
                      "three-content-word floor, so the comparability guard never "
                      "fires.")},
            {"defect": ("a TAX abbreviation read as a scheme acronym. SGST is the State "
                        "Goods and Services Tax; the budget writes it in capitals for "
                        "two power-utility grant heads and myScheme writes it in the "
                        "title of two industrial subsidy schemes"),
             "reason_string": "acronym containment: sgst / sgst",
             "joins": 4,
             "example_myscheme": ("Banglashree for Micro, Small and Medium Enterprises: "
                                  "Subsidy for State Goods and Services Tax (SGST)"),
             "example_budget": "Grants to WBSEDCL on account of SGST [PO]"},
            {"defect": ("two DIFFERENT acronyms matched because one contains the other "
                        "and the shorter covers four of the longer's five letters, which "
                        "clears the 0.5 coverage floor. SDRFS is West Bengal's Stamp "
                        "Duty and Registration Fee Subsidy; SDRF is the State Disaster "
                        "Response Fund"),
             "reason_string": "acronym containment: sdrfs / sdrf",
             "joins": 5,
             "example_myscheme": ("Banglashree for Micro, Small and Medium Enterprises: "
                                  "Subsidy on Stamp Duty and Registration Fee (SDRFS)"),
             "example_budget": "State Disaster Response Fund (SDRF) [DM]",
             "note": ("the coverage floor exists to stop SMAM matching SMAMOFGIFCOI. It "
                      "cannot stop a four-letter acronym matching the five-letter one it "
                      "is a prefix of, and adding an S to an acronym is how a subsidy "
                      "scheme is named.")},
            {"defect": ("an acronym matched against a derived initialism of a name that "
                        "happens to contain the same letters. PWCS is a Primary Weavers "
                        "Co-operative Society; ttmpwcsc is derived from 'Tantuja/Tantusree"
                        "/Manjusha to the Primary Weavers Co-operative Societies'"),
             "reason_string": "acronym containment: pwcs / ttmpwcsc",
             "joins": 6,
             "example_myscheme": ("West Bengal Handloom and Khadi Weavers Financial "
                                  "Benefit Scheme 2024: Support for One Time Settlement "
                                  "(OTS) of NPA Accounts of PWCS"),
             "example_budget": ("Expenditure for payment of outstanding dues of "
                                "Tantuja/Tantusree/Manjusha to the Primary Weavers "
                                "Co-operative Societies")},
            {"defect": ("the STATE'S OWN NAME as the only shared skeleton. 'West Bengal' "
                        "reduces to wst and bngl, which is two skeletons, which is "
                        "enough for the transliteration rule when the shorter name has "
                        "little else"),
             "reason_string": "transliteration variant: ['bngl', 'wst']",
             "joins": 3,
             "example_myscheme": "Widow Pension-West Bengal",
             "example_budget": "8.00% West Bengal Loan (New Loan) [FD]",
             "note": ("three myScheme records, Pratyasha, the Freeship Scheme and the "
                      "Widow Pension, all joined to the same government bond. match.py "
                      "already blocks the bare prefix 'West Bengal' on the prefix rule "
                      "after 49 joins from two subjects; the skeleton rule has no such "
                      "guard.")},
            {"defect": ("containment on eight words that are all generic once the "
                        "specific ones are stripped. A grant to INDIVIDUAL ARTISANS "
                        "matched a grant to an individual CO-OPERATIVE SOCIETY for "
                        "tools, equipment and a work shed"),
             "reason_string": "all 8 content words of the shorter name are present",
             "joins": 3,
             "example_myscheme": ("West Bengal Artisans Financial Benefit Scheme 2024: "
                                  "Grant to Individual Artisans"),
             "example_budget": ("One Time Grant for individual Co-operative Society for "
                                "tool, equipment, work shed and marketing support")},
            {"defect": ("an acronym matched to a project of the same name in a different "
                        "place. CETP is a Common Effluent Treatment Plant, a category of "
                        "works; the budget rows are the one at the Calcutta Leather "
                        "Complex"),
             "reason_string": "acronym containment: cetp / cetp",
             "joins": 2,
             "example_myscheme": ("West Bengal Incentive Scheme for Approved Industrial "
                                  "Park (SAIP) for MSMEs: Incentive for Common Effluent "
                                  "Treatment Plant (CETP)"),
             "example_budget": ("Setting up of CETP & its Network at Calcutta Leather "
                                "Complex [CS]")},
        ],
        "caveat": (
            "One row here is one SUB-HEAD of a demand for grant, keyed on its full head "
            "of account, which is West Bengal's own scheme-level unit. The object heads "
            "beneath it (Salaries, Wages, Other Charges) are deliberately not published, "
            "because they are what a scheme spends money on and not schemes. The state "
            "also files establishment and recovery provisions at sub-head level, so this "
            "list is a superset of West Bengal's schemes and not a count of them, and a "
            "reader counting schemes should discount the Deduct - Recoveries heads and "
            "the directorate and secretariat rows. A scheme with a revenue head and a "
            "capital head appears twice, because the state votes them separately. The "
            "tags the books append to a name, [WC], [PS], (State Share), (OCASPS), "
            "(60:40), are the state's own and are kept. One artefact is left as printed "
            "and not repaired: 66 names are LETTER-SPACED in the source, so "
            "'Expenditure for payment' is typeset as 'E x p e n d i t u r e f o r p a y "
            "m e n t' and pdftotext reproduces it faithfully. The word boundaries are "
            "lost in the PDF itself, single spaces separating letters and words alike, "
            "so closing the gaps would give one run-on word and guessing where the words "
            "end would be inventing a name. They are published as the state printed "
            "them, and counted in names_the_state_letter_spaced. A scheme with a "
            "general, a Scheduled Caste (789) and a Tribal (796) head appears three "
            "times, because the state votes them separately."),
        "entries": out,
    })
    return out, per_book, sub_checks, sub_failed, minor_checks, minor_failed, stats, date


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived West Bengal Detailed Demands for Grants.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, sc, sf, mc, mf, stats, date = run(a.date)
    print(f"westbengal snapshot {date}")
    print(f"  {len(per_book)} volumes read, {len(out)} sub-heads")
    print(f"     with a positive 2026-27 provision "
          f"{sum(1 for r in out if r['be_lakh'] > 0):>6}")
    print(f"     sum of 2026-27 provisions "
          f"{sum(r['be_lakh'] for r in out):>18,.2f} lakh")
    print(f"  sub-head totals   {len(sc) - len(sf):>6} of {len(sc):<6} reconcile")
    print(f"  minor head totals {len(mc) - len(mf):>6} of {len(mc):<6} reconcile")
    for k, v in sorted(stats.items()):
        print(f"     {k:<38}{v:>8}")
    if sf or mf:
        for f in (sf + mf)[:10]:
            print("     MISMATCH", json.dumps(f)[:200])
        print(f"  ERROR: {len(sf)} sub-head and {len(mf)} minor head totals do not match")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
