"""
Can a LANGUAGE-INDEPENDENT signal fix the recall problem the seven state classifiers share?

AGENT-EDITABLE (PLAN.md SS7). Reads data/ only. Never fetches.

    data/<state>/schemes.json        the corpus
    data/<state>/labels.json         hand ground truth
    data/<state>/classification.json the current score per row, read only to ask whether a
                                     candidate adds anything the language does not already
                                     have. No weight in any classifier is changed by this
                                     file, and running it changes no classifier output.
    data/recall_investigation.json   the written record, the output

THE PROBLEM. All seven classifiers read English: benefit words, beneficiary classes, purpose
lines. Counted precision runs 90.3% to 97.4% and recall 12% to 41%, and the misses are not
random. In every state the largest schemes are missed and always for the same reason.
"Lakshmir Bhandar", "Thallikivandanam", "Magalir Urimai Thogai", "Subhadra Yojana" and
"Mukhyamantri Mazi Ladaki Bahin" are Bengali, Telugu, Tamil, Odia and Marathi brand names and
say nothing to an English vocabulary. There is nothing in the row to read.

WHAT IS NOT A CANDIDATE. Putting bhandar, thogai, vandanam, prakalpa and the rest into the
benefit vocabulary. Those words would be read off schemes already known to be schemes, so the
measurement that followed would be worthless. It was proposed and rejected in West Bengal and
Odisha on exactly that ground and it is not revisited here.

Also not a candidate: the RAW size of the allocation. Kerala, Maharashtra, Odisha and Tamil
Nadu each measured it and each rejected it as non-monotone across quartiles. The candidate
below is a different quantity, size RELATIVE TO THE DEPARTMENT the row sits in, on the
argument that a state's largest provisions inside a welfare department are overwhelmingly
schemes while its smallest are establishment and works heads.

HOW EVERYTHING IS MEASURED. P(scheme) with n on the DEVELOPMENT half of each state's existing
stratified sample, which is the same half every weight in every classifier was fitted on: the
sample rows sorted by key, even index. The held-out half is reported beside it, because the
whole failure mode of a signal fitted on a handful of rows is that it agrees with one half
and not the other, and that is exactly what happens below.

THREE TESTS EACH CANDIDATE HAS TO PASS, declared before the numbers were read:

  (a) it lifts P(scheme) above the state's base rate on BOTH halves;
  (b) its n is at least as large as the thinnest signal the state already weights;
  (c) it beats the CONTROL of simply lowering the publishing bar by the same number of
      points. This one is the test that matters and it is easy to skip. Adding +k to a
      signal publishes rows that scored bar-k or better, and the band just below every one
      of these bars is already mostly schemes, so ANY +k publishes more schemes. The
      question is whether the signal picks better rows out of that band than the band
      average, not whether it picks up schemes.

THE ANSWER, and the measurements for it are in data/recall_investigation.json. It does not
carry. Nothing here is wired into any classifier.
"""

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT_DIR, "collect"))

from common import ROOT, utcnow, write_json  # noqa: E402

STATES = ["andhra", "karnataka", "kerala", "maharashtra", "odisha", "tamilnadu",
          "westbengal"]

# The grouping each state prints that stands for "its own department". Andhra, Maharashtra
# and Tamil Nadu print a department name; Odisha prints a numbered department list and West
# Bengal a numbered demand, both of which are the department; Kerala prints a sector, which
# is the nearest its Annual Plan Statements carry; Karnataka prints neither, so the major
# head is used, which is the functional grouping its Gender and Child annexures share.
GROUP_FIELD = {
    "andhra": "the department name printed on the row",
    "karnataka": "the major head, because the Gender, Child and SCSP/TSP annexures print no "
                 "department",
    "kerala": "the sector printed on the row",
    "maharashtra": "the department name printed on the row",
    "odisha": "the lowest-numbered department funding the code, the same rule "
              "parse/classify_odisha.py uses to stratify",
    "tamilnadu": "the department name printed on the row",
    "westbengal": "the lowest-numbered demand, which is the department",
}

# The multi-book field. Where a row is printed in more than one of a state's books the state
# has said the same provision twice, once under each cross-cutting annexure. Maharashtra
# prints one statement and Tamil Nadu one departmental volume per row, so neither has one.
BOOK_FIELD = {
    "andhra": "books", "karnataka": "books", "kerala": "books",
    "maharashtra": None, "odisha": "departments", "tamilnadu": "books",
    "westbengal": "books",
}

# Prior-year columns, where the parsers captured them. None means the book prints one year.
PRIOR_FIELD = {
    "andhra": None, "karnataka": None, "kerala": None,
    "maharashtra": "actual_2024_25_lakh",
    "odisha": "actual_2024_25_lakh",
    "tamilnadu": None,
    "westbengal": "actual_2024_25_lakh",
}

# Andhra's classifier takes every labelled row that is not audit; the other six take
# stratified explicitly. Replicated exactly, so the development half here is the development
# half the weights were fitted on.
SAMPLE_TEST = {"andhra": lambda r: r.get("sample") != "audit"}

# The Scheduled Caste and Scheduled Tribe sub-plan minor heads, the same set four of the
# seven classifiers already weight at +1. 789 is the Special Component Plan for Scheduled
# Castes, 796 the Tribal Area Sub-Plan, 793 and 794 their special central assistance twins.
SUBPLAN_MINOR = {"789", "793", "794", "796"}

# The welfare function major heads, the same set the state classifiers use. 2216 Housing,
# 2225 Welfare of SC, ST and OBC, 2235 Social Security and Welfare, 2236 Nutrition, 2501 and
# 2505 rural development and employment.
WELFARE_MAJOR = {"2216", "2225", "2235", "2236", "2501", "2505"}


def group_of(state, row):
    if state == "andhra":
        return row.get("department") or ""
    if state == "karnataka":
        return (row.get("hoa") or "").split("-")[0]
    if state == "kerala":
        return row.get("sector") or ""
    if state == "maharashtra":
        return row.get("department") or ""
    if state == "odisha":
        return sorted(row.get("departments") or [""])[0]
    if state == "tamilnadu":
        return row.get("department") or ""
    if state == "westbengal":
        return str(sorted(row.get("demands") or [0])[0])
    raise KeyError(state)


def key_of(state, row):
    """The key each classifier builds for a corpus row. Copied from the classifier rather
    than guessed: a wrong key joins nothing and every measurement below silently reads n=0,
    which is what the first run of this file did for Andhra Pradesh and Tamil Nadu."""
    if state == "andhra":
        return (row.get("department") or "") + " | " + (row.get("name") or "")
    if state in ("karnataka", "tamilnadu", "westbengal"):
        return row.get("hoa")
    if state in ("maharashtra", "odisha"):
        return row.get("code")
    return row.get("key")


def joined_key(row):
    """The key on a labels.json or classification.json row. Both files carry the key the
    classifier built, under 'key' everywhere except Karnataka, which keys on the head of
    account and calls the field 'hoa'."""
    return row.get("key") or row.get("hoa")


