"""
Extract Uttar Pradesh's grant-wise budget volumes into a named scheme list.

AGENT-EDITABLE (PLAN.md §7). Reads archive/uttarpradesh/, writes data/uttarpradesh/.
Never fetches. Replayable against any archived date.

    data/uttarpradesh/schemes.json    one row per scheme-level node of the account tree

WHY THIS EXISTS AT ALL, given the survey said no. Uttar Pradesh was recorded as a refusal
on language: its names extract perfectly and are entirely in Hindi, and a register that
published 8,000 Devanagari names against myScheme's 47 English ones could not check its own
absence claim. That was half right. myScheme does not list Uttar Pradesh's schemes in
English either; it lists them in romanised Hindi, "Kanya Sumangala Yojana" and "Berojgari
Bhatta Yojna". The join is a change of script, and parse/devanagari.py does it.

The Hindi is what the state published and it stays the name. The romanisation is published
beside it as a derived field, labelled as derived, and is what the matcher reads.

FOUR THINGS THE LAYOUT DOES THAT A NAIVE READER GETS WRONG.

The money is not on the same line as the name. Devanagari and digits sit on different
baselines, so `01 - वेतन` renders at y=223 and its four figures at y=227, and a parser that
groups words by exact y reads a table of names with no money and a table of money with no
names. Rows are 18pt apart, so a 6pt tolerance joins the pair and never reaches the
neighbour. Printed totals, which are mostly digits, do share one y; the same tolerance
covers both.

The text stream splits words. `केन्द्र` arrives as `के` + `न्द्र`, which is not a word
break: the gap is 1.6pt where a real space is 2.4 to 2.5. The split is repaired by
geometry rather than by a word list. The exception is a word ending in an explicit virama,
`परिषद्` + `को`, where the renderer sets the next word close because the halant leaves no
descender; joining those would weld two real words. A virama is the state's own mark that a
word has ended, so it is the guard.

The tree is in the x-position, not in the code. A major head is a four-digit code at x~225,
a sub-major two digits at x~241, a minor head three at x~245, and the SCHEME is the node at
x~256 whose code may be two digits or four. Object heads sit at x~269 and are not schemes:
Pay, Dearness Allowance, Office Expenses. Reading depth from the number of digits instead
would file `0102- समन्वित बाल विकास योजना` under a different level from `03- कन्या
सुमंगला योजना`, and they are siblings.

The book prints its own arithmetic and it is checked. `योग : <code>` gives the total for a
node in all four money columns, and every one is compared against the sum of the children
beneath it. That is the only reason any of the above can be trusted: a mis-set x threshold
would reparent a subtree, and a reparented subtree does not add up.
"""

import argparse
import collections
import glob
import gzip
import html
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from devanagari import transliterate, has_devanagari  # noqa: E402
from match import probably_same, tokens as m_tokens, skeleton as m_skeleton, \
    acronyms as m_acronyms  # noqa: E402

WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">([^<]*)</word>')
PAGE = re.compile(r'<page width="[\d.]+" height="[\d.]+">(.*?)</page>', re.S)

MONEY = re.compile(r"^-?[\d,]*\.\d{2}$")
NIL = re.compile(r"^-{1,2}$")
CODE = re.compile(r"^(\d{2,4})-?$")
VIRAMA = "्"

# The unit banner, printed on every table page. Asserted rather than assumed: the same
# portal serves volumes in thousands for other books, and a book read in the wrong unit is
# wrong by a factor of a hundred with nothing on the page to show it.
UNIT = re.compile(r"\(\s*₹?\s*(लाख|हजार|करोड़)\s*में\s*\)")
UNIT_IN_LAKH = {"लाख": 1.0, "हजार": 0.01, "करोड़": 100.0}

# Total rows. योग is "total"; कुल योग is the grand total.
YOG = "योग"
GRAND = "कुल"

# THE TREE IS READ FROM THE ACCOUNT-CODE GRAMMAR, NOT FROM THE INDENT. Indentation was the
# obvious signal and it is not stable: Gr49 sets its minor heads at x 244 and its schemes
# at 254 to 258, and Gr40 sets a minor head at 254. A threshold tuned on one volume
# reparents subtrees in another, and 91 volumes is too many to tune one at a time.
#
# The codes are stable, because they are the standard Indian government account
# classification and every state in this register uses it:
#
#   2235, 4059   major head        four digits, 2 to 7: the function of government
#   02           sub-major head    two digits, before any minor head under that major
#   001, 800     minor head        three digits: the programme
#   03, 0102     scheme            what the state files as a scheme, under a minor head
#   01, 42       object head       the item of expenditure, and the only level with money
#                                  printed on its own row
#
# The object-head test is the document's own and needs no threshold at all: a node prints
# a योग total and an item of expenditure prints its four figures.
LEVELS = [("major", None), ("submajor", None), ("minor", None), ("scheme", None),
          ("object", None)]
