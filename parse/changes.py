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
import importlib.util
import json
import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def _parser(name):
    """parse/<name>.py, by path. collect/ has a module of the same name, and each parser
    puts collect/ first on sys.path as it loads, so a plain import finds the wrong one."""
    spec = importlib.util.spec_from_file_location(
        f"parse_{name}", os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cag_parse, dbt_parse = _parser("cag"), _parser("dbt")


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


def compare(a, b, fields=None):
    """Two {key: record} snapshots: keys added, keys removed, and per kept key the fields
    that differ as (field, before, after). Without `fields`, every field of the older
    record is watched."""
    changed = {}
    for k in sorted(set(a) & set(b)):
        d = [(f, a[k].get(f), b[k].get(f)) for f in (fields or a[k])
             if a[k].get(f) != b[k].get(f)]
        if d:
            changed[k] = d
    return sorted(set(b) - set(a)), sorted(set(a) - set(b)), changed


def deltas(d):
    return [{"field": f, "from": shorten(x), "to": shorten(y)} for f, x, y in d]


def diff(a, b):
    added, removed, changed = compare(a, b)
    return ([{"slug": s, "name": b[s].get("name")} for s in added],
            [{"slug": s, "name": a[s].get("name")} for s in removed],
            [{"slug": s, "name": b[s].get("name"), "changes": deltas(d)}
             for s, d in changed.items()])


def complete(source, ok):
    """Snapshot dates of an archived source whose manifest passes `ok`, oldest first. A
    crawl that did not finish would show every report it missed as removed."""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "archive", source, "*", "_manifest.json"))):
        with open(p, encoding="utf-8") as fh:
            if ok(json.load(fh)):
                out.append(os.path.basename(os.path.dirname(p)))
    return out


# What a CAG listing says about a report. Not the PDF URL: the CAG moves its files between
# CDN hosts, and 2,722 links changing host in October 2026 is not 2,722 reports changing.
CAG_FIELDS = ("title", "tabled", "audit_type", "government", "sector")


def cag_changes():
    dates = complete("cag", lambda m: m.get("complete"))
    if len(dates) < 2:
        return {"comparable": False, "snapshots": dates}
    older, newer = dates[-2:]
    a = {r["id"]: r for r in cag_parse.read(older)[0]}
    b = {r["id"]: r for r in cag_parse.read(newer)[0]}
    added, removed, changed = compare(a, b, CAG_FIELDS)

    def brief(r):
        return {k: r.get(k) for k in ("id", "title", "government", "tabled", "detail_url")}
    return {"comparable": True, "older": older, "newer": newer,
            "reports_before": len(a), "reports_after": len(b),
            "added": [brief(b[k]) for k in added],
            "removed": [brief(a[k]) for k in removed],
            "edited": [{**brief(b[k]), "changes": deltas(d)} for k, d in changed.items()],
            "pdf_host_moved": sum(
                1 for k in set(a) & set(b)
                if urlsplit(a[k].get("pdf_url") or "").netloc
                != urlsplit(b[k].get("pdf_url") or "").netloc)}


def dbt_changes():
    dates = complete("dbt", lambda m: not m.get("error_count")
                     and m.get("states_written") == m.get("states_expected"))
    if len(dates) < 2:
        return {"comparable": False, "snapshots": dates}
    older, newer = dates[-2:]
    (sa, ca), (sb, cb) = dbt_parse.read(older), dbt_parse.read(newer)
    return {"comparable": True, "older": older, "newer": newer,
            "total_before": sum(v or 0 for v in sa.values()),
            "total_after": sum(v or 0 for v in sb.values()),
            "central_before": ca, "central_after": cb,
            "states": [{"state": s, "from": sa.get(s), "to": sb.get(s)}
                       for s in sorted(set(sa) | set(sb)) if sa.get(s) != sb.get(s)]}


