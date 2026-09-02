"""
Kerala state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md §7 before editing.

Why a state budget at all: see collect/karnataka.py. myScheme lists 81 schemes for
Kerala. The Annual Plan alone prints more than 1,600 scheme codes, so the gap here is the
largest in the country, and a gap you can name is worth more than a gap you can count.

Kerala puts every budget document on ONE page at the Legislature, 36 direct PDF links,
no postback and no session:

    http://www.niyamasabha.org/codes/15kla/Session_16/Budget%20doc%202026.htm

Four of the 36 carry a scheme table, and they are not alternatives to each other:

    annual-plan   Annual Plan 2026-27 (Statements) Vol I, 529 pages, the comprehensive
                  list: every plan scheme with its code, its name in Malayalam and again
                  in English, its head of account and six years of figures
    gender-child  Gender & Child Budget, four statements (Gender Part A, Gender Part B,
                  Transgender, Child), each with an Objectives column in English
    environment   Environment Budget, scheme-wise details with the environment share of
                  each scheme's outlay and a justification paragraph
    elderly       Elderly Budget, the Gender Budget's layout with an elderly earmark

Two documents on that page were surveyed and are NOT collected, and the reasons are
recorded in SKIPPED below so the decision is auditable rather than silent:

    23. R & D Budget      prose and sector-level aggregates. It estimates the R&D content
                          of the plan by sector and never lists a scheme with a code, so
                          there is nothing here a scheme register can key on.
    25. SDG 2026          not an SDG budget. The file behind that link is the
                          SUPPLEMENTARY DEMANDS FOR GRANTS 2025-26, an appropriation
                          document organised by head of account with no scheme code and
                          no scheme name. The link text on the index page says "SDG 2026"
                          and the document says otherwise; the document wins.

    archive/kerala/D/index.html.gz    the budget page, so URL discovery is auditable
    archive/kerala/D/<book>.pdf.gz    raw bytes, byte-identical to what was served
    archive/kerala/D/_manifest.json

Books are matched on words in the FILENAME, not on the leading number the site prints in
front of it. The numbers are a list position and move between cycles; "Environment
Budget" is what the document is. A book that matches more than one href is recorded as an
error rather than resolved by taking the first, because two candidate addresses mean the
site changed shape and a guess would be indistinguishable from a read.

The index URL carries a session number (Session_16) that no naming convention derives
from the cycle: 2026-27 is the sixteenth session of the fifteenth Assembly, and knowing
that requires knowing the Assembly's calendar, not arithmetic. So the address is an
argument with a default rather than something constructed, and the page itself is
archived every run as the evidence that the 36 hrefs were read and not invented.
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

INDEX = ("http://www.niyamasabha.org/codes/15kla/Session_16/"
         "Budget%20doc%202026.htm")

# Books wanted. The key is the archive filename, the value is (words that must all
# appear in the served filename, what the book is). The description is recorded so the
# archive is readable without this file.
BOOKS = {
    "annual-plan": (
        ("annual plan", "statements", "vol i"),
        "Annual Plan Statements Vol I, every plan scheme with code, head of account "
        "and six years of figures"),
    "gender-child": (
        ("gender", "child budget"),
        "Gender & Child Budget: Gender Part A and Part B, Transgender and Child "
        "statements, each with an Objectives column"),
    "environment": (
        ("environment budget",),
        "Environment Budget, scheme-wise environment share of outlay with a "
        "justification paragraph"),
    "elderly": (
        ("elderly budget",),
        "Elderly Budget, scheme-wise elderly share of outlay with an Objectives "
        "column"),
}

# Surveyed on the 2026-27 page and deliberately not collected. Kept here rather than in a
# commit message because the absence of a document from the archive is otherwise
# indistinguishable from a collector that failed to find it.
SKIPPED = {
    "R & D Budget": ("prose and sector-level aggregates; no scheme code anywhere, so "
                     "there is nothing to key a scheme register on"),
    "SDG 2026": ("the link says SDG but the file is the Supplementary Demands for "
                 "Grants 2025-26, organised by head of account with no scheme names"),
}


def absolute(href, page):
    """Resolve a relative href against the index page. Kerala's are all relative."""
    return urllib.parse.urljoin(page, href)


def filename_of(url):
    """The served filename, percent-decoded, for matching words against."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?")[0])
    return name.lower()


def discover(index_url, pace):
    """Read the budget page and find each wanted book's URL.

    Returns (index_bytes, {book: url}, {book: why it could not be resolved}, n_pdfs, err).
    """
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, {}, 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")

    # html.unescape because the Gender & Child href is written with &amp; in the page
    # source. Fetching the raw href would ask for a filename with a literal "&amp;" in
    # it, which is a 404 against a file that is really there.
    urls = []
    for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', body, re.I):
        urls.append(absolute(html.unescape(href), index_url))
    urls = sorted(set(urls))

    found, unresolved = {}, {}
    for book, (words, _) in sorted(BOOKS.items()):
        hits = [u for u in urls if all(w in filename_of(u) for w in words)]
        if len(hits) == 1:
            found[book] = hits[0]
        elif not hits:
            unresolved[book] = "no href whose filename contains " + ", ".join(words)
        else:
            unresolved[book] = f"{len(hits)} hrefs match, refusing to guess: " + \
                ", ".join(filename_of(u) for u in hits[:4])
    return r.body, found, unresolved, len(urls), None


def collect(cycle, index_url=INDEX, date=None, pace=1.5):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "kerala", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "kerala", "started": utcnow(), "base": index_url, "cycle": cycle,
           "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, urls, unresolved, n_pdfs, err = discover(index_url, pace)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/kerala/{date}/_manifest.json", man)
        return man
    man["urls"] = urls
    for book, why in sorted(unresolved.items()):
        man["errors"].append({"stage": book, "why": why})

    for book in sorted(BOOKS):
        url = urls.get(book)
        if not url:
            continue
        # 180s rather than the default 45: the Environment Budget is 27 MB and the R&D
        # Budget 18 MB, and a timeout on a slow link would look like a missing book.
        r = fetch(url, timeout=180, pace=pace)
        note(r.status)
        if not r.ok:
            man["errors"].append({"stage": book, "why": f"http {r.status}"})
            continue
        # A PDF that is really an error page is a valid write and the failure mode that
        # matters, so check the magic bytes here rather than trusting the status.
        if not r.body.startswith(b"%PDF"):
            man["errors"].append({"stage": book, "why": "response is not a PDF"})
            continue
        bad = looks_like_error(r.body[:4096])
        if bad:
            man["errors"].append({"stage": book, "why": str(bad)})
            continue
        with gzip.open(os.path.join(out_dir, f"{book}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["books"][book] = {"url": url, "bytes": len(r.body),
                              "sha256": r.sha256, "what": BOOKS[book][1]}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json(f"archive/kerala/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Kerala scheme-wise budget books.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--index", default=INDEX,
                    help="the Legislature's budget document page for this cycle")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.cycle, a.index, a.date, a.pace)
    print(f"kerala {a.cycle}: {man.get('books_collected', 0)} of "
          f"{len(BOOKS)} books archived from {man.get('pdfs_on_index', 0)} PDFs on "
          f"the index")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<14}{d['bytes']:>11,} bytes   {d['what'][:60]}")
    for name, why in sorted(SKIPPED.items()):
        print(f"    skipped {name}: {why}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
