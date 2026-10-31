"""
The conservative name matcher, for joins that publish a figure under a scheme's name.

SECONDARY LAYER (PLAN.md §7, agent-editable). Pure functions; reads nothing, never fetches.
Used by enrich/outcome.py to attach Outcome Budget targets to myScheme records.

It was the matcher of enrich/budget.py, which attached Budget allocations to myScheme
pages by its own join while the index, the CSV and the absence claims read
parse/registry.py's: two joins for one field, disagreeing on two schemes (PMAY-U's page
showed the 2.0 line's Rs 3,000 cr where the register held PMAY-Urban's Rs 18,625 cr). The
register is now the one source of every Budget figure, and this file keeps only the
matcher the Outcome join still needs.

It answers a different question from parse/match.py's generous probably_same. That one
decides absence claims, where a missed match is a false accusation; this one decides what
figure appears on a page, where a wrong match is a false figure.
"""
import difflib
import re

# Words that carry no distinguishing signal in Indian scheme names — almost every scheme
# is a "yojana" or a "mission", so matching on them manufactures similarity.
STOP = {"scheme", "yojana", "yojna", "programme", "program", "mission", "abhiyan",
        "the", "of", "for", "and", "a", "an", "in", "to"}

STRONG, LIKELY, WEAK = 0.85, 0.75, 0.55


def norm(s):
    s = re.sub(r"\(.*?\)", " ", (s or "").lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 2}


def similarity(a, b):
    """Lower of sequence ratio and a ratio/overlap blend — the conservative reading.

    Ratio alone rewards two long names sharing boilerplate; token overlap alone rewards
    one shared word. A wrong join here publishes a figure under the wrong scheme's name,
    so the bias is deliberately toward under-matching.
    """
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = tokens(a), tokens(b)
    overlap = len(ta & tb) / max(len(ta | tb), 1) if (ta and tb) else 0.0
    return min(ratio, (overlap + ratio) / 2)


def band(score):
    if score >= STRONG:
        return "strong"
    if score >= LIKELY:
        return "likely"
    if score >= WEAK:
        return "weak"
    return None