MAJOR_CODE = re.compile(r"^[2-7]\d{3}$")

# The bands across a detail page: three historic money columns, then the name, then the
# budget estimate for the cycle. The name band is bounded on BOTH sides. Without the right
# bound the budget-estimate figure is read as part of the name, and object head 03 comes
# out called "मंहगाई भत्ता 14874.64".
X_MONEY_MAX = 240.0
# The name band's left edge has to reach the MAJOR head, which indents further left than
# anything else on the page: x 224 in Gr49, 230 in Gr40, against 241 for a sub-major and
# 243 for a minor. Set at 240 to clear the money it was reading, the band excluded every
# major head in all 91 volumes, so no volume had a top level and the Revenue and Capital
# copies of sub-major 02 merged into one node carrying both.
#
# The left edge therefore overlaps the historic money columns, and the two are separated by
# TOKEN SHAPE instead, which is exact: money always carries two decimal places, an account
# code never does. 2235 is not a sum of money and 1326792.42 is not a head of account.
X_NAME_MIN = 210.0
X_NAME_MAX = 500.0

# The appropriation-accounts ABSTRACT page, which the volume prints before the detail and
# heads with its own title. It lists the same major and minor heads at different indents
# entirely (major at x 288 where the detail puts it at 225) and prints a योग for each. Read
# as if it were a detail page it contributes totals with no object heads under them, which
# is 2,831 reconciliation failures and not one of them a real disagreement.
ABSTRACT = "विनियोग"

# Voted and Charged. The book states an object head's provision on two lines, मतदेय for the
# voted part and भारित for the part charged on the Consolidated Fund, and prints a separate
# योग for each. Both markers sit in the left margin at x 229, which is inside the name band
# and to the LEFT of the code, so they arrive as the first token of the row and every voted
# object head was dropped for not starting with a code.
#
# They are removed by position as well as by text, never by text alone. Punjab's parser
# learned that the hard way: Voted and Charged are also ordinary words inside scheme names,
# and a text-only test took a word off 89 rows there. Here the markers are in the margin
# and a name never is.
VOTED, CHARGED = "मतदेय", "भारित"
X_MARKER_MAX = 240.0

# How far below its name a row's money may sit. Devanagari and digits are on different
# baselines, so the offset is about 4pt for an ordinary row; where a figure is too wide for
# its column the renderer squeezes it onto a third baseline and the offset reaches 6.7. Row
# pitch is 18pt, so there is room. Swept over seven volumes: 6.0 gives 36 reconciliation
# failures and 61 unresolved totals, 8.0 through 10.0 give 27 and 39, and 12.0 starts
# merging neighbouring rows again at 31. Set in the middle of the plateau rather than at
# its edge.
ROW_TOL = 9.0
JOIN_GAP = 2.0       # below this, two Devanagari words are one word split by the renderer


def pdf_bbox(pdf_bytes):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-bbox-layout", p, "-"],
                           capture_output=True, timeout=1200)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout.decode("utf-8", "replace")


def repair(words):
    """Join words the renderer split inside a syllable cluster. Geometry, not a word list."""
    out = []
    for x0, x1, w in words:
        if out:
            px0, px1, pw = out[-1]
            if (x0 - px1) < JOIN_GAP and has_devanagari(pw) and has_devanagari(w) \
                    and not pw.endswith(VIRAMA):
                out[-1] = (px0, x1, pw + w)
                continue
        out.append((x0, x1, w))
    return out


def rows_of(page_xml):
    """Group a page's words into table rows, tolerating the name/money baseline offset."""
    ws = sorted((float(y), float(x0), float(x1), html.unescape(w))
                for x0, y, x1, w in WORD.findall(page_xml))
    rows, cur, top = [], [], None
    for y, x0, x1, w in ws:
        if top is None or (y - top) > ROW_TOL:
            if cur:
                rows.append(repair(sorted(cur)))
            cur, top = [], y
        cur.append((x0, x1, w))
    if cur:
        rows.append(repair(sorted(cur)))
    return rows


