"""
Extract Karnataka's scheme-wise budget books into a named scheme list.

AGENT-EDITABLE (PLAN.md §7). Reads archive/karnataka/, writes data/karnataka/. Never
fetches. Replayable against any archived date.

    data/karnataka/schemes.json    one row per head of account

What a row is. Karnataka's books are keyed by head of account,
`2401-00-102-0-27`, whose last field is the scheme code within a minor head. That code is
the state's own identifier for the scheme and is far more stable than the name, which is
retyped by every office that touches it. It is the join key here, and the reason the same
scheme appearing in both the Gender and Child books collapses to one row rather than two.

Three things the layout does that a naive reader gets wrong:

The name wraps. "CSS-Central Share-Training of Anganwadi Workers &" ends a line and
"Helpers / <Kannada>" begins the next, so a parser that reads the line containing the
slash records a scheme called "Helpers". 41 of 901 rows came out that way. Lines are
accumulated up to and including the slash instead.

The Kannada is not Unicode. These PDFs use a legacy font, so Kannada extracts as
Latin-range byte soup, and a plain is-this-ASCII test passes it. Latin Extended letters
are the tell: no English scheme name contains Ŵ or ĸ.

Every scheme carries a purpose line. "Free travel to all women (including girl students)
and transgenders in State Road Transport Corporation buses." That single sentence is
better than what myScheme publishes for many schemes it does list, and it is the reason
this is worth parsing rather than just counting.
"""

import argparse
import gzip
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import utcnow, write_json  # noqa: E402
from pdf import layout_text as pdftotext, require_books, snapshot  # noqa: E402
from text import joined  # noqa: E402

HOA = re.compile(r"^(\d{4}-\d{2}-\d{3}-\d-\d{2})$")
# An amounts row: two or more money-shaped tokens, where "......" is how these books
# print a nil provision. A figure can be negative: the Gender Budget prints -0.01 for
# 2851-00-107-1-48's 2024-25 actuals, and without the sign that amounts line was read as
# the start of the scheme's name ("0.01 0.00 0.00 0.00 New Initiatives for ...") and its
# provision as missing. The Gender Budget's BY Grand Total is short by exactly that 0.01.
FIG = r"-?[\d,]+\.\d{2}"
AMTS = re.compile(rf"^\s*(?:{FIG}|\.{{3,}}|-)(?:\s+(?:{FIG}|\.{{3,}}|-)){{1,}}\s*$")
MONEY = re.compile(rf"{FIG}|\.{{4,}}")
# Every table page prints "(₹ in Lakhs)", and no page of the three books names any other
# unit. Checked per page that carries a head of account, not assumed.
UNIT = re.compile(r"in\s+Lakh", re.I)
OTHER_UNIT = re.compile(r"in\s+(?:Crore|Thousand|Rupees|Million)\b", re.I)
# A printed total with its figures on its own line: "Transport Total  561501.65 ...",
# "AY - Grand Total ...", and in SCSP/TSP "<Kannada> / Total  BC Welfare  17953.70 ...".
TOTAL = re.compile(rf"^(?P<label>.*?\bTotal\b.*?)\s+(?P<figs>(?:{FIG}\s+)+{FIG})\s*$")
# A total whose label wraps: the department's name with the figures, then "Total" or
# "Department Total" alone on the next line (Gender Budget, Department of Personnel and
# Administrative Reforms, and every "Department Total" closing a part).
NAMED_FIGS = re.compile(rf"^(?P<label>.*[A-Za-z].*?)\s+(?P<figs>(?:{FIG}\s+){{3}}{FIG})\s*$")
TOTAL_ALONE = re.compile(r"(?:^|\s)Total$")
# Latin-1 supplement and Latin Extended-A/B. Present in the legacy-font Kannada, absent
# from any English scheme name.
LEGACY = re.compile(r"[À-ɏ]")
CTRL = re.compile(r"[\x00-\x08\x0b-\x1f]")
BOOK_LABEL = {"GB": "Gender Budget", "CB": "Child Budget",
              "SCSPTSP": "SCSP/TSP Allocations"}




def is_english(s):
    return bool(s) and not LEGACY.search(s) and not CTRL.search(s)


