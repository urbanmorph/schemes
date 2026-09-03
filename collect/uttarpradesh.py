"""
Uttar Pradesh state budget collector — raw PDF bytes only, no extraction.

FROZEN CODE. Read PLAN.md §7 before editing.

Uttar Pradesh is the largest state in India and has the smallest portal listing relative
to its size in this register: myScheme lists 47 schemes for it, DBT Bharat counts 193, and
its own grant-wise volumes name on the order of 8,000 budget lines. It was surveyed and
recorded as a refusal, on language rather than on layout, and that has been revisited:
myScheme lists Uttar Pradesh's schemes in romanised Hindi rather than in English, so the
join is a change of script and not a translation. See parse/devanagari.py.

    archive/uttarpradesh/D/GrantWisepdf.html.gz   the grant index, so discovery is auditable
    archive/uttarpradesh/D/khand2part2.html.gz    the memorandum index, same reason
    archive/uttarpradesh/D/Gr<NN>.pdf.gz          one grant volume, raw bytes
    archive/uttarpradesh/D/memorandum.pdf.gz      Memorandum on Grant Wise Demand
    archive/uttarpradesh/D/_manifest.json

WHAT IS DISCOVERED AND WHY. The grant volumes are not linked. `GrantWisepdf.html` carries a
<select> of 96 grants and a <select> of 31 budget years, and a line of JavaScript builds
`PDF{year}/Gr{grant}.pdf` from the pair. So the addresses are constructed here, which is
addressing and not adaptation, and the page they are constructed from is archived beside
the PDFs so a later reader can check the construction against the source.

The grant dropdown is worth archiving for a second reason: it is the only place the state
publishes the DEPARTMENT NAME against each grant number. The volumes themselves carry it
only as a page heading.

THE CYCLE IS ASSERTED, NOT ASSUMED. Telangana's finance portal serves a budget-volumes page
whose newest directory is a year behind the live cycle, and building from it would have
published last year's allocations as this year's. Here the year is a path component, so the
failure would be quieter still: `PDF25_26/Gr01.pdf` is a perfectly valid 200. The requested
cycle is therefore checked against the year dropdown before anything is fetched, and a
cycle the state does not offer is an error rather than a silent fetch of a neighbouring
year.
"""

import argparse
import gzip
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, fetch, looks_like_error, utcnow, today, write_json  # noqa: E402

BASE = "https://budget.up.nic.in"
GRANT_INDEX = f"{BASE}/GrantWisepdf.html"
MEMO_INDEX = f"{BASE}/khand2part2.html"

