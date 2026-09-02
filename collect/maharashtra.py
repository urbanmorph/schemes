"""
Maharashtra state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

Why Maharashtra: DBT Bharat counts 308 schemes here against myScheme's 84, the largest
absolute gap of any state on /divergence. The state answers it in one document.

Where the budget actually lives. The Finance Department's own site
(finance.maharashtra.gov.in) publishes circulars, pay commission reports and a
performance budget, and NOT the budget books. Those are on BEAMS, the Budget Estimation,
Allocation and Monitoring System run by the Directorate of Accounts and Treasuries:

    https://beams.mahakosh.gov.in/Beams5/BudgetMVC/MISRPT/HomePage2021.html

The filename says 2021 and the page is live and current: its title is
"महाराष्ट्र राज्य अर्थसंकल्प २०२६-२०२७" and every link points into
BudgetBooksPDF1/2026-2027/. The name is a leftover, not a date, which is why the index
URL is an argument with a default rather than something constructed from the cycle.

TWO TRAPS, both measured 2026-09-02, both encoded below.

1. The PDF directory 404s without a Referer. The identical GET returns 89 bytes of
   "Page Not Found on BEAMS" with HTTP 404 with no Referer, HTTP 404 with the bare host
   as Referer, and HTTP 200 application/pdf with a page under /Beams5/BudgetMVC/MISRPT/
   as Referer. A collector that omits it archives an error page named .pdf. The magic
   bytes check below catches that anyway, but sending the header is the fix.

2. The index page carries a large block of commented-out HTML holding dead links to the
   2022-2023 supplementary demands, including one labelled 2025-2026 that points at a
   2026-2027 file. Comments are stripped before any href is read; 17,514 bytes of source
   become 9,711 bytes of live markup.

What is collected, and what is deliberately not:

    annual-scheme-en   ANNUAL SCHEME 2026-2027 (Departmentwise), English edition, 752pp.
                       The register. One row per scheme with a 10-digit scheme code, the
                       name in English, an 8-character budget code, the source of fund
                       and four years of figures, in seven statements (GN2 state schemes
                       general/SCCS/TCS, GN3 physical targets, GN4 centrally sponsored,
                       GN5 externally aided, GN6 domestic financial institutions, GN7
                       women and child, GN8 human development).
    summary-en         ANNUAL SCHEME Summary, English. Department and sector totals, so
                       the detailed book can be reconciled against a figure the state
                       prints about itself in a different document.
    gender-child       Gender Budget and Child Budget statements, 2026-2027. Carries the
                       head of account inline with the English name.
    errata-be          Budget Errata 2026-2027. Corrections to the budget estimates.
    errata             Budget Errata 2026-2027, the second of two errata files the index
                       lists separately.

    NOT collected, recorded in SKIPPED so the absence is a decision and not a failure:
    the Marathi editions of the same two Annual Scheme books, the 34 departmentwise
    Demand for Grants volumes, the 36 districtwise volumes, the 11 Part-III appendices,
    the Green, Pink and Yellow Books, the speeches and the receipts volume.

VARIANT. Maharashtra presents one budget for 2026-2027, and its supplementary demands are
published separately as their own PDFs (supplementaryDemandJune2026.pdf and the December
and February files) linked from the BEAMS front page, not from the budget index. Only the
budget estimate books are collected, so the figure published here is a Budget Estimate
2026-27 and is comparable with Karnataka's and Kerala's. The supplementary demands exist
and are recorded here rather than merged, because adding them would silently turn a BE
into a part-year revised figure.

    archive/maharashtra/D/index.html.gz          the budget index, so discovery is auditable
    archive/maharashtra/D/index-<name>.html.gz   the sub-index pages linked from it
    archive/maharashtra/D/<book>.pdf.gz          raw bytes, byte-identical to what was served
    archive/maharashtra/D/_manifest.json
"""

import argparse
import gzip
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

INDEX = ("https://beams.mahakosh.gov.in/Beams5/BudgetMVC/MISRPT/"
         "HomePage2021.html")

# Sub-index pages linked from the master index. They hold the Annual Scheme books, which
# is why they are followed; they are archived too, for the same reason the master index
# is, so the set of hrefs that were read is recoverable from the archive alone.
SUB_INDEX = ("Anuual_DeptPublication.html", "Anuual_SummeryPublication.html",
             "Anuual_RegionPublication.html", "dept.html", "dist.html",
             "appendix.html")

