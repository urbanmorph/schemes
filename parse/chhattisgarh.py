"""
Chhattisgarh's Outcome, Gender, Youth and Child budgets: one row per scheme.

AGENT-EDITABLE (PLAN.md 7). Reads archive/ only. Never fetches.

    archive/chhattisgarh/<date>/<kind>-<NN>.pdf.gz   the bytes
    data/chhattisgarh/schemes.json                   one row per scheme

WHAT THIS READS AND WHAT IT LEAVES. Chhattisgarh's 44 department scheme books hold 2,562
rows and set every name in Chanakya, a legacy font whose encoding cannot be recovered from
the PDF. This reads the other books, the ones 33 departments publish in KRUTI DEV, whose
table is fixed and checked in parse/krutidev.py against the state's own Unicode index. The
state page says so: the number here will grow the day parse/chanakya_derive.py converges,
and it will grow because this register learned to read something, not because Chhattisgarh
started funding it.

TWO THINGS ABOUT THE GEOMETRY, both of which returned zero rows before they were found.

  THE PAGES ARE ROTATED 90 DEGREES. They are landscape, and a printed row runs down the x
  axis rather than across y. PyMuPDF reports unrotated coordinates whatever the page says,
  so every scheme name on a page lands in one band with no provision beside it unless the
  axes are swapped.

  A LONG NAME WRAPS onto the following bands, which carry the name column and no figure.
  The first line shares a band with the provision; continuations have to be joined back or
  every long name is cut at its first line.

The columns are found from the header row rather than hard-coded, because the six columns
sit at different offsets in different departments' books.
"""

import argparse
import collections
import glob
import gzip
import io
import json
import os
import re
import sys

import fitz

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from krutidev import decode  # noqa: E402

KIND = {"outcome": "Outcome Budget", "gender": "Gender Budget",
        "youth": "Youth Budget", "child": "Child Budget"}


def bands_of(doc, tol=5.0):
    """Spans grouped into printed rows, with the across-row position and the font."""
    out = []
    for pno, p in enumerate(doc):
        rot = p.rotation in (90, 270)
        bands = {}
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    if not s["text"].strip():
                        continue
                    row = s["bbox"][0] if rot else s["bbox"][3]
                    col = s["bbox"][3] if rot else s["bbox"][0]
                    key = next((k for k in bands if abs(k - row) <= tol), None)
                    if key is None:
                        key = row
                        bands[key] = []
                    bands[key].append((col, s["font"], s["text"]))
        for y in sorted(bands):
            out.append((pno, y, sorted(bands[y])))
    return out


def read_book(raw, kind, dep):
    """One book's schemes: (name, objective, provision in thousands)."""
    doc = fitz.open(stream=raw, filetype="pdf")
    bands = bands_of(doc)
    # TWO HEADER LAYOUTS. The Outcome books head the name column "yojana@karyakram ka
    # naam"; the Gender, Youth and Child books head it "yojana ka naam". Matching only the
    # first read the Outcome books and returned nothing at all from the other three, which
    # is three quarters of the documents.
    name_col = amt_col = obj_col = code_col = None
    dept = None
    for pno, y, spans in bands:
        for x, f, t in spans:
            tt = t.strip()
            if name_col is None and (";kstuk@dk;Z" in tt or tt.startswith(";kstuk dk uke")):
                name_col = x
            elif amt_col is None and tt.startswith("ctV izko/kku"):
                amt_col = x
            elif obj_col is None and "mn~ns" in tt:
                obj_col = x
            # The Gender, Youth and Child books print the state's OWN scheme code beside
            # each name. The Outcome books do not, which is why this is optional.
            elif code_col is None and tt.rstrip(" ") == "dksM":
                code_col = x
        # The department's NAME and the word "vibhag-" that labels it are separate spans in
        # the same band, not one string. A regex over the label found the name in only nine
        # of the seventy-six books and the rest fell back to a number.
        if dept is None:
            for x, f, t in spans:
                # Sometimes the label and the name are ONE span, sometimes two. The Child
                # books use the first shape and the Outcome books the second, and reading
                # only the second left a third of the documents filed under a number.
                m = re.search(r"foHkkx&\s*(\S.+)", t)
                if m:
                    dept = decode(m.group(1).strip())
                    # "shram vibhag vibhag": the label is sometimes repeated at the end of
                    # the captured span. One trailing duplicate, collapsed.
                    dept = re.sub(r"(\S+)\s+\1$", r"\1", dept)
                    break
            else:
                lab = [x for x, f, t in spans if t.strip().startswith("foHkkx&")]
                if lab:
                    near = [(x, t) for x, f, t in spans if x < lab[0]]
                    if near:
                        dept = decode(max(near)[1].strip())
    if not (name_col and amt_col):
        return [], dept

    # NEAREST COLUMN, not a fixed tolerance around the header. The Gender books print a
    # data cell up to 38 points off the header that labels it, because the header is
    # centred over a column the data is left-aligned in, and a tolerance wide enough for
    # that in one book swallows the neighbouring column in another. Assigning each span to
    # whichever header it is closest to has no such tuning.
    heads = [c for c in (name_col, amt_col, obj_col, code_col) if c is not None]

    def which(x):
        return min(heads, key=lambda h: abs(h - x))

    got, cur, page = [], None, None
    for pno, y, spans in bands:
        # A row never continues across a page. The first bands of a new page carry the
        # department header, and appending those to whatever row was open produced names
        # like "(16) Shyam Ghunghutta Water Resources Department vibhag- Chief Engineer".
        if page is not None and pno != page and cur:
            got.append(cur)
            cur = None
        page = pno
        if any("foHkkx" in t for x, f, t in spans):
            if cur:
                got.append(cur)
                cur = None
            continue
        name, obj, amt, code = [], [], None, None
        for x, f, t in spans:
            t = t.strip()
            h = which(x)
            if h == amt_col and re.fullmatch(r"[\d,]+", t):
                if amt is None:
                    amt = t
            elif code_col is not None and h == code_col and re.fullmatch(r"\d{2,6}", t):
                code = t
            elif (h == name_col and abs(x - name_col) <= 45
                    and not re.fullmatch(r"[\d,.\-\u0964 ]*", t)):
                # Nearest-column is right for a first line and too generous for a
                # continuation: in the agriculture books a wrapped OBJECTIVE line is nearer
                # the name column than to its own, and 19 names came out as a sentence of
                # someone else's prose. A hard window on top of nearest fixes those without
                # touching the books where the offset is real.
                name.append(t)
            elif obj_col is not None and h == obj_col and not re.fullmatch(r"[\d,.\- ]*", t):
                obj.append(t)
        if name and amt:
            if cur:
                got.append(cur)
            cur = [" ".join(name).strip(), " ".join(obj).strip(),
                   amt.replace(",", ""), code]
        elif cur and name and not amt:
            cur[0] += " " + " ".join(name).strip()
            if obj:
                cur[1] += " " + " ".join(obj).strip()
        elif cur and obj and not name and not amt:
            cur[1] += " " + " ".join(obj).strip()
    if cur:
        got.append(cur)
    return got, dept


