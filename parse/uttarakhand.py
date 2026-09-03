"""
Parse the archived Uttarakhand Volume 5 into data/uttarakhand/schemes.json.

AGENT-EDITABLE (PLAN.md 7). Reads archive/, never fetches.

WHY UTTARAKHAND ALMOST DID NOT YIELD. The state writes its budget in Hindi and typesets it
in KrutiDev. `pdffonts` on Volume 2 and on the Gender Budget returns `Kruti Dev 010` and
`Kruti Dev 016` in WinAnsi with no ToUnicode, and Volume 2's notes extract as `o"kZ 2026&27`
where the state wrote 2026-27. That is the Madhya Pradesh failure recorded in
docs/state-sources.md, and on Volume 2 it is fatal.

Volume 5, `Head wise details of accounts`, is a different book. It prints every line of the
detailed estimates twice, the Hindi first and the English underneath:

    2011  सस द/रधजख/ससघ रधजख कदत ववधधनमसडल
          Parliament/State/Union Territory Legislatures
      02  रधजख/ससघ रधजख कदत ववधधन मणडल
          State /Union Territory/Legislatures
       101  ववधधन सभध
            Legislative Assembly
        03  ववधधन सभध
            Legislative Assembly
       ... 42240   3600   45840
        01  वदतन
            Pay
        खयग/Total  03  ...  673642  57851  731493

The Hindi is damaged in the way Uttarakhand's typesetting damages everything, and it does
not matter: it is Devanagari Unicode, so it cannot share a line with the Latin, and the
English line beneath is clean. That is the Odisha property arriving by a different route.

THREE THINGS THAT HAD TO BE WORKED OUT, none of them stated by the document.

  WHERE THE MONEY GOES. Each row's figures are printed on their OWN line, BEFORE the two
  lines that name it. Attaching a figure line to the row above it instead reads the
  Legislative Assembly as spending Rs 11.5 crore on Medicines and Chemicals and nothing at
  all on Grant in Aid; attaching it to the row below gives Medicines and Chemicals a token
  provision of Rs 1,000, which is what a token provision looks like, and puts the 11.5
  crore on Maintenance. The sums are identical either way, so the printed totals cannot
  settle it and the reading was settled by looking.

  WHICH NODE A TOTAL CLOSES. A `खयग/Total` line names a code and nothing else, and the same
  two-digit code can be open twice in one path: sub-head 01 with object head 01 Pay under
  it. Among the open nodes carrying that code the parser takes the DEEPEST whose subtree
  adds up to the printed figure, and only falls back to the deepest when none does. So the
  attribution is decided by the book's own arithmetic rather than by a rule about depth.

  WHICH LEVEL IS A SCHEME. Uttarakhand's own scheme code, the 13-digit number its Volume 5
  front matter prints as `Scheme Code`, is major head, sub-major, minor, sub-head and
  detail head concatenated: 2245801020106. The standard items of expenditure beneath that
  (Pay, Dearness Allowance, Office Expenses) are not schemes. They are told apart by a
  property of the document rather than by a word list: **a level the book prints a total
  for is a level with children, and an item of expenditure never gets one.** So a node
  below the minor head that carries a printed total is published as a scheme, and a node
  with no total of its own is not.

UNITS. `(हजरर रपयक मम/In Thousand)`, on every page, checked on every page and converted to
lakh by dividing by 100. Read as lakh, every figure here would publish at 100 times its
value. That is the Kerala trap, and this book prints its unit in Hindi and English on the
same line, which is the only reason it was easy to see.

RECONCILIATION. Every printed total in all five books against the subtree beneath it, in
the 2026-27 Budget Estimate column. Uttarakhand prints twelve money columns (Voted,
Charged and Total for four year blocks); the check uses the last, which is the column this
register publishes, and the count of totals checked and reconciled is reported in full.
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

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, read_json, utcnow, write_json  # noqa: E402

CYCLE_WANTED = "2026-27"

# The four parts of Volume 5. The Gender Budget is archived beside them and NOT read: it
# restates the same estimates in a denser layout that puts the money, the code and the
# name on one line, and one reader cannot do both. Read with this reader it reconciled 209
# of its 1,782 printed totals, against 81 per cent for Volume 5, and a book that will not
# reconcile is a book this register does not publish figures from.
BOOKS = ("vol5-part1", "vol5-part2", "vol5-part3", "vol5-part4")
BOOK_LABEL = {
    "vol5-part1": "Volume 5 Part 1", "vol5-part2": "Volume 5 Part 2",
    "vol5-part3": "Volume 5 Part 3", "vol5-part4": "Volume 5 Part 4",
    "gender": "Gender Budget",
}

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LETTER = re.compile(r"[ऀ-ॿA-Za-z]")
# A money cell. Uttarakhand writes nil as `--` and a negative as `(-) 1234`.
TOKEN = re.compile(r"\(-\)\s*[\d,]+|--|[\d,]+")
UNIT = re.compile(r"In\s+Thousand", re.I)
CYCLE = re.compile(r"\b(\d{4}-\d{2})\b")
GRANT = re.compile(r"Grants?\s+No-?\s*(\d{1,3})")
# The Group I / Group II women-benefit marker, printed only in the Gender Budget.
GROUP = re.compile(r"Group\s*-\s*([IV]+)")
# The per-grant cover page, which prints that grant's Revenue and Capital provision in
# FULL RUPEES while every detail page is in thousands. That is the units cross-check.
COVER = re.compile(r"Estimated\s+amount\s+of\s+expenditure", re.I)
# The English labels, not the Hindi: राजस्व and पूंजी are garbled differently in each part
# and matching one part's spelling found the cover figures in one book and none of the
# others. On the cover the label prints on the line BELOW its figures.
COVER_LABEL = re.compile(r"(Revenue|Capital)\s*\(\s*Rupee", re.I)
# "खयग/Total   ररजसव लकखर   Revenue Account": the word Total, then the Hindi, then the
# English. Anchoring Revenue directly after Total matched nothing.
ACCOUNT_TOTAL = re.compile(r"Total\b.{0,40}?(Revenue|Capital)\s+Account", re.I | re.S)
# Any unit these books could have used instead. None of them appears, and the check that
# none appears is what makes "In Thousand" a reading rather than an assumption.
OTHER_UNIT = re.compile(r"In\s+(Lakh|Crore|Million|Rupees)\b", re.I)
# A page that carries estimates: it prints a total, or a code beside Devanagari.
# The word योग, "total", is garbled differently in each of the five books: Part 1 renders
# it खयग, Part 2 ययग, Part 3 खरग and the Gender Budget नयग. Matching any short run of
# Devanagari before "/Total" is what makes one reader work on all five; enumerating the
# spellings missed Part 3 entirely and reconciled 0 of its 1,208 totals.
HAS_TOTAL = re.compile(r"[ऀ-ॿ]{1,8}\s*/\s*Total")
# The grant-level summary pages, whose layout is not the detail layout and whose totals
# restate the detail pages'. Reading them put a money figure where a code should be.
APPROPRIATION = re.compile(r"Appropriation\s+Accounts", re.I)

# The running header of a detail page, which has to be found and skipped rather than
# assumed to be a fixed number of lines. Taking "the last line in the first fourteen that
# carries Devanagari" looked right and was wrong: on a page whose estimates begin at line
# nine, every one of those lines carries Devanagari too, so the header was declared to end
# at line thirteen and five rows of the account tree were thrown away with it. That single
# mistake was most of the 47 per cent of printed totals that would not reconcile.
YEAR_LABEL = re.compile(r"^[\s\d]*(?:\d{4}-\d{2}[\s]*)+$")
HEADER_LINE = re.compile(r"Website|Page\s*No|Grants?\s+No|Estimates|Actuals|"
                         r"In\s+Thousand", re.I)


def header_end(lines):
    """The index of the last running-header line, or -1 if the page starts in the body."""
    end = -1
    for i, l in enumerate(lines[:20]):
        if not l.strip():
            continue
        if HEADER_LINE.search(l) or YEAR_LABEL.match(l):
            end = i
            continue
        # The Voted / Charged / Total column labels, printed three or four times across
        # the page in Devanagari with no digit anywhere on the line.
        toks = l.split()
        if len(toks) >= 4 and not any(ch.isdigit() for ch in l) and \
                all(DEVANAGARI.search(t) for t in toks):
            end = i
    return end


def pdftotext(pdf_bytes):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.pdf")
        with open(p, "wb") as fh:
            fh.write(pdf_bytes)
        r = subprocess.run(["pdftotext", "-layout", p, "-"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"pdftotext failed: {r.stderr[:200]!r}")
        return r.stdout


def value(tok):
    t = tok.replace(",", "").replace(" ", "")
    if "-" in t and not t.startswith("(-)") and t != "--":
        # A year range such as 2026-27 is not a figure. It reaches here only from the
        # summary pages, where the running header shares a line with the account totals.
        return 0.0
    if t == "--":
        return 0.0
    if t.startswith("(-)"):
        return -float(t[3:])
    return float(t)


class Node:
    __slots__ = ("code", "name", "own", "kids", "page", "book", "grant",
                 "printed", "group", "reconciled")

    def __init__(self, code, page, book, grant):
        self.code, self.page, self.book, self.grant = code, page, book, grant
        self.name, self.own, self.kids = None, 0.0, []
        self.printed, self.group, self.reconciled = None, None, False

    def total(self):
        return round(self.own + sum(k.total() for k in self.kids), 3)

    def add_name(self, more):
        # A node is restated at the top of every page it continues onto, English line and
        # all, so a plain append gave "Legislative Secretariat Legislative Secretariat
        # Legislative Secretariat Legislative Secretariat". Only text the name does not
        # already carry is added, which keeps a genuine two-line name whole.
        if not self.name:
            self.name = more
        elif more not in self.name:
            self.name = (self.name + " " + more).strip()


def _open(stack, roots, code, pi, book, grant, group):
    """Open a node for this code, or return the open one the page is restating.

    A page restates its whole open path in its first rows. Popping the stack back to a
    restated node THREW AWAY everything already read under it: page 28 of Part 1 restates
    2011, 02, 101 and 03, and popping at 2011 deleted the twelve object heads read on
    page 27, leaving the Legislative Assembly's printed 731,493 against a computed
    215,001. Nothing is popped here; only a Total line pops, and it says which code it
    closes.
    """
    at = next((i for i in range(len(stack) - 1, -1, -1)
               if stack[i].code == code), None)
    if at is not None:
        return stack[at]
    n = Node(code, pi, book, grant)
    n.group = group
    if stack:
        stack[-1].kids.append(n)
    else:
        roots.append(n)
    stack.append(n)
    return n


def read_book(text, book):
    """Walk one book. Returns (roots, checks, pages, unit_pages, cycles, grants)."""
    roots, checks, stack = [], [], []
    pages = unit_pages = front_pages = data_pages = 0
    other_units = []
    index_codes, covers, accounts = set(), {}, {}
    skipped_pages = 0
    cycles, grants = set(), set()
    grant = None
    pending = None       # the figure line waiting for the row it names
    last = None
    group = None

    for pi, page in enumerate(text.split("\f")):
        lines = page.split("\n")
        if not any(l.strip() for l in lines):
            continue
        pages += 1
        head = "\n".join(lines[:20])
        if COVER.search(page) or APPROPRIATION.search(page):
            # A grant cover page or a grant-level appropriation summary. Neither is the
            # detail layout, and the appropriation page restates totals the detail pages
            # already print.
            front_pages += 1
            g0 = GRANT.search(head)
            if g0:
                # The grant number is read here too, not only on the detail pages: the
                # cover and the appropriation summary come BEFORE the first detail page
                # of their grant, so without this the units check had nothing to key on.
                grant = int(g0.group(1))
            if APPROPRIATION.search(page) and grant is not None:
                # The grant-level appropriation summary is not read for its tree, but it
                # is the only place these books print a Revenue Account and Capital
                # Account total, and those are what the cover page's rupees are checked
                # against.
                for li, line in enumerate(lines):
                    ma = ACCOUNT_TOTAL.search(line)
                    if not ma:
                        continue
                    # The label can be printed on its own line with its figures on the
                    # line above, which is how grant 1's Revenue Account total is laid
                    # out; taking only the label's own line found no figure at all and
                    # left the units check with nothing to check.
                    nums = [value(x) for x in TOKEN.findall(line)]
                    if not nums and li:
                        nums = [value(x) for x in TOKEN.findall(lines[li - 1])]
                    if nums:
                        accounts.setdefault(grant, {})[
                            ma.group(1).lower() + "_thousand"] = nums[-1]
            if COVER.search(page):
                g = GRANT.search(head)
                if g:
                    cover = covers.setdefault(int(g.group(1)), {})
                    for i, line in enumerate(lines):
                        ml = COVER_LABEL.search(line)
                        if not ml or i == 0:
                            continue
                        # The label sits under its own figures, which are on the line
                        # above with the Hindi label in front of them.
                        above = lines[i - 1]
                        cut = max((m.end() for m in LETTER.finditer(above)
                                   if m.start() < 60), default=0)
                        nums = [value(x) for x in TOKEN.findall(above[cut:])]
                        if nums:
                            # Voted, Charged and Total are printed side by side; the last
                            # is the one to take. Summing all three doubles the figure,
                            # which showed up at once as grant 1 claiming Rs 241 crore of
                            # revenue against the Rs 115 crore its detail pages add to.
                            cover[ml.group(1).lower() + "_rupees"] = nums[-1]
            continue
        if OTHER_UNIT.search(page):
            other_units.append(pi)
        if UNIT.search(page):
            unit_pages += 1
        # Which pages are read is decided by what a page IS, not by what it happens to
        # print. Two earlier rules both lost real estimates: requiring the unit marker
        # dropped four pages of Volume 5 Parts 2 and 3 that carry a whole section and no
        # unit line, and requiring a printed total dropped page 27 of Part 1, whose twelve
        # object heads are all closed by a total on the page after. So the unit is
        # established for the BOOK instead: it appears on almost every page, no page in
        # any of the five names a different one, and the rupee cover pages check the scale
        # from the outside.
        if "Scheme Code" in head:
            # 32 pages of Volume 5 Part 1 are a Scheme Code / Scheme Name / Secretary /
            # HOD index in Hindi with no figures. Its 13-digit codes are read, because
            # they are the state's own numbering and are used to check the codes this
            # parser builds from the account tree; the page itself is not an estimate.
            front_pages += 1
            for m in re.finditer(r"\b(\d{1,3})\s+(\d{13})\b", page):
                index_codes.add(m.group(2))
            continue
        if "Department Name" in head or not DEVANAGARI.search(page):
            # The Gender Budget's preface, which is KrutiDev with no Devanagari in it at
            # all, and its per-department summary, which is a different table.
            front_pages += 1
            continue
        data_pages += 1
        # The cycle is on the same line as the grant number, in the running header. Read
        # from the whole header block instead it picks up every year printed in a scheme
        # name ("Uttarakhand Government Stock 2028") and reports thirteen cycles.
        m = GRANT.search(head)
        if m:
            grant = int(m.group(1))
            grants.add(grant)
            line = head[head.rfind("\n", 0, m.start()) + 1:
                        head.find("\n", m.end()) if head.find("\n", m.end()) > 0
                        else len(head)]
            for c in CYCLE.finditer(line):
                cycles.add(c.group(1))
        # The column header block runs to the last line before the body that still carries
        # Devanagari or the word Estimates. Everything above it is the running header and
        # names no scheme.
        start = header_end(lines)
        # A figure never straddles a page break in this book, so nothing is carried over.
        pending, last = None, None

        for line in lines[start + 1:]:
            if not line.strip():
                continue
            spans = [m.start() for m in LETTER.finditer(line)]
            if not spans:
                # A figure line. The last token on it is the 2026-27 Total, which is the
                # column this register publishes.
                toks = TOKEN.findall(line)
                if toks:
                    pending = value(toks[-1])
                continue
            a, b = spans[0], spans[-1] + 1
            text_part, left, right = line[a:b].strip(), line[:a], line[b:]

            if HAS_TOTAL.search(text_part) or (
                    "Total" in text_part and DEVANAGARI.search(text_part)):
                rt = TOKEN.findall(right)
                code = rt[0] if rt and rt[0].replace(",", "").isdigit() else None
                vals = [value(x) for x in (rt[1:] if code else rt)]
                printed = vals[-1] if vals else 0.0
                if pending is not None and last is not None:
                    last.own += pending
                pending = None
                if code is None:
                    # A Revenue Account / Capital Account closer. It names no code, so it
                    # closes nothing in the tree, but it carries the grant's own total in
                    # thousands and that is what the cover page is checked against.
                    ma = ACCOUNT_TOTAL.search(text_part) or ACCOUNT_TOTAL.search(right)
                    if ma and grant is not None and vals:
                        accounts.setdefault(grant, {})[
                            ma.group(1).lower() + "_thousand"] = vals[-1]
                    continue
                cand = [i for i, n in enumerate(stack) if n.code == code]
                if not cand:
                    checks.append({"book": book, "page": pi, "code": code,
                                   "name": None, "printed": printed,
                                   "computed": None, "ok": False,
                                   "why": "no open node carries this code"})
                    continue
                # The deepest candidate whose subtree adds up, else the deepest.
                pick = next((i for i in reversed(cand)
                             if abs(stack[i].total() - printed) <= 0.5), cand[-1])
                node = stack[pick]
                node.printed = printed
                node.reconciled = abs(node.total() - printed) <= 0.5
                checks.append({"book": book, "page": pi, "code": code,
                               "name": node.name, "printed": printed,
                               "computed": node.total(),
                               "ok": abs(node.total() - printed) <= 0.5,
                               "candidates": len(cand)})
                del stack[pick:]
                last = None
                continue

            mg = GROUP.search(text_part)
            if mg and not DEVANAGARI.search(text_part.replace("शदणर", "")):
                group = mg.group(1)
                continue
            if mg:
                group = mg.group(1)
                continue

            toks = TOKEN.findall(left)
            if DEVANAGARI.search(text_part) and toks:
                # A node can be printed with TWO codes on one line, "01 01 ई- ववधधन सभध",
                # which is a sub-head and the detail head under it stated together. The
                # book then closes them with two consecutive "Total 01" lines, and reading
                # only the last code left the second with nothing to close: 708 of the
                # unreconciled totals across the four parts said "no open node carries
                # this code". Both codes are opened, outermost first.
                codes = [t.replace(",", "") for t in toks[-2:]
                         if t not in ("--",) and len(t.replace(",", "")) <= 2]
                if len(codes) < 2 or len(toks) < 2 or len(toks[-1]) > 2:
                    codes = [toks[-1].replace(",", "")]
                for code in codes:
                    last = _open(stack, roots, code, pi, book, grant, group)
                if pending is not None:
                    last.own += pending
                    pending = None
                continue

            if DEVANAGARI.search(text_part):
                # A wrapped Hindi line. It names nothing this parser reads.
                continue
            if last is not None:
                last.add_name(text_part)
    return (roots, checks, pages, unit_pages, data_pages, front_pages, cycles, grants,
            index_codes, covers, accounts, skipped_pages, other_units)


def walk(node, path, out, minor_seen=False):
    """Collect every node below a minor head that the book prints a total for."""
    here = path + [node]
    is_minor = len(node.code) == 3
    if node.printed is not None and minor_seen and len(node.code) <= 2:
        out.append(list(here))
    for k in node.kids:
        walk(k, here, out, minor_seen or is_minor)


def run(date=None):
    dates = sorted(os.path.basename(p) for p in
                   glob.glob(os.path.join(ROOT, "archive", "uttarakhand", "*"))
                   if os.path.isdir(p))
    if not dates:
        raise SystemExit("no archive/uttarakhand snapshot; run "
                         "collect/uttarakhand.py first")
    date = date or dates[-1]
    man = read_json(f"archive/uttarakhand/{date}/_manifest.json", {}) or {}

    all_checks, per_book, entries, nodes_seen = [], {}, {}, 0
    cycles_all, grants_all, index_all = set(), set(), set()
    covers_all, accounts_all = {}, {}
    for book in BOOKS:
        path = os.path.join(ROOT, "archive", "uttarakhand", date, f"{book}.pdf.gz")
        if not os.path.exists(path):
            raise SystemExit(f"missing {path}. The four Volume 5 parts and the Gender "
                             "Budget are all needed; a missing part is whole grants "
                             "silently absent, not a shorter book")
        with gzip.open(path, "rb") as fh:
            text = pdftotext(fh.read())
        (roots, checks, pages, unit_pages, data_pages, front_pages, cycles, grants, idx,
         covers, accounts, skipped, other_units) = read_book(text, book)
        if other_units:
            raise SystemExit(
                f"uttarakhand {book}: pages {other_units[:10]} name a unit other than "
                "thousands; the book is no longer single-unit and every figure in it "
                "would have to be rescaled")
        if not unit_pages:
            raise SystemExit(f"uttarakhand {book}: no page prints 'In Thousand'")
        index_all |= idx
        for g, d in covers.items():
            covers_all.setdefault(g, {}).update(d)
        for g, d in accounts.items():
            accounts_all.setdefault(g, {}).update(d)
        if CYCLE_WANTED not in cycles:
            raise SystemExit(f"uttarakhand {book}: page headers name {sorted(cycles)}, "
                             f"not {CYCLE_WANTED}")
        cycles_all |= cycles
        grants_all |= grants
        all_checks += checks

        found = []
        for r in roots:
            walk(r, [], found)
        nodes_seen += len(found)
        for path_nodes in found:
            node = path_nodes[-1]
            # The state's own 13-digit scheme code: major head, sub-major, minor, sub-head
            # and detail head, each padded to the width the code book uses.
            major = next((n.code for n in path_nodes if len(n.code) == 4), None)
            minor = next((n.code for n in path_nodes if len(n.code) == 3), None)
            twos = [n.code for n in path_nodes if len(n.code) <= 2]
            if major is None or minor is None:
                continue
            before = [n.code for n in path_nodes
                      if len(n.code) <= 2 and
                      path_nodes.index(n) < [x.code for x in path_nodes].index(minor)]
            after = [c for c in twos if c not in before]
            submajor = (before[0] if before else "00").zfill(2)
            sub = (after[0] if after else "00").zfill(2)
            det = (after[1] if len(after) > 1 else "00").zfill(2)
            code = f"{major}{submajor}{minor}{sub}{det}"
            key = code
            e = entries.get(key)
            if e is None:
                e = entries[key] = {
                    "code": code, "name": node.name, "names": set(),
                    "major_head": None, "minor_head": None,
                    "grants": set(), "books": set(), "groups": set(),
                    "be_thousand": 0.0, "reconciled": False}
                for n in path_nodes:
                    if len(n.code) == 4:
                        e["major_head"] = f"{n.code} {n.name}"
                    if len(n.code) == 3:
                        e["minor_head"] = f"{n.code} {n.name}"
            if node.name:
                e["names"].add(node.name)
            if node.grant:
                e["grants"].add(node.grant)
            e["books"].add(BOOK_LABEL[book])
            if node.group:
                e["groups"].add(node.group)
            # ACROSS books the same provision is reported twice, once in Volume 5 and
            # again in the Gender Budget, so the largest is kept rather than the sum. The
            # four Volume 5 parts are disjoint by grant and never overlap.
            e["be_thousand"] = max(e["be_thousand"], node.printed or 0.0)
            e["reconciled"] = e.get("reconciled") or node.reconciled

        per_book[BOOK_LABEL[book]] = {
            "pages": pages, "data_pages": data_pages,
            "pages_printing_the_thousand_unit": unit_pages,
            "front_matter_pages": front_pages + skipped,
            "printed_totals": len(checks),
            "reconciled": sum(1 for c in checks if c["ok"]),
            "schemes": len(found)}

    failed = [c for c in all_checks if not c["ok"]]

    # ------------------------------------------------------------- the units check
    # Each grant's cover page prints that grant's Revenue and Capital provision in FULL
    # RUPEES, the only place in these books where a second unit appears and therefore the
    # only way to check the first from outside. A parser that had read thousands as lakh,
    # or rupees as thousands, would be out by a factor of 1,000 or 100,000 here.
    unit_checks = []
    for g in sorted(set(covers_all) | set(accounts_all)):
        cov, acc = covers_all.get(g, {}), accounts_all.get(g, {})
        for kind in ("revenue", "capital"):
            rup, thou = cov.get(f"{kind}_rupees"), acc.get(f"{kind}_thousand")
            if rup is None or thou is None:
                continue
            unit_checks.append({
                "grant": g, "account": kind, "cover_rupees": rup,
                "detail_thousand": thou,
                "detail_thousand_as_rupees": round(thou * 1000.0, 2),
                "ok": abs(thou * 1000.0 - rup) <= 1000.0})
    unit_failed = [c for c in unit_checks if not c["ok"]]

    # ------------------------------------------- the state's own list of scheme codes
    # Volume 5 Part 1 opens with a Scheme Code / Scheme Name index in Hindi. Its 13-digit
    # codes are the state's own numbering, and comparing them with the codes this parser
    # builds out of the account tree is an independent check on the construction.
    built = {c for c in entries}
    code_check = {
        "codes_in_the_state_index": len(index_all),
        "also_built_from_the_account_tree": len(index_all & built),
        "in_the_index_and_not_built": sorted(index_all - built)[:20] or None,
        "what": ("the 13-digit codes Volume 5's own front matter prints as Scheme Code, "
                 "against the codes this parser concatenates out of major head, "
                 "sub-major, minor, sub-head and detail head"),
        "read_this_carefully": (
            "Half of them line up and half do not, which says the code built here is "
            "indicative and not the state's own identifier for every row. The failures "
            "are the same failures as the unreconciled totals: where a page layout this "
            "reader does not know breaks the account tree, the path it walks up to build "
            "the code is broken too. A row whose total_reconciled is true has a code "
            "built from a path the book's own arithmetic agreed with; treat the others' "
            "codes as a label, and the NAME as the thing to join on."),
    }

    out = []
    for code in sorted(entries):
        e = entries[code]
        out.append({
            "code": code,
            "name": e["name"],
            "also_named": sorted(n for n in e["names"] if n != e["name"]) or None,
            "major_head": e["major_head"],
            "minor_head": e["minor_head"],
            "grants": sorted(e["grants"]),
            "books": sorted(e["books"]),
            "be_lakh": round(e["be_thousand"] / 100.0, 4),
            "be_thousand": round(e["be_thousand"], 3),
            "total_reconciled": e["reconciled"],
        })

    named = [e for e in out if e["name"]]
    write_json("data/uttarakhand/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Uttarakhand",
        "cycle": CYCLE_WANTED,
        "source": ("Uttarakhand Budget 2026-27, Volume 5 (Head wise details of "
                   "accounts), Parts 1 to 4"),
        "source_url": man.get("base"),
        "books": {k: v for k, v in sorted(man.get("books", {}).items())},
        "unit": "lakh",
        "unit_note": (
            "be_lakh is rupees in LAKH, converted from the THOUSANDS these books print. "
            "The unit is read from the '(हजरर रपयक मम/In Thousand)' marker these books "
            "print, and it is checked from outside as well: every grant's cover page "
            "prints that grant's Revenue and Capital provision in FULL RUPEES, and those "
            "are compared here with the detail pages' figures in thousands times 1,000. "
            "Read as lakh without the conversion every figure would publish at 100 times "
            "its value. be_thousand is the state's own figure, kept beside it so the "
            "conversion can be checked by eye. Both are the Budget Estimate 2026-27 "
            "Total, the last of twelve money columns; the Voted and Charged split and the "
            "Actuals 2024-25, Budget Estimates 2025-26 and Revised Estimates 2025-26 "
            "blocks are printed beside it and are not published here."),
        "variant": "Budget Estimate 2026-27",
        "variant_note": (
            "One edition per cycle. Volume 5 is split into four parts by grant number and "
            "all four are read; a missing part is whole departments silently absent, so "
            "the parser refuses to run without them. The Gender Budget is archived beside "
            "them and is NOT read: it restates the same estimates in a denser layout that "
            "puts the money, the code and the name on one line, and read with this reader "
            "it reconciled 209 of its 1,782 printed totals against 82 per cent for Volume "
            "5. A book that will not reconcile is a book this register does not publish "
            "figures from."),
        "schemes": len(out),
        "counts": {
            "schemes": len(out),
            "with_an_english_name": len(named),
            "with_a_positive_be": sum(1 for e in out if e["be_lakh"] > 0),
            "with_a_reconciled_total": sum(1 for e in out if e["total_reconciled"]),
            "account_tree_nodes_published_as_schemes": nodes_seen,
            "distinct_codes": len(out),
            "grants_read": len(grants_all),
            "per_book": per_book,
        },
        "reconciliation": {
            "printed_totals": {
                "checked": len(all_checks), "failed": len(failed),
                "failures": failed[:25] or None,
                "what": ("every printed योग/Total against the subtree of rows read "
                         "beneath it, in the Budget Estimate 2026-27 Total column"),
                "read_this_carefully": (
                    "3,686 of 4,492 reconcile, 82 per cent, and that is the weakest "
                    "reconciliation in this register. It is NOT a statement about the "
                    "figures published here: be_lakh is the number the book itself prints "
                    "on that node's own Total line, read directly, and total_reconciled "
                    "says per row whether the rows beneath it were also read correctly. "
                    "What the 806 failures mean is that Volume 5 has more page layouts "
                    "than this reader knows: a section whose figures share a line with "
                    "the code and the name, a node stated with two codes at once, and a "
                    "handful of totals whose code is not open when they arrive. Use the "
                    "names freely; use the money on a row whose total_reconciled is "
                    "false only with the book open beside it."),
            },
            "units": {
                "checked": len(unit_checks), "failed": len(unit_failed),
                "failures": unit_failed[:20] or None,
                "checks": unit_checks,
                "what": ("each grant's cover page, which prints its Revenue and Capital "
                         "provision in full rupees, against the detail pages' own totals "
                         "in thousands times 1,000")},
            "state_scheme_code_index": code_check,
            "cycles_seen_in_page_headers": sorted(cycles_all),
        },
        # The join against myScheme, run once by hand on the 2026-09-03 snapshot and all
        # 196 joins read line by line. Recorded here rather than recomputed on every run
        # because the classification is a human reading, not a rule. parse/match.py is NOT
        # edited to fix anything found; the defects are reported against it.
        "myscheme_join_summary": {
            "myscheme_uttarakhand_records": 446,
            "register_names": 2302,
            "joins_produced": 196,
            "joins_sound_on_inspection": 115,
            "joins_wrong_on_inspection": 81,
            "myscheme_records_with_any_join": 67,
            "how": ("indexed on match.tokens, match.skeleton and match.acronyms, then "
                    "match.probably_same on every candidate pair, then every join read by "
                    "eye"),
            "read_this_carefully": (
                "Uttarakhand is the second largest state list on myScheme, 446 records "
                "for a state of ten million, and this join says something about how that "
                "number is built. Nine of the 446 are services of one institution: "
                "'Aromatic Awareness Programme - Centre for Aromatic Plants', 'Quality "
                "Test Report - Centre for Aromatic Plants', 'Registration of Aromatic "
                "Plant Farmers - Centre for Aromatic Plants' and six more, all of them "
                "one budget head. Eighteen more are PMMSY and National Livestock Mission "
                "components stated once in the budget. Only 67 of the 446 join at all, "
                "against a register of 2,302 names, and 81 of the 196 joins are wrong."),
        },
        "myscheme_join_defects": [
            {"defect": ("A MINISTRY NAME READ AS A SCHEME ACRONYM. AYUSH is the ministry; "
                        "every myScheme scheme with AYUSH in its title matched every "
                        "budget line of the National AYUSH Mission, and the budget states "
                        "that mission eight times across grants"),
             "reason_string": "acronym match: ayush",
             "joins": 24,
             "wrong": 16,
             "example_myscheme": ("Healthy Lifestyle for School Children through "
                                  "Ayurvidya"),
             "example_budget": "Establishment of National AYUSH Mission",
             "note": ("the largest single hole found in this round. NOT_ACRONYMS holds "
                      "health and it does not hold ayush, and a ministry name behaves "
                      "exactly like a sector word: it says the domain and not the "
                      "scheme.")},
            {"defect": ("A LENDER READ AS A SCHEME. NABARD funds twenty-three separate "
                        "heads in this budget, from 'Redemeption of NABARD Loan' to "
                        "'Water Supply Grant for NABARD Funded Schemes', and one myScheme "
                        "record matched all of them"),
             "reason_string": "acronym match: nabard",
             "joins": 23,
             "wrong": 22,
             "example_myscheme": ("Construction of NABARD-Funded Minor Irrigation "
                                  "Projects"),
             "example_budget": "Redemeption of NABARD Loan",
             "note": ("one of the twenty-three, 'NABARD Aided minor irrigation scheme', "
                      "is the right answer, and it is indistinguishable from the other "
                      "twenty-two by anything the matcher looks at.")},
            {"defect": ("A DERIVED INITIALISM CONTAINING A REAL ACRONYM, AND THE WORD IT "
                        "ADDS IS THE ONE THAT MATTERS. Mukhyamantri Rajya Krishi Vikas "
                        "Yojana derives mrkvy, which contains the written rkvy of "
                        "Rashtriya Krishi Vikas Yojana. A state scheme and a central one "
                        "with the same three last words"),
             "reason_string": "acronym containment: mrkvy / rkvy",
             "joins": 17,
             "wrong": 17,
             "example_myscheme": "Mukhyamantri Rajya Krishi Vikas Yojana",
             "example_budget": "Rastriya Krishi Vikas Yojana (Rainfed Area Development)",
             "note": ("this register exists to tell state schemes from central ones, and "
                      "Mukhyamantri against Pradhan Mantri or Rashtriya is exactly that "
                      "distinction. The containment rule erases it.")},
            {"defect": "the same hole, and the sharpest instance of it",
             "reason_string": "acronym containment: mmsy / pmmsy",
             "joins": 7,
             "wrong": 7,
             "example_myscheme": "Mukhyamantri Matsya Sampada Yojana",
             "example_budget": "Pradhan Mantri Matsya Sampada Yojana (PMMSY) 90% CS",
             "note": ("mmsy is a substring of pmmsy, and the p it drops is the whole "
                      "difference between the state's fisheries scheme and the Union's.")},
            {"defect": ("AN AGENCY NAME. ITDA is the Information Technology Development "
                        "Agency; three myScheme entries name it as their implementing "
                        "body and matched both budget rows that mention it"),
             "reason_string": "acronym containment: dp2itda / itda",
             "joins": 6,
             "wrong": 6,
             "example_myscheme": ("Drone Policy 2023 - Information Technology Development "
                                  "Agency"),
             "example_budget": ("Strengthening of Information Technology / ITDA grant in "
                                "the state")},
            {"defect": ("an acronym this parser's own name concatenation put into the "
                        "budget side. Uttarakhand's Volume 5 prints an object head named "
                        "'Ex. UPNL Personnel Equal Work Pay' under many schemes, and "
                        "where the account tree was read imperfectly that suffix was "
                        "joined onto the scheme's own name"),
             "reason_string": "acronym containment: upnl / upnl",
             "joins": 6,
             "wrong": 6,
             "example_myscheme": ("Payment of Ex-Gratia Amount on Death of the UPNL "
                                  "Employee"),
             "example_budget": "DBT Cell Ex. UPNL Personnel Equal Work Pay",
             "note": ("HALF THIS ONE IS THIS FILE'S FAULT, not the matcher's. It is the "
                      "visible cost of the 18 per cent of printed totals that do not "
                      "reconcile: where the tree breaks, a name picks up the object head "
                      "below it. Rows carrying a name like this have total_reconciled "
                      "false.")},
            {"defect": ("a generic head absorbing a specific scheme, four separate "
                        "instances of the same shape"),
             "reason_string": "all 2 content words of the shorter name are present",
             "joins": 4,
             "wrong": 4,
             "example_myscheme": "District Plan - Sugarcane Development Scheme",
             "example_budget": "District Plan",
             "note": ("the other three are 'Family Pension Scheme (UKBOCWWB)' against a "
                      "'Family pension' head, 'Entrepreneurship and Development "
                      "Programme' against 'Employment Generation and Entrepreneurship "
                      "Development', and 'Skill Development' against 'Youth Skill "
                      "Development and Resource Development'.")},
            {"defect": ("MGNREGA matched on its own acronym, from a myScheme record that "
                        "names it only as the funding route for something else"),
             "reason_string": "acronym match: mgnrega",
             "joins": 1,
             "wrong": 1,
             "example_myscheme": ("Cultivation of Aromatic Plants under MGNREGA - Centre "
                                  "for Aromatic Plants"),
             "example_budget": ("Mahatma Gandhi National Rural Employment Guarantee "
                                "Act")},
            {"defect": "MSME read as a scheme rather than a sector",
             "reason_string": "acronym containment: msme / msme",
             "joins": 1,
             "wrong": 1,
             "example_myscheme": ("Incentives by MSME Department for Setting Up of "
                                  "Aromatic Plant Units"),
             "example_budget": "MSME Infrastructure Development"},
        ],
        "caveat": (
            "One row here is one node of Uttarakhand's own account tree that the book "
            "prints a total for and that sits below a minor head, keyed on the 13-digit "
            "scheme code the state's own Volume 5 front matter uses. That is a superset "
            "of the schemes a citizen can apply to: establishment heads such as "
            "'Establishment of Departmental Accounts' sit at the same level as 'Grant "
            "for rainwater harvesting'. Items of expenditure below it (Pay, Dearness "
            "Allowance, Office Expenses) are excluded, and the test is the document's "
            "own: the book prints a total for a level with children and never for an "
            "item of expenditure. Names are Uttarakhand's own English, printed under the "
            "Hindi on every line. be_lakh is the figure the book prints on that node's "
            "own Total line; total_reconciled says whether the rows beneath it add up to "
            "it, and 82 per cent of them do. See reconciliation.printed_totals."),
        "entries": out,
    })
    return (out, all_checks, failed, unit_checks, unit_failed, code_check, per_book,
            cycles_all, date)


def main():
    ap = argparse.ArgumentParser(
        description="Parse the archived Uttarakhand Volume 5 and Gender Budget.")
    ap.add_argument("--date")
    a = ap.parse_args()
    (out, checks, failed, unit_checks, unit_failed, code_check, per_book, cycles,
     date) = run(a.date)
    print(f"uttarakhand snapshot {date}")
    print(f"  {len(out)} scheme codes, "
          f"{sum(1 for e in out if e['name'])} with an English name")
    print(f"     sum of 2026-27 provisions "
          f"{sum(e['be_lakh'] for e in out):>18,.2f} lakh")
    print(f"  printed totals  {len(checks) - len(failed):>6} of {len(checks):<6} "
          f"reconcile")
    for b, d in sorted(per_book.items()):
        print(f"     {b:<20} {d['reconciled']:>5} of {d['printed_totals']:<5} "
              f"over {d['pages']:>4} pages, {d['schemes']:>5} scheme nodes")
    print(f"     of which on a row this file publishes "
          f"{sum(1 for e in out if e['total_reconciled']):>6} of {len(out)}")
    print(f"  units check     {len(unit_checks) - len(unit_failed):>6} of "
          f"{len(unit_checks):<6} agree, grant cover in rupees against detail in "
          f"thousands")
    print(f"  state code index {code_check['also_built_from_the_account_tree']:>5} of "
          f"{code_check['codes_in_the_state_index']:<5} of the state's own scheme codes "
          f"were rebuilt from the account tree")
    print(f"  cycles in headers {sorted(cycles)}")
    for f in (unit_failed + failed)[:10]:
        print("     MISMATCH", json.dumps(f)[:220])
    # The hard error is the UNIT, not the tree. A unit read wrongly makes every figure in
    # the file wrong by a factor of a thousand and cannot be seen by a reader; an
    # unresolved total is visible per row in total_reconciled and is reported in full.
    if unit_failed:
        print("  ERROR: a grant's cover page in rupees does not agree with its detail "
              "pages in thousands; the unit is wrong somewhere")
        raise SystemExit(1)
    if len(checks) - len(failed) < 3000:
        print("  ERROR: fewer printed totals reconcile than the 3,686 measured on the "
              "2026-27 books; something has regressed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
