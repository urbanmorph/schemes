"""
The chrome every state classifier shares. The SIGNALS are never shared.

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

WHAT BELONGS HERE and what does not. Every classifier in this directory does the same four
things with its verdicts: join them to myScheme so a row already on the portal is not
reported as absent from it, sweep a threshold against hand labels, count precision over an
audit census at the publishing bar, and write one classification.json the site can read.
None of that is state-specific and all of it was being copied.

The signals are the opposite. Karnataka's strongest instrument is a purpose line at 0.947
and Haryana's purpose line is worth 0.008; Tripura's yojana measures 0.750 and its abhiyan
0.333; Jharkhand's book needs five separate negatives for places, power, residences,
utilities and administration that no other state needs at all. A shared scorer would mean
publishing the poorest common denominator of what fifteen states print, which is the
opposite of the point. Each classify_<state>.py owns its own regexes, its own weights and
its own signals_rejected, and calls this for everything else.

THE TWO BARS, once, here, because getting them the same way in every state is the whole
reason this file exists:

    publish   the accusation bar. "This is funded and no portal lists it." Every row at or
              above it carries a hand label, so precision is a COUNT and the errors are
              named. Set high; recall is sacrificed on purpose.
    listing   the F1 optimum. "The state's budget names this as a scheme." Listing a budget
              head is an annoyance; naming one as hidden is a false accusation.
"""

import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from match import probably_same, tokens, skeleton, acronyms  # noqa: E402

# Underscores and slashes are word characters to a regex and word breaks to a reader.
# TRIPURA_NATIONAL HEALTH MISSION did not match \bnational health mission\b for exactly
# that reason, and it was the last error in that state's file.
def norm(name):
    return re.sub(r"[_/]+", " ", name or "")


def myscheme_records(state):
    """myScheme's own state-level records for one state, from the archived snapshot."""
    out = []
    for f in glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if state not in ((d.get("_list") or {}).get("beneficiaryState") or []):
            continue
        b = (d.get("en") or {}).get("basicDetails") or {}
        if b.get("schemeName"):
            out.append(b["schemeName"])
    return sorted(set(out))


def joiner(names, cap=40):
    """A name -> matching myScheme record, or None.

    Candidates are ranked on (shared index keys, index) and capped. Never on
    Counter.most_common: its tie-break is insertion order, insertion order comes from
    iterating a set of strings, and hash randomisation reorders that every run. The site
    build had this bug and its page count moved on its own between builds.
    """
    idx = collections.defaultdict(set)
    for i, n in enumerate(names):
        for k in (set(tokens(n)) | {skeleton(t) for t in tokens(n)}
                  | {a for a in acronyms(n) if len(a) >= 5}):
            idx[k].add(i)

    def hit(name):
        c = collections.Counter()
        for k in sorted(set(tokens(name)) | {skeleton(t) for t in tokens(name)}
                        | {a for a in acronyms(name) if len(a) >= 5}):
            c.update(idx.get(k, ()))
        for i, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:cap]:
            if n >= 2 and probably_same(name, names[i])[0]:
                return names[i]
        return None
    return hit


