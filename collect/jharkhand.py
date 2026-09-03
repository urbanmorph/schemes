"""
Jharkhand state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

WHY JHARKHAND: DBT Bharat counts 156 schemes here against myScheme's 96. The state
answers that in 36 per-department Demand for Grants books whose every structural line is
printed as `<Hindi> / <English>` and whose every scheme carries an English banner line

    STATE SCHEME        MINORITY HOSTEL NUTRITION SCHEME(2073)

with the state's own 4-digit scheme code in brackets at the end. The bracket is the
terminator: a wrapped banner continues on the next line and the code closes it. That is
Karnataka's bilingual slash in a different costume, and it is the whole reason this state
parses.

The Devanagari in these books extracts damaged (matras and conjuncts drop, so
"स्थापना व्यय" comes out as "थापना यय"), which does not matter here because nothing is
read from it: the English half of every slash and the all-caps English banner carry the
names. Measured 2026-09-03 on the Welfare book: 2,577 slash lines, 323 object-head rows
each with a full 9-part bill code and exactly four money columns, 277 printed totals with
four columns each, and 102 of 108 pages carrying "In Lakhs of Rupees" with no page naming
any other unit.

WHAT IS TAKEN AND WHAT IS NOT. Only the 36 department books under the index heading
"Department wise details of demands for grants". They are large: 318 MiB for the set,
which is more than the whole rest of this archive put together, and there is no smaller
document that carries the same list. The two obvious candidates were measured and both
fail, which is recorded in SKIPPED below rather than left as an absence.

    archive/jharkhand/<date>/index.html.gz    the index page, so discovery is auditable
    archive/jharkhand/<date>/<book>.pdf.gz    raw bytes, byte-identical to what was served
    archive/jharkhand/<date>/_manifest.json
"""

import argparse
import gzip
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

INDEX = "https://finance.jharkhand.gov.in/budget2026.aspx"

# finance.jharkhand.gov.in serves an INCOMPLETE CERTIFICATE CHAIN, the same fault
# finance.karnataka.gov.in has and for the same reason: a leaf issued by "GlobalSign GCC
# R46 OV TLS CA 2025" with no intermediate attached. openssl reports "unable to verify
# the first certificate" and Python fails with "unable to get local issuer certificate",
# while browsers and curl paper over it by fetching the intermediate from the leaf's
# Authority Information Access extension, which Python does not do. Measured 2026-09-03:
# without this line every fetch here returns CONN in 0.18s.
#
# The missing link is carried, verification is NOT turned off, so this host is checked
# The certificate this host needs is registered in collect/common.py, beside the
# identical GlobalSign fault on finance.karnataka.gov.in.

# The index prints one <h1> per section and the department books sit between this heading
# and the next one. Taking the section rather than a filename pattern is deliberate: the
# Outcome Budget PDFs live under .../OutCome/ with department names that collide with the
# demand books (Health.pdf against Health_Medical_Education_and_Family_Welfare_Department
# .pdf), so a name-based rule would mix two different documents into one archive slot.
SECTION_START = "Department wise details of demands for grants"

# Everything else on the page, recorded rather than silently dropped. A document missing
# from the archive is otherwise indistinguishable from a collector that failed to find it.
SKIPPED = {
    "Gender Budget 2026-27, Child Budget 2026-27": (
        "both are SCANS. `pdftotext -layout` returns 34 characters from the 34-page "
        "Gender Budget and 26 from the 26-page Child Budget, one form feed per page; "
        "`pdffonts` returns no rows and `pdfimages` finds one 150 dpi JPEG per page. "
        "Measured 2026-09-03. They would have been the cheap way to do this state, 26 MB "
        "against 318 MB, and they cannot be read at all"),
    "Outcome Budget 2026-27, 13 departments": (
        "has a text layer and names schemes with their outcome indicators, but repeats "
        "the demand books' scheme list at another 300+ MB. Worth collecting the day the "
        "outcome indicators are wanted; not worth doubling this archive for names "
        "already carried"),
    "Annual Financial Statement, Demand for Grants, Revenue and Receipts, Public "
    "Accounts, Budget at a Glance, Budget Summary, Explanatory Memorandum": (
        "aggregate and receipts documents. The summary Demand for Grants is a 68-page "
        "one-line-per-demand abstract; the 36 department books carry the scheme rows"),
    "Budget Speech, Economic Survey, Fiscal Policy Strategy Statement, Action Taken "
    "Report": "prose",
    "1st Supplementary Book 2026-27": (
        "a supplementary demand voted after the main budget. Mixing it into the main "
        "estimates would publish a figure that is neither the BE nor the final grant. "
        "Tamil Nadu's original-against-revised trap in another form"),
    "All_Departments.zip": (
        "the same 36 books in one archive. Collected individually so that a single "
        "department that fails to serve leaves a hole you can see and date"),
}

