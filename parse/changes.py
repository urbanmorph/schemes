"""
Diff two archived snapshots, field by field.

AGENT-EDITABLE (PLAN.md §7). Reads archive/, writes data/changes.json. Never fetches.

This exists because the /changes page was reading `git log` over data/, which is the
history of THIS REPOSITORY, not of the government. With a single snapshot collected,
every commit touching data/ is a re-parse of the same bytes, so a page headed "What the
government changed without saying" was listing commit subjects like "Schemes first, a
live stats rail, state filter" against 4,776 files changed. That is a claim about the
state, evidenced by my own development log. Nothing about it was true.

A change here is a difference between two SNAPSHOTS: the same scheme, fetched a month
apart, saying something different. Anything else is noise from this repository and does
not belong on a page that points at government.

    data/changes.json   added, removed and per-field changes between two snapshots
    data/lastmod.json   per slug, the snapshot its watched fields last changed in

Only fields where a difference means something are compared. Ordering inside lists is
normalised first, because a source that returns the same three references in a different
order has not changed anything and reporting it as change would drown the real ones.
"""

import argparse
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def snapshots():
    """Archived snapshot dates, oldest first. A snapshot is a details file, not a commit."""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "archive", "myscheme", "*"))):
        if os.path.isfile(os.path.join(p, "details.ndjson.gz")):
            out.append(os.path.basename(p))
    return out


def _lbl(v):
    if isinstance(v, dict):
        return v.get("label")
    if isinstance(v, list):
        return sorted(x.get("label") if isinstance(x, dict) else str(x) for x in v if x)
    return v


def fields(rec):
    """The fields worth watching, flattened and order-normalised."""
    en = (rec or {}).get("en") or {}
    b = en.get("basicDetails") or {}
    c = en.get("schemeContent") or {}
    el = en.get("eligibilityCriteria") or {}
    return {
        "name": b.get("schemeName"),
        "short title": b.get("schemeShortTitle"),
        "start date": b.get("schemeOpenDate"),
        "end date": b.get("schemeCloseDate"),
        "level": _lbl(b.get("level")),
        "type": _lbl(b.get("schemeType")),
        "ministry": _lbl(b.get("nodalMinistryName")),
        "department": _lbl(b.get("nodalDepartmentName")),
        "DBT flag": b.get("dbtScheme"),
        "implementing agency": b.get("implementingAgency"),
        "beneficiaries": _lbl(b.get("targetBeneficiaries")),
        "description": (c.get("briefDescription") or "").strip() or None,
        "benefits": (c.get("benefits_md") or "").strip() or None,
        "eligibility": (el.get("eligibilityDescription_md") or "").strip() or None,
        "reference URLs": sorted(
            r.get("url") for r in (c.get("references") or [])
            if isinstance(r, dict) and r.get("url")),
        "application URLs": sorted(
            a.get("url") for a in (en.get("applicationProcess") or [])
            if isinstance(a, dict) and a.get("url")),
    }


def load(date):
    p = os.path.join(ROOT, "archive", "myscheme", date, "details.ndjson.gz")
    out = {}
    with gzip.open(p, "rb") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            body = row.get("body") or {}
            rec = body.get("data") if isinstance(body.get("data"), dict) else body
            out[row.get("slug")] = fields(rec)
    return out


def shorten(v, n=110):
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v)
    if v is None:
        return None
    s = " ".join(str(v).split())
    return s if len(s) <= n else s[:n - 1] + "…"


def diff(older, newer):
    a, b = load(older), load(newer)
    added = [{"slug": s, "name": b[s].get("name")} for s in sorted(set(b) - set(a))]
    removed = [{"slug": s, "name": a[s].get("name")} for s in sorted(set(a) - set(b))]
    changed = []
    for s in sorted(set(a) & set(b)):
        deltas = [{"field": k, "from": shorten(a[s].get(k)), "to": shorten(b[s].get(k))}
                  for k in a[s] if a[s].get(k) != b[s].get(k)]
        if deltas:
            changed.append({"slug": s, "name": b[s].get("name"), "changes": deltas})
    return added, removed, changed