def clean(s):
    return re.sub(r"\s+", " ", CTRL.sub(" ", LEGACY.sub("", s))).strip(" .,-/")


def amounts(line):
    out = []
    for tok in MONEY.findall(line):
        out.append(None if tok.startswith("..") else float(tok.replace(",", "")))
    return out


def next_text(lines, i):
    """The next non-blank line after i, stripped, and its index."""
    for j in range(i + 1, min(i + 4, len(lines))):
        if lines[j].strip():
            return j, lines[j].strip()
    return None, ""


class Ledger:
    """Each book's own arithmetic, held against the rows this parser publishes.

    Every department block closes with a printed total of the four years (six columns in
    SCSP/TSP), and every part (AY, AN, BY, BN in the Gender Budget, HP, HNP, LP, LNP in the
    Child Budget) with a Grand Total. A row is added here only when it is published, so a
    row the reader drops or a figure it misreads shows up as a total that does not close.
    Grand Totals printed before any row (the department summary at the front of SCSP/TSP)
    are held against the whole book at the end."""

    def __init__(self, book, width):
        self.book, self.width, self.checks, self.early = book, width, [], []
        self.dept, self.part, self.whole = ([0.0] * width for _ in range(3))
        self.dept_rows = self.part_rows = self.rows = 0

    def row(self, amt):
        """A published row's figures. A row with fewer figures than the book prints adds
        zeros, so money the reader lost shows as a total that does not close."""
        if len(amt) > self.width:
            raise SystemExit(f"karnataka {self.book}: a row read {len(amt)} figures, "
                             f"the book prints {self.width}")
        v = [a or 0.0 for a in amt] + [0.0] * (self.width - len(amt))
        self.dept = [a + b for a, b in zip(self.dept, v)]
        self.part = [a + b for a, b in zip(self.part, v)]
        self.whole = [a + b for a, b in zip(self.whole, v)]
        self.dept_rows += 1
        self.part_rows += 1
        self.rows += 1

    def total(self, label, figs, page):
        printed = [0.0 if f is None else f for f in figs]
        label = re.sub(r"\s+", " ", clean(label))
        if "Grand Total" in label:
            if not self.rows:
                self.early.append((label, printed, page))
                return
            self._check(label, printed, self.part, self.part_rows, page, "part")
            self.part, self.part_rows = [0.0] * self.width, 0
        else:
            self._check(label, printed, self.dept, self.dept_rows, page, "department")
        self.dept, self.dept_rows = [0.0] * self.width, 0

    def _check(self, label, printed, got, n, page, scope):
        got = [round(x, 2) for x in got]
        self.checks.append({
            "book": self.book, "label": label[:80], "page": page, "scope": scope,
            "printed": printed, "parsed": got, "rows": n,
            "ok": len(got) == len(printed) and all(
                abs(a - b) < 0.005 for a, b in zip(printed, got))})

    def close(self):
        for label, printed, page in self.early:
            self._check(label, printed, self.whole, self.rows, page, "whole book")
        return self.checks


# SCSP/TSP prints the head of account and every figure on one line, and puts the Kannada
# name BEFORE the slash with the English after it — the opposite of the Gender and Child
# books. One parser trying to serve both read zero rows from it. The prefix is the sector,
# not the sub plan: ST is a state scheme and ZP a Zilla Panchayat one, whose district head
# of account follows in brackets on the next line. Every row prints SCSP and TSP side by
# side. Reading only ST lines (taken for "SC or ST") dropped all 63 ZP rows, Rs 10,15,015
# lakh of SCSP, which the book's own Grand Total showed at once.
SCSP = re.compile(r"^(ST|ZP)\s+(\d{4}-\d{2}-\d{3}-\d-\d{2})\s*(.*)$")
ZP_HEAD = re.compile(r"\(\d{4}-\d{2}-\d{3}-\d-\d{2}\)")
SCSP_TOTAL = re.compile(r"/\s*Total\b")


