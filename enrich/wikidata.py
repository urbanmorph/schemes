"""
Enrichment from Wikidata and Wikipedia — a SECONDARY source, kept strictly apart.

This is not a collector and it is not `collect/`. Nothing here is ever written into
data/myscheme/, and nothing here is ever counted by parse/checks.py.

The reason is the register's whole claim. Tier-1 checks measure what the *government*
publishes: "99% of schemes record no end date" is a statement about myScheme's fields.
If a launch date sourced from Wikipedia were merged into the canonical record, that
number would silently become a measure of how much Wikipedia we managed to scrape, and
the register would be reporting on itself. So enrichment lives in its own namespace,
carries its own provenance per field, and is shown to readers as clearly borrowed.

    archive/wikidata/<date>/lookups.ndjson.gz   raw API responses, one per scheme
    data/enrichment/wikidata.json               matched fields + confidence

Matching is conservative by design. Scheme names are often generic — "Marriage
Assistance" resolves to a Wikidata item about a bachelor tax — so a match must clear a
name-similarity floor AND carry an India signal (country = Q668, or an India-related
description). Every accepted match stores its score so a reader can dispute it, and
anything below the floor is recorded as a miss rather than guessed at.
"""

import argparse
import difflib
import gzip
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, fetch, utcnow, today, write_json  # noqa: E402

WD = "https://www.wikidata.org"
WP = "https://en.wikipedia.org"
INDIA = "Q668"

# Date properties, best first. P571 inception is the one that ought to hold a scheme's
# launch date and almost never does; P580 start time and P1619 official opening carry it
# more often in practice, and P577 publication date is right for schemes created by an
# Act. Measured on four flagship schemes: PM-KISAN and PMAY have none of them, MGNREGA
# has P577, Ayushman Bharat has P580.
DATE_PROPS = [("P571", "inception"), ("P580", "start time"),
              ("P1619", "official opening"), ("P577", "publication date")]

MATCH_FLOOR = 0.86          # normalised name similarity below which a hit is not a match
STOP = {"scheme", "yojana", "yojna", "programme", "program", "mission", "abhiyan",
        "the", "of", "for", "and", "a", "an", "in", "to"}


def norm(s):
    s = re.sub(r"\(.*?\)", " ", (s or "").lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 2}


def similarity(a, b):
    """Sequence ratio on normalised names, floored by content-token overlap.

    Ratio alone rewards two long generic names that share boilerplate; token overlap
    alone rewards a single shared word. Taking the lower of the two is the conservative
    reading, and conservative is the right bias when a wrong match publishes a wrong
    fact under a government scheme's name.
    """
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = content_tokens(a), content_tokens(b)
    overlap = len(ta & tb) / max(len(ta | tb), 1) if (ta and tb) else 0.0
    return min(ratio, (overlap + ratio) / 2)


def api(url, pace):
    r = fetch(url, headers={"Accept": "application/json"}, timeout=30, pace=pace)
    if not r.ok:
        return None
    try:
        return r.json()
    except Exception:
        return None