def classify(key, state, score, publish, listing, rejected, row_fields=None,
             ident=None):
    """Score one state's rows, validate against its labels, and write its verdicts.

    `score(row)` returns (points, evidence) and is the only state-specific thing here.
    `row_fields(row)` adds whatever that state publishes and others do not, because the
    scheme pages render what a state prints rather than a common subset of it.
    """
    d = json.load(open(os.path.join(ROOT, "data", key, "schemes.json"), encoding="utf-8"))
    lj = json.load(open(os.path.join(ROOT, "data", key, "labels.json"), encoding="utf-8"))
    labels = {c: v["label"] for c, v in lj["labels"].items()}
    lab = {c: v == "scheme" for c, v in labels.items()}
    ms = myscheme_records(state)
    hit = joiner(ms)
    flag = f"in_myscheme_{key}"

    # `key` first, then `code`. Punjab publishes BOTH and its labels are keyed on the
    # first; most states have one or the other, so this order is safe for them and wrong
    # for none. Getting it backwards silently drops every hand label: Punjab reported 127
    # of 154 census rows unlabelled and a precision of 0.175.
    #
    # A state whose identifier is neither passes its own. Uttar Pradesh's scheme code is
    # unique only WITHIN a grant volume -- code 04 exists in all 91 of them -- so its rows
    # are keyed on grant, code and page together.
    ident = ident or (lambda r: r.get("key") or r.get("code")
                      or (r.get("hoas") or [None])[0])

    out = []
    for r in sorted(d["entries"], key=lambda x: str(ident(x))):
        s, ev = score(r)
        m = hit(r["name"])
        row = {
            "key": ident(r), "code": r.get("code"), "name": r["name"],
            "be_lakh": r.get("be_lakh"), "hoas": r.get("hoas") or [],
            "score": s, "evidence": ev,
            "verdict": "scheme" if s >= publish else "not_scheme",
            "hand_label": labels.get(ident(r)),
            flag: bool(m), "myscheme_name": m,
        }
        if row_fields:
            row.update(row_fields(r))
        out.append(row)

    def sweep(t):
        h = [o for o in out if o["score"] >= t and o["hand_label"]]
        if not h:
            return None
        tp = sum(1 for o in h if o["hand_label"] == "scheme")
        return {"threshold": t, "n_labelled": len(h), "precision": round(tp / len(h), 3),
                "recall": round(tp / max(1, sum(lab.values())), 3)}

    census = [o for o in out if o["score"] >= publish]
    unlabelled = [o for o in census if o["hand_label"] is None]
    right = sum(1 for o in census if o["hand_label"] == "scheme")
    errors = [o["name"] for o in census if o["hand_label"] == "not_scheme"]
    absent = [o for o in census if not o[flag]]

    write_json(f"data/{key}/classification.json", {
        "built": utcnow(), "snapshot": d.get("snapshot"), "state": state,
        "cycle": d.get("cycle"), "source": d.get("source"),
        "publish_threshold": publish, "listing_threshold": listing,
        f"myscheme_{key}_records": len(ms),
        "classified_scheme": len(census),
        "classified_not_scheme": len(out) - len(census),
        "ground_truth": {"labelled": len(labels),
                         "scheme": sum(1 for v in labels.values() if v == "scheme"),
                         "not_scheme": sum(1 for v in labels.values() if v == "not_scheme"),
                         "question": lj.get("question"), "sampling": lj.get("sampling")},
        "threshold_sweep": [x for x in (sweep(t) for t in range(-2, 9)) if x],
        "validation": {
            "at_publish_threshold_census": {
                "rows": len(census),
                "rows_hand_labelled": len(census) - len(unlabelled),
                "unlabelled": len(unlabelled),
                "schemes": right, "not_schemes": len(errors),
                "precision": round(right / len(census), 3) if census else None,
                "what": ("Every row at or above the publishing bar carries a hand label, so "
                         "this precision is a COUNT and the errors below are named ones."),
            },
            "at_publish_threshold": sweep(publish) or {},
        },
        "known_errors": errors,
        "signals_rejected": rejected,
        "caveat": d.get("caveat"),
        "absent_schemes": sorted(absent, key=lambda o: -(o["be_lakh"] or 0))[:60],
        "absent_distinct": absent,
        "all_entries": out,
    })
    return out, census, right, errors, ms, unlabelled


def report(key, out, census, right, errors, ms, unlabelled, publish):
    print(f"{key}: {len(out):,} lines, {len(census)} clear the publishing bar of {publish}")
    if unlabelled:
        print(f"  {len(unlabelled)} rows at the bar carry NO hand label. Precision below is "
              f"not yet a count; label them before publishing.")
    print(f"  counted precision {right/len(census):.3f} on {len(census)-len(unlabelled)} "
          f"hand-labelled rows, {len(errors)} named errors")
    for e in errors[:6]:
        print(f"     not a scheme: {e[:68]}")
    print(f"  myScheme lists {len(ms)}; "
          f"{sum(1 for o in census if not o.get('myscheme_name'))} of these reach it nowhere")