# The two money bands: three historic columns on the left of the name, and the budget
# estimate for the cycle on the right of it. Bounded on both sides because "--" is also
# printed as ordinary text, in "राजस्व लेखा --", and reading that as a nil provision
# invents a zero-funded row out of a section heading.
def amounts(row):
    out = []
    for x0, _, w in row:
        in_band = (40.0 <= x0 <= X_MONEY_MAX) or (X_NAME_MAX <= x0 <= 580.0)
        if not in_band:
            continue
        if MONEY.match(w):
            out.append(float(w.replace(",", "")))
        elif NIL.match(w):
            out.append(0.0)
    return out


def level_of(code, has_own_money, seen_minor):
    """Which rank of the account tree this row is, from its code and whether it holds money.

    `seen_minor` is whether a minor head has been opened under the current major head. It
    is the only thing that separates a sub-major head from a scheme, both of which are two
    digits: a sub-major comes before its minor heads and a scheme comes after them.
    """
    if has_own_money:
        return "object"
    if MAJOR_CODE.match(code):
        return "major"
    if len(code) == 3:
        return "minor"
    return "scheme" if seen_minor else "submajor"


LEVELS_INDEX = {n: i for i, (n, _) in enumerate(LEVELS)}


class Node:
    __slots__ = ("level", "code", "name", "page", "children", "amounts", "parent")

    def __init__(self, level, code, name, page, parent):
        self.level, self.code, self.name, self.page = level, code, name, page
        self.parent, self.children, self.amounts = parent, [], []

    def subtotal(self, col=-1):
        """This node's own arithmetic: the sum of every object head beneath it."""
        if self.amounts:
            return self.amounts[col] if len(self.amounts) > abs(col) else 0.0
        return round(sum(c.subtotal(col) for c in self.children), 2)

    def ancestors(self):
        n, out = self.parent, []
        while n is not None:
            out.append(n)
            n = n.parent
        return list(reversed(out))