def run(date=None):
    root = os.path.join(ROOT, "archive", "chhattisgarh")
    dates = sorted(os.listdir(root)) if os.path.isdir(root) else []
    date = date if date in dates else (dates[-1] if dates else None)
    if not date:
        raise SystemExit("no archive at archive/chhattisgarh/")
    man = json.load(open(os.path.join(root, date, "_manifest.json"), encoding="utf-8"))

    entries, by_kind, depts = [], collections.Counter(), {}
    seen = set()
    for f in sorted(glob.glob(os.path.join(root, date, "*.pdf.gz"))):
        base = os.path.basename(f)[:-7]
        kind, dep = base.split("-", 1)
        with gzip.open(f, "rb") as fh:
            raw = fh.read()
        rows, dept = read_book(raw, kind, dep)
        if dept:
            depts[dep] = dept
        for name_kd, obj_kd, amt, code in rows:
            name = decode(name_kd).strip()
            if not name or len(name) < 3:
                continue
            key = f"{dep}|{kind}|{code or name}"
            if key in seen:
                continue
            seen.add(key)
            by_kind[kind] += 1
            entries.append({
                "key": key, "code": code, "name": name,
                "name_kruti_dev": name_kd,
                "objective": decode(obj_kd).strip() or None,
                "department": depts.get(dep) or f"Department {dep}",
                "department_no": dep,
                "book": KIND.get(kind, kind),
                # The books print thousands of rupees; be_lakh is the register's unit.
                "be_lakh": round(int(amt) / 100.0, 2) if amt.isdigit() else None,
            })

    write_json("data/chhattisgarh/schemes.json", {
        "built": utcnow(), "snapshot": date, "state": "Chhattisgarh",
        "cycle": man.get("cycle"), "source": man.get("source"),
        "caveat": ("One row is one scheme as Chhattisgarh's Outcome, Gender, Youth or Child "
                   "budget names it, with the objective and the provision the state prints "
                   "beside it. These are NOT all of Chhattisgarh's schemes. Its 44 "
                   "department scheme books name 2,562 more and set every name in the "
                   "Chanakya legacy font, whose encoding cannot be recovered from the PDF, "
                   "so this register cannot read them and will not publish names it cannot "
                   "read. The names here are in Kruti Dev, whose table is fixed and checked "
                   "against the state's own Unicode department index."),
        "books": dict(by_kind), "departments": len(depts),
        "documents_read": len(glob.glob(os.path.join(root, date, "*.pdf.gz"))),
        "entries": entries,
    })
    return entries, by_kind, depts


def main():
    ap = argparse.ArgumentParser(description="Parse Chhattisgarh's outcome budget books.")
    ap.add_argument("--date")
    a = ap.parse_args()
    e, by_kind, depts = run(a.date)
    print(f"chhattisgarh: {len(e):,} scheme rows from {len(depts)} departments")
    for k, n in sorted(by_kind.items()):
        print(f"    {KIND.get(k, k):<16} {n:>5}")
    money = sum(x["be_lakh"] or 0 for x in e)
    print(f"    provision together   Rs {money/100:,.0f} crore")


if __name__ == "__main__":
    main()