def parse_scsptsp(text, book):
    rows, ledger = [], Ledger(book, 6)
    for pno, page in enumerate(text.split("\f"), 1):
        lines = page.splitlines()
        check_unit(page, book, pno)
        for i, raw in enumerate(lines):
            t = TOTAL.match(raw.strip())
            if t and not SCSP.match(raw.strip()):
                ledger.total(t.group("label"), amounts(t.group("figs")), pno)
                continue
            if SCSP_TOTAL.search(raw) and not MONEY.search(raw):
                # "/ Total" with its figures alone on the line below.
                j, nxt = next_text(lines, i)
                if j is not None and AMTS.match(lines[j]):
                    ledger.total(raw, amounts(nxt), pno)
                continue
            m = SCSP.match(raw.strip())
            if not m:
                continue
            amt = amounts(m.group(3))
            name = scsp_name(lines, i, m.group(3))
            if len(name) < 5:
                continue
            ledger.row(amt)
            # The book prints, per head, its SCSP and its TSP allocation, each as Revenue,
            # Capital and Total. be_lakh is SCSP Total + TSP Total: the 2026-27 estimate this
            # book earmarks for the head, as the Gender and Child books' be_lakh is the
            # 2026-27 estimate they print. It used to be the first column, SCSP Revenue
            # alone, which left out every capital provision and the whole TSP.
            rows.append({"hoa": m.group(2), "name": name, "purpose": None,
                         "be_lakh": round(amt[2] + amt[5], 2) if len(amt) == 6 else None,
                         "scsp_lakh": amt[2] if len(amt) == 6 else None,
                         "tsp_lakh": amt[5] if len(amt) == 6 else None,
                         "book": book})
    return rows, ledger.close()


# The SCSP/TSP name cell. The Kannada name comes first and then a slash and the English;
# the Kannada extracts as stray fragments or nothing at all, so the English often sits
# several blank lines below the figures. A slash with no Latin letter before it on its
# line is that separator; a slash inside English ("Construction/Upgradation", "SC/ST")
# is part of the name. The next separator, row, total, department heading or page
# footer ends the name. Stopping at the first blank line instead dropped 175 of the 440
# rows, which the book's own totals showed at once.
SEPARATOR = re.compile(r"^[^A-Za-z]*/")
KANNADA = re.compile(r"[\u0C80-\u0CFF\u2013]")
NAME_STOP = re.compile(r"^\d{2}\s+[A-Za-z]|Budget\s+20\d\d|Outlay on|Department and Schemes")


def scsp_name(lines, i, rest):
    started = bool(SEPARATOR.match(rest))
    parts, before = [], []

    def add(seg, into):
        seg = re.sub(r"\s+", " ", KANNADA.sub(" ", MONEY.sub("", seg))).strip(" /")
        if clean(seg):
            into.append(seg)

    if started:
        add(rest.split("/", 1)[1], parts)
    for line in lines[i + 1:]:
        s = ZP_HEAD.sub("", line).strip()      # a ZP row's district head of account
        if not s:
            continue
        if SCSP.match(s) or AMTS.match(line) or SCSP_TOTAL.search(s) or TOTAL.match(s) \
                or NAME_STOP.search(s):
            break
        if SEPARATOR.match(s):
            if parts:
                break
            started, s = True, s.split("/", 1)[1]
        add(s, parts if started else before)
    return clean(joined(parts if started else before))


def check_unit(page, book, pno):
    """A page carrying a head of account must print the lakh unit and no other."""
    if not re.search(r"\d{4}-\d{2}-\d{3}-\d-\d{2}", page):
        return
    if not UNIT.search(page) or OTHER_UNIT.search(page):
        raise SystemExit(f"karnataka {book} page {pno}: a table page without '(₹ in Lakhs)' "
                         f"or naming another unit; every figure here is read as lakh")


