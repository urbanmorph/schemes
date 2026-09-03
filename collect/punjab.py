"""
Punjab state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

Why Punjab: DBT Bharat counts 128 schemes here against myScheme's 41, and the Demands for
Grants alone print about 2,800 distinct English scheme names.

Why it can be read at all, which is the thing to record: Punjab publishes its demand books
BILINGUALLY, with the Punjabi and the English in separate columns, and Gurmukhi occupies
U+0A00 to U+0A7F, a block no English name can borrow a character from. So the two scripts
separate on codepoint alone, with no geometry involved, which is the same property that
makes Odisha and Kerala readable and the property Gujarat's outcome budget lacks.

One index, static, no postback:

    https://finance.punjab.gov.in/StateBudget/Index

193 unique PDF links covering 2022-23 through 2026-27. The Finance Department's home page
carries exactly one budget link and it points here.

THE FILENAMES CANNOT BE CONSTRUCTED. Every document is served as
`/uploads/<uuid>_<human name> FY 2026-27.pdf`, and the uuid is a fresh random one per
upload: `84998369-36db-4b71-a8ed-3b154dde550a_Demand for Grants Vol-I FY 2026-27.pdf`. The
human half of the name is stable across years and the uuid is not, so books are matched on
words in the filename and the address is always read off the index, which is archived every
run as the evidence.

The names also contain spaces, which have to be percent-encoded before the fetch; the page
prints them raw.

Six books are taken. The three Demand for Grants volumes and the Central Sponsored Scheme
book are the state's own detailed accounts, with a printed total at four levels; the Gender
Budget is a plain English scheme table; the Special Component Plan is archived and NOT
parsed, so that it can be read later without a new fetch.

    archive/punjab/D/index.html.gz   the budget page, so URL discovery is auditable
    archive/punjab/D/<book>.pdf.gz   raw bytes, byte-identical to what was served
    archive/punjab/D/_manifest.json
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

INDEX = "https://finance.punjab.gov.in/StateBudget/Index"

# The key is the archive filename; the value is (words that must all appear in the served
# filename, what the book is). Matched on the filename rather than the link text because
# every anchor on this page prints the same words, "View File".
BOOKS = {
    "dfg-1": (("demand for grants", "vol-i "),
              "Demand for Grants Volume I: detailed accounts by demand, minor head, "
              "sub-head and object head, Punjabi and English in separate columns, four "
              "years of figures in thousands"),
    "dfg-2": (("demand for grants", "vol-ii "),
              "Demand for Grants Volume II"),
    "dfg-3": (("demand for grants", "vol-iii "),
              "Demand for Grants Volume III"),
    "css": (("central sponsored scheme",),
            "Central Sponsored Scheme Budget Book: the same layout with the State and "
            "CSS shares of each object head printed on separate lines"),
    "gender": (("gender budget",),
               "Gender Budget: Parts A, B and C, a plain English numbered scheme table "
               "with four years of figures in thousands"),
    "scp": (("special component plan", "(english)"),
            "Special Component Plan, English edition. ARCHIVED AND NOT PARSED: its "
            "schemes carry codes and outlays but are interleaved with narrative rather "
            "than tabulated, so it is kept for a later reading rather than guessed at"),
}

# On the page and deliberately not collected. Recorded here rather than in a commit
# message because a document missing from the archive is otherwise indistinguishable from
# a collector that failed to find it.
SKIPPED = {
    "Annual Financial Statement, Budget at a Glance, Receipt Budget Book, "
    "Statistical Abstract": (
        "aggregate and receipts documents, organised by major head; none names a scheme"),
    "Capital Expenditure Budget Book": (
        "a cut of the same provisions by capital head. Every scheme in it is already in "
        "the three Demand for Grants volumes, which carry the revenue side too"),
    "Supplementary Demand (English and Punjabi)": (
        "the supplementary demands for the CURRENT year, 2025-26. A different document "
        "from the 2026-27 demands and not a variant of them; mixing the two would put a "
        "2025-26 figure in a 2026-27 register"),
    "Special Component Plan (Punjabi), Budget Speech (Punjabi, Hindi, English), "
    "Research & Development Budget": "prose, or the Punjabi edition of a book taken in English",
}

ANCHOR = re.compile(r'href="([^"]+\.pdf[^"]*)"', re.I)


def filename_of(url):
    """The served filename, percent-decoded and lowercased, for matching words against.

    The uuid prefix is left on: it is 36 characters of hex and hyphens and cannot collide
    with any of the words matched below, and stripping it would be one more assumption
    about a naming convention this collector deliberately does not rely on.
    """
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?")[0])
    return " " + name.lower() + " "


def encoded(url):
    """Percent-encode the path. Punjab's filenames contain spaces and the page prints
    them raw, so the href cannot be fetched as written."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        parts.scheme, parts.netloc, urllib.parse.quote(parts.path, safe="/%"),
        parts.query, parts.fragment))


