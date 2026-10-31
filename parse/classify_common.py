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

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, utcnow, write_json  # noqa: E402
from match import probably_same, similarity, tokens, skeletons, acronyms  # noqa: E402

# Underscores and slashes are word characters to a regex and word breaks to a reader.
# TRIPURA_NATIONAL HEALTH MISSION did not match \bnational health mission\b for exactly
# that reason, and it was the last error in that state's file.
def norm(name):
    return re.sub(r"[_/]+", " ", name or "")


# THE RULE, NOT A SIGNAL, WHICH IS WHY IT IS THE ONE PATTERN THIS FILE HOLDS.
#
# The register's definition of a scheme excludes money that "pays for the capacity of the
# delivery system rather than the benefit". A helpline, a creche, an anganwadi's running
# costs, a child-protection system, a one-stop centre, an agricultural extension wing: each
# is how a benefit reaches somebody and none is the benefit. Seven states were labelled
# against that wording from the start. Eight later ones were labelled against a looser
# sentence that admitted "a service", and 56 of their published rows changed side when they
# were re-read against this one.
#
# It sits here rather than in each state's file because it is not an observation about any
# state's book. It is the definition, and the whole point of the definition is that it is
# the same everywhere.
CAPACITY = re.compile(
    r"helpline|help line|one stop cent|hub for empowerment|anganwadi service|"
    r"aanganwadi service|creche|palna|vatsalya|child protection|nari adalat|"
    r"anganwadi chalo|poshan abhiyan|poshan abiyan|food centre|"
    r"agriculture extension|agricultural extension|agriculture extensio|"
    r"soil health management|sankalp|women helpdesk|"
    r"components other than nutrition", re.I)

# A row that names the benefit itself survives, even when a capacity word is also in it.
# "ICDS Projects (Saksham Aanganwadi & Poshan 2.0) Supplementary Nutrition Programme" buys
# food for a household and carries two capacity words; "Mission Vatsalya - care and support
# to victims" reaches a named person. The override is what keeps the rule a rule rather
# than a word list.
BENEFIT_DESPITE = re.compile(
    r"supplementary nutrition|adolescent girls|janman|victim|pavala|pavalavaddi|"
    r"fodder|seed|insurance coverage|stipend|scholarship", re.I)


def excluded_by_rule(name):
    """True when the money buys delivery capacity rather than a benefit."""
    n = name or ""
    return bool(CAPACITY.search(n)) and not BENEFIT_DESPITE.search(n)


