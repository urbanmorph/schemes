"""
Tamil Nadu state budget collector, raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md SS7 before editing.

Why a state budget at all: see collect/karnataka.py. Tamil Nadu is the state where the
question runs the other way. myScheme lists 234 Tamil Nadu schemes, the second highest of
any state, so this is the one place where the portal may not be badly behind. Whether the
Demand Books exceed 234 is the open question, and a finding either way is publishable.

Tamil Nadu publishes one page with every budget document since 2011 on it,

    https://financedept.tn.gov.in/en/budget-publications/

which carried 1,414 distinct PDF URLs across 1,379 table rows when measured on
2026-09-02. It is not a page to read whole. It is three tables (Detailed Demand List, Charged Appropriation,
Other Budget Publications), each a three-column grid of YEAR, a linked title, and the URL
again in a hidden column. The YEAR cell is what makes this tractable: it says
`2026-2027(RBE)` or `2026-2027 (IBE)` or a bare `2025-2026`, and it is the only thing on
the page that says which budget a file belongs to.

WHICH SET, AND WHY. Four files answer to demand 04 on that page and picking wrongly is the
whole risk of this collector:

    DemandBook_04.pdf     YEAR 2024-2025          "ADI-DRAVIDAR AND TRIBAL WELFARE"
    DemandBook_04-1.pdf   YEAR 2025-2026          "ADI-DRAVIDAR AND TRIBAL WELFARE"
    DemandBook_04-2.pdf   YEAR 2026-2027 (IBE)    "ADI-DRAVIDAR AND TRIBAL WELFARE"
    DemandBook_4.pdf      YEAR 2026-2027(RBE)     "SOCIAL JUSTICE DEPARTMENT"
    d04.pdf               YEAR 2023-2024          "ADI-DRAVIDAR AND TRIBAL WELFARE"

Nothing in the filenames orders them. The YEAR column does, and it is read rather than
inferred. 2026-27 is an assembly election year in Tamil Nadu, so the state presented TWO
budgets for the SAME financial year, exactly as it did in 2011-12, 2016-17 and 2021-22,
and the page labels both:

    IBE   Interim Budget Estimate 2026-2027, presented 13 February 2026 by the outgoing
          government. Its books are dated 13 Feb 2026 in their own PDF metadata.
    RBE   Revised Budget Estimate 2026-2027, presented 5 August 2026 by the incoming
          government. Its books are dated 4 Aug 2026 in their own PDF metadata.

RBE is collected. Three reasons, in order:

  1. It is the budget in force. The interim budget was a vote on account that the revised
     budget replaced; the appropriation Tamil Nadu is spending under in 2026-27 is the
     RBE. A register that says "Tamil Nadu funds this scheme in 2026-27" has to point at
     the figures that are actually in force.
  2. It loses nothing. The RBE book prints FOUR money columns and the third of them is the
     Interim Budget Estimate 2026-2027, so the RBE book contains the IBE figure as well as
     its own. The IBE book's four columns are Accounts 2024-25, BE 2025-26, RE 2025-26 and
     BE 2026-27, and contain no RBE column, because it did not exist yet. Taking the RBE
     is therefore a strict superset; taking the IBE would throw away the operative figure.
  3. It is the current machinery of government. Demand 04 is the Social Justice Department
     in the RBE and the Adi-Dravidar and Tribal Welfare Department in the IBE, demand 36
     and demand 47 also moved, and the RBE names are the ones in use.

And a warning about comparability, since this is the point of the whole register. "RBE" in
Tamil Nadu does NOT mean a revised estimate of the previous year in the ordinary sense. It
is a second BUDGET ESTIMATE for 2026-27, the first having been interim. So the figure
collected here is a 2026-27 budget estimate, the same kind of thing as Karnataka's,
Kerala's and Andhra Pradesh's 2026-27 budget estimates, and not a mid-year revision of
2025-26. What differs is the date it was presented, August rather than February, and the
parser publishes the interim February figure alongside it so a reader can see both.

    archive/tamilnadu/D/index.html.gz        the publications page, so discovery is auditable
    archive/tamilnadu/D/demand-NN.pdf.gz     raw bytes, byte-identical to what was served
    archive/tamilnadu/D/_manifest.json

HOW THE SET IS ENUMERATED, and why it is not a filename prefix. The demand books are
serials 1 to 55 of the Detailed Demand List; serials 56 to 67 are Debt Charges, works
lists, the Annual Financial Statement and the Budget Memorandum, which are not
department demands. The RBE set is served as DemandBook_1.pdf through DemandBook_9.pdf,
unpadded, and DemandBook_10-3.pdf through DemandBook_55-3.pdf, padded and suffixed, so
filenames cannot be constructed. Worse, the IBE set serves demand 01 as
`d.no_.01-Final.pdf` and everything else as DemandBook_NN-2.pdf, so a filename-prefix
filter would silently collect 54 books and call it a set.

So the filename family is used only to find the RANGE (the highest serial the page serves
under a DemandBook* name), and the SERIAL is used to enumerate the set inside it. Every
serial from 1 to that highest one must resolve to exactly one URL or the run is recorded
as incomplete. A page that changes shape then leaves a hole that is visible and dated
rather than a set that is quietly one book short.

The other variants are not collected but ARE recorded in the manifest, under
`other_variants`, with their full serial-to-URL map. The absence of a document from an
archive is otherwise indistinguishable from a collector that failed to find it.

Replayed against the archived index page, this resolves 55 contiguous demands for the
2026-27 RBE, 55 for the 2026-27 IBE including the oddly named d.no_.01-Final.pdf, and 55
for 2025-26. It resolves ZERO for 2023-24 and says so: that cycle is served as d01.pdf to
d54.pdf, no file is named DemandBook*, so the range cannot be found and the run records
"no DemandBook* file for 2023-2024" rather than inventing one. That is the intended
behaviour. This collector exists to take the current cycle each month, and a back-fill of
2023-24 should be a deliberate decision with its own naming rule, not something this file
guesses at.
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

INDEX = "https://financedept.tn.gov.in/en/budget-publications/"

# The YEAR cell. Written `2026-2027(RBE)`, `2026-2027 (IBE)` and bare `2025-2026` on the
# same page, so the space before the bracket is optional and the marker may be absent.
YEAR_CELL = re.compile(r"(\d{4})\s*-\s*(\d{4})\s*(?:\(\s*([A-Z]{2,4})\s*\))?")

# The serial the page prints in front of every title: "04. SOCIAL JUSTICE DEPARTMENT".
SERIAL = re.compile(r"^\s*(\d{1,3})\s*\.")

# The filename family that marks a row as a department demand rather than one of the
# other publications on the same table. Used ONLY to find the highest demand serial, never
# to decide whether an individual row is wanted. See the module docstring.
DEMAND_FILE = re.compile(r"^demandbook", re.I)

VARIANTS = {
    "RBE": "Revised Budget Estimate, the budget in force for the year",
    "IBE": "Interim Budget Estimate, the vote on account the revised budget replaced",
}


def long_cycle(cycle):
    """2026-27 is how this repo names a cycle; the Tamil Nadu page writes 2026-2027."""
    m = re.match(r"^(\d{4})-(\d{2})$", cycle)
    if not m:
        return cycle
    return "%s-%d" % (m.group(1), int(m.group(1)[:2] + m.group(2)))


def _text(fragment):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def rows_of(body):
    """Every table row on the page, as (year, variant, serial, title, url).

    The page is WordPress plus a table plugin, so a row is a plain <tr> of <td>s: the
    YEAR, then the linked title, then the same URL again in a column the CSS hides.
    """
    out = []
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I):
        frag = m.group(1)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", frag, re.S | re.I)
        if len(tds) < 2:
            continue
        ym = YEAR_CELL.search(_text(tds[0]))
        if not ym:
            continue
        href = re.search(r'href="([^"]+\.pdf[^"]*)"', frag, re.I)
        if not href:
            continue
        # Strip the "#new_tab" the plugin appends: it is a hint to the front end and not
        # part of the address. Fetching it is harmless, but the archive should record the
        # document's URL and not the page's UI.
        url = urllib.parse.urljoin(INDEX, html.unescape(href.group(1))).split("#")[0]
        title = _text(tds[1])
        sm = SERIAL.match(title)
        out.append(("%s-%s" % (ym.group(1), ym.group(2)),
                    (ym.group(3) or "").upper() or None,
                    int(sm.group(1)) if sm else None, title, url))
    return out


def discover(body, cycle, variant):
    """Resolve the wanted demand books off the publications page.

    Returns (books, others, notes, err) where books is {serial: (title, url)}.
    """
    rows = rows_of(body)
    if not rows:
        return {}, {}, {}, "no table rows on the publications page"

    want_year = long_cycle(cycle)
    mine = [r for r in rows if r[0] == want_year and r[1] == variant and r[2]]
    if not mine:
        seen = sorted({(r[0] + ("(%s)" % r[1] if r[1] else "")) for r in rows})
        return {}, {}, {}, ("no rows for %s %s; the page carries %s"
                            % (want_year, variant, ", ".join(seen)))

    # The highest serial the page serves under a DemandBook* name is the last department
    # demand. Everything above it on the same table is Debt Charges, a works list or a
    # statement, and everything below it is a demand however its own file is named.
    last = max((s for _, _, s, _, u in mine
                if DEMAND_FILE.match(u.rsplit("/", 1)[-1])), default=0)
    if not last:
        return {}, {}, {}, "no DemandBook* file for %s %s" % (want_year, variant)

    books, notes = {}, {}
    for serial in range(1, last + 1):
        hits = sorted({(t, u) for _, _, s, t, u in mine if s == serial}, key=lambda x: x[1])
        # A serial appearing twice with the SAME url is the Charged Appropriation table
        # repeating a row of the Detailed Demand List, which it does for demands 55 to 57.
        # Two different urls means the page changed shape, and a guess would be
        # indistinguishable from a read.
        urls = {u for _, u in hits}
        if len(urls) == 1:
            books[serial] = hits[0]
        elif not urls:
            notes[serial] = "no row for demand %d" % serial
        else:
            notes[serial] = ("%d different urls for demand %d, refusing to guess: %s"
                             % (len(urls), serial, ", ".join(sorted(
                                 u.rsplit("/", 1)[-1] for u in urls))))

    # Every other cut of the same cycle, recorded so the archive says what was NOT taken.
    others = {}
    for r in rows:
        if r[0] != want_year or r[1] == variant or not r[2]:
            continue
        others.setdefault(r[1] or "none", {})[str(r[2])] = r[4]

    return books, others, notes, None


def collect(cycle="2026-27", variant="RBE", index_url=INDEX, date=None, pace=1.5):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "tamilnadu", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "tamilnadu", "started": utcnow(), "base": index_url,
           "cycle": cycle, "variant": variant,
           "variant_is": VARIANTS.get(variant, "unrecognised variant marker"),
           "variant_note": (
               "Tamil Nadu presented two budgets for 2026-27 because it is an election "
               "year: an Interim Budget Estimate on 13 February 2026 and a Revised "
               "Budget Estimate on 5 August 2026. Both are budget estimates FOR 2026-27 "
               "and neither is a mid-year revision of 2025-26. The RBE set is collected "
               "because it is the appropriation in force and because its books print the "
               "interim figure in their own third money column, so it contains the other "
               "set's number and the other set does not contain this one."),
           "books": {}, "errors": [], "status_histogram": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    r = fetch(index_url, timeout=120, pace=pace)
    note(r.status)
    if not r.ok:
        man["errors"].append({"stage": "index", "why": "http %s" % r.status})
        write_json("archive/tamilnadu/%s/_manifest.json" % date, man)
        return man
    with gzip.open(os.path.join(out_dir, "index.html.gz"), "wb") as fh:
        fh.write(r.body)
    man["index_bytes"] = len(r.body)
    body = r.body.decode("utf-8", "replace")
    man["pdfs_on_index"] = len(set(re.findall(r'href="([^"]+\.pdf[^"]*)"', body, re.I)))

    books, others, notes, err = discover(body, cycle, variant)
    if err:
        man["errors"].append({"stage": "index", "why": err})
        write_json("archive/tamilnadu/%s/_manifest.json" % date, man)
        return man
    man["books_expected"] = sorted(books)
    man["demands_on_index"] = max(books) if books else 0
    man["other_variants"] = others
    for serial, why in sorted(notes.items()):
        man["errors"].append({"stage": "demand-%02d" % serial, "why": why})

    for serial in sorted(books):
        title, url = books[serial]
        book = "demand-%02d" % serial
        # 180s rather than the default 45. The larger demand books run to several MB and
        # a timeout on a slow link would look like a missing department.
        got = fetch(url, timeout=180, pace=pace)
        note(got.status)
        if not got.ok:
            man["errors"].append({"stage": book, "why": "http %s" % got.status})
            continue
        # A PDF that is really an error page is a valid write and the failure mode that
        # matters, so check the magic bytes here rather than trusting the status.
        if not got.body.startswith(b"%PDF"):
            man["errors"].append({"stage": book, "why": "response is not a PDF"})
            continue
        bad = looks_like_error(got.body[:4096])
        if bad:
            man["errors"].append({"stage": book, "why": str(bad)})
            continue
        with gzip.open(os.path.join(out_dir, "%s.pdf.gz" % book), "wb") as fh:
            fh.write(got.body)
        man["books"][book] = {"url": url, "bytes": len(got.body), "sha256": got.sha256,
                              "demand": serial, "what": title}

    man["finished"] = utcnow()
    man["books_collected"] = len(man["books"])
    write_json("archive/tamilnadu/%s/_manifest.json" % date, man)
    return man


def main():
    ap = argparse.ArgumentParser(
        description="Archive the Tamil Nadu per-department Demand Books.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--variant", default="RBE", choices=sorted(VARIANTS),
                    help="which of the year's budgets to take; see the module docstring")
    ap.add_argument("--index", default=INDEX)
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.5)
    a = ap.parse_args()
    man = collect(a.cycle, a.variant, a.index, a.date, a.pace)
    print("tamilnadu %s %s: %d of %d demand books archived from %d PDFs on the index"
          % (a.cycle, a.variant, man.get("books_collected", 0),
             len(man.get("books_expected") or ()), man.get("pdfs_on_index", 0)))
    for b, d in sorted(man.get("books", {}).items()):
        print("    %-11s%11s bytes   %s" % (b, format(d["bytes"], ","), d["what"][:58]))
    for v, m in sorted((man.get("other_variants") or {}).items()):
        print("    not collected: %s, %d documents for this cycle" % (v, len(m)))
    for e in man.get("errors", []):
        print("    ERROR %s: %s" % (e["stage"], e["why"]))


if __name__ == "__main__":
    main()