# Books wanted. Key is the archive filename; value is (words that must ALL appear in the
# served filename, lowercased, what the book is).
#
# Matched on the filename and not on the number the index prints in front of it, for the
# same reason as Kerala: the numbers are list positions and move between cycles, while
# "ANNUAL SCHEME - Deptwise English.pdf" is what the document is. A book matching more
# than one href is an error rather than a first-hit guess, because two candidate
# addresses mean the site changed shape.
BOOKS = {
    "annual-scheme-en": (
        ("annual scheme", "deptwise", "english"),
        "ANNUAL SCHEME 2026-2027 (Departmentwise), English: one row per scheme with a "
        "10-digit scheme code, an 8-character budget code, source of fund and four "
        "years of figures, in statements GN2 to GN8"),
    "summary-en": (
        ("annual scheme", "summary", "english"),
        "ANNUAL SCHEME summary statement, English: department and sector totals, used "
        "to reconcile the detailed book against a figure printed elsewhere"),
    "gender-child": (
        ("genderbudget",),
        "Gender Budget and Child Budget statements, with the head of account inline "
        "beside the English scheme name"),
    "errata-be": (
        ("errata_be",),
        "Budget Errata 2026-2027, corrections to the budget estimates"),
    "errata": (
        ("errata.pdf",),
        "Budget Errata 2026-2027, the second errata file the index lists"),
}

# Surveyed on the 2026-2027 index and deliberately not collected. Kept here rather than in
# a commit message because a document missing from the archive is otherwise
# indistinguishable from a collector that failed to find it.
SKIPPED = {
    "ANNUAL SCHEME - Deptwise/Summary Marathi": (
        "the same two books in Marathi. Same rows, same codes, same figures; collecting "
        "both would double the bytes and add nothing a register can key on"),
    "34 Departmentwise Publication volumes": (
        "the Demand for Grants books, bilingual, with the full head of account rather "
        "than the 8-character budget code. Richer per line and 34 files; the Annual "
        "Scheme book already names every scheme, so these are a second phase, not a "
        "substitute"),
    "36 Districtwise volumes": (
        "the same provisions cut by district. A district cut of a scheme is not another "
        "scheme, and summing them would double-count"),
    "Part-III Appendices A to I": (
        "works lists, road and bridge and building schedules. Works, not schemes"),
    "Financial Statement (Green Book), Budget in Brief (Pink Book), "
    "Med Term Fiscal Policy (Yellow Book), Receipts, Schedule of Appropriations": (
        "aggregate and receipts documents with no scheme-level rows"),
    "Budget speeches and highlights": "prose",
    "Supplementary demands (June 2026, December 2025, February 2025)": (
        "linked from the BEAMS front page, not the budget index. They amend the year in "
        "progress; adding them would turn a Budget Estimate into a part-year revised "
        "figure and break comparability with the other states here"),
}

# The Referer this host requires. Any page under /Beams5/BudgetMVC/MISRPT/ works; the
# bare host does not. See trap 1 in the module docstring.
REFERER = INDEX


def live_html(body):
    """The index with commented-out markup removed. See trap 2."""
    return re.sub(r"<!--.*?-->", "", body, flags=re.S)


def encode(url):
    """Percent-encode the path. Half these filenames contain spaces.

    "ANNUAL SCHEME - Deptwise English.pdf" is served with literal spaces in the href.
    urllib.request raises rather than encoding them, which arrives here as a generic
    transport error and looks exactly like a dead host: measured 2026-09-02, the first
    run of this collector reported "http ERR" for both Annual Scheme books while the
    Gender Budget and both errata files, whose names have no spaces, came back fine.
    quote() is given the sub-delimiters as safe characters so the ampersand and comma in
    other departments' filenames survive unchanged.
    """
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=~"),
         p.query, p.fragment))


def hrefs(body, page_url):
    """Every href on a page, comment-stripped, unescaped and made absolute."""
    out = []
    for h in re.findall(r'href="([^"]+)"', live_html(body), re.I):
        out.append(encode(urllib.parse.urljoin(page_url, html.unescape(h).strip())))
    return out


def filename_of(url):
    """The served filename, percent-decoded and lowercased, to match words against."""
    return urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?")[0]).lower()