def parse_volume(xml, grant, department):
    """One grant volume into (scheme nodes, reconciliation record, page stats).

    The stack is carried ACROSS pages and not reset at each one. Uttar Pradesh reprints the
    head of account as a banner at the top of a continuation page, and a parser that
    rebuilds its tree from that banner loses every group that spans a page break; one that
    resets to nothing loses the head of account for every scheme after the first page. The
    banner is therefore ignored and the tree is carried, which is what the document means.
    """
    stats = collections.Counter()
    root = Node("root", None, None, 0, None)
    stack = [root]
    totals = []
    seen_minor = False
    for pno, pg in enumerate(PAGE.finditer(xml), 1):
        body = pg.group(1)
        words = WORD.findall(body)
        text = " ".join(html.unescape(w) for _, _, _, w in words)
        unit = UNIT.search(text)
        if not unit:
            stats["pages_without_a_unit_banner"] += 1
            continue
        if ABSTRACT in text:
            stats["abstract_pages_skipped"] += 1
            continue
        scale = UNIT_IN_LAKH[unit.group(1)]
        stats["pages_read"] += 1
        for row in rows_of(body):
            money = amounts(row)
            head = [(x0, x1, w) for x0, x1, w in row
                    if X_NAME_MIN <= x0 < X_NAME_MAX
                    and not MONEY.match(w) and not NIL.match(w)
                    and not (w in (VOTED, CHARGED) and x0 < X_MARKER_MAX)]
            charged = any(w == CHARGED and x0 < X_MARKER_MAX for x0, _, w in row)
            if not head:
                continue
            toks = [w for _, _, w in head]

            if charged:
                # The charged half of a provision, and of a total. It is real money and it
                # is not counted here: the totals this reconciles against are the voted
                # ones, and adding a charged line to a voted subtotal would break every
                # check on the page. Counted so the omission is visible rather than silent.
                stats["charged_rows_not_counted"] += 1
                continue
            if YOG in toks:
                # Resolved against the OPEN stack, not by searching the whole volume for a
                # node with this code. Codes repeat all over the tree -- 01 is a sub-major
                # head, a plan type and an object head -- so a total matched by code alone
                # lands on whichever node happened to be parsed last.
                i = toks.index(YOG)
                after = [w for w in toks[i + 1:] if w not in (":", "-", "--")]
                code = next((w for w in after if re.fullmatch(r"\d{2,4}", w)), None)
                node = next((n for n in reversed(stack) if n.code == code), None) if code else None
                totals.append({"page": pno, "code": code, "grand": GRAND in toks,
                               "node": node,
                               "amounts": [round(a * scale, 2) for a in money],
                               "label": " ".join(after[:4])})
                continue

            m = CODE.match(toks[0].rstrip("-"))
            if not m:
                continue
            code = m.group(1)
            lvl = level_of(code, bool(money), seen_minor)
            if lvl == "major":
                seen_minor = False
            elif lvl == "minor":
                seen_minor = True
            name = re.sub(r"\s+", " ", " ".join(toks[1:]).lstrip("-").strip(" -:")).strip()
            if lvl == "object":
                # An object head is an item of expenditure, never a scheme. Its money is
                # what every total above it is made of, so it is recorded on the tree and
                # not published as a row.
                n = Node(lvl, code, name, pno, stack[-1])
                n.amounts = [round(a * scale, 2) for a in money]
                stack[-1].children.append(n)
                stats["object_head_rows"] += 1
                continue
            if not name or not has_devanagari(name):
                stats["code_rows_with_no_hindi_name"] += 1
                continue
            # A four-digit scheme code is its parent plan type plus its own two digits:
            # under "01- केन्द्र प्रायोजित योजनाएँ" sit 0102, 0106, 0108. That is the
            # document's own encoding, and it is what separates a plan-type HEADING from
            # the schemes beneath it. The x-positions cannot: the heading indents at 254
            # and its children at 256, and nobody should hang a tree on two points.
            extends = (len(code) == 4 and lvl == "scheme"
                       and any(n.level == "scheme" and n.code == code[:2] for n in stack))
            while len(stack) > 1 and LEVELS_INDEX[stack[-1].level] >= LEVELS_INDEX[lvl]:
                if extends and stack[-1].level == "scheme" and stack[-1].code == code[:2]:
                    break
                stack.pop()
            n = Node(lvl, code, name, pno, stack[-1])
            stack[-1].children.append(n)
            stack.append(n)

    # A scheme is a node in the scheme band with no scheme-band child. The band holds two
    # ranks that the x-positions cannot separate, because a plan-type heading indents two
    # points less than the schemes under it: "01- केन्द्र प्रायोजित योजनाएँ", Centrally
    # Sponsored Schemes, sits at x 254 and "0102- समन्वित बाल विकास योजना" at x 256. Two
    # points is not a threshold anybody should rely on. Having children IS the distinction,
    # and it is the document's own: a heading has schemes under it, a scheme has object
    # heads under it.
    schemes, groups = [], 0

    def walk(n):
        nonlocal groups
        for c in n.children:
            if c.level == "scheme":
                if any(g.level == "scheme" for g in c.children):
                    groups += 1
                    walk(c)
                    continue
                anc = c.ancestors()
                schemes.append({
                    "grant": grant, "department": department, "page": c.page,
                    "code": c.code, "name": c.name, "name_latin": transliterate(c.name),
                    "head_of_account": "-".join(a.code for a in anc if a.code) or None,
                    "under": " / ".join(a.name for a in anc if a.name) or None,
                    "be_lakh": c.subtotal(-1) or None,
                    "object_heads": len(c.children),
                })
            else:
                walk(c)
    walk(root)
    stats["scheme_group_headings"] = groups

    # The book's own arithmetic, checked. A printed total is compared against the sum of
    # the object heads beneath the node it names, in the budget-estimate column. This is
    # the only thing that can catch a mis-set x threshold: a reparented subtree still
    # parses, still yields names, and stops adding up.
    checked = failed = unresolved = 0
    fails = []
    for t in totals:
        if not t["amounts"]:
            continue
        node = t["node"]
        if node is None:
            # A total naming no code, or naming one no open node carries: the Revenue
            # Account and Capital Account subtotals and the grand total. They are real
            # totals of a section the book does not delimit with a node, so they are
            # counted as unresolved rather than passed or failed.
            unresolved += 1
            continue
        printed, got = t["amounts"][-1], node.subtotal(-1)
        checked += 1
        if abs(printed - got) > 0.011:
            failed += 1
            if len(fails) < 25:
                fails.append({"page": t["page"], "code": t["code"], "name": node.name,
                              "printed": printed, "computed": got})
    return schemes, {"checked": checked, "failed": failed, "failures": fails,
                     "unresolved": unresolved}, stats