OPTION = re.compile(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', re.S)


def options(body, select_name):
    """The <option> pairs of one named <select>, in document order."""
    m = re.search(rf'<select[^>]*name="{select_name}"[^>]*>(.*?)</select>', body, re.S | re.I)
    if not m:
        return []
    out = []
    for value, label in OPTION.findall(m.group(1)):
        text = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        out.append((value.strip(), text))
    return out


def cycle_key(cycle):
    """2026-27 -> 26_27, which is how the year appears in the path and the dropdown."""
    m = re.match(r"^(\d{4})-(\d{2})(\d{2})?$", cycle.strip())
    if not m:
        raise SystemExit(f"cycle {cycle!r} is not of the form 2026-27")
    return f"{m.group(1)[2:]}_{m.group(2)}"


def collect(cycle, date=None, pace=1.2, limit=None):
    date = date or today()
    out_dir = os.path.join(ROOT, "archive", "uttarpradesh", date)
    os.makedirs(out_dir, exist_ok=True)
    man = {"source": "uttarpradesh", "started": utcnow(), "base": BASE, "cycle": cycle,
           "grants": {}, "errors": [], "status_histogram": {}}

    def note(s):
        k = str(s)
        man["status_histogram"][k] = man["status_histogram"].get(k, 0) + 1

    def fail(stage, why):
        man["errors"].append({"stage": stage, "why": why})

    r = fetch(GRANT_INDEX, pace=pace)
    note(r.status)
    if not r.ok:
        fail("grant index", f"http {r.status}")
        write_json(f"archive/uttarpradesh/{date}/_manifest.json", man)
        return man
    body = r.body.decode("utf-8", "replace")
    with gzip.open(os.path.join(out_dir, "GrantWisepdf.html.gz"), "wb") as fh:
        fh.write(r.body)

    years = options(body, "drpBudgetYr")
    key = cycle_key(cycle)
    offered = {v for v, _ in years}
    if key not in offered:
        # Not a warning. Fetching PDF{key}/ for a year the state does not list would either
        # 404 or, worse, serve a neighbouring cycle's book with no sign that it had.
        fail("cycle", f"{cycle} ({key}) is not in the year dropdown")
        man["years_offered"] = sorted(offered)
        write_json(f"archive/uttarpradesh/{date}/_manifest.json", man)
        return man
    man["cycle_key"] = key
    man["latest_cycle_offered"] = years[-1][0] if years else None
    man["years_offered"] = len(years)

    # value "00" is the "-----SELECT------" placeholder, not a grant.
    grants = [(v, t) for v, t in options(body, "drpGrant") if re.fullmatch(r"\d{2}", v or "")
              and v != "00"]
    man["grants_listed"] = len(grants)
    if limit:
        grants = grants[:limit]

    for value, label in grants:
        url = f"{BASE}/PDF{key}/Gr{value}.pdf"
        r = fetch(url, pace=pace)
        note(r.status)
        if not r.ok:
            # A missing grant volume is ordinary here: the survey found 91 of 97 live, and
            # a state is entitled not to publish a volume for a grant with no provision.
            # It is recorded rather than raised, and the count is in the manifest.
            fail(f"Gr{value}", f"http {r.status}")
            continue
        if not r.body.startswith(b"%PDF"):
            fail(f"Gr{value}", "response is not a PDF")
            continue
        bad = looks_like_error(r.body[:4096])
        if bad:
            fail(f"Gr{value}", str(bad))
            continue
        with gzip.open(os.path.join(out_dir, f"Gr{value}.pdf.gz"), "wb") as fh:
            fh.write(r.body)
        man["grants"][value] = {"url": url, "bytes": len(r.body), "department": label}

    # The Memorandum on Grant Wise Demand is a single 186-page volume covering every grant.
    # It is linked rather than constructed, so the link is read from the page.
    r = fetch(MEMO_INDEX, pace=pace)
    note(r.status)
    if r.ok:
        with gzip.open(os.path.join(out_dir, "khand2part2.html.gz"), "wb") as fh:
            fh.write(r.body)
        page = r.body.decode("utf-8", "replace")
        want = f"khand2part2_{cycle[:4]}_{int(cycle[:4]) + 1}.pdf"
        href = next((h for h in re.findall(r'href="([^"]+\.pdf)"', page, re.I)
                     if h.endswith(want)), None)
        if not href:
            fail("memorandum", f"no link ending {want} on {MEMO_INDEX}")
        else:
            url = href if href.startswith("http") else f"{BASE}/{href.lstrip('/')}"
            r2 = fetch(url, pace=pace)
            note(r2.status)
            if r2.ok and r2.body.startswith(b"%PDF"):
                with gzip.open(os.path.join(out_dir, "memorandum.pdf.gz"), "wb") as fh:
                    fh.write(r2.body)
                man["memorandum"] = {"url": url, "bytes": len(r2.body),
                                     "what": "Memorandum on Grant Wise Demand, Khand-2 part 2"}
            else:
                fail("memorandum", f"http {r2.status}")
    else:
        fail("memorandum index", f"http {r.status}")

    man["finished"] = utcnow()
    man["grants_collected"] = len(man["grants"])
    write_json(f"archive/uttarpradesh/{date}/_manifest.json", man)
    return man


def main():
    ap = argparse.ArgumentParser(description="Archive the Uttar Pradesh grant-wise budget volumes.")
    ap.add_argument("--cycle", default="2026-27")
    ap.add_argument("--date")
    ap.add_argument("--pace", type=float, default=1.2)
    ap.add_argument("--limit", type=int, help="first N grants only, for a smoke test")
    a = ap.parse_args()
    man = collect(a.cycle, a.date, a.pace, a.limit)
    print(f"uttarpradesh {a.cycle}: {man.get('grants_collected', 0)} of "
          f"{man.get('grants_listed', 0)} grant volumes archived")
    if man.get("memorandum"):
        print(f"    memorandum {man['memorandum']['bytes']:>12,} bytes")
    total = sum(d["bytes"] for d in man.get("grants", {}).values())
    if total:
        print(f"    grants     {total:>12,} bytes")
    for e in man.get("errors", [])[:8]:
        print(f"    ERROR {e['stage']}: {e['why']}")
    if len(man.get("errors", [])) > 8:
        print(f"    ... and {len(man['errors']) - 8} more")


if __name__ == "__main__":
    main()