def parse_book(text, book):
    """One row per head of account. Names are accumulated across wrapped lines."""
    rows, ledger = [], Ledger(book, 4)
    for pno, page in enumerate(text.split("\f"), 1):
        lines = page.splitlines()
        check_unit(page, book, pno)
        for i, raw in enumerate(lines):
            t = TOTAL.match(raw.strip())
            if t:
                ledger.total(t.group("label"), amounts(t.group("figs")), pno)
                continue
            t = NAMED_FIGS.match(raw.strip())
            if t:
                nxt = next_text(lines, i)[1]
                if TOTAL_ALONE.search(nxt):
                    ledger.total(t.group("label") + " " + nxt, amounts(t.group("figs")), pno)
                    continue
            m = HOA.match(raw.strip())
            if not m:
                continue
            amt, start = [], i + 1
            for j in range(i + 1, min(i + 3, len(lines))):
                if AMTS.match(lines[j]):
                    amt, start = amounts(lines[j]), j + 1
                    break
            # Name: everything before the first slash, accumulated over wrapped lines.
            name_parts, k, name = [], start, None
            while k < min(start + 6, len(lines)):
                s = lines[k].strip()
                if not s or AMTS.match(lines[k]) or HOA.match(s):
                    k += 1
                    continue
                if "/" in s:
                    head = s.split("/", 1)[0]
                    if clean(head) or name_parts:
                        name_parts.append(head)
                    name = clean(" ".join(name_parts))
                    k += 1
                    break
                if is_english(s):
                    name_parts.append(s)
                    k += 1
                    continue
                break
            if not name and name_parts:
                name = clean(" ".join(name_parts))
            if not name or len(name) < 5:
                continue
            # Purpose: the first fully English sentence after the name.
            desc = None
            for j in range(k, min(k + 7, len(lines))):
                s = lines[j].strip()
                if not s or AMTS.match(lines[j]):
                    continue
                # Stop rather than skip. A slash means the next scheme's name has started
                # and a Total line means the department block has ended, so anything past
                # either belongs to a different record. Skipping instead of stopping is
                # how "Subsidy for Supply of free Power to Irrigation Pumpsets" came to be
                # described as "Gruha Jyothi".
                if HOA.match(s) or re.search(r"\bTotal\s*:?\s*$|\bTotal\b\s+[\d,]", s):
                    break
                # A slash alone does not mean the next record: the Kannada continuation
                # lines carry them too. It is the next scheme's name only when there is
                # readable English in front of the slash.
                if "/" in s and len(clean(s.split("/", 1)[0])) > 3 \
                        and is_english(s.split("/", 1)[0]):
                    break
                if is_english(s) and len(s.split()) >= 4 and re.search(r"[a-z]{3}", s):
                    desc = re.sub(r"\s+", " ", s)
                    break
            ledger.row(amt)
            rows.append({"hoa": m.group(1), "name": name, "purpose": desc,
                         "be_lakh": amt[-1] if amt else None, "book": book})
    return rows, ledger.close()


def run(date=None):
    date, src, man = snapshot("karnataka", date)
    require_books(src, man)

    by_hoa, per_book, checks = {}, {}, []
    for book in sorted(BOOK_LABEL):
        p = os.path.join(src, f"{book}.pdf.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rb") as fh:
            text = pdftotext(fh.read())
        rows, chk = (parse_scsptsp if book == "SCSPTSP" else parse_book)(text, book)
        checks += chk
        per_book[book] = len(rows)
        for r in rows:
            # First book wins the name; later books only fill gaps. The allocation is
            # NOT summed across books: the Gender and Child books report overlapping
            # slices of the same provision, so adding them would double-count a scheme
            # that serves women and children both.
            cur = by_hoa.get(r["hoa"])
            if cur is None:
                r["books"] = [BOOK_LABEL[book]]
                by_hoa[r["hoa"]] = r
            else:
                if BOOK_LABEL[book] not in cur["books"]:
                    cur["books"].append(BOOK_LABEL[book])
                if not cur.get("purpose") and r.get("purpose"):
                    cur["purpose"] = r["purpose"]
                if cur.get("be_lakh") in (None, 0) and r.get("be_lakh"):
                    cur["be_lakh"] = r["be_lakh"]
    out = sorted(by_hoa.values(), key=lambda r: r["hoa"])
    for r in out:
        r.pop("book", None)
    bad = [c for c in checks if not c["ok"]]
    write_json("data/karnataka/schemes.json", {
        "snapshot": date,
        "built": utcnow(),
        "state": "Karnataka",
        "cycle": man.get("cycle"),
        "source": "Karnataka Budget, scheme-wise books (Gender, Child, SCSP/TSP)",
        "source_url": man.get("base"),
        "books": man.get("books", {}),
        "rows_per_book": per_book,
        "schemes": len(out),
        "with_allocation": sum(1 for r in out if r.get("be_lakh")),
        "with_purpose": sum(1 for r in out if r.get("purpose")),
        "caveat": ("These are the scheme-wise cuts of the state budget, so a scheme with "
                   "no women, child or SC/ST earmark does not appear. The number here is "
                   "a floor on Karnataka's schemes, never a total."),
        "unit": "lakh",
        "unit_note": ("Every page carrying a head of account prints '(₹ in Lakhs)' and no "
                      "page names another unit; the parser refuses a page that does not."),
        "reconciliation": {
            b: {"checked": sum(1 for c in checks if c["book"] == b),
                "failed": sum(1 for c in bad if c["book"] == b)} for b in sorted(per_book)},
        "reconciliation_what": (
            "every printed department Total and Grand Total (Gender: parts AY, AN, BY, BN; "
            "Child: HP, HNP, LP, LNP; SCSP/TSP: the whole book, printed twice) against the "
            "published rows beneath it, in every column the book prints"),
        "reconciliation_failures": bad or None,
        "entries": out,
    })
    return out, per_book, date, checks, bad