def discover(index_url, cycle, pace):
    """Read the budget page. Returns (bytes, books, alternates, n_pdfs, cycles, err)."""
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, [], 0, [], f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    urls = sorted({urllib.parse.urljoin(index_url, html.unescape(h).strip())
                   for h in ANCHOR.findall(body)})

    # The cycle is matched in the FILENAME, because that is the only place this page
    # states it: the anchors all read "View File" and the year headings are markup.
    marker = "fy %s" % cycle
    alt = "%s.pdf" % cycle
    this_cycle = [u for u in urls
                  if marker in filename_of(u) or alt in filename_of(u)]

    books, alternates = {}, []
    for name, (wordset, what) in sorted(BOOKS.items()):
        hits = [u for u in this_cycle if all(w in filename_of(u) for w in wordset)]
        if len(hits) == 1:
            books[name] = {"url": encoded(hits[0]), "what": what,
                           "served_as": urllib.parse.unquote(hits[0].rsplit("/", 1)[-1])}
        elif not hits:
            alternates.append({"book": name, "why_not_taken":
                               "no filename contains " + ", ".join(wordset)})
        else:
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} files match, refusing to guess: "
                               + ", ".join(filename_of(u).strip() for u in hits[:4])})
    cycles = sorted({m.group(1) for u in urls
                     for m in [re.search(r"fy (\d{4}-\d{2})", filename_of(u))] if m}
                    - {cycle})
    return r.body, books, alternates, len(urls), cycles, None


def collect(cycle, index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "punjab", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "punjab", "started": utcnow(), "base": index_url, "cycle": cycle,
           "books_expected": sorted(BOOKS), "books": {}, "errors": [],
           "status_histogram": {}, "skipped": SKIPPED}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    index_body, wanted, alternates, n_pdfs, cycles, err = discover(
        index_url, cycle, pace)
    if index_body:
        with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
            fh.write(index_body)
        man["index_bytes"] = len(index_body)
        man["pdfs_on_index"] = n_pdfs
        man["other_cycles_on_index"] = cycles
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json(f"archive/punjab/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        # 300s rather than the default 45: Volume I is 15 MB and 732 pages, and a timeout
        # on a slow link would look like a missing volume.
        r = fetch(meta["url"], timeout=300, pace=pace)
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
    write_json(f"archive/punjab/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Punjab budget books.")
    ap.add_argument("--cycle", default="2026-27",
                    help="the cycle as it appears in the served filenames")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*", help="archive names, for a partial re-run")
    a = ap.parse_args()
    man = collect(a.cycle, a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"punjab {a.cycle}: {man.get('books_collected', 0)} of {len(BOOKS)} books "
          f"archived from {man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for b, d in sorted(man.get("books", {}).items()):
        print(f"    {b:<8}{d['bytes']:>11,} bytes   {d['served_as'][:62]}")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
