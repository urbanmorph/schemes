"""
Odisha state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md 7 before editing.

Why Odisha: DBT Bharat counts 173 schemes here against myScheme's 83. The state answers
that in 44 Demand for Grants books whose every scheme row is English with the Odia
beneath it, in Unicode, so the two scripts separate on character range alone.

WHICH INDEX, AND WHY NOT THE OBVIOUS ONE. Odisha runs a dedicated budget portal at
budget.odisha.gov.in/budget-details, and it is NOT used here. Two reasons, both measured
2026-09-02:

  1. Its TLS chain is incomplete. `*.odisha.gov.in` is served as a leaf with no
     intermediate attached, so openssl reports "unable to verify the first certificate"
     and Python fails with "unable to get local issuer certificate". Browsers and curl
     paper over this by fetching the intermediate from the certificate's Authority
     Information Access extension; Python does not do AIA fetching. finance.odisha.gov.in
     serves a complete chain and the same documents.
  2. Its listing is wrong. The portal lists all 44 demands TWICE, the second set being
     last year's VOLUME - II (D-19 there prints "VOLUME - II / 2025-2026" on its cover),
     and for Demand 34, Co-operation, it links the 2025-2026 book while the 2026-2027
     one, 107 pages, created 2026-02-19, sits on the server unlinked. A register built
     from that page would carry a 2025-26 figure for one department and call it 2026-27.

The Finance Department's own publication page has neither problem:

    https://finance.odisha.gov.in/en/publication/finance-budget

67 PDF links, all 44 demands from one directory, D-34 pointing at the 2026-2027 book,
plus the Gender, Child, Nutrition, Agriculture, Climate and SDG statements. Two demands,
15 and 28, are listed twice with identical byte sizes; the first occurrence is taken and
the second recorded in `alternates`.

The cycle is not in any URL, so it is NOT constructed here. Each book prints its own year
on its own cover and parse/odisha.py reads it there and refuses to mix two.

    archive/odisha/D/index.html.gz   the publication page, so discovery is auditable
    archive/odisha/D/<book>.pdf.gz   raw bytes, byte-identical to what was served
    archive/odisha/D/_manifest.json
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

INDEX = "https://finance.odisha.gov.in/en/publication/finance-budget"

# The scheme-wise cross-cuts on the same page, matched on words in the label the page
# prints beside the link. Labels rather than filenames here because Odisha's filenames
# are inconsistent ("Gender Budget.pdf" but "Odisha Child Budget 2026-27.pdf") while the
# labels are not.
CROSSCUTS = {
    "gender": (("gender budget",),
               "Gender Budget: Part A (100% women-specific) and Part B (30 to 99%) "
               "scheme-wise tables in Rs crore, each row carrying the state's own "
               "4-digit scheme code beside the English name"),
    "child": (("child budget",),
              "Child Budget, scheme-wise, the Gender Budget's layout"),
    "nutrition": (("nutrition budget",),
                  "Nutrition Budget, scheme-wise"),
    "agriculture": (("agriculture budget",),
                    "Agriculture Budget, scheme-wise"),
    "sdg": (("sdg budget",),
            "SDG Budget at a Glance"),
    "outlay-link": (("budget head programme outlay link",),
                    "Budget Head Programme Outlay Link, which maps each budget head to "
                    "the programme it funds"),
}

# On the page and deliberately not collected. Recorded here rather than in a commit
# message because a document missing from the archive is otherwise indistinguishable
# from a collector that failed to find it.
SKIPPED = {
    "Annual Financial Statement, Budget at a Glance, Revenue Receipts, Explanatory "
    "Memorandum, Demand for Grants (summary), FRBM, Fiscal Strategy, Fiscal Risk, "
    "Status Paper on Public Debt": (
        "aggregate and receipts documents. The summary Demand for Grants is a one-line "
        "-per-demand abstract; the 44 per-department books carry the scheme rows"),
    "Budget Speech, People Guide, Economic Survey": "prose",
    "Climate Budget": (
        "an appended statement of the climate share of provisions already counted in the "
        "demand books, so it names no scheme the demands do not"),
    "budget.odisha.gov.in/budget-details": (
        "the state's dedicated budget portal, not used: broken TLS chain for a "
        "non-AIA-fetching client, a duplicate listing of last year's Volume-II, and a "
        "stale link for Demand 34. See the module docstring"),
}

DEMAND = re.compile(r"/D-(\d{2})(?:_\d+)?\.pdf$", re.I)
# The label the page prints beside a demand link: "19. INDUSTRIES DEPARTMENT", and once
# without the space, "23.DEPARTMENT OF AGRICULTURE AND FARMERS' EMPOWERMENT".
DEMAND_LABEL = re.compile(r"^(\d{1,2})\.\s*(.+)$")

# Text nodes and PDF hrefs in document order. The page gives every link the same text,
# "Download(189.3 KB)", and prints the department name in the cell before it, so the
# label for a link is the last real text seen before it.
TOKEN = re.compile(r'(?:>([^<>]{2,200})<)|(?:href="([^"]+\.pdf[^"]*)")', re.I)


def labelled_pdfs(body, page_url):
    """[(label, absolute url)] in document order."""
    out, label = [], None
    for m in TOKEN.finditer(body):
        if m.group(1) is not None:
            t = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
            if t and not t.lower().startswith("download") and t not in (",", "|"):
                label = t
        else:
            out.append((label, urllib.parse.urljoin(
                page_url, html.unescape(m.group(2)).strip())))
    return out


def discover(index_url, pace):
    """Read the publication page. Returns (bytes, books, alternates, n_pdfs, err)."""
    r = fetch(index_url, pace=pace)
    if not r.ok:
        return None, {}, [], 0, f"index http {r.status}"
    body = r.body.decode("utf-8", "replace")
    pdfs = labelled_pdfs(body, index_url)

    books, alternates, seen = {}, [], set()
    for label, url in pdfs:
        m = DEMAND.search(urllib.parse.unquote(url))
        if not m:
            continue
        n = int(m.group(1))
        # The demand number is taken from the FILENAME, not from the label, and the two
        # are cross-checked. The page lists demand 35 before demand 34, so trusting
        # document order would misname two departments.
        lm = DEMAND_LABEL.match(label or "")
        dept, mismatch = (label or "").strip(), None
        if lm:
            dept = lm.group(2).strip()
            if int(lm.group(1)) != n:
                mismatch = f"label says demand {lm.group(1)}, filename says {n}"
        key = f"demand-{n:02d}"
        if key in seen:
            alternates.append({"demand": n, "url": url, "label": label,
                               "why_not_taken": "a second link to the same demand"})
            continue
        seen.add(key)
        books[key] = {"url": url, "demand": n, "department": dept,
                      "what": f"Demand for Grants, demand {n}, {dept}"}
        if mismatch:
            books[key]["label_mismatch"] = mismatch

    for name, (wordset, what) in sorted(CROSSCUTS.items()):
        hits = [u for label, u in pdfs
                if label and all(w in label.lower() for w in wordset)]
        hits = sorted(set(hits))
        if len(hits) == 1:
            books[name] = {"url": hits[0], "what": what}
        elif not hits:
            alternates.append({"book": name, "why_not_taken":
                               "no link whose label contains " + ", ".join(wordset)})
        else:
            alternates.append({"book": name, "why_not_taken":
                               f"{len(hits)} links match, refusing to guess: "
                               + ", ".join(u.rsplit("/", 1)[-1] for u in hits[:4])})
    return r.body, books, alternates, len(pdfs), None


def collect(index_url=INDEX, date=None, pace=1.0, only=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "odisha", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "odisha", "started": utcnow(), "base": index_url,
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
        write_json(f"archive/odisha/{date}/_manifest.json", man)
        return man
    man["alternates"] = alternates
    man["books_expected"] = sorted(wanted)

    for book in sorted(wanted):
        if only and book not in only:
            continue
        meta = wanted[book]
        # 240s rather than the default 45: the largest demand book runs to 271 pages, and
        # a timeout on a slow link would look like a missing department.
        r = fetch(meta["url"], timeout=240, pace=pace)
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
    write_json(f"archive/odisha/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Odisha Demand for Grants books and scheme-wise cuts.")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--only", nargs="*", help="archive names, for a partial re-run")
    a = ap.parse_args()
    man = collect(a.index, a.date, a.pace, set(a.only) if a.only else None)
    print(f"odisha: {man.get('books_collected', 0)} of "
          f"{len(man.get('books_expected', []))} books archived from "
          f"{man.get('pdfs_on_index', 0)} PDFs on the index, "
          f"{sum(d['bytes'] for d in man.get('books', {}).values()):,} bytes")
    for a_ in man.get("alternates", []):
        print(f"    not taken: {a_}")
    for b, d in sorted(man.get("books", {}).items()):
        if d.get("label_mismatch"):
            print(f"    NOTE {b}: {d['label_mismatch']}")
    for e in man.get("errors", []):
        print(f"    ERROR {e['stage']}: {e['why']}")


if __name__ == "__main__":
    main()