def cycle_of(url):
    """The BudgetBooksPDF1/<cycle>/ directory a book sits in, or None."""
    m = re.search(r"/BudgetBooksPDF1/(\d{4}-\d{4})/", urllib.parse.unquote(url))
    return m.group(1) if m else None


def discover(index_url, pace):
    """Read the index and its sub-indexes and find each wanted book's URL.

    Returns (pages, {book: url}, {book: why not}, n_pdfs, err) where pages is
    [(archive filename, url, bytes)] for every index page read.
    """
    r = fetch(index_url, headers={"Referer": REFERER}, pace=pace)
    if not r.ok:
        return [], {}, {}, 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    pages = [("index.html", index_url, r.body)]

    links = hrefs(body, index_url)
    for name in SUB_INDEX:
        target = [u for u in links if u.rsplit("/", 1)[-1].lower() == name.lower()]
        if not target:
            continue
        s = fetch(target[0], headers={"Referer": REFERER}, pace=pace)
        if s.ok:
            pages.append((f"index-{name}", target[0], s.body))
            links.extend(hrefs(s.body.decode("utf-8", "replace"), target[0]))

    pdfs = sorted({u for u in links if u.lower().split("?")[0].endswith(".pdf")})
    found, unresolved = {}, {}
    for book, (wordsets, _) in sorted(BOOKS.items()):
        hits = [u for u in pdfs if all(w in filename_of(u) for w in wordsets)]
        if len(hits) == 1:
            found[book] = hits[0]
        elif not hits:
            unresolved[book] = "no href whose filename contains " + ", ".join(wordsets)
        else:
            unresolved[book] = f"{len(hits)} hrefs match, refusing to guess: " + \
                ", ".join(filename_of(u) for u in hits[:4])
    return pages, found, unresolved, len(pdfs), None


def collect(index_url=INDEX, date=None, pace=1.5):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "maharashtra", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "maharashtra", "started": utcnow(), "base": index_url,
           "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED, "index_pages": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    pages, urls, unresolved, n_pdfs, err = discover(index_url, pace)
    for name, url, body in pages:
        with gzip.open(os.path.join(out_dir, name + ".gz"), "wb") as fh:
            fh.write(body)
        man["index_pages"][name] = {"url": url, "bytes": len(body)}
    man["pdfs_on_index"] = n_pdfs
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/maharashtra/{date}/_manifest.json", man)
        return man
    man["urls"] = urls
    for book, why in sorted(unresolved.items()):
        man["errors"].append({"stage": book, "why": why})

    # The cycle is READ from the paths the index serves, never constructed. If the state
    # publishes 2027-2028 next year every URL moves with it and this records the move; if
    # two books ever disagree that is a half-updated index and worth failing on rather
    # than mixing two years' figures into one register.
    cycles = sorted({c for c in (cycle_of(u) for u in urls.values()) if c})
    man["cycle"] = cycles[0] if len(cycles) == 1 else None
    if len(cycles) != 1:
        man["errors"].append({"stage": "cycle",
                              "why": f"books span {len(cycles)} cycles: {cycles}"})

    for book in sorted(BOOKS):
        url = urls.get(book)
        if not url:
            continue
        # 300s rather than the default 45: the Annual Scheme book is 13 MB and the
        # Gender Budget 13 MB, and a timeout on a slow link would look like a missing
        # book rather than a slow one.
        r = fetch(url, headers={"Referer": REFERER}, timeout=300, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        # The failure mode that matters here: a 404 arriving as an 89-byte HTML body
        # written to a file named .pdf. Checking the magic bytes rather than the status
        # is what catches it, because a missing Referer produces a real 404 but a
        # misconfigured one could produce a 200.
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
        man["books"][book] = {"url": url, "bytes": len(r.body), "sha256": r.sha256,
                              "cycle": cycle_of(url), "what": BOOKS[book][1]}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/maharashtra/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Maharashtra Annual Scheme and Gender Budget books.")
    ap.add_argument("--index", default=INDEX,
                    help="the BEAMS budget index page for this cycle")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace)
    print(f"maharashtra {man.get('cycle')}: {man.get('books_collected', 0)} of "
          f"{len(BOOKS)} books archived from {man.get('pdfs_on_index', 0)} PDFs across "
          f"{len(man.get('index_pages', {}))} index pages")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<18}{d['bytes']:>11,} bytes   {d['what'][:58]}")
    for name, why in sorted(SKIPPED.items()):
        print(f"    skipped {name[:60]}: {why[:80]}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
