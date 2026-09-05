"""
Every published ratio must divide two counts of the SAME list.

AGENT-EDITABLE (PLAN.md 7). Reads data/ only. Never fetches. Runs after the classifiers,
because what it checks is what they concluded.

WHY THIS FILE EXISTS. Three separate bugs in one day, all the same shape, none of them
caught by anything:

  * Karnataka's classifier published its absence claim under `absent_schemes` and every
    other state published it under `absent_distinct`. The site counted the key it knew, so
    the register's headline said 1,560 schemes funded and unlisted while rendering
    Karnataka's 72 of them on the page below. A state was missing from a total that was
    displaying it.

  * Recall was divided by the stratified sample PLUS the audit census in eight states and
    by the stratified sample alone in seven. The census is chosen on the classifier's own
    output, so it lifted the numerator and the denominator together and the eight looked
    better than the seven by up to 41 points. Nothing about the classifiers differed.

  * The CAG join divided its 22 matches by 5,475, the names from the four national
    sources, while the page above it divided by 10,598, which includes the state books
    the join could not see. Two denominators, one page.

Each was a number computed over one population and labelled with another, which is the
exact failure this register documents in government sources. A register that publishes
that error while pointing at it has no argument left, so this file asserts the invariants
rather than trusting that the next classifier remembers them.

It is fail-loud and it gates nothing else: run.sh records it as a failed step, publishes
what succeeded, and exits non-zero. A ratio that cannot be reproduced from the data it
claims to summarise is a bug in this repository, not in a government's PDF.
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
from common import ROOT  # noqa: E402


def provenance(v):
    """Which set a hand label was drawn from. The two spellings are historical.

    The seven oldest states record it per row as `sample`, the eight built on
    classify_common as `how`. Both say the same thing and neither is preferred; what
    matters is that a label whose provenance is unrecorded is never counted on either side.
    """
    h = str(v.get("how") or v.get("sample") or "")
    if h.startswith(("audit census", "audit")):
        return "audit"
    if h.startswith("whole corpus"):
        return "corpus"
    if h.startswith("stratified"):
        return "stratified"
    return None


def label_rows(lj):
    """(key, label, provenance) for every hand label, whatever shape the file is."""
    L = lj["labels"]
    if isinstance(L, dict):
        return [(k, v["label"], provenance(v)) for k, v in L.items()]
    out = []
    for r in L:
        k = r.get("key") or r.get("code") or r.get("hoa") or r.get("name")
        out.append((k, r["label"], provenance(r)))
    return out


def check_state(key):
    """Every assertion for one state. Returns a list of failure strings."""
    cp = os.path.join(ROOT, "data", key, "classification.json")
    lp = os.path.join(ROOT, "data", key, "labels.json")
    with open(cp, encoding="utf-8") as fh:
        d = json.load(fh)
    if not d.get("all_entries"):
        return []
    bad = []
    E = d["all_entries"]
    bar = d.get("publish_threshold")

    # 1. The two thresholds are the classifier's to publish. When one is missing, something
    #    downstream guesses: site/build.py held a second copy of the listing bar in a dict
    #    and parse/cag_join.py skipped every state whose file did not carry it.
    for k in ("publish_threshold", "listing_threshold"):
        if d.get(k) is None:
            bad.append(f"{key}: publishes no {k}")
    if bar is None:
        return bad

    # 2. The absence claim under the name the site reads. Karnataka published only the
    #    other one and was counted as zero.
    if d.get("absent_distinct") is None:
        bad.append(f"{key}: publishes no absent_distinct, so the site counts it as zero")

    # 3. Census precision divides the census by the census.
    cen = (d.get("validation") or {}).get("at_publish_threshold_census") or {}
    at_bar = [r for r in E if r.get("score", -99) >= bar]
    rows = cen.get("rows") or cen.get("published")
    if rows is not None and rows != len(at_bar):
        bad.append(f"{key}: census says {rows} rows at the bar, all_entries has {len(at_bar)}")
    p = cen.get("precision")
    if p is not None and at_bar:
        want = round(sum(1 for r in at_bar if r.get("hand_label") == "scheme") / len(at_bar), 3)
        if abs(want - p) > 0.0015:
            bad.append(f"{key}: census precision {p} but recomputes to {want}")

    # 4. Recall divides the STRATIFIED sample by the stratified sample. This is the one
    #    that was wrong in eight states at once, and it is wrong silently: the number stays
    #    plausible, it just measures the size of the audit.
    with open(lp, encoding="utf-8") as fh:
        lj = json.load(fh)
    labs = label_rows(lj)
    if any(pv is None for _, _, pv in labs):
        n = sum(1 for _, _, pv in labs if pv is None)
        bad.append(f"{key}: {n} hand labels record no provenance, so recall cannot be checked")
    else:
        # A whole-corpus state has no sample and no census: every row carries a label, so
        # both precision and recall are counts over the population. Tripura is the only one,
        # and it is the control this register used to prove the census inflated recall
        # elsewhere. Treating its labels as a "sample" would flag the strongest ground
        # truth here as the weakest.
        whole = all(pv == "corpus" for _, _, pv in labs)
        pool = "corpus" if whole else "stratified"
        den = sum(1 for k, lab, pv in labs if pv == pool and lab == "scheme")
        ident = {}
        for r in E:
            i = r.get("key") or r.get("code") or r.get("hoa") or (r.get("hoas") or [None])[0]
            ident.setdefault(i, r)
            ident.setdefault(r.get("name"), r)
        num = sum(1 for k, lab, pv in labs
                  if pv == pool and lab == "scheme"
                  and (ident.get(k) or {}).get("score", -99) >= bar)
        got = (d.get("validation") or {}).get("at_publish_threshold", {}).get("recall")
        if got is not None and den:
            want = round(num / den, 3)
            if abs(want - got) > 0.0015:
                bad.append(f"{key}: recall {got} but the stratified sample gives {want} "
                           f"({num}/{den}); a census row is in the fraction")
        # Precision at the bar is only a COUNT if every row there carries a label. That is
        # what the audit census buys, and a whole-corpus state gets it for free.
        if not whole:
            unl = [r for r in at_bar if r.get("hand_label") is None]
            if unl:
                bad.append(f"{key}: {len(unl)} of {len(at_bar)} rows at the bar carry no hand "
                           f"label, so its precision is an estimate published as a count")
    return bad


def main():
    argparse.ArgumentParser(
        description="Assert every published ratio divides one list by itself.").parse_args()
    bad, checked = [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "*", "classification.json"))):
        key = os.path.basename(os.path.dirname(f))
        out = check_state(key)
        if out is not None:
            checked += 1
            bad += out

    # 5. One page, one denominator. The CAG join and the overview both divide by "the
    #    names this register holds", and for months they meant different things.
    cag = os.path.join(ROOT, "data", "cag", "audited.json")
    if os.path.exists(cag):
        with open(cag, encoding="utf-8") as fh:
            c = json.load(fh)
        nat, st = c.get("register_names_national"), c.get("register_names_state")
        if nat is None or st is None:
            bad.append("cag: audited.json does not say what its denominator is made of")
        elif nat + st != c.get("register_names"):
            bad.append(f"cag: register_names {c.get('register_names')} != "
                       f"{nat} national + {st} state")

    print(f"ratios: {checked} classified states checked")
    for b in bad:
        print(f"  FAIL {b}")
    if bad:
        print(f"{len(bad)} published ratio(s) do not divide one list by itself.")
        return 1
    print("  every published ratio divides two counts of the same list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
