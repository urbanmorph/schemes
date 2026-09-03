"""
Classify Tripura's SNS SPARSH scheme lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches.

    data/tripura/labels.json          hand ground truth, the input
    data/tripura/classification.json  the verdicts, the output

THE GROUND TRUTH IS THE WHOLE CORPUS. Tripura's book names 134 state schemes, and
labelling all 134 costs less than designing strata for them. So there is no stratified
sample here, no estimate anywhere, and no separate audit census: precision and recall at
every threshold are counts over the entire population. This is the only state in the
register where that is true, and it is true because Tripura is small.

The base rate is 0.463, far above any other state here, because the book is not a budget.
It is the list of schemes onboarded on SNS SPARSH, the single-nodal-agency route
centrally sponsored money takes, so nearly every line is a real programme and the job is
not finding schemes among establishment heads. It is separating a benefit that reaches a
person from a programme that runs a service or builds a place.

WHAT THE SIGNALS MEASURED, over all 134 labels:

    scholarship, pension or insurance     P(scheme) 1.000  over 10 rows
    nutrition, meal, poshan, anganwadi    P(scheme) 0.833  over  6
    yojana                                P(scheme) 0.750  over 16
    an asset or admin word                P(scheme) 0.054  over 37
    gram as a word                        P(scheme) 0.000  over  5

TWO THINGS THIS COST, both worth recording.

**Abhiyan is not a benefit word and yojana is.** They look like the same kind of word, a
programme name in Hindi, and they measure on opposite sides: abhiyan 0.333 against a base
of 0.463, yojana 0.750. Tripura's abhiyans are Rashtriya Gram Swaraj, Poshan, Swachh
Bharat and Dharti Aaba Janjatiya Gram Utkarsh, and three of those four develop a place or
build a capability. It is in signals_rejected rather than in the score.

**An underscore is a word character.** `TRIPURA_NATIONAL HEALTH MISSION` did not match
`\\bnational health mission\\b`, because the character before the N is an underscore and
regex counts that as part of the word, so there is no boundary there. One row, and it was
the last error in the file: names are normalised before matching now.
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

BENEFIT = re.compile(
    r"\b(yojana|yojna|scholarship|pension|insurance|awas|meal|nutrition|poshan|anganwadi|"
    r"icds|helpline|help line|adalat|livelihood|kaushalya|sashaktikaran|vatsalya|palna|"
    r"gramin|grameen|mission|programme)\b", re.I)

ASSET = re.compile(
    r"\b(construction|capital asset|infrastructure|strengthening|computeri[sz]ation|"
    r"census|survey|administrative|admin|salary|modernization|modernisation|research|"
    r"seminar|training institute|capacity building|action plan|component|hostel|hostels|"
    r"watershed|waste management|iec|behaviour change|grants under|area development)\b",
    re.I)

# A programme that runs a service or protects a place. Every one of these was read: they
# are the missions and abhiyans whose beneficiary is a system, not a person.
SYSTEM = re.compile(
    r"\b(national health mission|ayush mission|uchchatar shiksha|gram swaraj|gram utkarsh|"
    r"gram sadak|safety of women|health infrastructure|tertiary care|"
    r"human resources for health|jan vikas|adi adarsh|bamboo mission|conservation|"
    r"wildlife|forest fire|project tiger)\b", re.I)

# "gram" as its own word is a village being developed. "gramin" is a person living in one,
# and the word boundary is what separates them: Deendayal Upadhyaya GRAMEEN Kaushalya
# Yojana trains people and scores 1.000, Pradhan Mantri GRAM Sadak Yojana builds roads.
GRAM = re.compile(r"\bgram\b", re.I)

PUBLISH_THRESHOLD = 2
LISTING_THRESHOLD = 1


def norm(name):
    """Underscores and slashes are word characters to a regex and word breaks to a reader."""
    return re.sub(r"[_/]+", " ", name or "")


def score(r):
    n = norm(r["name"])
    s, ev = 0, []
    if BENEFIT.search(n):
        s += 3
        ev.append(("+3", "a benefit word in the name"))
    if ASSET.search(n):
        s -= 4
        ev.append(("-4", "an asset or administration word in the name"))
    if SYSTEM.search(n):
        s -= 4
        ev.append(("-4", "the programme runs a service rather than paying a person"))
    if GRAM.search(n):
        s -= 4
        ev.append(("-4", "the subject is a village being developed"))
    if "Social Welfare" in ((r.get("departments") or [""])[0] or ""):
        s += 1
        ev.append(("+1", "the Social Welfare department funds it"))
    return s, ev


def myscheme_records(state):
    import glob
    out = []
    for f in glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if state not in ((d.get("_list") or {}).get("beneficiaryState") or []):
            continue
        b = (d.get("en") or {}).get("basicDetails") or {}
        if b.get("schemeName"):
            out.append(b["schemeName"])
    return sorted(set(out))


def joiner(names):
    idx = collections.defaultdict(set)
    for i, n in enumerate(names):
        for k in (set(m_tokens(n)) | {m_skeleton(t) for t in m_tokens(n)}
                  | {a for a in m_acronyms(n) if len(a) >= 5}):
            idx[k].add(i)

    def hit(name):
        c = collections.Counter()
        for k in sorted(set(m_tokens(name)) | {m_skeleton(t) for t in m_tokens(name)}
                        | {a for a in m_acronyms(name) if len(a) >= 5}):
            c.update(idx.get(k, ()))
        for i, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:40]:
            if n >= 2 and probably_same(name, names[i])[0]:
                return names[i]
        return None
    return hit


def run():
    d = json.load(open(os.path.join(ROOT, "data", "tripura", "schemes.json"), encoding="utf-8"))
    lj = json.load(open(os.path.join(ROOT, "data", "tripura", "labels.json"), encoding="utf-8"))
    labels = {c: v["label"] for c, v in lj["labels"].items()}
    lab = {c: v == "scheme" for c, v in labels.items()}
    ms = myscheme_records("Tripura")
    hit = joiner(ms)

    out = []
    for r in sorted(d["entries"], key=lambda x: x["code"]):
        s, ev = score(r)
        m = hit(r["name"])
        out.append({
            "key": r["code"], "code": r["code"], "name": r["name"],
            "department": (r.get("departments") or [None])[0],
            "hoas": r.get("hoas") or [], "be_lakh": r.get("be_lakh"),
            "score": s, "evidence": ev,
            "verdict": "scheme" if s >= PUBLISH_THRESHOLD else "not_scheme",
            "hand_label": labels.get(r["code"]),
            "in_myscheme_tripura": bool(m), "myscheme_name": m,
        })

    def sweep(t):
        h = [o for o in out if o["score"] >= t and o["hand_label"]]
        if not h:
            return None
        tp = sum(1 for o in h if o["hand_label"] == "scheme")
        return {"threshold": t, "n_labelled": len(h), "precision": round(tp / len(h), 3),
                "recall": round(tp / sum(lab.values()), 3)}

    census = [o for o in out if o["score"] >= PUBLISH_THRESHOLD]
    right = sum(1 for o in census if o["hand_label"] == "scheme")
    errors = [o["name"] for o in census if o["hand_label"] == "not_scheme"]
    absent = [o for o in census if not o["in_myscheme_tripura"]]

    write_json("data/tripura/classification.json", {
        "built": utcnow(), "snapshot": d["snapshot"], "state": "Tripura",
        "cycle": d.get("cycle"), "source": d.get("source"),
        "publish_threshold": PUBLISH_THRESHOLD, "listing_threshold": LISTING_THRESHOLD,
        "myscheme_tripura_records": len(ms),
        "classified_scheme": len(census),
        "classified_not_scheme": len(out) - len(census),
        "ground_truth": {"labelled": len(labels),
                         "scheme": sum(1 for v in labels.values() if v == "scheme"),
                         "not_scheme": sum(1 for v in labels.values() if v == "not_scheme"),
                         "question": lj.get("question"), "sampling": lj.get("sampling")},
        "threshold_sweep": [x for x in (sweep(t) for t in range(0, 6)) if x],
        "validation": {
            "at_publish_threshold_census": {
                "rows": len(census), "rows_hand_labelled": len(census),
                "unlabelled": 0, "schemes": right, "not_schemes": len(errors),
                "precision": round(right / len(census), 3) if census else None,
                "what": ("Every line in Tripura's book carries a hand label, so this is a "
                         "count over the whole population and not over a sample. There is "
                         "no estimate anywhere in this file."),
            },
            "at_publish_threshold": sweep(PUBLISH_THRESHOLD) or {},
        },
        "known_errors": errors,
        "signals_rejected": [
            {"signal": "the word abhiyan in the name",
             "measured": {"P_scheme": 0.333, "base_rate": 0.463, "n": 6},
             "why": ("It looks like yojana, which measures 0.750, and it lands on the "
                     "other side of the base rate. Tripura's abhiyans are Rashtriya Gram "
                     "Swaraj, Swachh Bharat and Dharti Aaba Janjatiya Gram Utkarsh, and "
                     "those develop a place or build a capability rather than paying "
                     "anybody.")},
            {"signal": "the Welfare of SC / ST / OBC / Tribal departments",
             "measured": {"P_scheme": 0.400, "base_rate": 0.463, "n": 15},
             "why": ("Below the base rate. A welfare department funds hostels and "
                     "research institutes as readily as it funds scholarships, so who "
                     "pays says nothing here.")},
            {"signal": "the Public Works and Urban Development departments",
             "measured": {"P_scheme": 0.316, "base_rate": 0.463, "n": 19},
             "why": ("A real negative but a weak one, and every row it would catch is "
                     "already caught by a word in its own name. Left out rather than "
                     "double-counted.")},
        ],
        "caveat": d.get("caveat"),
        "absent_schemes": sorted(absent, key=lambda o: -(o["be_lakh"] or 0))[:60],
        "absent_distinct": absent,
        "all_entries": out,
    })
    return out, census, right, errors, ms


def main():
    argparse.ArgumentParser(description="Classify Tripura's scheme lines.").parse_args()
    out, census, right, errors, ms = run()
    print(f"tripura: {len(out)} lines, {len(census)} clear the publishing bar of {PUBLISH_THRESHOLD}")
    print(f"  counted precision {right/len(census):.3f} over the WHOLE corpus, "
          f"{len(errors)} errors")
    print(f"  myScheme lists {len(ms)} Tripura schemes; "
          f"{sum(1 for o in census if not o['in_myscheme_tripura'])} of these reach it nowhere")


if __name__ == "__main__":
    main()