def major_heads(row):
    """The major heads on a row, as a set. Maharashtra carries them in budget_codes, whose
    first four digits are the major head; everyone else prints them in the head of account.
    Maharashtra's own 10-digit scheme code is a statement serial and NOT a major head, which
    is why it is not read here."""
    out = set()
    if row.get("major_head"):
        out.add(row["major_head"])
    for h in row.get("hoas") or ([row.get("hoa")] if row.get("hoa") else []):
        p = (h or "").replace("-", " ").split()
        if p and p[0]:
            out.add(p[0])
    for b in row.get("budget_codes") or []:
        out.add(str(b)[:4])
    out.discard("")
    return out


def minor_heads(row):
    """The minor heads on a row, as a set. Maharashtra prints no minor head anywhere in its
    Annual Scheme book, so this returns empty there and the sub-plan candidates simply do
    not fire; its cross-cutting split is carried in the component field instead."""
    out = set()
    for h in row.get("hoas") or ([row.get("hoa")] if row.get("hoa") else []):
        p = (h or "").replace("-", " ").split()
        if len(p) > 2:
            out.add(p[2])
    return out


def alloc(row):
    """The budget estimate in lakh, as a float, with nil and missing both zero."""
    v = row.get("be_lakh")
    try:
        return float(v) if v else 0.0
    except (TypeError, ValueError):
        return 0.0


def is_round(v):
    """Round in the sense a policy provision is round: a whole number of lakh with at most
    two significant digits. 21000.0 is round, 3109.87 is not, 5333.33 is not. Nil is not
    round, it is nil."""
    if not v or v <= 0 or abs(v - round(v)) > 1e-9:
        return False
    n = int(round(v))
    d = int(math.floor(math.log10(n)))
    return True if d < 1 else n % (10 ** (d - 1)) == 0


def top_decile(x):
    return bool(x["rank"] and x["group_size"]
                and x["rank"] <= max(1, int(math.ceil(x["group_size"] * 0.1))))


