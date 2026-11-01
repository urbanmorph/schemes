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
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify_common import classify, norm, report  # noqa: E402

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


REJECTED = [
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
]


def main():
    argparse.ArgumentParser(description="Classify Tripura's scheme lines.").parse_args()
    report("tripura",
           *classify("tripura", "Tripura", score, PUBLISH_THRESHOLD, REJECTED,
                     row_fields=lambda r: {"department": (r.get("departments") or [None])[0]},
                     what=("Every line in Tripura's book carries a label, so this is a "
                           "count over the whole population and not over a sample. There is "
                           "no estimate anywhere in this file.")),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
