"""
Classify Haryana Plan Memo lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

    data/haryana/labels.json          hand ground truth, the input
    data/haryana/classification.json  the verdicts, the output

READ THIS FIRST, because Haryana is the state that breaks the pattern the other seven
classifiers established. THE PURPOSE LINE IS WORTHLESS HERE, and it was the strongest
signal in the file for Karnataka at P(scheme) 0.947.

Haryana prints a paragraph of its own describing 824 of its 970 lines, which looked like
the richest evidence any state in this register publishes. Measured against 300 hand
labels it is worth nothing at all:

    a purpose paragraph is present        P(scheme) 0.288   base rate 0.280   lift +0.008
    the paragraph is longer than 200 chars P(scheme) 0.267                    lift -0.013

The reason is visible the moment the paragraphs are read beside each other. Haryana
describes a works line as fully as it describes a cash transfer: "Under this scheme, the
funds are required for purchase of land and construction of the building" is a purpose
paragraph. A field that is present for everything says nothing about anything, and the
LENGTH of it is very slightly worse than a coin. Karnataka's purpose line worked because
Karnataka prints one only for schemes.

WHAT DOES WORK IS THE SHAPE OF THE MONEY, and Haryana publishes it in a form no other state
here does. Every line's provision is either WORKS money or ESTABLISHMENT money, never both:
378 rows carry works_lakh, 564 carry establishment_lakh, and 0 carry the two together. The
book has already sorted its own lines into building things and running things.

    the provision is works money          P(scheme) 0.033   over 121 labelled rows
    an asset or office word in the name   P(scheme) 0.036   over 137 labelled rows
    a benefit word in the name            P(scheme) 0.862   over  58 labelled rows

Those are not weak instruments. Works money alone is a near-exact negative, and it is the
state's own accounting rather than anything inferred from a name.

BASE RATE. The Plan Memo is a register of welfare and development schemes, not the whole
budget, so establishment and pension heads are largely absent and this is a cleaner list
than most states publish. The job here is therefore NOT separating schemes from
establishment. It is separating a benefit to a PERSON from the development of a PLACE and
from the running of an INSTITUTION, which is a harder line and the one every surviving
error falls on.

WHAT THE CENSUS CAUGHT THAT THE SAMPLE DID NOT, which is the argument for doing both. The
stratified sample put precision at the publishing bar at 0.978. Labelling every row at that
bar instead of estimating from a sample brought it to 0.859, and the 19 errors were not
scattered: six were area-development yojanas (Divya Nagar Yojna, Swaran Jayanti Khand
Utthan Yojana, Vidhayak Adarsh Nagar Evam Gram Yojana) and five were infrastructure
programmes with Mission in the name (AMRUT 2.0, Swachh Bharat Mission Used Water
Management). Both patterns were then measured over all 390 labels and both come out at
P(scheme) 0.000, over 19 and 7 rows. They are in the score because they were measured, and
they were looked for because the census showed them; that order matters and it is the order
this file was written in.

AND WHAT THE CENSUS MUST NOT TOUCH IS RECALL. Every row in it is at or above the bar by
construction, so counting it there adds a true positive to both sides of the fraction and
the number rises with the size of the audit rather than with the quality of the scoring.
This file swept all 390 labels and published 0.742; on the 300 stratified labels alone,
which are the only ones drawn without looking at the score, it is 0.524.

REJECTED SIGNALS, with the measurement that rejected each, are in signals_rejected below.
The purpose line is there. So is the word "assistance", at 0.385 against a 0.280 base: too
weak to carry a positive when "Assistance to States for Conduct of Livestock Census" and
"Scouting & Guiding Assistance" are both filed under it.
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from match import probably_same, tokens as m_tokens, skeleton as m_skeleton, \
    acronyms as m_acronyms  # noqa: E402
from classify_common import excluded_by_rule  # noqa: E402

# A benefit a person, household, farmer, student, worker or firm receives. "assistance" is
# deliberately absent and "mission" deliberately present; both are measured in
# signals_rejected and in the docstring.
BENEFIT = re.compile(
    r"\b(yojna|yojana|scholarship|pension|stipend|allowance|subsidy|subvention|insurance|"
    r"incentive|compensation|award|shagun|relief|reimbursement|free|welfare of|mission)\b",
    re.I)

# The vocabulary of building things and running offices.
ASSET = re.compile(
    r"\b(construction|building|buildings|capital asset|share capital|equity|loan to|"
    r"loans to|engineer|pensionary|office|purchase of land|infrastructure|works|"
    r"maintenance|modernisation|modernization|computerisation|computerization|survey|"
    r"research|publicity|establishment of|setting up|strengthening|grant.in.aid to|"
    r"special revenue|administration)\b", re.I)

# A facility rather than a person: the thing funded is a place people go to.
INSTITUTION = re.compile(
    r"\b(waste|wasteland|college|university|hostel|cell|centre|center|capacity building|"
    r"census|road|roads|canal|canals|drainage|dam|sewerage|aerodrome|memorial|monument|"
    r"museum|zoo|tourism|resort)\b", re.I)

# Developing a PLACE. This is the distinction the census errors all fell on, and it is a
# real one: a village made better is not a person given something, however good the scheme.
AREA = re.compile(
    r"\b(nagar|maha gram|gram uday|adarsh gram|adarsh nagar|shahari vikas|shehri vikas|"
    r"khand utthan|urban transformation|urban renewal|rejuvenation|afforestation|"
    r"action plan|behaviour change|iec|used water|solid waste)\b", re.I)

# Money for an institution's own running, which the book files beside real subsidies.
ADMIN_GRANT = re.compile(
    r"\b(administrative subsidy|administrative expenditure|reimbursement of market fee|"
    r"gia to|grant in aid to)\b", re.I)

SIGNALS = [
    ("benefit", BENEFIT, +3, "a benefit word in the name"),
    ("works_money", None, -4, "the provision is works money and not establishment money"),
    ("asset_word", ASSET, -4, "an asset or office word in the name"),
    ("institution", INSTITUTION, -3, "the subject is a facility rather than a person"),
    ("area", AREA, -4, "the subject is a place being developed rather than a person"),
    ("admin_grant", ADMIN_GRANT, -4, "money for an institution's own running"),
]

# Every row at or above this carries a hand label, so precision here is a COUNT.
PUBLISH_THRESHOLD = 4
# The weaker bar, for listing a row as something the state's budget names as a scheme. This
# is the F1 optimum and it is NOT the bar above: listing a budget head is an annoyance,
# naming one as hidden is a false accusation.
LISTING_THRESHOLD = 3


def score(r):
    # The register's definition, held in classify_common because it is the rule and not a
    # signal: money that buys the capacity of a delivery system is not a scheme however
    # strongly this state's own evidence reads it. This file predates that harness and has
    # to reach for it explicitly.
    if excluded_by_rule(r["name"]):
        return -99, [("rule", "buys the capacity of the delivery system, not the benefit")]

    s, ev = 0, []
    for key, rx, pts, why in SIGNALS:
        hit = bool(r.get("works_lakh")) if key == "works_money" else bool(rx.search(r["name"]))
        if hit:
            s += pts
            ev.append((f"{pts:+d}", why))
    if r.get("establishment_lakh"):
        s += 1
        ev.append(("+1", "the provision is establishment money, not works"))
    if r.get("central_share_lakh"):
        s += 1
        ev.append(("+1", "the Centre shares the cost"))
    if r["part"].startswith("Part-II "):
        s += 1
        ev.append(("+1", "the state files it as a shared scheme"))
    return s, ev


def myscheme_haryana():
    import glob
    out = []
    for f in glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if "Haryana" not in ((d.get("_list") or {}).get("beneficiaryState") or []):
            continue
        b = (d.get("en") or {}).get("basicDetails") or {}
        if b.get("schemeName"):
            out.append(b["schemeName"])
    return sorted(set(out))


def run():
    d = json.load(open(os.path.join(ROOT, "data", "haryana", "schemes.json"), encoding="utf-8"))
    rows = d["entries"]
    lj = json.load(open(os.path.join(ROOT, "data", "haryana", "labels.json"), encoding="utf-8"))
    labels = {c: v["label"] for c, v in lj["labels"].items()}
    # The sweep sees the stratified sample and not the audit census. The census is chosen
    # on this classifier's own output -- every row in it is at or above the bar -- so
    # letting it into recall raises the number with the size of the audit instead of with
    # the quality of the scoring. classify_common carries the full note; this file predates
    # that harness and has to say it again. Haryana's 90 audited rows had it reading 0.742.
    sampled = {c for c, v in lj["labels"].items()
               if not str(v.get("how") or v.get("sample") or "").startswith(
                   ("audit census", "audit"))}
    lab = {c: labels[c] == "scheme" for c in sampled}

    ms = myscheme_haryana()
    idx = collections.defaultdict(set)
    for i, n in enumerate(ms):
        for k in (set(m_tokens(n)) | {m_skeleton(t) for t in m_tokens(n)}
                  | {a for a in m_acronyms(n) if len(a) >= 5}):
            idx[k].add(i)

    def in_myscheme(name):
        hits = collections.Counter()
        for k in sorted(set(m_tokens(name)) | {m_skeleton(t) for t in m_tokens(name)}
                        | {a for a in m_acronyms(name) if len(a) >= 5}):
            hits.update(idx.get(k, ()))
        for i, n in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))[:40]:
            if n >= 2 and probably_same(name, ms[i])[0]:
                return ms[i]
        return None

    out = []
    for r in sorted(rows, key=lambda x: x["code"]):
        s, ev = score(r)
        m = in_myscheme(r["name"])
        out.append({
            "key": r["code"], "code": r["code"], "name": r["name"],
            "department": r.get("department"), "purpose": r.get("purpose"),
            "be_lakh": r.get("be_lakh"), "part": r.get("part"),
            "score": s, "evidence": ev,
            "verdict": "scheme" if s >= PUBLISH_THRESHOLD else "not_scheme",
            "hand_label": labels.get(r["code"]),
            "in_myscheme_haryana": bool(m), "myscheme_name": m,
        })

    by_code = {r["code"]: r for r in rows}

    def sweep2(t):
        hit = [c for c in lab if score(by_code[c])[0] >= t]
        if not hit:
            return None
        tp = sum(lab[c] for c in hit)
        return {"threshold": t, "n_labelled": len(hit),
                "precision": round(tp / len(hit), 3),
                "recall": round(tp / sum(lab.values()), 3),
                "measured_on": "the stratified sample only"}

    census = [o for o in out if o["score"] >= PUBLISH_THRESHOLD]
    unlabelled = [o for o in census if o["hand_label"] is None]
    right = sum(1 for o in census if o["hand_label"] == "scheme")
    errors = [o["name"] for o in census if o["hand_label"] == "not_scheme"]

    absent = [o for o in census if not o["in_myscheme_haryana"]]
    write_json("data/haryana/classification.json", {
        "built": utcnow(), "snapshot": d["snapshot"], "state": "Haryana",
        "cycle": d.get("cycle"),
        "source": d.get("source"),
        "publish_threshold": PUBLISH_THRESHOLD,
        "listing_threshold": LISTING_THRESHOLD,
        "myscheme_haryana_records": len(ms),
        "classified_scheme": sum(1 for o in out if o["score"] >= PUBLISH_THRESHOLD),
        "classified_not_scheme": sum(1 for o in out if o["score"] < PUBLISH_THRESHOLD),
        "ground_truth": {"labelled": len(labels),
                         "scheme": sum(1 for v in labels.values() if v == "scheme"),
                         "not_scheme": sum(1 for v in labels.values() if v == "not_scheme"),
                         "question": lj.get("question"), "sampling": lj.get("sampling")},
        "threshold_sweep": [x for x in (sweep2(t) for t in range(0, 8)) if x],
        "validation": {
            "at_publish_threshold_census": {
                "rows_hand_labelled": len(census) - len(unlabelled),
                "rows": len(census),
                "unlabelled": len(unlabelled),
                "schemes": right,
                "not_schemes": len(errors),
                "precision": round(right / len(census), 3) if census else None,
                "what": ("Every row at or above the publishing bar carries a hand label, so "
                         "this precision is a COUNT and the errors are named ones."),
            },
            "at_publish_threshold": next(
                (x for x in (sweep2(t) for t in range(0, 8)) if x and x["threshold"] == PUBLISH_THRESHOLD), {}),
        },
        "known_errors": errors,
        "signals_rejected": [
            {"signal": "a purpose paragraph is present",
             "measured": {"P_scheme": 0.288, "base_rate": 0.280, "n": 260},
             "why": ("The strongest signal in the Karnataka classifier at 0.947, and worth "
                     "nothing here. Haryana prints a paragraph for 824 of 970 lines and "
                     "describes a works line as fully as a cash transfer: 'the funds are "
                     "required for purchase of land and construction of the building' is "
                     "one of them. A field present for everything says nothing about "
                     "anything.")},
            {"signal": "the purpose paragraph is longer than 200 characters",
             "measured": {"P_scheme": 0.267, "base_rate": 0.280, "n": 221},
             "why": "Slightly worse than the base rate. Length is not evidence."},
            {"signal": "the word assistance in the name",
             "measured": {"P_scheme": 0.385, "base_rate": 0.280, "n": 13},
             "why": ("Too weak to carry a positive. 'Assistance to States for Conduct of "
                     "Livestock Census' and 'Scouting & Guiding Assistance' are both filed "
                     "under it, and both are budget heads.")},
            {"signal": "Part-III, a 100% centrally sponsored scheme",
             "measured": {"P_scheme": 0.306, "base_rate": 0.280, "n": 36},
             "why": ("Almost exactly the base rate. Who pays says nothing about whether a "
                     "citizen can apply, which Part-II at 0.483 only barely contradicts.")},
        ],
        "caveat": d.get("caveat"),
        "absent_schemes": sorted(absent, key=lambda o: -(o["be_lakh"] or 0))[:60],
        "absent_distinct": absent,
        "all_entries": out,
    })
    return out, census, right, errors, ms


def main():
    argparse.ArgumentParser(description="Classify Haryana's Plan Memo lines.").parse_args()
    out, census, right, errors, ms = run()
    print(f"haryana: {len(out)} lines, {len(census)} clear the publishing bar of {PUBLISH_THRESHOLD}")
    print(f"  counted precision {right/len(census):.3f} on {len(census)} hand-labelled rows, "
          f"{len(errors)} named errors")
    for e in errors:
        print(f"     not a scheme: {e[:70]}")
    print(f"  myScheme lists {len(ms)} Haryana schemes; "
          f"{sum(1 for o in census if not o['in_myscheme_haryana'])} of these reach it nowhere")


if __name__ == "__main__":
    main()