def load_state(state):
    """Corpus rows joined to hand labels and to the current classifier score.

    Sorted by key. Rank within the department is computed over the WHOLE corpus and never
    over the sample, because the rank is a fact about the book.
    """
    entries = json.load(open(os.path.join(ROOT, "data", state, "schemes.json"),
                             encoding="utf-8"))["entries"]
    labels = json.load(open(os.path.join(ROOT, "data", state, "labels.json"),
                            encoding="utf-8"))
    classified = json.load(open(os.path.join(ROOT, "data", state, "classification.json"),
                                encoding="utf-8"))["all_entries"]

    lab = {joined_key(r): r for r in labels["labels"]}
    scores = {joined_key(r): r.get("score") for r in classified}

    # Department groups, then rank by allocation descending with the key as the tie break so
    # two equal provisions rank in a fixed order on every run and every machine.
    groups = {}
    for r in entries:
        groups.setdefault(group_of(state, r), []).append(r)
    rank, gsize, gmedian, gtotal = {}, {}, {}, {}
    for g in sorted(groups):
        rows = sorted(groups[g], key=lambda x: (-alloc(x), str(key_of(state, x))))
        funded = sorted(alloc(x) for x in rows if alloc(x) > 0)
        med = funded[len(funded) // 2] if funded else 0.0
        for i, x in enumerate(rows):
            k = key_of(state, x)
            rank[k], gsize[k], gmedian[k], gtotal[k] = i + 1, len(rows), med, sum(funded)

    # Two facts that read the structure of the book and never the language of the name: how
    # often the same NAME recurs in the corpus, and whether the state books that name under a
    # Scheduled Caste or Tribal sub-plan minor head as well as a general one. A state must
    # show its SCSP and TSP earmark, so a provision paid to citizens is split across
    # components while an office is not.
    recur, minors_by_name = {}, {}
    for r in entries:
        nm = (r.get("name") or "").strip().lower()
        recur[nm] = recur.get(nm, 0) + 1
        minors_by_name.setdefault(nm, set()).update(minor_heads(r))

    book_field, prior_field = BOOK_FIELD[state], PRIOR_FIELD[state]
    in_sample = SAMPLE_TEST.get(state, lambda r: r.get("sample") == "stratified")

    out = []
    for r in entries:
        k = key_of(state, r)
        lr = lab.get(k)
        v = alloc(r)
        med = gmedian.get(k) or 0.0
        tot = gtotal.get(k) or 0.0
        nm = (r.get("name") or "").strip().lower()
        mins = minors_by_name.get(nm, set())
        books = r.get(book_field) if book_field else None
        prior = r.get(prior_field) if prior_field else None
        out.append({
            "key": k,
            "name": r.get("name") or "",
            "group": group_of(state, r),
            "be_lakh": v,
            "rank": rank.get(k),
            "group_size": gsize.get(k),
            "median_multiple": (v / med) if med else None,
            "dept_share": (v / tot) if tot else None,
            "welfare_major": bool(major_heads(r) & WELFARE_MAJOR),
            "name_recurs": recur.get(nm, 1),
            "hoa_count": len(r.get("hoas") or []) or (1 if r.get("hoa") else 0),
            "on_subplan": bool(minor_heads(r) & SUBPLAN_MINOR),
            "split_across_subplan": bool(mins & SUBPLAN_MINOR) and bool(mins - SUBPLAN_MINOR),
            "component": r.get("component"),
            "books": len(books) if isinstance(books, list) else None,
            "prior": float(prior) if isinstance(prior, (int, float)) else None,
            "round": is_round(v),
            "score": scores.get(k),
            "label": (lr or {}).get("label"),
            "reason": (lr or {}).get("reason") or "",
            "in_sample": bool(lr) and in_sample(lr),
        })
    return sorted(out, key=lambda x: str(x["key"]))


def halves(rows):
    """The development and held-out halves, exactly as every classifier splits them: the
    sample rows sorted by key, even index is development."""
    s = sorted((x for x in rows if x["in_sample"]), key=lambda x: str(x["key"]))
    return ([x for i, x in enumerate(s) if i % 2 == 0],
            [x for i, x in enumerate(s) if i % 2 == 1])


def p(rows, pred):
    hit = [x for x in rows if pred(x)]
    if not hit:
        return {"p": None, "n": 0}
    return {"p": round(sum(1 for x in hit if x["label"] == "scheme") / len(hit), 3),
            "n": len(hit)}


def base(rows):
    if not rows:
        return None
    return round(sum(1 for x in rows if x["label"] == "scheme") / len(rows), 3)


# Words that would show a hand labeller citing the size of the provision as a ground for the
# label. Deliberately over-broad: it is meant to over-report, so that a near-empty result is
# evidence rather than a narrow regex missing things.
SIZE_WORDS = re.compile(
    r"\b(crore|crores|lakh|lakhs|rs\.?|rupee|rupees|largest|biggest|large|small|smallest|"
    r"big|huge|substantial|sizeable|sizable|the size|allocation|provision of|amount)\b", re.I)

# The narrow form: a labeller actually reasoning from how big the head is.
SIZE_AS_GROUND = re.compile(
    r"\b(largest|biggest|huge|the size of|large provision|large allocation|well.funded|"
    r"heavily funded|big head|so large|too large|too small|small provision)\b", re.I)


def candidates(state, dev, held, corpus):
    b_dev, b_held = base(dev), base(held)
    out = []

    def rec(signal, pred, note=""):
        d, h = p(dev, pred), p(held, pred)
        ld = round(d["p"] - b_dev, 3) if d["p"] is not None and b_dev is not None else None
        lh = round(h["p"] - b_held, 3) if h["p"] is not None and b_held is not None else None
        out.append({
            "signal": signal,
            "development": d, "held_out": h,
            "base_rate_development": b_dev, "base_rate_held_out": b_held,
            "lift_development": ld, "lift_held_out": lh,
            "agrees_on_both_halves": bool(ld is not None and lh is not None
                                          and ld > 0 and lh > 0),
            "fires_on_rows_in_corpus": sum(1 for x in corpus if pred(x)),
            "note": note,
        })

    # The headline candidate and its variants.
    rec("largest allocation in its own department", lambda x: x["rank"] == 1)
    rec("top 3 allocations in its own department",
        lambda x: bool(x["rank"]) and x["rank"] <= 3)
    rec("top 5 allocations in its own department",
        lambda x: bool(x["rank"]) and x["rank"] <= 5)
    rec("top decile of allocations in its own department", top_decile)
    rec("top quartile of allocations in its own department",
        lambda x: bool(x["rank"]) and bool(x["group_size"])
        and x["rank"] <= max(1, int(math.ceil(x["group_size"] * 0.25))))
    rec("bottom half of allocations in its own department, read as a NEGATIVE",
        lambda x: bool(x["rank"]) and bool(x["group_size"])
        and x["rank"] > x["group_size"] / 2)

    rec("the row takes a quarter or more of its department's whole provision",
        lambda x: (x["dept_share"] or 0) >= 0.25)
    rec("the row takes a tenth or more of its department's whole provision",
        lambda x: (x["dept_share"] or 0) >= 0.10)
    rec("allocation at least 10 times the department median row",
        lambda x: x["median_multiple"] is not None and x["median_multiple"] >= 10)
    rec("allocation at least 3 times the department median row",
        lambda x: x["median_multiple"] is not None and x["median_multiple"] >= 3)
    rec("allocation at least the department median row",
        lambda x: x["median_multiple"] is not None and x["median_multiple"] >= 1)

    rec("largest in its department AND on a welfare function major head",
        lambda x: x["rank"] == 1 and x["welfare_major"])
    rec("top decile of its department AND on a welfare function major head",
        lambda x: x["welfare_major"] and top_decile(x))

    # The other language-independent candidates.
    if BOOK_FIELD[state]:
        rec("the row appears in more than one of the state's books",
            lambda x: (x["books"] or 0) > 1)
        rec("the row appears in three or more of the state's books",
            lambda x: (x["books"] or 0) >= 3)
    if PRIOR_FIELD[state]:
        rec("the head carried an actual provision in the previous year",
            lambda x: (x["prior"] or 0) > 0)
        rec("the head carried NO actual provision in the previous year, so it is new",
            lambda x: not (x["prior"] or 0))
    rec("the same NAME is printed on two or more rows of the corpus",
        lambda x: x["name_recurs"] >= 2)
    rec("the same NAME is printed on three or more rows of the corpus",
        lambda x: x["name_recurs"] >= 3)
    rec("the state books this NAME under a sub-plan minor head AND under a general one",
        lambda x: x["split_across_subplan"])
    rec("the row is itself on a sub-plan minor head, which four of the seven classifiers "
        "already weight at +1",
        lambda x: x["on_subplan"],
        "carried only as the redundancy check for the clause above")
    rec("the row is NOT on a sub-plan minor head but the state books the same NAME on one, "
        "so this row is the general head of an earmarked provision",
        lambda x: x["split_across_subplan"] and not x["on_subplan"],
        "the only part of the sub-plan clause above that four classifiers do not already "
        "have")
    rec("the row spans three or more heads of account", lambda x: x["hoa_count"] >= 3)
    if state == "maharashtra":
        rec("the row is a Scheduled Caste or Tribal component row",
            lambda x: x["component"] in ("SCCS", "TCS"))
    rec("the allocation is a round number, at most two significant digits",
        lambda x: x["round"])
    rec("the allocation is a round number AND in the top decile of its department",
        lambda x: x["round"] and top_decile(x))
    return out


def marginal(dev, held, corpus, bar):
    """Does the candidate separate the rows the LANGUAGE cannot see?

    This is the question the whole investigation turns on. The recall is lost on rows whose
    English says nothing, so a signal that only re-ranks rows the vocabulary already reads
    adds no recall whatever its P(scheme) looks like.
    """
    out = []
    for label, lo, hi in [("rows below the publishing bar", -99, bar),
                          ("rows scoring 0 or less, where the name says nothing", -99, 1)]:
        def sub(rows):
            return [x for x in rows if x["score"] is not None and lo <= x["score"] < hi]
        d, h, c = sub(dev), sub(held), sub(corpus)
        for name, pred in [("largest in its department", lambda x: x["rank"] == 1),
                           ("top 3 in its department",
                            lambda x: bool(x["rank"]) and x["rank"] <= 3),
                           ("top decile of its department", top_decile)]:
            out.append({
                "restricted_to": label, "signal": name,
                "base_rate_development": base(d), "base_rate_held_out": base(h),
                "development": p(d, pred), "held_out": p(h, pred),
                "fires_on_rows_in_corpus": sum(1 for x in c if pred(x)),
            })
    return out


def control(rows, bar, pred):
    """The test that decides it: does the signal beat simply lowering the bar?

    Adding +k for a signal publishes rows that already scored bar-k or better and carry it.
    The band just below every one of these bars is already 70% to 87% schemes, so ANY +k
    publishes more schemes and the increment looks good. The comparison that means something
    is the same band WITHOUT the signal. Counted on the hand labels, which are a census of
    the published region and the bands below it in all seven states, so these are counts
    rather than estimates wherever hand_labelled equals rows.
    """
    out = []
    for w in (1, 2, 3):
        sig = [x for x in rows if x["score"] is not None and pred(x)
               and x["score"] < bar <= x["score"] + w]
        band = [x for x in rows if x["score"] is not None and bar - w <= x["score"] < bar]

        def stat(v):
            lab = [x for x in v if x["label"]]
            good = sum(1 for x in lab if x["label"] == "scheme")
            return {"rows": len(v), "hand_labelled": len(lab), "schemes": good,
                    "precision_of_the_increment":
                        round(good / len(lab), 3) if lab else None}
        out.append({
            "weight": w,
            "rows_the_signal_would_newly_publish": stat(sig),
            "control_lower_the_bar_by_the_same_amount": stat(band),
        })
    return out


def circularity(rows):
    """Did the hand labeller read the figure?

    The worry is that a labeller who saw a large allocation was more inclined to call the row
    a scheme, which would make any size-derived signal a measurement of the labeller rather
    than of the books. Three counts, all on the labelled rows:

      1. how many reason strings cite magnitude at all, split by whether the row is top of
         its department, and how many cite the size of the head AS THE GROUND for the label.
         A labeller reasoning from size would have to say so somewhere in 4,159 reasons.
      2. P(scheme) by RAW allocation quartile on the probability sample. A size-biased
         labeller would have made raw size work. Four of these states already measured this
         and rejected it as non-monotone, and that rejection is itself the evidence.
      3. the top-of-department rows and the reason each was given, printed so a reader can
         see the ground the labeller actually gave rather than take this file's word for it.
    """
    lab = sorted((x for x in rows if x["label"]), key=lambda x: str(x["key"]))
    top = [x for x in lab if x["rank"] == 1]
    rest = [x for x in lab if x["rank"] != 1]
    samp = [x for x in lab if x["in_sample"]]
    funded = sorted(x["be_lakh"] for x in samp if x["be_lakh"] > 0)
    cuts = [funded[int(len(funded) * f)] for f in (0.25, 0.5, 0.75)] if funded else [0, 0, 0]

    def band(x):
        v = x["be_lakh"]
        if v <= 0:
            return "nil"
        return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"

    return {
        "reason_strings_citing_magnitude_at_all": {
            "top_of_department": {"n": len(top),
                                  "citing": sum(1 for x in top
                                                if SIZE_WORDS.search(x["reason"]))},
            "every_other_labelled_row": {"n": len(rest),
                                         "citing": sum(1 for x in rest
                                                       if SIZE_WORDS.search(x["reason"]))},
        },
        "reason_strings_citing_the_size_of_the_head_AS_THE_GROUND": {
            "top_of_department": sum(1 for x in top if SIZE_AS_GROUND.search(x["reason"])),
            "every_other_labelled_row": sum(1 for x in rest
                                            if SIZE_AS_GROUND.search(x["reason"])),
        },
        "p_scheme_by_raw_allocation_quartile_on_the_probability_sample": {
            nm: {"p": base([x for x in samp if band(x) == nm]),
                 "n": len([x for x in samp if band(x) == nm])}
            for nm in ["nil", "q1", "q2", "q3", "q4"]},
        "top_of_department_rows_and_the_reason_each_was_given": [
            {"key": x["key"], "name": x["name"], "be_lakh": round(x["be_lakh"], 2),
             "label": x["label"], "reason": x["reason"]} for x in top],
    }


def pooled(dev_pairs, held_pairs, per_state):
    """Observed versus expected scheme count over all seven states.

    The headline candidate fires on one row per department, so no single state's sample holds
    enough of them to measure. Pooling is the best powered test available, and it is done as
    an EXCESS over each state's OWN base rate rather than as a raw average, because pooling
    states whose base rates run 8% to 41% would otherwise let the state with the highest base
    rate decide the answer.
    """
    tests = [
        ("largest allocation in its own department", lambda x: x["rank"] == 1),
        ("top 3 allocations in its own department",
         lambda x: bool(x["rank"]) and x["rank"] <= 3),
        ("top decile of allocations in its own department", top_decile),
        ("the row takes a quarter or more of its department's whole provision",
         lambda x: (x["dept_share"] or 0) >= 0.25),
        ("top decile of its department, among rows on a welfare function major head only",
         lambda x: x["welfare_major"] and top_decile(x)),
        ("on a welfare function major head and NOT in the top decile, the control for the "
         "clause above",
         lambda x: x["welfare_major"] and not top_decile(x)),
        ("the allocation is a round number, at most two significant digits",
         lambda x: x["round"]),
        ("the same NAME is printed on three or more rows of the corpus",
         lambda x: x["name_recurs"] >= 3),
    ]
    out = []
    for name, pred in tests:
        row = {"signal": name}
        for half, pairs, key in [("development", dev_pairs, "base_rate_development"),
                                 ("held_out", held_pairs, "base_rate_held_out")]:
            hit = [(s, x) for s, x in pairs if pred(x)]
            obs = sum(1 for s, x in hit if x["label"] == "scheme")
            exp = sum(per_state[s][key] or 0.0 for s, x in hit)
            row[half] = {"n": len(hit), "observed_schemes": obs,
                         "expected_from_state_base_rates": round(exp, 1),
                         "p": round(obs / len(hit), 3) if hit else None,
                         "excess_schemes": round(obs - exp, 1)}
        out.append(row)
    return out


# Every candidate, with the measurement that rejected it, in the shape signals_rejected takes
# in each classification.json. Numbers are read off the per-state tables below; they are
# written out here so the record can be read without joining seven nested objects.
REJECTED = [
    {"signal": "ALLOCATION RANK WITHIN ITS OWN DEPARTMENT, the candidate this investigation "
               "was opened to test: largest in its department, top 3, top 5, top decile, "
               "top quartile",
     "measured": (
         "Top decile, development half then held out, against each state's base rate: "
         "Andhra Pradesh 0.444 over 18 and 0.500 over 22 against 0.412 and 0.426; Karnataka "
         "0.467 over 15 and 0.267 over 15 against 0.370 and 0.364; Kerala 0.250 over 16 and "
         "0.158 over 19 against 0.174 and 0.137; Maharashtra 0.318 over 22 and 0.200 over 20 "
         "against 0.240 and 0.231; Odisha 0.167 over 18 and 0.273 over 22 against 0.092 and "
         "0.113; Tamil Nadu 0.350 over 20 and 0.143 over 21 against 0.160 and 0.146; West "
         "Bengal 0.118 over 17 and 0.174 over 23 against 0.080 and 0.089. Pooled over all "
         "seven, 38 schemes observed against 27.2 expected on 126 development rows and 35 "
         "against 29.7 on 142 held-out rows. LARGEST IN ITS DEPARTMENT is thinner and worse: "
         "46 development rows across all seven states, 16 schemes against 12.5 expected."),
     "why": (
         "Three reasons, and the third is the one that settles it. First, the two halves "
         "disagree in SIGN in three of the seven states for the top decile and in five of "
         "the seven for the largest row, which is what a signal fitted on a handful of rows "
         "looks like; the candidate fires on about one row per department, so no state's "
         "probability sample holds enough of them to measure. Second, it carries nothing "
         "where the recall is actually lost: among rows the classifier scores 0 or less, "
         "where the English says nothing at all, P(scheme | largest in its department) is "
         "0.000 on the development half in ALL SEVEN states, on 1 to 7 rows each. Third and "
         "decisive, it does not beat the control. Adding +k publishes rows that already "
         "scored bar-k, and the band just below every one of these bars is already 73% to "
         "88% schemes, so any positive weight publishes more schemes. Set against simply "
         "lowering the bar by the same k, at +1 the signal is WORSE in Maharashtra, 0.714 "
         "over 7 rows against 0.868 over 53, a tie in Andhra Pradesh at 0.750 against 0.745, "
         "and better in the other five only on increments of 2 to 15 hand labelled rows. "
         "What the candidate actually selects is visible in "
         "circularity_check.top_of_department_rows_and_the_reason_each_was_given: the "
         "largest provision in a department is the establishment block. Odisha's 44 are led "
         "by Loans at Rs 14,911 crore, General Primary Schools at Rs 9,498 crore, "
         "Construction of Buildings, District Establishment and Emoluments of Members of "
         "Legislative Assembly. West Bengal's largest row in any demand is Secondary Schools "
         "for Boys and Girls at Rs 19,438 crore, larger than Lakshmir Bhandar, with West "
         "Bengal Police third. Maharashtra's include District and Other Roads at Rs 6,600 "
         "crore and 'Office Building.'. Being big inside a department is a fact about "
         "payroll and public works before it is a fact about schemes.")},

    {"signal": "the bottom half of its department's allocations, read as a NEGATIVE rather "
               "than the top read as a positive",
     "measured": ("Development half then held out against base: Andhra Pradesh 0.343 over 67 "
                  "and 0.319 over 47; Karnataka 0.259 over 58 and 0.327 over 55; Kerala "
                  "0.221 over 86 and 0.133 over 75; Maharashtra 0.224 over 98 and 0.188 over "
                  "101; Odisha 0.055 over 91 and 0.100 over 110; Tamil Nadu 0.125 over 104 "
                  "and 0.113 over 97; West Bengal 0.078 over 116 and 0.065 over 107."),
     "why": ("The n is finally large, and the effect is gone. The lift is within two points "
             "of the base rate in five of the seven states and points the wrong way in "
             "Kerala. A small provision is not evidence of an establishment head: the "
             "grazing subsidy to shepherd families is Rs 5 crore and the pension to indigent "
             "sportsmen is a few lakh. This is the same finding the raw-size rejection "
             "already carries in four of these files, restated on a normalised axis.")},

    {"signal": "the allocation as a multiple of the department's median row, at 10x, 3x and 1x",
     "measured": ("At 10 times the department median, development then held out against "
                  "base: Andhra Pradesh 0.545 over 11 and 0.565 over 23 against 0.412 and "
                  "0.426; Karnataka 0.444 over 9 and 0.500 over 6 against 0.370 and 0.364; "
                  "Kerala 0.300 over 10 and 0.200 over 10 against 0.174 and 0.137; "
                  "Maharashtra 0.400 over 35 and 0.216 over 37 against 0.240 and 0.231; "
                  "Odisha 0.182 over 33 and 0.269 over 26 against 0.092 and 0.113; Tamil "
                  "Nadu 0.243 over 37 and 0.152 over 33 against 0.160 and 0.146; West Bengal "
                  "0.143 over 14 and 0.125 over 16 against 0.080 and 0.089."),
     "why": ("The best behaved member of the family and still not enough. It is the only "
             "variant that lifts on both halves in six of the seven states, and the lift is "
             "between +0.01 and +0.16, which on this repository's scale is worth +1 and no "
             "more: Karnataka gives +4 to a purpose line measuring 0.947 and Odisha +1 to a "
             "sub-plan head measuring 0.145. At +1 it beats the control of lowering the bar "
             "in five states by between 3 and 9 points of precision on 2 to 13 newly "
             "published rows, ties in Andhra Pradesh and loses in Maharashtra. And at +1 it "
             "moves NONE of the seven named schemes: Mukhyamantri Mazi Ladaki Bahin would go "
             "from 5 to 6 against a bar of 8, Lakshmir Bhandar from 3 to 4 against 10, "
             "Subhadra from 7 to 8 against 9, Magalir Urimai Thogai's general head from 4 to "
             "5 against 10, Gruha Lakshmi from 2 to 3 against 7 and Thallikivandanam from 0 "
             "to 1 against 4. It would buy a few rows per state, cost seven censuses their "
             "coverage, and leave the stated problem exactly where it is.")},

    {"signal": "the row takes a quarter or a tenth of its whole department's provision",
     "measured": ("At a quarter, development then held out: Andhra Pradesh 0.467 over 15 and "
                  "0.600 over 10; Karnataka 0.444 over 9 and 0.250 over 12; Kerala 0.000 "
                  "over 4 and 0.600 over 5; Maharashtra 0.429 over 7 and 0.000 over 5; "
                  "Odisha 0.167 over 6 and 1.000 over 1; Tamil Nadu 0.000 over 2 and 0.000 "
                  "over 3; West Bengal 0.500 over 2 and no held-out row at all."),
     "why": ("Unmeasurable. Four states put fewer than eight development rows on it and "
             "three of those flip sign between the halves. Pooled it is 16 schemes against "
             "12.9 expected on 45 rows, the same weak excess as the rank family it "
             "belongs to.")},

    {"signal": "the row appears in more than one of the state's books",
     "measured": ("Development then held out against base: Andhra Pradesh 0.407 over 54 and "
                  "0.515 over 66 against 0.412 and 0.426; Karnataka 0.462 over 52 and 0.411 "
                  "over 56 against 0.370 and 0.364; Kerala 0.286 over 14 and 0.217 over 23 "
                  "against 0.174 and 0.137; Odisha 0.100 over 10 and 0.091 over 11 against "
                  "0.092 and 0.113; West Bengal 0.091 over 11 and 0.111 over 9 against 0.080 "
                  "and 0.089. Tamil Nadu prints one departmental volume per row and "
                  "Maharashtra one statement, so it fires on nothing in either."),
     "why": ("Flat. It is within two points of the base rate in Andhra Pradesh, Odisha and "
             "West Bengal, and where it lifts, in Karnataka and Kerala, the lift is +0.05 to "
             "+0.11 on 14 to 56 rows. It also measures the wrong thing: a row is in the "
             "Gender Budget and the Scheduled Caste annexure because the state cross-tabs "
             "the same provision, which is a fact about how many annexures the state "
             "publishes and not about what the money buys.")},

    {"signal": "whether the same head carried a provision in an earlier year, where the "
               "parsers captured prior-year columns",
     "measured": ("Only Maharashtra, Odisha and West Bengal print a prior-year actual. NO "
                  "prior actual, so the head is new, development then held out against base: "
                  "Maharashtra 0.300 over 80 and 0.263 over 95 against 0.240 and 0.231; "
                  "Odisha 0.111 over 45 and 0.167 over 48 against 0.092 and 0.113; West "
                  "Bengal 0.109 over 119 and 0.065 over 123 against 0.080 and 0.089. The "
                  "converse, a prior actual present, runs at or below the base rate in all "
                  "three."),
     "why": ("The direction is right and the size is nothing: a new head is very slightly "
             "more likely to be a scheme, by 2 to 6 points, and West Bengal's halves "
             "disagree. The reason it is weak is visible in the corpus: a state opens new "
             "heads for offices, works and centrally sponsored components as readily as for "
             "schemes, and the schemes that matter here are not new. Lakshmir Bhandar, "
             "Kanyashree and Magalir Urimai Thogai all carry last year's actual.")},

    {"signal": "the allocation is a round number, which might mark a policy provision rather "
               "than an establishment estimate",
     "measured": ("A whole number of lakh with at most two significant digits. Development "
                  "then held out against base: Andhra Pradesh 0.500 over 28 and 0.406 over "
                  "32 against 0.412 and 0.426; Karnataka 0.429 over 42 and 0.600 over 40 "
                  "against 0.370 and 0.364; Kerala 0.157 over 89 and 0.163 over 86 against "
                  "0.174 and 0.137; Maharashtra 0.232 over 99 and 0.232 over 82 against "
                  "0.240 and 0.231; Odisha 0.214 over 42 and 0.171 over 35 against 0.092 and "
                  "0.113; Tamil Nadu 0.056 over 18 and 0.136 over 22 against 0.160 and "
                  "0.146; West Bengal 0.081 over 37 and 0.077 over 39 against 0.080 and "
                  "0.089. Pooled, 82 schemes against 76.0 expected on 355 development rows."),
     "why": ("Flat in five states and pointing the wrong way in Tamil Nadu. It lifts in "
             "Odisha, by +0.12 and +0.06 on 42 and 35 rows, and in Karnataka, and that is "
             "the whole of it. Even in Odisha it is useless for the problem at hand: "
             "Subhadra Yojana is Rs 1,014,520 lakh and Samrudha Krushaka Rs 608,840 lakh, "
             "neither of them round, while AAHAAR is round at Rs 9,000 lakh and would go "
             "from 6 to 7 against a bar of 9. The premise is wrong in a way worth recording: "
             "a state rounds a WORKS provision as readily as a scheme, and it does not round "
             "a cash transfer at all, because that figure is a beneficiary count times a "
             "rate.")},

    {"signal": "the same NAME is printed on two or three or more rows of the corpus",
     "measured": ("At three or more, development then held out against base: Andhra Pradesh "
                  "0.611 over 18 and 0.444 over 9 against 0.412 and 0.426; Karnataka 0.000 "
                  "over 7 and 0.000 over 6; Maharashtra 0.429 over 7 and 0.333 over 3 "
                  "against 0.240 and 0.231; Tamil Nadu 0.345 over 29 and 0.333 over 27 "
                  "against 0.160 and 0.146; West Bengal 0.145 over 62 and 0.156 over 77 "
                  "against 0.080 and 0.089. Kerala and Odisha collapse repeated names in the "
                  "parser, so it fires on 3 rows and 0 rows there."),
     "why": ("The strongest of the structural candidates and still not enough, and most of "
             "it is already counted. A name recurs because the state votes the provision "
             "again under its Scheduled Caste and Tribal sub-plan heads, which is the "
             "sub-plan minor head signal that Tamil Nadu, West Bengal, Odisha and Kerala "
             "already weight at +1. Its lift over the base rate is +0.19 in Tamil Nadu and "
             "+0.07 in West Bengal, which buys +1 at most on this repository's scale, and at "
             "+1 Magalir Urimai Thogai's general head goes from 4 to 5 against a bar of 10 "
             "and Lakshmir Bhandar from 3 to 4 against 10. It also points the wrong way in "
             "Karnataka, where the recurring names are the Development Action Plan sub-plan "
             "allocation heads.")},

    {"signal": "the state books this NAME under a Scheduled Caste or Tribal sub-plan minor "
               "head AND under a general one, so the general head is an earmarked provision",
     "measured": ("Development then held out against base: Odisha 0.155 over 58 and 0.246 "
                  "over 61 against 0.092 and 0.113; Tamil Nadu 0.600 over 20 and 0.667 over "
                  "15 against 0.160 and 0.146; West Bengal 0.156 over 64 and 0.159 over 69 "
                  "against 0.080 and 0.089. The part that is NOT already counted, rows not "
                  "themselves on a sub-plan head, measures 0.500 over 8 and 0.429 over 7 in "
                  "Tamil Nadu and 0.038 over 26 and 0.192 over 26 in West Bengal."),
     "why": ("This was the best idea in the investigation and it is nearly all redundant. In "
             "Odisha it measures 0.155 and 0.246 where the plain sub-plan head the file "
             "already weights measures 0.145 and 0.242, which is the same signal counted "
             "twice. The genuinely new part, giving the GENERAL head of a provision credit "
             "for having sub-plan twins, is the exact defect West Bengal records in "
             "known_errors, where the Jai Bangla pensions' Scheduled Caste and Tribal twins "
             "clear the bar and the general head does not. It fails anyway: 8 development "
             "rows in Tamil Nadu, and in West Bengal it points the WRONG WAY on the "
             "development half, 0.038 against a base of 0.080, which is the half every "
             "weight in that file was fitted on.")},

    {"signal": "the row spans three or more heads of account",
     "measured": ("Only Andhra Pradesh, Kerala and Odisha print a list of heads per row. "
                  "Andhra Pradesh 0.192 over 26 and 0.472 over 36 against 0.412 and 0.426; "
                  "Kerala 0.200 over 10 and 0.286 over 14 against 0.174 and 0.137; Odisha "
                  "0.115 over 52 and 0.200 over 60 against 0.092 and 0.113."),
     "why": ("Points the wrong way on the development half in Andhra Pradesh and lifts by "
             "+0.03 to +0.11 elsewhere. It is the same sub-plan fact as the clause above, "
             "counted less precisely: a row spans several heads because the state votes it "
             "under the general, Scheduled Caste and Tribal heads.")},

    {"signal": "top decile of its department AND on a welfare function major head, the "
               "interaction, which is the strongest looking number in this file",
     "measured": ("Pooled over all seven states it is P(scheme) 0.750 on 20 development rows "
                  "and 0.640 on 25 held-out rows, against a control of 0.426 and 0.446 for "
                  "welfare-major rows NOT in the top decile. Per state the development n is "
                  "1 to 5: Andhra Pradesh 1.000 over 3, Karnataka 0.500 over 2, Kerala 0.667 "
                  "over 3, Maharashtra 0.800 over 5, Odisha 0.000 over 1, Tamil Nadu 1.000 "
                  "over 3, West Bengal 0.667 over 3."),
     "why": ("Published here because it is the one number in the investigation that looks "
             "spectacular, and it must not be read as a finding. It can only be stated "
             "pooled, and a weight cannot be pooled: each classifier is fitted on its own "
             "state, against its own base rate, and no state here puts more than five "
             "development rows on it. Against the control of lowering the bar it fails "
             "outright in Maharashtra, where at +1 the rows it newly publishes are 0.500 "
             "precise against 0.868 for the band, and in Kerala and Tamil Nadu, and it "
             "passes on 1 to 9 rows in the other three. A rule fitted on five rows that "
             "publishes 52 in Maharashtra and 129 in Tamil Nadu is not a measurement.")},
]


# The schemes the task named, one per state plus the extras each classification.json already
# records in known_errors. Matched on a substring of the printed name, lower-cased.
NAMED = [
    ("maharashtra", "Mukhyamantri Mazi Ladaki Bahin", "mukhyamantri mazi ladaki bahin"),
    ("westbengal", "Lakshmir Bhandar", "lakshmir bhandar"),
    ("odisha", "Subhadra Yojana", "subhadra yojana"),
    ("tamilnadu", "Magalir Urimai Thogai", "magalir urimai thogai"),
    ("odisha", "Samrudha Krushaka Yojana", "samrudha krushaka"),
    ("karnataka", "Gruha Lakshmi", "gruha lakshmi"),
    ("andhra", "Thallikivandanam", "thallikivandanam"),
]


def named_schemes(by_state, bars):
    out = []
    for state, label, pat in NAMED:
        for x in sorted(by_state[state], key=lambda r: (-r["be_lakh"], str(r["key"]))):
            if pat not in x["name"].lower():
                continue
            bar = bars[state]
            out.append({
                "state": state, "scheme": label, "name_as_printed": x["name"],
                "key": x["key"], "be_lakh": round(x["be_lakh"], 2),
                "score": x["score"], "publish_threshold": bar,
                "points_short": (bar - x["score"]) if x["score"] is not None else None,
                "published_today": bool(x["score"] is not None and x["score"] >= bar),
                "rank_in_its_department": x["rank"],
                "rows_in_that_department": x["group_size"],
                "in_the_top_decile_of_its_department": top_decile(x),
                "largest_in_its_department": x["rank"] == 1,
                "allocation_as_a_multiple_of_the_department_median":
                    round(x["median_multiple"], 1) if x["median_multiple"] else None,
            })
    return out


def main():
    per_state, by_state, bars = {}, {}, {}
    pool_dev, pool_held = [], []
    for state in STATES:
        rows = load_state(state)
        dev, held = halves(rows)
        bar = json.load(open(os.path.join(ROOT, "data", state, "classification.json"),
                             encoding="utf-8"))["publish_threshold"]
        by_state[state], bars[state] = rows, bar
        per_state[state] = {
            "corpus_rows": len(rows),
            "labelled_rows": sum(1 for x in rows if x["label"]),
            "departments": len({x["group"] for x in rows}),
            "department_grouping": GROUP_FIELD[state],
            "n_development": len(dev), "n_held_out": len(held),
            "base_rate_development": base(dev), "base_rate_held_out": base(held),
            "publish_threshold": bar,
            "candidates": candidates(state, dev, held, rows),
            "marginal_on_the_rows_the_language_misses": marginal(dev, held, rows, bar),
            "control_does_it_beat_lowering_the_bar": {
                "top_decile_of_its_department": control(rows, bar, top_decile),
                "top_decile_of_its_department_AND_a_welfare_major_head": control(
                    rows, bar, lambda x: x["welfare_major"] and top_decile(x)),
            },
            "circularity_check": circularity(rows),
        }
        pool_dev.extend((state, x) for x in dev)
        pool_held.extend((state, x) for x in held)

    write_json("data/recall_investigation.json", {
        "built": utcnow(),
        "question": (
            "All seven state classifiers read English and all seven miss the state's own "
            "largest schemes, because a Bengali, Telugu, Tamil, Odia, Marathi or Kannada "
            "brand name says nothing to a vocabulary of English benefit words. Is there a "
            "LANGUAGE-INDEPENDENT signal in what these states print that would recover "
            "them? The candidate named for testing was allocation rank within the row's own "
            "department, on the argument that a state's largest provisions inside a welfare "
            "department are overwhelmingly schemes and its smallest are establishment and "
            "works heads."),
        "answer": (
            "No. Nothing here is wired into any classifier and no state was changed. The "
            "department-rank signal is real and far too weak. Pooled over all seven states "
            "its top decile carries P(scheme) 0.302 against an expected 0.216 on the "
            "development half and 0.246 against 0.209 on the held-out half, a lift of nine "
            "points and then four. Per state the two halves disagree in SIGN in three of the "
            "seven for the top decile and in five of the seven for the largest row in a "
            "department. On the rows where the recall is actually lost, those the English "
            "cannot read at all, it carries nothing: P(scheme | largest in its department) "
            "among rows scoring 0 or less is 0.000 on the development half in ALL SEVEN "
            "states. Against the control that matters, simply lowering the publishing bar by "
            "the same number of points, it is worse in Maharashtra at every weight tried, a "
            "tie in Andhra Pradesh, and better elsewhere only on increments of 2 to 20 hand "
            "labelled rows. And at +1, the most any of these measurements would buy on this "
            "repository's scale, not one of the seven named schemes clears its bar: "
            "Mukhyamantri Mazi Ladaki Bahin goes 5 to 6 against a bar of 8, Subhadra 7 to 8 "
            "against 9, Samrudha Krushaka 5 to 6 against 9, Lakshmir Bhandar 3 to 4 against "
            "10, Magalir Urimai Thogai's general head 4 to 5 against 10, Gruha Lakshmi 2 to "
            "3 against 7 and Thallikivandanam 0 to 1 against 4."),
        "why_the_signal_looked_good_and_is_not": (
            "The reason is visible by listing the rows it fires on, which is done per state "
            "under circularity_check.top_of_department_rows_and_the_reason_each_was_given. "
            "The largest provision inside a department is usually the establishment block. "
            "In Odisha the 44 largest-in-department rows are led by 'Loans' at Rs 14,911 "
            "crore, 'General Primary Schools' at Rs 9,498 crore, 'Construction of "
            "Buildings', 'District Establishment', 'Tahasil Establishment' and 'Emoluments "
            "of Members of Legislative Assembly'. In West Bengal the largest row in any "
            "demand is 'Secondary Schools for Boys and Girls' at Rs 19,438 crore, larger "
            "than Lakshmir Bhandar, and 'West Bengal Police' is third. In Maharashtra they "
            "include 'District and Other Roads' at Rs 6,600 crore, 'Capital Outlay on Major "
            "Irrigation' and 'Office Building.'. Being big inside a department is a fact "
            "about payroll and public works before it is a fact about schemes, and the "
            "classifiers already reject those rows at scores of -7 to -15, which is why "
            "adding the signal does not publish them and also why it adds no information."),
        "what_would_have_been_needed": (
            "The gap is not one signal wide. Lakshmir Bhandar scores 3 against a bar of 10, "
            "Magalir Urimai Thogai's general head 4 against 10, Gruha Lakshmi 2 against 7, "
            "Thallikivandanam 0 against 4, Mukhyamantri Mazi Ladaki Bahin 5 against 8, "
            "Samrudha Krushaka 5 against 9 and Subhadra 7 against 9. Recovering them needs "
            "+2 to +7 from a signal measuring P(scheme) 0.15 to 0.35, where these files give "
            "+4 to a benefit word measuring 0.947 in Karnataka and 0.389 in Odisha. A weight "
            "of that size on evidence of that strength would not be a classifier, it would "
            "be a decision to publish the biggest rows in the book and call it a "
            "measurement."),
        "method": (
            "Every P(scheme) is measured on the DEVELOPMENT half of each state's existing "
            "stratified sample, the same half every weight in every classifier was fitted "
            "on: sample rows sorted by key, even index. The held-out half is reported beside "
            "it. Three tests, declared before the numbers were read: (a) the candidate must "
            "lift P(scheme) above the state's base rate on BOTH halves; (b) its n must be at "
            "least as large as the thinnest signal the state already weights; (c) it must "
            "beat the control of simply lowering the publishing bar by the same number of "
            "points. Test (c) is the one that is easy to skip and it is the one that decides "
            "this: the band just below every one of these bars is already 70% to 87% "
            "schemes, so any positive weight publishes more schemes and the increment always "
            "looks good."),
        "did_the_signal_survive_the_circularity_check": (
            "The question does not arise on the merits, because the signal fails on strength "
            "long before its provenance matters. It was tested anyway, three ways. FIRST, "
            "the reason string every hand label carries was read for any sign that the "
            "labeller reasoned from how big the head is. Of 4,159 labelled rows across the "
            "seven states, 39 reasons mention magnitude at all and exactly TWO cite the size "
            "of the head, both of them describing the row rather than grounding the label, "
            "and both labelled not_scheme: 'the district police establishment, the largest "
            "salary head in the book' in Tamil Nadu and 'a recovery mirror carrying the name "
            "of Lakshmir Bhandar, the state's largest cash transfer' in West Bengal. The "
            "reasons that do quote a rupee figure quote the BENEFIT, 'Ladki Bahin pays Rs "
            "1,500 a month to a woman', which is what a person receives and not what the "
            "head costs. SECOND, P(scheme) by raw allocation quartile on the probability "
            "sample: a labeller biased by size would have made raw size work, and it is "
            "non-monotone in six of the seven states, which is the same rejection Kerala, "
            "Maharashtra, Odisha and Tamil Nadu already wrote into their own "
            "signals_rejected. Andhra Pradesh is the exception, running 0.234, 0.312, 0.447 "
            "and 0.625 across quartiles, and that is a fact about its corpus rather than "
            "about its labeller: those six books are the Gender, Child, Scheduled Caste, "
            "Scheduled Tribe, Backward Class and Minority annexures, already filtered to "
            "beneficiary-facing rows, where the base rate is 41% and the big rows really are "
            "the big schemes. THIRD, and this is the test with teeth, the marginal table: if "
            "size drove the labels then within a fixed score band a larger row would be "
            "labelled scheme more often. It is not. Restricted to rows below the publishing "
            "bar the excess is a row or two on n of 1 to 22, and restricted to rows scoring "
            "0 or less it is zero everywhere. The same measurement says the signal is not "
            "circular and that it is not useful, and those are not two findings."),
        "the_census_was_not_extended_and_did_not_need_to_be": (
            "Adding a signal moves rows above the publishing bar that were never hand "
            "labelled, so the audit census would no longer cover the published set and the "
            "counted precision in each classification.json would no longer apply. No state "
            "was changed here, so every published set is exactly what it was and every "
            "counted precision still stands. The seven files are untouched."),
        "signals_rejected": REJECTED,
        "states_changed": [],
        "why_the_control_table_can_reject_a_weight_and_can_never_justify_one": (
            "The control table below is counted on the hand labels, and in every state most "
            "of those labels are the AUDIT set, a census of the rows the classifier already "
            "scores highly, made after the weights were fixed and deliberately not fed back "
            "into them. Maharashtra's known_errors states the rule plainly for a different "
            "fix: it would be principled, and it is not done, because it was found by "
            "reading the audit and refitting on the audit would destroy the one measurement "
            "in the file that counts errors rather than estimating them. So the control is "
            "used here in one direction only. Where it says the signal is no better than "
            "lowering the bar, that is a rejection and it stands. Where it says the signal "
            "looks good, that is not a justification. West Bengal is the case that makes the "
            "distinction concrete and it is the closest any state came to a change: +1 on "
            "the top decile there would newly publish 15 rows, 14 of them schemes, taking "
            "counted precision from 92.5% to 92.6% with no new hand labelling needed at all, "
            "because the census already covers them. And of those 15 rows exactly ONE is in "
            "the probability sample. Choosing the weight on the strength of the other 14 "
            "would be fitting on the audit, and the development half, which is the only half "
            "any weight in that file was fitted on, puts the signal at 0.118 over 17 rows "
            "against a base of 0.080. West Bengal's own file refuses to give more than +1 to "
            "a sub-plan head measuring 0.255 over 47. This one does not earn the point."),
        "states_left_alone": [
            {"state": "andhra",
             "why": ("Top decile of department measures 0.444 over 18 development rows and "
                     "0.500 over 22 held out, against base rates of 0.412 and 0.426: a lift "
                     "of three and seven points on a corpus that is already six welfare "
                     "annexures filtered to beneficiary-facing rows. Against the control it "
                     "is a dead heat, 0.750 over 4 rows against 0.745 over 55. "
                     "Thallikivandanam scores 0 against a bar of 4 and is rank 2, 2, 3, 3 "
                     "and 8 in its five departments, so even the largest-in-department form "
                     "does not fire on four of its five heads.")},
            {"state": "karnataka",
             "why": ("The halves disagree: 0.467 over 15 development rows against a base of "
                     "0.370, and 0.267 over 15 held out against 0.364. Gruha Lakshmi is rank "
                     "1 of 108 on major head 2235 and scores 2 against a bar of 7, so it "
                     "needs +5 from a signal whose held-out half points the wrong way. "
                     "Karnataka's real recall problem is also not this: 580 of its 969 rows "
                     "carry no purpose line, and the purpose line is the signal that "
                     "measures 0.947 in that file.")},
            {"state": "kerala",
             "why": ("0.250 over 16 development rows and 0.158 over 19 held out, against "
                     "0.174 and 0.137. Both halves lift, by eight points and two. Against "
                     "the control it wins at +1 on three rows and ties exactly at +2, 0.875 "
                     "against 0.875 over 64. Kerala has no scheme in the named seven and its "
                     "recall is the second best in the register, so there is nothing here "
                     "worth the cost of voiding a 97.4% counted precision.")},
            {"state": "maharashtra",
             "why": ("The clearest failure. 0.318 over 22 development rows against a base of "
                     "0.240, and 0.200 over 20 held out against 0.231, so the held-out half "
                     "points the wrong way. Against the control it is WORSE at every weight "
                     "tried: at +1 the rows it newly publishes are 0.714 precise against "
                     "0.868 for the band it comes from. Mukhyamantri Mazi Ladaki Bahin is "
                     "rank 1 of 86 and needs +3, on a signal that in this state is worse "
                     "than moving the bar.")},
            {"state": "odisha",
             "why": ("One of the two states where both halves lift: 0.167 over 18 "
                     "development rows and 0.273 over 22 held out, against 0.092 and 0.113. "
                     "It beats the control at +2, 0.833 over 6 rows against 0.513 over 39. "
                     "It is left alone because that is 6 rows, because +2 is what this file "
                     "pays for a welfare major head measured at 0.233 over 30 rows, and "
                     "because at the +1 the development half supports Subhadra Yojana goes "
                     "from 7 to 8 against a bar of 9 and Samrudha Krushaka from 5 to 6. The "
                     "state's two largest schemes stay out either way.")},
            {"state": "tamilnadu",
             "why": ("The halves disagree: 0.350 over 20 development rows against a base of "
                     "0.160, and 0.143 over 21 held out against 0.146, which is the base "
                     "rate to within a rounding error. Magalir Urimai Thogai is already "
                     "published on two of its three heads at scores 11 and 12; the head that "
                     "is missed is the Rs 9,803 crore general head at score 4, which needs "
                     "+6.")},
            {"state": "westbengal",
             "why": ("The other state where both halves lift, and the closest call in the "
                     "register: 0.118 over 17 development rows and 0.174 over 23 held out, "
                     "against 0.080 and 0.089. See "
                     "why_the_control_table_can_reject_a_weight_and_can_never_justify_one "
                     "for why the 14-of-15 audit result is not the argument it looks like. "
                     "On the development half the lift is under four points on 17 rows, "
                     "below the weakest positive this file already weights, and it fires on "
                     "931 of 9,024 rows. Lakshmir Bhandar would go from 3 to 4 against a bar "
                     "of 10.")},
        ],
        "the_seven_named_schemes": named_schemes(by_state, bars),
        "pooled": {
            "what": ("Candidates that fire on about one row per department are too thin to "
                     "measure in any one state. Pooling all seven is the best powered test "
                     "available. Observed is the count of rows the hand labels call schemes; "
                     "expected is what the base rate of each contributing state predicts for "
                     "the same rows, so a state with a 41% base rate cannot carry the "
                     "answer for a state with 8%."),
            "signals": pooled(pool_dev, pool_held, per_state),
        },
        "states": per_state,
    })


if __name__ == "__main__":
    main()