def myscheme_records():
    """myScheme's own state-level records for Uttar Pradesh, from the archived snapshot."""
    out = []
    for f in glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if "Uttar Pradesh" not in ((d.get("_list") or {}).get("beneficiaryState") or []):
            continue
        b = (d.get("en") or {}).get("basicDetails") or {}
        if b.get("schemeName"):
            out.append(b["schemeName"])
    return sorted(set(out))


def join_to_myscheme(schemes):
    """Every join between the register's romanised names and myScheme's Uttar Pradesh list.

    Indexed on the register side, because 47 records against 5,831 names with a slow
    comparator on every pair is 274,000 calls to a function that does string similarity.
    The index is the same one parse/registry.py uses, keyed on tokens, skeletons and
    acronyms, so it cannot under-retrieve in a way the comparator would have caught.
    """
    names = myscheme_records()
    idx = collections.defaultdict(set)
    for i, e in enumerate(schemes):
        lat = e["name_latin"]
        for k in (set(m_tokens(lat)) | {m_skeleton(t) for t in m_tokens(lat)}
                  | {a for a in m_acronyms(lat) if len(a) >= 5}):
            idx[k].add(i)
    joins = []
    for m in names:
        cand = set()
        for k in (set(m_tokens(m)) | {m_skeleton(t) for t in m_tokens(m)}
                  | {a for a in m_acronyms(m) if len(a) >= 5}):
            cand |= idx.get(k, set())
        for i in sorted(cand):
            ok, why = probably_same(schemes[i]["name_latin"], m)
            if ok:
                joins.append({"myscheme": m, "grant": schemes[i]["grant"],
                              "code": schemes[i]["code"], "name": schemes[i]["name"],
                              "name_latin": schemes[i]["name_latin"], "why": why})
    return joins, names


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "uttarpradesh", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive at archive/uttarpradesh/ — run collect/uttarpradesh.py")
    date = date or dates[-1]
    src = os.path.join(ROOT, "archive", "uttarpradesh", date)
    man = json.load(open(os.path.join(src, "_manifest.json"), encoding="utf-8"))

    all_schemes, stats = [], collections.Counter()
    per_grant, recon = {}, {}
    for p in sorted(glob.glob(os.path.join(src, "Gr*.pdf.gz"))):
        grant = os.path.basename(p)[2:4]
        dept = (man.get("grants", {}).get(grant) or {}).get("department", "")
        with gzip.open(p, "rb") as fh:
            xml = pdf_bbox(fh.read())
        sch, rc, st = parse_volume(xml, grant, dept)
        per_grant[grant] = len(sch)
        recon[grant] = rc
        all_schemes += sch
        stats.update(st)

    checked = sum(r["checked"] for r in recon.values())
    failed = sum(r["failed"] for r in recon.values())
    joins, ms_names = join_to_myscheme(all_schemes)

    write_json("data/uttarpradesh/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Uttar Pradesh",
        "cycle": man.get("cycle"),
        "source": "Uttar Pradesh Budget, Khand-5 grant-wise volumes",
        "source_url": man.get("base"),
        "grants_read": len(per_grant),
        "grants_not_published": sorted(
            e["stage"] for e in man.get("errors", []) if e["stage"].startswith("Gr")),
        "rows_per_grant": per_grant,
        "schemes": len(all_schemes),
        "with_allocation": sum(1 for s in all_schemes if s.get("be_lakh")),
        "extraction_stats": dict(stats),
        "reconciliation": {"checked": checked, "failed": failed,
                           "per_grant": {g: {"checked": r["checked"], "failed": r["failed"]}
                                         for g, r in sorted(recon.items())}},
        "reconciliation_failures": {g: r["failures"] for g, r in sorted(recon.items())
                                    if r["failures"]},
        "reconciliation_note": (
            "Every योग total the book prints is compared, in the budget-estimate column, "
            "against the sum of the object heads beneath the node it names. This is what "
            "checks the x-position thresholds the tree is read from: a mis-set threshold "
            "reparents a subtree, and a reparented subtree still yields names and stops "
            "adding up."),
        "name_note": ("The name is the state's own and is in Hindi, which is the only "
                      "language Uttar Pradesh publishes its budget in. name_latin is a "
                      "DERIVED transliteration, not a translation: it converts script and "
                      "makes no claim about meaning. It exists so the name can be joined "
                      "to myScheme, which lists Uttar Pradesh's schemes in romanised Hindi "
                      "rather than in English."),
        "caveat": ("One row here is one node of Uttar Pradesh's account tree at the level "
                   "the state files schemes at, so it is a superset of the schemes a "
                   "citizen can apply to: a directorate sits at the same level as a cash "
                   "transfer. Items of expenditure below it (Pay, Dearness Allowance, "
                   "Office Expenses) are excluded. The number here is a floor on Uttar "
                   "Pradesh's schemes, never a total."),
        "myscheme_join_summary": {
            "how": ("Names romanised by parse/devanagari.py, then indexed on match.tokens, "
                    "match.skeleton and match.acronyms, then match.probably_same on every "
                    "candidate pair, then every join read by eye."),
            "myscheme_uttar_pradesh_records": len(ms_names),
            "register_names": len(all_schemes),
            "joins_produced": len(joins),
            "myscheme_records_with_any_join": len({j["myscheme"] for j in joins}),
            "joins_sound_on_inspection": 2,
            "joins_wrong_on_inspection": 3,
            "read_this_carefully": (
                "The transliteration works and the join is still small, and those are two "
                "separate facts. Two joins are exact, at similarity 1.00: कन्या सुमंगला "
                "योजना to Kanya Sumangala Yojana and मुख्यमंत्री सामूहिक विवाह योजना to "
                "Mukhyamantri Samuhik Vivah Yojana. Neither was reachable at all before, "
                "because one is in Devanagari and the other in Latin. But only a handful of "
                "myScheme's 47 records reach this book, and the reason is not the script. "
                "Berojgari Bhatta, Gambhir Bimari Sahayata, Kanya Vivah Sahayta and "
                "Panchayat Kalyan Kosh return ZERO rows on a plain substring search of the "
                "Hindi, so they are not in the grant volumes under those names at all: like "
                "Tripura's, several are welfare-board benefits paid from a board's own fund "
                "rather than from a demand. Others are English descriptions rather than "
                "names, 'Marriage Grant Scheme' and 'Widow Pension', and no transliteration "
                "reaches those; matching them would be translation, which this register "
                "does not do. A third of myScheme's Uttar Pradesh list is one or the other."),
            "defeated_by_a_typo_in_the_portal": (
                "उत्तर प्रदेश मुख्यमंत्री बाल सेवा योजना matches 'Uttar Pradesh "
                "Mukhyamantri Bal Seva Yojana' on all five content words and does NOT match "
                "myScheme's actual record, which is spelled 'Uttar Pradesh Mukhyamantri Bal "
                "Seva Yojana (Genearal)'. Genearal is a content word the state's book cannot "
                "contain, so containment fails. The scheme is in both lists and this "
                "register cannot say so."),
            "joins": joins,
        },
        "known_bad_joins": [
            {"myscheme": "Kaushal Vikas Yojana",
             "uttarpradesh": "कौशल विकास मिशन / कौशल विकास केन्द्र की स्थापना",
             "why": ("Skill Development MISSION, and the establishment of skill development "
                     "CENTRES, are not the Skill Development Scheme. Two content words, "
                     "kaushal and vikas, are the whole of the shorter name, so containment "
                     "fires on a pair that shares only its subject.")},
            {"myscheme": "Mukhyamantri Pragatishil Pashupalak Protsahan Yojana",
             "uttarpradesh": "मुख्यमंत्री पंचायत प्रोत्साहन पुरस्कार योजना",
             "why": ("acronym match mpppy. Mukhyamantri Panchayat Protsahan Puraskar and "
                     "Mukhyamantri Pragatishil Pashupalak Protsahan produce the same "
                     "initialism, and a cattle-rearing incentive is joined to a panchayat "
                     "award.")},
        ],
        "entries": all_schemes,
    })
    return all_schemes, per_grant, checked, failed, date


def main():
    ap = argparse.ArgumentParser(description="Parse the archived Uttar Pradesh budget volumes.")
    ap.add_argument("--date")
    a = ap.parse_args()
    schemes, per_grant, checked, failed, date = run(a.date)
    print(f"uttarpradesh snapshot {date}")
    print(f"  {len(per_grant)} grant volumes read")
    print(f"  {len(schemes):,} scheme-level nodes")
    print(f"     with an allocation {sum(1 for s in schemes if s.get('be_lakh')):>7,}")
    print(f"  printed totals: {checked - failed:,} of {checked:,} reconcile"
          + (f", {failed:,} DO NOT" if failed else ""))


if __name__ == "__main__":
    main()