def india_signal(ent):
    """Is this entity actually about something Indian? Returns (bool, why)."""
    claims = ent.get("claims", {})
    for pid in ("P17", "P1001", "P137"):        # country, applies to jurisdiction, operator
        for c in claims.get(pid, []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and v.get("id") == INDIA:
                return True, f"{pid}={INDIA}"
    desc = (ent.get("descriptions", {}).get("en", {}) or {}).get("value", "").lower()
    if "india" in desc or "indian" in desc:
        return True, "description mentions India"
    return False, "no India signal"


def first_date(ent):
    for pid, label in DATE_PROPS:
        for c in ent.get("claims", {}).get(pid, []):
            t = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(t, dict) and t.get("time"):
                iso = t["time"][1:11]
                if iso.endswith("-00-00"):
                    iso = iso[:4]
                elif iso.endswith("-00"):
                    iso = iso[:7]
                return iso, label, pid
    return None, None, None


def lookup(name, pace):
    """Search Wikidata for `name` and return (record, raw) or (None, raw)."""
    q = urllib.parse.quote(name[:180])
    raw = {"query": name}
    s = api(f"{WD}/w/api.php?action=wbsearchentities&search={q}"
            f"&language=en&format=json&limit=5", pace)
    raw["search"] = s
    if not s or not s.get("search"):
        return None, raw

    best = None
    for hit in s["search"]:
        score = similarity(name, hit.get("label", ""))
        if best is None or score > best[0]:
            best = (score, hit)
    score, hit = best
    raw["best"] = {"id": hit.get("id"), "label": hit.get("label"), "score": round(score, 3)}
    if score < MATCH_FLOOR:
        raw["rejected"] = f"similarity {score:.2f} below floor {MATCH_FLOOR}"
        return None, raw

    qid = hit["id"]
    ed = api(f"{WD}/wiki/Special:EntityData/{qid}.json", pace)
    if not ed:
        return None, raw
    ent = (ed.get("entities") or {}).get(qid) or {}
    raw["entity_claims"] = sorted(ent.get("claims", {}).keys())

    ok, why = india_signal(ent)
    if not ok:
        raw["rejected"] = f"matched {qid} but {why}"
        return None, raw

    date, date_label, date_pid = first_date(ent)
    rec = {
        "qid": qid,
        "wikidata_label": hit.get("label"),
        "match_score": round(score, 3),
        "india_signal": why,
        "description": (ent.get("descriptions", {}).get("en", {}) or {}).get("value"),
        "start_date": date,
        "start_date_kind": date_label,
        "start_date_property": date_pid,
        "official_website": next(
            (c["mainsnak"]["datavalue"]["value"]
             for c in ent.get("claims", {}).get("P856", [])
             if c.get("mainsnak", {}).get("datavalue")), None),
        "enwiki": (ent.get("sitelinks", {}).get("enwiki", {}) or {}).get("title"),
        "source_url": f"{WD}/wiki/{qid}",
    }
    if rec["enwiki"]:
        t = urllib.parse.quote(rec["enwiki"].replace(" ", "_"))
        sm = api(f"{WP}/api/rest_v1/page/summary/{t}", pace)
        raw["summary"] = sm
        if sm and sm.get("extract"):
            rec["summary"] = sm["extract"]
            rec["summary_url"] = (sm.get("content_urls", {}).get("desktop", {}) or {}).get("page")
    return rec, raw


def run(date, limit=None, level=None, pace=0.35):
    schemes = (json.load(open(os.path.join(ROOT, "data", "checks.json")))
               .get("schemes", []))
    if level:
        schemes = [s for s in schemes if s.get("level_value") == level]
    # Enrich where the register is actually thin, hardest cases first.
    schemes.sort(key=lambda s: s["passed"])
    if limit:
        schemes = schemes[:limit]

    out_dir = os.path.join(ROOT, "archive", "wikidata", date)
    os.makedirs(out_dir, exist_ok=True)
    found, seen = {}, 0
    stats = {"matched": 0, "no_result": 0, "below_floor": 0, "no_india": 0,
             "with_date": 0, "with_summary": 0}

    with gzip.open(os.path.join(out_dir, "lookups.ndjson.gz"), "wb") as fh:
        for s in schemes:
            seen += 1
            rec, raw = lookup(s["name"] or s["slug"], pace)
            fh.write(json.dumps({"slug": s["slug"], "raw": raw},
                                ensure_ascii=False)[:200000].encode() + b"\n")
            if rec:
                found[s["slug"]] = rec
                stats["matched"] += 1
                stats["with_date"] += bool(rec.get("start_date"))
                stats["with_summary"] += bool(rec.get("summary"))
            elif not raw.get("search", {}).get("search"):
                stats["no_result"] += 1
            elif "below floor" in str(raw.get("rejected", "")):
                stats["below_floor"] += 1
            else:
                stats["no_india"] += 1
            if seen % 50 == 0:
                print(f"    {seen}/{len(schemes)}  matched={stats['matched']}"
                      f"  dated={stats['with_date']}", flush=True)

    write_json("data/enrichment/wikidata.json", {
        "snapshot": date,
        "fetched": utcnow(),
        "source": "Wikidata + English Wikipedia",
        "licence": "Wikidata CC0; Wikipedia text CC BY-SA 4.0",
        "match_floor": MATCH_FLOOR,
        "schemes_attempted": seen,
        "stats": stats,
        "caveat": ("Secondary source. These values are NOT what the Indian government "
                   "publishes about these schemes, and are never counted in the "
                   "documentation checks. Each carries a match score; treat a low score "
                   "as a claim to verify, not a fact."),
        "schemes": found,
    })
    return stats, seen


def main():
    ap = argparse.ArgumentParser(description="Enrich schemes from Wikidata/Wikipedia.")
    ap.add_argument("--date", default=today())
    ap.add_argument("--limit", type=int)
    ap.add_argument("--level", choices=["central", "state"])
    ap.add_argument("--pace", type=float, default=0.35)
    a = ap.parse_args()
    print(f"Wikidata enrichment {a.date}"
          + (f" · level={a.level}" if a.level else "") + (f" · limit={a.limit}" if a.limit else ""))
    stats, seen = run(a.date, a.limit, a.level, a.pace)
    print(f"\n  attempted {seen}")
    for k, v in stats.items():
        print(f"    {k:<14}{v:>6}" + (f"   {100*v/seen:.1f}%" if seen else ""))


if __name__ == "__main__":
    main()
