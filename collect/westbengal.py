"""
West Bengal state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

Why West Bengal: 109 schemes on myScheme for a state of 100 million. The Detailed Demands
for Grants name far more, in English, with a head of account against every one.

WHERE IT IS. Not where the obvious guess puts it. wbfin.wb.gov.in does not resolve
(NXDOMAIN), and wbfin.nic.in and www.wbfin.gov.in both resolve to 164.100.233.151 and
time out. The live host is finance.wb.gov.in and the page is

    https://finance.wb.gov.in/Fin_New/Pages/Budget_Publication.aspx

which is ASP.NET WebForms whose FINANCIAL YEAR selector is a __doPostBack. That does not
have to be fought: a plain GET renders the current year, 2026-2027, with ordinary static
hrefs, and only earlier years need the postback. Filenames cannot be constructed across
years either, because the BP numbering shifts: 2024_bp30.pdf exists and 2023_bp30.pdf and
2025_bp30.pdf are 404. So the index is read, never guessed, and archived every run.

WHAT IS COLLECTED. BP-11 to BP-26, the sixteen Detailed Demands for Grants volumes, which
between them cover every demand of the state. Each prints, under a head of account, one
row per SUB-HEAD, which is West Bengal's scheme-level unit, then the object heads beneath
it and a printed Total line carrying the full head of account:

    012- Paray Samadhan in Rural Areas [PS]
     27- Minor Works/ Maintenance          ...   35,00,000   1,75,000   35,00,000
                     Total - 2515-00-001-012 ...  35,00,000   1,75,000   35,00,000

BP-1, BP-3 to BP-10 and BP-25 are summaries, receipts and guarantee statements and are
not collected.

WHAT IS NOT COLLECTED, AND THIS ONE MATTERS. BP-30, the Gender and Child Budget, is the
best-shaped document West Bengal publishes and it CANNOT BE READ BY A MACHINE. Measured
2026-09-02 on 2026_bp30.pdf, 46,485,276 bytes, 65 pages: `pdftotext -layout` over the
whole file returns 65 characters, one form feed per page and nothing else; `pdffonts`
returns no rows at all; `pdfimages -list` shows a 300 dpi JPEG per page. It is a scan.
The same is true of BP-31, the SDG Budget, 29,770,590 bytes, 57 pages, 57 characters.
Rendering page 46 of BP-30 shows exactly the table this register wants, department-grouped,
one row per scheme, four years in Rs crore, with rows like "Scheme for power subsidy under
Hasir Alo 846.80 / 771.75 / 970.97 / 816.75". None of it is text. They are not archived
because 76 MB of images is not evidence anyone can act on, and the measurement above is
reproducible from the URLs recorded in SKIPPED.

    archive/westbengal/D/index.html.gz   the publication page, so discovery is auditable
    archive/westbengal/D/<book>.pdf.gz   raw bytes, byte-identical to what was served
    archive/westbengal/D/_manifest.json
"""

import argparse
import collections
import gzip
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

INDEX = "https://finance.wb.gov.in/Fin_New/Pages/Budget_Publication.aspx"

# The Detailed Demands for Grants volumes. The range is stated rather than discovered
# because "which BP numbers are the detailed demands" is a fact about the publication and
# not about this year's page: BP-1 to BP-10 are the Civil Budget Estimate, receipts,
# guarantees, public accounts and the Key to Budget Documents, BP-25 is a supplement on
# transfers to local bodies, and BP-27 to BP-31 are the analytical statements.
DDG_FIRST, DDG_LAST = 11, 26

BP = re.compile(r"/(\d{4})_bp-?(\d{1,2})(?:-[\w\.]+)?\.pdf$", re.I)

SKIPPED = {
    "BP-30 Gender & Child Budget": (
        "https://finance.wb.gov.in/writereaddata/Budget_Publication/2026_bp30.pdf , "
        "46,485,276 bytes, 65 pages, and a pure scan: pdftotext returns 65 characters "
        "over the whole file, one per page; pdffonts returns no rows; pdfimages shows a "
        "300 dpi JPEG per page. It is the best-shaped scheme table the state publishes "
        "and it is unreadable without OCR"),
    "BP-31 SDG Budget": (
        "https://finance.wb.gov.in/writereaddata/Budget_Publication/2026_bp31.pdf , "
        "29,770,590 bytes, 57 pages, 57 characters of text. Also a scan, and "
        "department-wise rather than scheme-wise, so it is not a substitute for BP-30"),
    "BP-1 to BP-10": (
        "Civil Budget Estimate, Departmental Expenditure summary, Revenue and Receipts, "
        "Public Account, Guarantee Statement, PSU financial results, Budget at a Glance "
        "and the Key to Budget Documents. No scheme-level rows"),
    "BP-25": "a supplement on transfers to rural and urban local bodies, not scheme-wise",
    "Budget Speech, FRBM": "prose and fiscal policy",
    "Earlier financial years": (
        "the year selector is a __doPostBack and is not driven. This register collects "
        "one cycle per year, so an earlier year is a separate decision, not a default"),
}


def discover(index_url, pace):
    """Read the publication page. Returns (bytes, books, n_pdfs, cycles, err)."""
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, 0, [], f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    urls = sorted({urllib.parse.urljoin(index_url, html.unescape(h).strip())
                   for h in re.findall(r'href="([^"]+\.pdf[^"]*)"', body, re.I)})

    books, years = {}, collections.Counter()
    for u in urls:
        m = BP.search(urllib.parse.unquote(u))
        if not m:
            continue
        year, n = m.group(1), int(m.group(2))
        years[year] += 1
        if DDG_FIRST <= n <= DDG_LAST:
            books[f"bp-{n:02d}"] = {
                "url": u, "bp": n, "file_year": year,
                "what": f"Budget Publication {n}, Detailed Demands for Grants"}
    return r.body, books, len(urls), sorted(years), None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "westbengal", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "westbengal", "started": utcnow(), "base": index_url,
           "books": {}, "errors": [], "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, wanted, n_pdfs, years, err = discover(index_url, pace)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/westbengal/{date}/_manifest.json", man)
        return man

    # The year is READ off the filenames the page serves, never constructed. A page that
    # served two years' files at once would be a half-updated index and is worth failing
    # on rather than mixing two years' figures into one register.
    man["file_years"] = years
    man["cycle"] = None
    if len(years) == 1:
        y = int(years[0])
        man["cycle"] = f"{y}-{y + 1}"
    else:
        man["errors"].append({"stage": "cycle",
                              "why": f"the index serves {len(years)} file years: {years}"})
    man["books_expected"] = sorted(wanted)
    missing = [f"bp-{n:02d}" for n in range(DDG_FIRST, DDG_LAST + 1)
               if f"bp-{n:02d}" not in wanted]
    if missing:
        man["errors"].append({"stage": "index",
                              "why": "no link found for " + ", ".join(missing)})

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        r = fetch(meta["url"], timeout=300, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        if not r.body.startswith(b"%PDF"):
            man["errors"].append({"stage": book,
                                  "why": f"response is not a PDF ({len(r.body)} bytes)"})
            continue
        bad = looks_like_error(r.body[:4096])
        if bad:
            man["errors"].append({"stage": book, "why": str(bad)})
            continue
        with gzip.open(os.path.join(out_dir, f"{book}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["books"][book] = dict(meta, bytes=len(r.body), sha256=r.sha256)

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/westbengal/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the West Bengal Detailed Demands for Grants volumes.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"westbengal {man.get('cycle')}: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} volumes archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for name, why in sorted(SKIPPED.items()):
        print(f"    skipped {name}: {why[:100]}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