def last_changed(snaps, loader=load):
    """slug -> the snapshot in which its watched fields last differed from the one before.

    For the sitemap's lastmod. Stamping every page with the build date tells a crawler that
    all 11,000 changed on every deploy, and a crawler that is told that learns to ignore the
    field. A record unchanged since the first snapshot is dated by that snapshot, which is
    as far back as this archive can see. Only two snapshots are ever held in memory.
    """
    out, prev = {}, {}
    for date in snaps:
        cur = loader(date) or {}
        for s, f in cur.items():
            if prev.get(s) != f:
                out[s] = date
        prev = cur
    return {s: d for s, d in out.items() if s in prev}


def run(older=None, newer=None):
    snaps = snapshots()
    out = {"built": utcnow(), "snapshots_held": len(snaps), "snapshots": snaps}
    # Written before the two-snapshot test: one snapshot still dates every record.
    write_json("data/lastmod.json", {"built": out["built"], "snapshots": snaps,
                                     "last_changed": dict(sorted(last_changed(snaps).items()))})
    if len(snaps) < 2:
        # Not an error. A change feed needs two snapshots and cannot be back-filled,
        # which is the entire reason collection started before the site did.
        out.update(comparable=False, older=None, newer=None,
                   added=[], removed=[], changed=[],
                   note="A change feed needs two snapshots. Only one has been collected.")
        write_json("data/changes.json", out)
        return out
    older = older or snaps[-2]
    newer = newer or snaps[-1]
    added, removed, changed = diff(older, newer)
    field_counts = {}
    for c in changed:
        for d in c["changes"]:
            field_counts[d["field"]] = field_counts.get(d["field"], 0) + 1
    out.update(comparable=True, older=older, newer=newer,
               added=added[:300], removed=removed[:300], changed=changed[:400],
               added_total=len(added), removed_total=len(removed),
               changed_total=len(changed),
               by_field=dict(sorted(field_counts.items(), key=lambda kv: -kv[1])))
    write_json("data/changes.json", out)
    return out


def selftest():
    snaps = {"2026-08-30": {"a": {"name": "A"}, "b": {"name": "B"}},
             "2026-09-02": {"a": {"name": "A"}, "b": {"name": "B2"}, "c": {"name": "C"}},
             "2026-09-03": {"a": {"name": "A"}, "b": {"name": "B2"}, "c": {"name": "C"}}}
    got = last_changed(sorted(snaps), snaps.get)
    want = {"a": "2026-08-30", "b": "2026-09-02", "c": "2026-09-02"}
    bad = 0
    for s, w in want.items():
        ok = got.get(s) == w
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {s}: want {w} got {got.get(s)}")
    # a record that leaves and comes back has changed, as far as a reader can tell
    gone = {"x": {"s": {"n": 1}}, "y": {}, "z": {"s": {"n": 1}}}
    ok = last_changed(["x", "y", "z"], gone.get) == {"s": "z"}
    bad += not ok
    print(f"  {'ok  ' if ok else 'FAIL'} a removed record that returns is dated by its return")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Diff two archived myScheme snapshots.")
    ap.add_argument("--older")
    ap.add_argument("--newer")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        print("last_changed self-test")
        sys.exit(1 if selftest() else 0)
    o = run(a.older, a.newer)
    if not o["comparable"]:
        print(f"snapshots held: {o['snapshots_held']}. {o['note']}")
        return
    print(f"{o['older']} -> {o['newer']}")
    print(f"  added   {o['added_total']}")
    print(f"  removed {o['removed_total']}")
    print(f"  changed {o['changed_total']}")
    for k, v in list(o["by_field"].items())[:10]:
        print(f"     {k:<22}{v}")


if __name__ == "__main__":
    main()