def myscheme_records(state):
    """myScheme's own state-level records for one state, from the archived snapshot. Names
    are stripped: myScheme stores some with stray spaces ("Arivu Education Loan Scheme ")."""
    out = set()
    for f in glob.glob(os.path.join(ROOT, "data", "myscheme", "schemes", "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if state not in ((d.get("_list") or {}).get("beneficiaryState") or []):
            continue
        n = ((d.get("en") or {}).get("basicDetails") or {}).get("schemeName")
        if n and n.strip():
            out.add(n.strip())
    return sorted(out)


def myscheme_index(listed):
    """Token, skeleton and acronym indexes over the myScheme names.

    An EXACT superset of the pairs probably_same can accept, not a speed-for-accuracy
    trade: every branch in probably_same that can return True needs the pair to share a
    content token, share a transliteration skeleton, or stand in an acronym relation.

      similarity >= 0.75      similarity is min(ratio, (overlap + ratio) / 2) and ratio
                              cannot exceed 1, so an overlap of zero caps it at 0.5.
      content word containment  the smaller token set is non-empty and inside the larger.
      one name begins with the other  the shorter name's content words are all in the longer.
      transliteration variant   the smaller skeleton set is inside the larger.
      acronym match             an acronym of one is a token or an acronym of the other.
      acronym containment       one acronym is a substring of the other.

    The one branch this does not index exactly is the prefix rule for a name made entirely
    of stop words, which cannot occur in a scheme name.

    It replaced a joiner that ranked records by how many index keys they shared, kept the
    top 40 and required two shared keys. That changed the answer, not only the speed:
    "Shakthi Scheme" shares one skeleton with "Shakti Scheme" and never reached
    probably_same, which accepts the pair.
    """
    tok, skel, acro = {}, {}, {}
    for n in listed:
        for k in set(tokens(n)):
            tok.setdefault(k, set()).add(n)
        for k in set(skeletons(n)):
            skel.setdefault(k, set()).add(n)
        for k in set(acronyms(n)):
            acro.setdefault(k, set()).add(n)
    return {"tok": tok, "skel": skel, "acro": acro, "acronyms": sorted(acro)}


def myscheme_candidates(name, idx):
    """Every myScheme name that could possibly match this one, sorted."""
    out = set()
    for k in set(tokens(name)):
        out |= idx["tok"].get(k, set())
        out |= idx["acro"].get(k, set())
    for k in set(skeletons(name)):
        out |= idx["skel"].get(k, set())
    for k in set(acronyms(name)):
        out |= idx["tok"].get(k, set())
        for other in idx["acronyms"]:
            if k in other or other in k:
                out |= idx["acro"][other]
    return sorted(out)


def myscheme_hits(name, idx):
    """Every myScheme name probably_same accepts for this one, sorted."""
    # [0] because probably_same returns (bool, why) and a tuple is always truthy.
    return [n for n in myscheme_candidates(name, idx) if probably_same(name, n)[0]]


def joiner(names):
    """A name -> its matching myScheme record, or None. The same pairs as calling
    probably_same against every record; where several match, the most similar, then the
    first by name, so the answer does not depend on set order."""
    idx = myscheme_index(names)

    def hit(name):
        hits = myscheme_hits(name, idx)
        return min(hits, key=lambda n: (-similarity(name, n), n)) if hits else None
    return hit


def provenance(v):
    """Which set a hand label was drawn from: "audit", "corpus", "stratified", or None when
    unrecorded. The seven oldest states record it per row as `sample`, the others as `how`.

    One copy for every classifier and parse/ratios.py. There were five, and three of them
    asked `!= "audit"`, so a label with a missing or misspelt provenance counted as
    stratified: the recall bug classify() documents, waiting to happen again."""
    h = str(v.get("how") or v.get("sample") or "")
    if h.startswith(("audit census", "audit")):
        return "audit"
    if h.startswith("whole corpus"):
        return "corpus"
    if h.startswith("stratified"):
        return "stratified"
    return None


def sampled_keys(labels):
    """The keys of the labels drawn from the probability sample (stratified or the whole
    corpus), never the audit census; a label with no provenance is refused, not guessed."""
    out = set()
    for c, v in labels.items():
        p = provenance(v)
        if p is None:
            raise SystemExit(
                f"label {c!r} records no provenance ('how' or 'sample'). The sweep cannot "
                f"tell a sampled row from an audited one, so no recall can be published "
                f"until it does.")
        if p != "audit":
            out.add(c)
    return out


def words(s):
    """A name's lowercase alphanumeric words, as a set."""
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def f1(precision, recall):
    """The harmonic mean of precision and recall, to three places; 0 where both are 0."""
    return round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0


def f1_optimal(sweep):
    """Every threshold in a published sweep whose F1 is the maximum, lowest first.

    A list because ties are real: PLAN.md §4 says the listing bar IS the F1 optimum, and on
    a coarse integer score two thresholds often reach the same F1. parse/ratios.py accepts
    any of them, and a reader can see that the choice between them was a choice."""
    best = max((x["f1"] for x in sweep), default=None)
    return [x["threshold"] for x in sweep if x["f1"] == best]


def label_sweep(rows, lo, hi):
    """Precision and recall over hand-labelled rows at every threshold, so the operating
    point is visible. One copy: it was written out identically in seven classifiers."""
    out = []
    for t in range(lo, hi + 1):
        tp = sum(1 for x in rows if x["score"] >= t and x["label"] == "scheme")
        fp = sum(1 for x in rows if x["score"] >= t and x["label"] != "scheme")
        fn = sum(1 for x in rows if x["score"] < t and x["label"] == "scheme")
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        out.append({"threshold": t, "called_scheme": tp + fp,
                    "true_positive": tp, "false_positive": fp, "false_negative": fn,
                    "precision": round(pr, 3), "recall": round(rc, 3), "f1": f1(pr, rc)})
    return out


# ---------------------------------------------------------------------------------------
# THE CENSUS-AND-SAMPLE MECHANICS of the seven oldest classifiers (Andhra Pradesh,
# Karnataka, Kerala, Maharashtra, Tamil Nadu, Odisha, West Bengal). Each of them scored its
# rows, split its stratified labels into a development and a held-out half, swept a
# threshold over each, counted an audit census band by band and drew its sample the same
# way, in about 250 lines written out seven times. What differs between them -- the
# signals, the labelling rules, the strata, the de-duplication of a scheme voted under
# several codes and the prose of the output -- stays in each state's own file.
# ---------------------------------------------------------------------------------------

def quartile_cuts(values):
    """The 25th, 50th and 75th percentile cut points of a list of allocations."""
    v = sorted(values)
    return [v[int(len(v) * f)] for f in (0.25, 0.5, 0.75)] if v else [0, 0, 0]


def quartile(v, cuts):
    """Which allocation quartile v falls in, given quartile_cuts."""
    return "q1" if v < cuts[0] else "q2" if v < cuts[1] else "q3" if v < cuts[2] else "q4"


def stratified_sample(entries, cell, key, target, floor):
    """Deterministic stratified sample: `cell(row)` names the stratum, a tuple of two.

    No random seed anywhere. Rows inside a stratum are sorted by `key` and picked at even
    spacing, so this returns the same rows on every machine and every run. parse/registry.py
    once returned a different answer each run because it iterated a set, and that
    manufactured false change events; nothing here iterates an unsorted anything.

    Proportional allocation with a `floor`, so the sample is close to self weighting and
    every stratum still gets enough rows to say anything about. Returns (row, stratum,
    stratum size, rows drawn from it), sorted by key.
    """
    cells = {}
    for r in entries:
        cells.setdefault(cell(r), []).append(r)
    out = []
    for k in sorted(cells):
        rows = sorted(cells[k], key=key)
        n = min(len(rows), max(floor, round(len(rows) * target / len(entries))))
        idx = sorted({round(i * (len(rows) - 1) / (n - 1)) if n > 1 else 0
                      for i in range(n)})
        for i in idx:
            out.append((rows[i], "%s/%s" % k, len(rows), len(idx)))
    return sorted(out, key=lambda t: key(t[0]))


def held_out(scored):
    """The development half (even-indexed) and the held-out half (odd-indexed).

    Labels were made before any weight was chosen, and the weights were then fitted looking
    only at the even-indexed half, so the odd-indexed half is the honest estimate. Reporting
    only the full-set number would flatter the classifier."""
    return scored[0::2], scored[1::2]


def sample_sweeps(scored, threshold, floor=-8):
    """The full and held-out sweeps over the stratified labels, and their rows at the bar.

    The sweep starts at the lowest labelled score but never below `floor`: below it every
    row is called a scheme and each further threshold repeats the one before. Odisha,
    Kerala and Maharashtra had no floor and published about a hundred such rows."""
    dev, held = held_out(scored)
    lo = max(min(x["score"] for x in scored), floor)
    hi = max(x["score"] for x in scored)
    full, held_sweep = label_sweep(scored, lo, hi), label_sweep(held, lo, hi)
    return {"dev": dev, "held": held, "hi": hi, "full": full, "held_sweep": held_sweep,
            "at": next(x for x in full if x["threshold"] == threshold),
            "at_held": next(x for x in held_sweep if x["threshold"] == threshold)}


def census_sweep(rows, audited, start, stop, corpus=True, bands=True,
                 error=lambda x: x["name"]):
    """Counted precision at every threshold from `start` to `stop` over the audit census.

    Every row scoring `start` or more carries a hand label, from one set or the other, so at
    those thresholds these are counts and not estimates. `bands` adds the band at exactly
    each score, which is where a bar is argued for; `corpus` adds the rows the corpus holds
    there, labelled or not."""
    out = []
    for t in range(start, stop + 1):
        pub = [x for x in audited if x["score"] >= t]
        bad = [x for x in pub if x["hand_label"] != "scheme"]
        c = {"threshold": t}
        if corpus:
            c["rows_in_corpus"] = sum(1 for x in rows if x["score"] >= t)
            c["rows_hand_labelled"] = len(pub)
        c.update({"published": len(pub), "not_schemes": len(bad),
                  "precision": round((len(pub) - len(bad)) / len(pub), 3) if pub else 0.0})
        if bands:
            band = [x for x in pub if x["score"] == t]
            band_bad = [x for x in band if x["hand_label"] != "scheme"]
            c.update({"band_at_exactly_this_score": len(band),
                      "band_not_schemes": len(band_bad),
                      "band_precision": round((len(band) - len(band_bad)) / len(band), 3)
                      if band else 0.0})
        c["the_errors"] = sorted(error(x) for x in bad)
        out.append(c)
    return out


def load(key, name):
    with open(os.path.join(ROOT, "data", key, name), encoding="utf-8") as fh:
        return json.load(fh)


def assess(key, state, ident, score, fields, threshold, census_from, label_key="key",
           floor=-8, census_to_sample=False, census_corpus=True, census_bands=True,
           error=None, myscheme=None):
    """Score, join, validate and census one of the seven oldest states. Writes nothing.

    The state supplies its SIGNALS and its shape: `score(row)` -> (points, evidence),
    `fields(row)` -> the leading fields of its published row, `ident(row)` -> the key its
    labels are written against (`label_key` in labels.json). `myscheme(listed)` returns a
    function (row, hits) -> the myScheme fields of a row, for a state that corrects the
    matcher by hand. Returns everything its run() needs to assemble its own output.
    """
    data, labels = load(key, "schemes.json"), load(key, "labels.json")
    by_key = {x[label_key]: x for x in labels["labels"]}
    sampled = sampled_keys(by_key)
    listed = myscheme_records(state)
    idx = myscheme_index(listed)
    flag = f"in_myscheme_{key}"
    join = myscheme(listed) if myscheme else (
        lambda r, hits: {flag: bool(hits), "myscheme_match": sorted(hits) or None})

    keyed = []
    for r in sorted(data["entries"], key=ident):
        total, ev = score(r)
        k = ident(r)
        keyed.append((k, {**fields(r), "score": total, "evidence": ev,
                          "verdict": "scheme" if total >= threshold else "not a scheme",
                          **join(r, myscheme_hits(r["name"], idx)),
                          "hand_label": by_key[k]["label"] if k in by_key else None}))
    rows = [x for _, x in keyed]

    # Validation on the probability sample. The audit set is a census of the published
    # region, so mixing it in would inflate precision at exactly the thresholds that
    # matter; it gets its own count below.
    scored = sorted(({"key": k, "name": x["name"], "score": x["score"],
                      "label": by_key[k]["label"]}
                     for k, x in keyed if k in by_key and k in sampled),
                    key=lambda x: x["key"])
    v = sample_sweeps(scored, threshold, floor)

    audited = [x for k, x in keyed if k in by_key]
    stop = v["hi"] if census_to_sample else max(x["score"] for x in rows)
    census = census_sweep(rows, audited, census_from, stop, census_corpus, census_bands,
                          error or (lambda x: x["name"]))

    schemes = [x for x in rows if x["verdict"] == "scheme"]
    order = {id(x): k for k, x in keyed}
    best = f1_optimal(v["full"])
    return {
        "data": data, "labels": labels, "listed": listed, "rows": rows, "scored": scored,
        "dev": v["dev"], "held": v["held"],
        "threshold_sweep": v["full"], "threshold_sweep_held_out": v["held_sweep"],
        "threshold_sweep_census": census,
        "at_census": next(x for x in census if x["threshold"] == threshold),
        "schemes": schemes,
        "absent_all": [x for x in rows if not x[flag]],
        "absent": sorted((x for x in schemes if not x[flag]),
                         key=lambda x: (-(x["be_lakh"] or 0), order[id(x)])),
        "counts": {"n_labelled": len(scored), "n_development": len(v["dev"]),
                   "n_held_out": len(v["held"])},
        "points": {
            "at_publish_threshold": {
                "threshold": threshold, "precision": v["at"]["precision"],
                "recall": v["at"]["recall"], "true_positive": v["at"]["true_positive"],
                "false_positive": v["at"]["false_positive"],
                "false_negative": v["at"]["false_negative"]},
            "at_publish_threshold_held_out": {
                "threshold": threshold, "precision": v["at_held"]["precision"],
                "recall": v["at_held"]["recall"],
                "true_positive": v["at_held"]["true_positive"],
                "false_positive": v["at_held"]["false_positive"]},
        },
        "f1": {"f1_optimal_threshold": best[0], "f1_optimal_thresholds": best},
    }


def base_rate(rows):
    """The share of hand-labelled rows labelled a scheme, to three places."""
    return round(sum(1 for x in rows if x["label"] == "scheme") / len(rows), 3)


def check_sample(key, ident, stratify, score, census_from, label_key="key"):
    """Report which sampled rows, and which census rows, have no hand label yet, so the
    label set can be extended. Nothing at or above census_from may be unlabelled."""
    entries = sorted(load(key, "schemes.json")["entries"], key=ident)
    have = {x[label_key] for x in load(key, "labels.json")["labels"]}
    frame = stratify(entries)
    missing = [(ident(r), st, r["name"]) for r, st, _, _ in frame if ident(r) not in have]
    print(f"sampling frame {len(frame)} rows, labelled {len(have)}, "
          f"unlabelled {len(missing)}")
    for k, st, name in missing:
        print(f"  [{st}]  {str(k)[:100]}  {name[:80]}")
    uncovered = [ident(r) for r in entries
                 if score(r)[0] >= census_from and ident(r) not in have]
    print(f"census at score >= {census_from}: {len(uncovered)} rows unlabelled")
    for k in uncovered:
        print(f"  {str(k)[:100]}")
    return missing, uncovered


def unique_idents(ids):
    """The identifiers, in order, with a collision broken by position: the first occurrence
    keeps its identifier, so every label written against it still lands, and each later one
    takes the next free `@n`. Deterministic for a fixed row order."""
    taken, seen, out = set(ids), set(), []
    for k in ids:
        if k in seen:
            n = 2
            while f"{k}@{n}" in taken:
                n += 1
            k = f"{k}@{n}"
            taken.add(k)
        seen.add(k)
        out.append(k)
    return out


def classify(key, state, score, publish, listing, rejected, row_fields=None,
             ident=None, omit=(), what=None):
    """Score one state's rows, validate against its labels, and write its verdicts.

    `score(row)` returns (points, evidence) and is the only state-specific thing here.
    `row_fields(row)` adds whatever that state publishes and others do not, because the
    scheme pages render what a state prints rather than a common subset of it, and `omit`
    drops a common field a state does not print at all (Haryana has no head of account).
    `what` replaces the sentence saying what the census precision is.
    """
    d = json.load(open(os.path.join(ROOT, "data", key, "schemes.json"), encoding="utf-8"))
    lj = json.load(open(os.path.join(ROOT, "data", key, "labels.json"), encoding="utf-8"))
    labels = {c: v["label"] for c, v in lj["labels"].items()}

    # WHICH LABELS THE SWEEP IS ALLOWED TO SEE, and it is not all of them.
    #
    # Every state here labels TWO sets: a stratified probability sample of the whole book,
    # and an audit census of every row at or above the publishing bar. The census is what
    # makes precision a count. It must never touch recall, because it is selected on the
    # classifier's own output: every census row is above the bar, most are schemes, and
    # each one therefore adds a true positive to the numerator AND to the denominator.
    # Recall computed over both sets rises with the size of the census and not with the
    # quality of the classifier.
    #
    # It had exactly that effect. The eight states built on this file reported recall
    # 0.742 to 0.907 and the seven older ones, whose own classifiers restrict the sweep,
    # reported 0.120 to 0.410 -- read for months as the newer work being better. Ranking
    # the eight by census share reproduces their recall ranking almost exactly. Corrected
    # to the sample alone: Uttar Pradesh 0.901 -> 0.436, Uttarakhand 0.748 -> 0.340,
    # Telangana 0.907 -> 0.622. Tripura is the control -- whole corpus, no census, nothing
    # selected on the outcome -- and its 0.618 does not move at all.
    #
    # West Bengal's labels file had already written the rule down: the stratified set "is
    # the only set the threshold sweep uses, because precision and recall estimated on
    # anything else would not generalise to the rows the classifier has not seen."
    sampled = sampled_keys(lj["labels"])
    lab = {c: labels[c] == "scheme" for c in sampled}
    # Tripura labelled its whole book: no sample, no census, nothing to call stratified.
    whole = all(provenance(v) == "corpus" for v in lj["labels"].values())
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
    # AN IDENTIFIER TWO ROWS SHARE IS BROKEN BY POSITION, because a label is looked up by
    # identifier and would otherwise land on both. Uttar Pradesh prints eight pairs of rows
    # identical in every field, so nothing in the row can tell them apart; the first in the
    # book keeps the identifier its label was written against and the second is suffixed.
    entries = d["entries"]
    base = [ident(r) for r in entries]
    keys = unique_idents(base)

    out = []
    for i in sorted(range(len(entries)), key=lambda i: str(base[i])):
        r, k = entries[i], keys[i]
        s, ev = score(r)
        # Applied after the state's own scoring and before any threshold, because it is the
        # definition rather than evidence: a row that buys delivery capacity is not a
        # scheme however strongly that state's signals read it.
        if excluded_by_rule(r["name"]):
            s = -99
            ev = [("rule", "buys the capacity of the delivery system, not the benefit")]
        m = hit(r["name"])
        row = {
            "key": k, "code": r.get("code"), "name": r["name"],
            "be_lakh": r.get("be_lakh"), "hoas": r.get("hoas") or [],
            "score": s, "evidence": ev,
            "verdict": "scheme" if s >= publish else "not_scheme",
            "hand_label": labels.get(k),
            flag: bool(m), "myscheme_name": m,
        }
        if row_fields:
            row.update(row_fields(r))
        for f in omit:
            del row[f]
        out.append(row)

    def sweep(t):
        # Stratified rows only, on both sides of the fraction. See the note above.
        h = [o for o in out
             if o["score"] >= t and o["hand_label"] and o["key"] in sampled]
        if not h:
            return None
        tp = sum(1 for o in h if o["hand_label"] == "scheme")
        pr, rc = tp / len(h), tp / max(1, sum(lab.values()))
        x = {"threshold": t, "n_labelled": len(h), "precision": round(pr, 3),
             "recall": round(rc, 3), "f1": f1(pr, rc)}
        if not whole:
            x["measured_on"] = "the stratified sample only"
        return x

    # The sweep runs up to the highest labelled score or the bar, whichever is higher, not
    # a fixed 8 that a bar above 8 fell outside of. A bar with no labelled row has no
    # recall; that is refused rather than published as {}, which parse/ratios.py read as
    # nothing to check.
    scores = [o["score"] for o in out if o["key"] in sampled and o["hand_label"]]
    lo, hi = -2, max(max(scores, default=publish), publish)
    at_bar = sweep(publish)
    if at_bar is None:
        raise SystemExit(f"{key}: no stratified labelled row at the publishing bar {publish}, "
                         "so no recall can be published there")

    census = [o for o in out if o["score"] >= publish]
    unlabelled = [o for o in census if o["hand_label"] is None]
    right = sum(1 for o in census if o["hand_label"] == "scheme")
    errors = [o["name"] for o in census if o["hand_label"] == "not_scheme"]
    absent = [o for o in census if not o[flag]]

    ground = {"labelled": len(labels),
              "scheme": sum(1 for v in labels.values() if v == "scheme"),
              "not_scheme": sum(1 for v in labels.values() if v == "not_scheme")}
    if not whole:
        ground.update({
            "stratified": len(sampled),
            "stratified_scheme": sum(1 for v in lab.values() if v),
            "audit_census": len(labels) - len(sampled),
            "recall_measured_on": (
                "The stratified sample alone. The audit census is selected on the "
                "classifier's own output -- every row in it is above the bar -- so counting "
                "it would raise recall with the size of the audit rather than with the "
                "quality of the classifier.")})
    ground.update({"question": lj.get("question"), "sampling": lj.get("sampling")})
    swept = [x for x in (sweep(t) for t in range(lo, hi + 1)) if x]
    best = f1_optimal(swept)

    write_json(f"data/{key}/classification.json", {
        "built": utcnow(), "snapshot": d.get("snapshot"), "state": state,
        "cycle": d.get("cycle"), "source": d.get("source"),
        "publish_threshold": publish, "listing_threshold": listing,
        f"myscheme_{key}_records": len(ms),
        "classified_scheme": len(census),
        "classified_not_scheme": len(out) - len(census),
        "ground_truth": ground,
        "threshold_sweep": swept,
        "validation": {
            "at_publish_threshold_census": {
                "rows": len(census),
                "rows_hand_labelled": len(census) - len(unlabelled),
                "unlabelled": len(unlabelled),
                "schemes": right, "not_schemes": len(errors),
                "precision": round(right / len(census), 3) if census else None,
                "what": what or ("Every row at or above the publishing bar carries a hand "
                                 "label, so this precision is a COUNT and the errors below "
                                 "are named ones."),
            },
            "at_publish_threshold": at_bar,
            "f1_optimal_threshold": best[0],
            "f1_optimal_thresholds": best,
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
    if census:
        print(f"  counted precision {right/len(census):.3f} on {len(census)-len(unlabelled)} "
              f"hand-labelled rows, {len(errors)} named errors")
    for e in errors[:6]:
        print(f"     not a scheme: {e[:68]}")
    print(f"  myScheme lists {len(ms)}; "
          f"{sum(1 for o in census if not o.get('myscheme_name'))} of these reach it nowhere")


def selftest_mechanics():
    """The shared mechanics of the census-and-sample classifiers, on rows small enough to
    check by hand."""
    out = []
    lab = [("a", 5, "scheme"), ("b", 4, "not_scheme"), ("c", 3, "scheme"), ("d", -20, "not_scheme"),
           ("e", 0, "scheme")]
    scored = [{"key": k, "name": k, "score": s, "label": lab_} for k, s, lab_ in lab]
    dev, held = held_out(scored)
    out.append(("the held-out half is the odd-indexed rows",
                ([x["key"] for x in dev], [x["key"] for x in held]), (["a", "c", "e"], ["b", "d"])))
    v = sample_sweeps(scored, 4)
    out.append(("the sweep is clamped at -8, not run down to a -20 outlier",
                v["full"][0]["threshold"], -8))
    out.append(("the sweep stops at the highest labelled score", v["full"][-1]["threshold"], 5))
    out.append(("the point at the bar is the sweep's row there",
                (v["at"]["true_positive"], v["at"]["false_positive"], v["at"]["false_negative"]),
                (1, 1, 2)))
    out.append(("the held-out sweep reads the held-out half only",
                v["at_held"]["called_scheme"], 1))
    out.append(("a floor below the lowest score leaves the sweep where the scores start",
                sample_sweeps(scored, 4, floor=-30)["full"][0]["threshold"], -20))
    out.append(("F1 optimum: every threshold tied at the maximum, lowest first",
                f1_optimal([{"threshold": 0, "f1": 0.5}, {"threshold": 1, "f1": 0.7},
                            {"threshold": 2, "f1": 0.7}, {"threshold": 3, "f1": 0.2}]),
                [1, 2]))
    out.append(("F1 of precision 0.5 and recall 1.0", f1(0.5, 1.0), 0.667))
    out.append(("F1 is 0 where precision and recall are both 0", f1(0.0, 0.0), 0.0))
    out.append(("quartile cuts", quartile_cuts([8, 1, 2, 3, 4, 5, 6, 7]), [3, 5, 7]))
    out.append(("quartile band", [quartile(v, [3, 5, 7]) for v in (1, 3, 6, 9)],
                ["q1", "q2", "q3", "q4"]))
    rows = [{"k": "%02d" % i, "cell": "x" if i < 10 else "y"} for i in range(12)]
    frame = stratified_sample(rows, lambda r: (r["cell"], "q1"), lambda r: r["k"], 6, 2)
    out.append(("stratified sample: proportional, floored, evenly spaced, sorted",
                [(r["k"], st, n, m) for r, st, n, m in frame],
                [("00", "x/q1", 10, 5), ("02", "x/q1", 10, 5), ("04", "x/q1", 10, 5),
                 ("07", "x/q1", 10, 5), ("09", "x/q1", 10, 5),
                 ("10", "y/q1", 2, 2), ("11", "y/q1", 2, 2)]))
    rows = [{"name": "A", "score": 6, "hand_label": "scheme"},
            {"name": "B", "score": 5, "hand_label": "not_scheme"},
            {"name": "C", "score": 5, "hand_label": "scheme"},
            {"name": "D", "score": 4, "hand_label": None}]
    c = census_sweep(rows, rows[:3], 5, 6, corpus=True, bands=True)
    out.append(("census at 5 counts the audited rows and names the errors",
                (c[0]["published"], c[0]["not_schemes"], c[0]["precision"],
                 c[0]["band_at_exactly_this_score"], c[0]["band_precision"], c[0]["the_errors"]),
                (3, 1, 0.667, 2, 0.5, ["B"])))
    out.append(("a census without the corpus or band columns publishes neither",
                sorted(census_sweep(rows, rows[:3], 5, 5, corpus=False, bands=False)[0]),
                ["not_schemes", "precision", "published", "the_errors", "threshold"]))
    out.append(("an identifier shared by two rows: the first keeps it, the second is suffixed",
                unique_idents(["a", "b", "a", "a@2", "a"]), ["a", "b", "a@3", "a@2", "a@4"]))
    out.append(("unique identifiers are left alone", unique_idents(["x", "y"]), ["x", "y"]))
    return out


def selftest():
    bad = 0
    for label, got, want in selftest_mechanics():
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": want {want!r} got {got!r}"))
    ms = ["Shakti Scheme", "Pre-Matric Scholarship to Scheduled Caste Students",
          "Jal Jeevan Mission", "Mukhya Mantri Kanya Utthan Yojana", "Old Age Pension"]
    hit = joiner(ms)
    rows = ["Shakthi Scheme", "Pre-Matric Scholarship Scheme", "Jal Jeevan Mission (JJM)",
            "Kanya Utthan Yojana", "Buildings- Animal Husbandry", "Old Age Pension Scheme"]
    for label, got, want in [
            ("a transliteration variant joins (Shakthi / Shakti)",
             hit("Shakthi Scheme"), "Shakti Scheme"),
            ("a generic name does not join a qualified sibling",
             hit("Pre-Matric Scholarship Scheme"), None),
            ("an unrelated head joins nothing", hit("Buildings- Animal Husbandry"), None),
            ("the joiner agrees with probably_same over every record",
             [hit(r) for r in rows],
             [next((n for n in ms if probably_same(r, n)[0]), None) for r in rows])]:
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": want {want!r} got {got!r}"))
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        print("classify_common self-test")
        sys.exit(1 if selftest() else 0)
    sys.exit("usage: python3 parse/classify_common.py --self-test")