def selftest():
    """SCSP/TSP name reading against lines shaped like the 2026-27 book's."""
    page = "\n".join([
        "   Outlay on Scheduled Caste Sub Plan and Tribal Sub Plan 2026-27-BE   (₹   in Lakhs)",
        "ST 2401-00-001-1-75                     0.57    0.00    0.57    0.47    0.00    0.47",
        "", "",
        "                   /",
        "      Unspent SCSP-TSP Amount as per",
        "      the SCSP-TSPAct 2013",
        "ZP 2225-00-102-0-68                     0.00    0.00    0.00 3000.00    0.00 3000.00",
        "   (2225-02-197-1-01)",
        "                     1",
        "      8                 / Pre-",
        "      Matric Scholarship for ST Students",
        "ST 4210-01-110-1-01        /      /      0.00 4246.22 4246.22    0.00 1698.48 1698.48",
        "      Hospital Construction/Upgradation",
        "                   / Science & Technology Schemes",
        "ST 3451-00-090-2-01   / IT Policy       1004.50    0.00 1004.50  465.50    0.00  465.50",
        "", "",
        "   17                                  Budget 2026-27"])
    rows, _ = parse_scsptsp(page, "SCSPTSP")
    got = [(r["hoa"], r["name"], r["be_lakh"]) for r in rows]
    want = [("2401-00-001-1-75", "Unspent SCSP-TSP Amount as per the SCSP-TSPAct 2013", 1.04),
            ("2225-00-102-0-68", "Pre-Matric Scholarship for ST Students", 3000.0),
            ("4210-01-110-1-01", "Hospital Construction/Upgradation", 5944.7),
            ("3451-00-090-2-01", "IT Policy", 1470.0)]
    bad = got != want
    print(f"  {'FAIL' if bad else 'ok  '} SCSP/TSP names carry across blank lines, skip the "
          "Kannada and the ZP head, keep a slash inside English, stop at the next name")
    if bad:
        print(f"       got  {got}\n       want {want}")
    return bad


def main():
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(1 if selftest() else 0)
    ap = argparse.ArgumentParser(description="Parse the archived Karnataka budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    out, per_book, date, checks, bad = run(a.date)
    print(f"karnataka snapshot {date}")
    for b, n in sorted(per_book.items()):
        nb = sum(1 for c in checks if c["book"] == b)
        nf = sum(1 for c in bad if c["book"] == b)
        print(f"    {b:<9}{n:>6} rows   {nb - nf}/{nb} printed totals reconcile")
    print(f"  {len(out)} distinct schemes by head of account")
    print(f"     with an allocation {sum(1 for r in out if r.get('be_lakh')):>6}")
    print(f"     with a purpose     {sum(1 for r in out if r.get('purpose')):>6}")
    for c in bad[:10]:
        print(f"     MISMATCH {c['book']} p{c['page']} {c['label']!r}: printed "
              f"{c['printed']}, rows {c['parsed']}")
    if bad:
        print("  ERROR: the books do not reconcile against their own printed totals")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