# Text nodes and PDF hrefs in document order. On this page the <a> around the PDF icon
# has no text of its own and the department name sits in the anchor immediately AFTER it,
# so the label for a link is the first real text seen after it, not before it as on
# Odisha's page.
TOKEN = re.compile(r'(?:href="(pdf/[^"]+\.pdf)")|(?:>([^<>]{2,200})<)', re.I)


def labelled_pdfs(section_html, page_url):
    """[(absolute url, label)] for the PDF links in one section, in document order."""
    out, pending = [], []
    for m in TOKEN.finditer(section_html):
        if m.group(1) is not None:
            pending.append(urllib.parse.urljoin(page_url, html.unescape(m.group(1))))
        else:
            t = re.sub(r"\s+", " ", html.unescape(m.group(2))).strip()
            if not t or t in (",", "|"):
                continue
            while pending:
                out.append((pending.pop(0), t))
    for u in pending:
        out.append((u, None))
    return out


def section(body, start_text):
    """The slice of the page from one <h1> to the next. Returns '' if not found."""
    i = body.find(start_text)
    if i < 0:
        return ""
    j = re.search(r"<h[1-4][\s>]", body[i + len(start_text):], re.I)
    return body[i:i + len(start_text) + (j.start() if j else len(body))]


def slug(url):
    """Archive name for a book: the PDF's own basename, lowercased.

    Keyed on the filename rather than on the department label because the label is
    typeset by hand and moves ("Planningand Development Department", "Labour Employment
    ,Training and Skill Development Department"), while the filename has been stable
    across the years this page lists.
    """
    stem = os.path.basename(urllib.parse.urlsplit(url).path)
    stem = re.sub(r"\.pdf$", "", stem, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def discover(index_url, pace):
    """Read the index. Returns (bytes, books, alternates, n_pdfs_on_page, err)."""
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, [], 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    n_pdfs = len(re.findall(r'href="[^"]+\.pdf"', body, re.I))

    sec = section(body, SECTION_START)
    if not sec:
        return r.body, {}, [], n_pdfs, f"no section headed {SECTION_START!r}"

    books, alternates, seen = {}, [], {}
    for url, label in labelled_pdfs(sec, index_url):
        name = slug(url)
        if name in seen:
            alternates.append({"book": name, "url": url, "label": label,
                               "why_not_taken": "a second link to the same file"})
            continue
        seen[name] = url
        books[name] = {"url": url, "department": label,
                       "what": f"Demand for Grants 2026-27, {label or name}"}
    return r.body, books, alternates, n_pdfs, None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "jharkhand", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "jharkhand", "started": utcnow(), "base": index_url,
           "books": {}, "errors": [], "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, wanted, alternates, n_pdfs, err = discover(index_url, pace)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/jharkhand/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates
    man["books_expected"] = sorted(wanted)

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        # 600s rather than the default 45: the largest book is 42 MB and a timeout on a
        # slow link would look like a missing department.
        r = fetch(meta["url"], timeout=600, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        # A 404 arriving as an HTML body written to a file named .pdf is the failure that
        # matters, so the magic bytes are checked rather than the status.
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
    write_json(f"archive/jharkhand/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Jharkhand per-department Demand for Grants books.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*", help="archive names, for a partial re-run")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"jharkhand: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
