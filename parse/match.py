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


# Indic transliteration variance. The same scheme is spelled differently by the office
# that typed it: Karnataka's Gruha Lakshmi is myScheme's "Griha Lakshmi Scheme", and the
# state's own books write Shakthi where the portal writes Shakti. Comparing those as
# plain tokens scores 0.55 and reports the scheme as missing from a portal that lists it.
# That is the expensive direction of error here, because claiming absence is an
# accusation, so this folds only in probably_same and never where money is attached.
#
# Two steps, both reversible by eye: drop the h of an aspirated consonant (shakthi ->
# shakti, jyothi -> jyoti), then reduce the token to its consonant skeleton, which is what
# survives a vowel disagreement (gruha and griha are both grh).
_ASPIRATE = re.compile(r"(?<=[kgcjtdpbs])h")


def skeleton(t):
    return re.sub(r"[aeiou]", "", _ASPIRATE.sub("", t)) or t


def skeletons(s):
    return {skeleton(t) for t in tokens(s)}


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

    # Same content words once transliteration is folded out. Two or more skeletons must
    # line up, because a skeleton is lossy enough that one alone proves little: mata,
    # mati and moti all reduce to mt. The exception is a name whose only content word is
    # the scheme's name, "Shakthi Scheme" against "Shakti Scheme", where there is no
    # second word to corroborate with. There the raw tokens must also look alike, which
    # shakthi/shakti does at 0.92 and mata/moti does not at 0.50.
    ta_, tb_ = tokens(a), tokens(b)
    sa, sb = skeletons(a), skeletons(b)
    if sa and sb:
        small, large = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
        if small <= large:
            if len(small) >= 2:
                return True, f"transliteration variant: {sorted(small)[:3]}"
            if len(ta_) == 1 and len(tb_) == 1 and \
                    difflib.SequenceMatcher(None, ta_[0], tb_[0]).ratio() >= 0.8:
                return True, f"transliteration variant: {ta_[0]} / {tb_[0]}"

    aa, ab = acronyms(a), acronyms(b)
    shared = (aa & set(tokens(b))) | (ab & set(tokens(a))) | (aa & ab)
    shared = {x for x in shared if len(x) >= 5}
    if shared:
        return True, f"acronym match: {sorted(shared)[0]}"

    # One acronym contained in another. "DAY-NRLM" yields NRLM; the expansion
    # "Deendayal Antyodaya Yojana - National Rural Livelihoods Mission" yields DAYNRLM.
    # Neither is a token of the other and they are not equal, but one is plainly the
    # other's tail — which is how these schemes are actually written down.
    for x in aa:
        for y in ab:
            if len(x) >= 4 and len(y) >= 4 and (x in y or y in x):
                return True, f"acronym containment: {x} / {y}"

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
    ("DAY-NRLM",
     "Deendayal Antyodaya Yojana - National Rural Livelihoods Mission", True),
    ("NRLM", "National Handloom Development Programme", False),
]


SELFTEST += [
    # Transliteration. Karnataka's budget writes Gruha; myScheme writes Griha. Reporting
    # this pair as absent was the error that prompted the skeleton rule.
    ("Gruha Lakshmi", "Griha Lakshmi Scheme", True),
    ("Shakthi Scheme", "Shakti Scheme", True),
    ("Jyothi Sanjeevini", "Jyoti Sanjeevini", True),
    # ...and it must not fold two different schemes together just because one word
    # collapses the same way. Shakthi is free bus travel; Shrama Shakthi is a loan scheme.
    ("Shakthi Scheme", "Shrama Shakthi Scheme", False),
    ("Gruha Jyothi", "Griha Lakshmi Scheme", False),
    ("Anna Bhagya", "Ksheera Bhagya", False),
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
