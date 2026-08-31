"""
Scheme-name matching, with an asymmetry the rest of the code got wrong.

AGENT-EDITABLE (PLAN.md §7). Pure functions, no I/O.

There are two different questions, and one threshold cannot answer both:

  ATTACHING data — "does this budget line's money belong to this scheme?"
  A wrong yes publishes a rupee figure under the wrong scheme's name. Bias toward NO.

  CLAIMING absence — "is this scheme missing from myScheme?"
  A wrong yes accuses a portal of omitting something it actually lists. Bias toward YES,
  i.e. match generously, and only claim absence when even a generous matcher finds
  nothing.

enrich/budget.py's conservative similarity was correctly biased for the first question
and then reused for the second, which inflated every absence claim. Measured failures
that prompted this module:

    "Jal Jeevan Mission (JJM) / National Rural Drinking Water Mission"   0.41
        — myScheme lists "Jal Jeevan Mission"; the suffix crushed the ratio
    "MGNREGA-Programme Component"                                        0.33
        — myScheme lists "Mahatma Gandhi National Rural Employment Guarantee Act";
          no shared token at all, because one side is an acronym
    "Pradhan Mantri Awas Yojna (PMAY)- Rural"  ->  "...Awas Yojana - Urban"   0.76
        — a WRONG match that cleared the 0.75 floor. Rural and Urban are different
          schemes with different budget lines.

So `probably_same` adds containment and acronym matching to catch the first two, and a
qualifier conflict check to reject the third. Qualifiers are the words that distinguish
sibling schemes — rural/urban, boys/girls, SC/ST — and two names that disagree on one
are never the same scheme however similar the rest reads.
"""

import difflib
import re

STOP = {"scheme", "schemes", "yojana", "yojna", "programme", "program", "mission",
        "abhiyan", "the", "of", "for", "and", "a", "an", "in", "to", "component"}

# Words that distinguish sibling schemes sharing a parent name. If two names disagree on
# any of these pairs they are different schemes, no matter how similar the rest is.
QUALIFIERS = [
    {"rural", "gramin", "grameen"}, {"urban", "shahari"},
    {"boys"}, {"girls"},
    {"sc", "scheduled caste"}, {"st", "scheduled tribe"}, {"obc"}, {"minority"},
    {"pre matric", "prematric"}, {"post matric", "postmatric"},
    {"primary"}, {"secondary"}, {"higher"},
]


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return [t for t in norm(s).split() if t not in STOP and len(t) > 2]


def acronyms(s):
    """Acronyms this name could be written as, plus any it already contains.

    "Mahatma Gandhi National Rural Employment Guarantee Act" -> "mgnrega", and a
    bracketed "(PMAY)" is picked up directly.
    """
    out = set()
    words = [w for w in norm(s).split() if len(w) > 1]
    if len(words) >= 3:
        out.add("".join(w[0] for w in words))
        big = [w for w in words if w not in STOP]
        if len(big) >= 3:
            out.add("".join(w[0] for w in big))
    for m in re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{2,12})\)", s or ""):
        out.add(norm(m).replace(" ", ""))
    # Only genuine acronym forms. An earlier version added any word of four or more
    # letters, which made "Shiksha" an acronym and matched "Samagra Shiksha" to the
    # unrelated "Samaaveshit Shiksha". A word counts only if the source writes it in
    # caps — MGNREGA, PMAY, JJM — which is what an acronym actually looks like.
    for w in re.findall(r"\b([A-Z][A-Z0-9]{3,})\b", s or ""):
        out.add(w.lower())
    return {a for a in out if len(a) >= 4}


def qualifier_conflict(a, b):
    """True when the two names commit to different sides of a sibling distinction."""
    na, nb = " " + norm(a) + " ", " " + norm(b) + " "
    for group in QUALIFIERS:
        ina = any(f" {q} " in na for q in group)
        inb = any(f" {q} " in nb for q in group)
        if ina != inb:
            # One side names this qualifier and the other does not. Only a conflict if
            # the other side names a *competing* qualifier from the same axis.
            for other in QUALIFIERS:
                if other is group:
                    continue
                if not (set(other) & set(group)):
                    oa = any(f" {q} " in na for q in other)
                    ob = any(f" {q} " in nb for q in other)
                    if (ina and ob and not oa) or (inb and oa and not ob):
                        if _same_axis(group, other):
                            return True
    return False


_AXES = [
    [{"rural", "gramin", "grameen"}, {"urban", "shahari"}],
    [{"boys"}, {"girls"}],
    [{"pre matric", "prematric"}, {"post matric", "postmatric"}],
    [{"primary"}, {"secondary"}, {"higher"}],
    [{"sc", "scheduled caste"}, {"st", "scheduled tribe"}, {"obc"}, {"minority"}],
]


def _same_axis(g1, g2):
    for axis in _AXES:
        if any(g1 == g for g in axis) and any(g2 == g for g in axis):
            return True
    return False


def similarity(a, b):
    """Conservative score — the one to use when ATTACHING data to a scheme."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(tokens(a)), set(tokens(b))
    overlap = len(ta & tb) / max(len(ta | tb), 1) if (ta and tb) else 0.0
    return min(ratio, (overlap + ratio) / 2)


def probably_same(a, b, floor=0.75):
    """Generous match — the one to use when CLAIMING ABSENCE. Returns (bool, why)."""
    if qualifier_conflict(a, b):
        return False, "qualifier conflict"

    if similarity(a, b) >= floor:
        return True, f"similarity {similarity(a, b):.2f}"

    ta, tb = set(tokens(a)), set(tokens(b))
    if ta and tb:
        small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
        if len(small) >= 2 and small <= large:
            return True, f"all {len(small)} content words of the shorter name are present"

    aa, ab = acronyms(a), acronyms(b)
    shared = (aa & set(tokens(b))) | (ab & set(tokens(a))) | (aa & ab)
    shared = {s for s in shared if len(s) >= 5}
    if shared:
        return True, f"acronym match: {sorted(shared)[0]}"

    return False, "no match"


SELFTEST = [
    ("Jal Jeevan Mission (JJM) / National Rural Drinking Water Mission",
     "Jal Jeevan Mission", True),
    ("MGNREGA-Programme Component",
     "Mahatma Gandhi National Rural Employment Guarantee Act", True),
    ("Pradhan Mantri Awas Yojna (PMAY)- Rural",
     "Pradhan Mantri Awas Yojana - Urban", False),
    ("Samagra Shiksha", "Samaaveshit Shiksha", False),
    ("Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
     "Pradhan Mantri Kisan Samman Nidhi (PM – KISAN)", True),
    ("Crop Insurance Scheme", "Weather Based Crop Insurance Scheme", True),
    ("Urea Subsidy", "Pradhan Mantri Awas Yojana - Urban", False),
]


def selftest():
    bad = 0
    for a, b, want in SELFTEST:
        got, why = probably_same(a, b)
        ok = got == want
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} want={str(want):<5} got={str(got):<5} "
              f"({why})\n        {a[:58]}\n        {b[:58]}")
    return bad


if __name__ == "__main__":
    import sys
    print("probably_same self-test")
    sys.exit(1 if selftest() else 0)
