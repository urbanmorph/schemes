"""
Telangana state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

Why Telangana: it is the sharpest gap in the country. myScheme lists 22 schemes for
Telangana against DBT Bharat's 152, and Volume VII/1 alone, the Pragathi Paddu, prints
more than a thousand named schemes with a head of account and three years of figures
against each.

WHICH INDEX, AND WHY NOT THE FINANCE DEPARTMENT'S. Telangana publishes the same budget
books in two places and only one of them is current. Measured 2026-09-03:

    finance.telangana.gov.in/budget-volumes.jsp   2014-15 through 2025-26. Complete for
                                                  every year it lists and a year behind.
    ifmis.telangana.gov.in/budget_volumes         2025-26 and 2026-27, the current cycle.

The Finance Department's own page carries fourteen `filePath=budget-YYYY-YY-books`
directories and the newest is `budget-2025-26-books`; there is no 2026-27 directory
behind it at all. So the collector reads IFMIS, the Integrated Financial Management
Information System, whose page links the same volumes on a CloudFront bucket. A register
built from the Finance Department's page would have published Telangana's 2025-26
allocations as if they were this year's.

THE FILENAMES CANNOT BE CONSTRUCTED. The 2025-26 set is served under readable names
(`Pragathi+paddu+VII-1.pdf`). The 2026-27 set is served under names carrying a unix
timestamp at both ends, `1773983749_Pragathi_Paddu__VII-I_1773983748_.pdf`, and the two
timestamps differ by a second, so neither is derivable from the other or from the cycle.
The URLs have to be read off the index, which is why the index is archived every run.

The cycle is taken from the URL PATH, `/publicfiles/budget-books/2026-27/`, and not from
the filename or the link text, because the page lists every year it has ever published on
one HTML page in per-year divs and the link text does not name the year.

    archive/telangana/D/index.html.gz   the IFMIS budget page, so discovery is auditable
    archive/telangana/D/<book>.pdf.gz   raw bytes, byte-identical to what was served
    archive/telangana/D/_manifest.json

Three books are collected out of the twenty-odd on the page. Volume VII is the scheme
volume in three parts and nothing else on the page lists a scheme by name:

    pragathi   Volume VII/1, Pragathi Paddu (Scheme Expenditure), 117 pages. The state's
               own scheme list: sector, department, scheme name, head of account and
               three years of figures, with a printed total at every level.
    scsdf      Volume VII/2, Scheduled Castes Special Development Fund, department-wise
               and scheme-wise, five money columns and a printed total per department.
    stsdf      Volume VII/3, Scheduled Tribes Special Development Fund, the same shape
               with six money columns.
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

INDEX = "https://ifmis.telangana.gov.in/budget_volumes"

# The key is the archive filename; the value is (words that must all appear in the link
# text, what the book is). Matched on the LINK TEXT rather than the filename because the
# 2026-27 filenames are timestamped machine names while the text the page prints beside
# them is the volume's real title.
BOOKS = {
    "pragathi": (
        ("pragathi paddu",),
        "Volume VII/1, Pragathi Paddu (Scheme Expenditure): the state's scheme list, "
        "sector and department wise, with the head of account and three years of "
        "figures against each scheme and a printed total at every level"),
    "scsdf": (
        ("scheduled castes", "scsdf"),
        "Volume VII/2, Scheduled Castes Special Development Fund, department wise and "
        "scheme wise, with a printed total per department and a grand total"),
    "stsdf": (
        ("scheduled tribes", "stsdf"),
        "Volume VII/3, Scheduled Tribes Special Development Fund, department wise and "
        "scheme wise, with a printed sub-total per group and a grand total"),
}

# On the page and deliberately not collected. Recorded here rather than in a commit
# message because a document missing from the archive is otherwise indistinguishable
# from a collector that failed to find it.
SKIPPED = {
    "Volume I/1 and I/2, II, IV, V, VIII/2, IX, X": (
        "Annual Financial Statement, Statement of Demands for Grants, Receipts, Public "
        "Account, Guarantees, Appendices, Analysis of Demands and Commercial "
        "Undertakings. All of them are organised by head of account or by demand and "
        "none prints a scheme name"),
    "Volume III/1 to III/17": (
        "the seventeen department budget books. They carry the detailed heads under "
        "each demand, which is the same money the Pragathi Paddu prints against a "
        "scheme name; they are a larger download for a coarser answer and were not "
        "taken this cycle"),
    "Volume VI, Budget in Brief; Volume VIII/1, Employee Strength; Budget Speech; "
    "FRBM Fiscal Policy Statement; Notice": "summary, staffing and prose documents",
    "finance.telangana.gov.in/budget-volumes.jsp": (
        "the Finance Department's own budget page, not used: its newest directory is "
        "budget-2025-26-books and it does not carry the current cycle at all. See the "
        "module docstring"),
}

# Document-order text nodes and PDF hrefs. The page gives each volume two anchors, one on
# the title and one on a download icon, and prints the title in the cell before both, so
# the label for a link is the last real text seen before it. Same shape as Odisha's page.
TOKEN = re.compile(r'(?:>([^<>]{2,300})<)|(?:href="([^"]+\.pdf[^"]*)")', re.I)


def labelled_pdfs(body, page_url):
    """[(label, absolute url)] in document order."""
    out, label = [], None
    for m in TOKEN.finditer(body):
        if m.group(1) is not None:
            t = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
            if t and t.lower() not in ("download", "|", ","):
                label = t
        else:
            # html.unescape because several 2026-27 filenames contain a literal & and
            # the page writes it as &amp;. Fetching the raw href would ask for a file
            # with "&amp;" in its name, which is a 404 against a file that is there.
            out.append((label, urllib.parse.urljoin(
                page_url, html.unescape(m.group(2)).strip())))
    return out


def discover(index_url, cycle, pace):
    """Read the IFMIS budget page. Returns (bytes, books, alternates, n_pdfs, err)."""
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, [], 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    pdfs = labelled_pdfs(body, index_url)

    # The cycle comes from the URL PATH. The page publishes every year it has ever held
    # on one page, and the link text never names the year, so a match on the text alone
    # would take whichever year happened to come first in the document.
    marker = "/budget-books/%s/" % cycle
    this_cycle = [(lab, u) for lab, u in pdfs if marker in u]

    books, alternates = {}, []
    for name, (wordset, what) in sorted(BOOKS.items()):
        hits = sorted({u for lab, u in this_cycle
                       if lab and all(w in lab.lower() for w in wordset)})
        if len(hits) == 1:
            books[name] = {"url": hits[0], "what": what}
        elif not hits:
            alternates.append({"book": name, "why_not_taken":
                               "no link whose text contains " + ", ".join(wordset)})
        else:
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} links match, refusing to guess: "
                               + ", ".join(u.rsplit("/", 1)[-1] for u in hits[:4])})
    # Every other cycle on the page, recorded so that a reader can see this run chose
    # among them rather than finding only one.
    other = sorted({m.group(1) for lab, u in pdfs
                    for m in [re.search(r"/budget-books/([0-9]{4}-[0-9]{2})/", u)] if m}
                   - {cycle})
    return r.body, books, alternates, len(pdfs), None, other


def collect(cycle, index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "telangana", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "telangana", "started": utcnow(), "base": index_url,
           "cycle": cycle, "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    got = discover(index_url, cycle, pace)
    index_body, wanted, alternates, n_pdfs, err, other_cycles = got
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
        man["other_cycles_on_index"] = other_cycles
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/telangana/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        # 180s rather than the default 45: the Pragathi Paddu is 117 pages and served
        # from a CDN edge that can be slow on a cold object, and a timeout on it would
        # look like a missing volume.
        r = fetch(meta["url"], timeout=180, pace=pace)
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
    write_json(f"archive/telangana/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Telangana Volume VII scheme books.")
    ap.add_argument("--cycle", default="2026-27",
                    help="the cycle as it appears in the CloudFront path")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*", help="archive names, for a partial re-run")
    a = ap.parse_args()
    man = collect(a.cycle, a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"telangana {a.cycle}: {man.get('books_collected', 0)} of {len(BOOKS)} "
          f"books archived from {man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<10}{d['bytes']:>11,} bytes   {d['what'][:58]}")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