def history(snaps, loader=load):
    """One pass over the snapshots, oldest first, reading each once. Returns:

    - slug -> the snapshot in which its watched fields last differed from the one before.
      For the sitemap's lastmod. Stamping every page with the build date tells a crawler
      that all 11,000 changed on every deploy, and a crawler that is told that learns to
      ignore the field. A record unchanged since the first snapshot is dated by that
      snapshot, which is as far back as this archive can see.
    - the snapshot from which every later one holds exactly the same records, or None with
      fewer than two to compare. A month with no change is a finding about the source and
      is published as one. Without it the page could only say "0 added, 0 removed", which
      reads as a feed that did not run: myScheme returned the same 4,771 records, byte for
      byte, from 30 August to 17 October 2026.
    - {date: records} for the newest two snapshots, for the diff. Only those two are ever
      held in memory.
    """
    out, since, prev, tail = {}, None, None, {}
    for date in snaps:
        cur = loader(date) or {}
        if prev is None or cur != prev:
            since = date
        for s, f in cur.items():
            if (prev or {}).get(s) != f:
                out[s] = date
        tail = {d: r for d, r in tail.items() if r is prev} | {date: cur}
        prev = cur
    return ({s: d for s, d in out.items() if s in (prev or {})},
            since if len(snaps) > 1 else None, tail)


def run(older=None, newer=None):
    snaps = snapshots()
    last, quiet, tail = history(snaps)
    out = {"built": utcnow(), "snapshots_held": len(snaps), "snapshots": snaps,
           "quiet_since": quiet, "cag": cag_changes(), "dbt": dbt_changes()}
    # Written before the two-snapshot test: one snapshot still dates every record.
    write_json("data/lastmod.json", {"built": out["built"], "snapshots": snaps,
                                     "last_changed": dict(sorted(last.items()))})
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
    a, b = (tail.get(d) or load(d) for d in (older, newer))
    added, removed, changed = diff(a, b)
    field_counts = {}
    for c in changed:
        for d in c["changes"]:
            field_counts[d["field"]] = field_counts.get(d["field"], 0) + 1
    out.update(comparable=True, older=older, newer=newer,
               added=added[:300], removed=removed[:300], changed=changed[:400],
               added_total=len(added), removed_total=len(removed),
               changed_total=len(changed), records=len(b),
               by_field=dict(sorted(field_counts.items(), key=lambda kv: -kv[1])))
    write_json("data/changes.json", out)
    return out


def selftest():
    snaps = {"2026-08-30": {"a": {"name": "A"}, "b": {"name": "B"}},
             "2026-09-02": {"a": {"name": "A"}, "b": {"name": "B2"}, "c": {"name": "C"}},
             "2026-09-03": {"a": {"name": "A"}, "b": {"name": "B2"}, "c": {"name": "C"}}}
    reads = []

    def counted(date):
        reads.append(date)
        return snaps.get(date)
    got, quiet, tail = history(sorted(snaps), counted)
    want = {"a": "2026-08-30", "b": "2026-09-02", "c": "2026-09-02"}
    bad = 0
    for s, w in want.items():
        ok = got.get(s) == w
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {s}: want {w} got {got.get(s)}")
    # a record that leaves and comes back has changed, as far as a reader can tell
    gone = {"x": {"s": {"n": 1}}, "y": {}, "z": {"s": {"n": 1}}}

    for label, got, want in [
            ("a removed record that returns is dated by its return",
             history(["x", "y", "z"], gone.get)[0], {"s": "z"}),
            ("quiet since the snapshot after the last difference", quiet, "2026-09-02"),
            ("a source whose newest snapshot moved is quiet since that one",
             history(["x", "y"], gone.get)[1], "y"),
            ("one snapshot cannot show quiet", history(["x"], gone.get)[1], None),
            ("each snapshot is read once", reads, sorted(snaps)),
            ("the newest two snapshots are kept for the diff",
             sorted(tail), ["2026-09-02", "2026-09-03"]),
            ("compare: added, removed, and only the fields that differ",
             compare({1: {"t": "a", "u": 1}, 2: {"t": "b"}},
                     {1: {"t": "A", "u": 1}, 3: {"t": "c"}}, ("t", "u")),
             ([3], [2], {1: [("t", "a", "A")]})),
            ("compare without fields watches every field of the older record",
             compare({1: {"t": "a"}}, {1: {"t": "b"}}), ([], [], {1: [("t", "a", "b")]}))]:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": want {want} got {got}"))
    return bad


def main():
    ap = argparse.ArgumentParser(description="Diff two archived myScheme snapshots.")
    ap.add_argument("--older")
    ap.add_argument("--newer")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        print("changes self-test")
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
