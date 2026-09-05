"""
Classify Jharkhand's Detailed Demands scheme codes: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Jharkhand's own.

    data/jharkhand/labels.json          hand ground truth, the input
    data/jharkhand/classification.json  the verdicts, the output

374 hand labels: a 249-row stratified sample on the statement each line appears under
(State Schemes, Central Assistance, Central Sector), then every row at the publishing bar
labelled so precision is a COUNT. 142 of 852 lines clear it, precision 0.958 with six
named errors, recall 0.732.

RECALL WAS PUBLISHED TOO HIGH UNTIL NOW, and by a lot. The sweep was counting the
audit census, which is selected on this classifier's own output -- every row in it is
at or above the bar -- so it added true positives to the numerator and the denominator
together and rose with the size of the audit rather than with the quality of the
scoring. classify_common sweeps the stratified sample alone now. The old figure was
0.886.

WHAT MAKES JHARKHAND DIFFERENT. Its book is the noisiest of the eight states classified
here: 852 scheme codes in which ROADS, BRIDGES, DIRECTION - ADMINISTRATION, SEMINAR
EXHIBITION ETC. and OTHERS sit at the same level as Abua Aawas Yojana. So the negative
vocabulary does most of the work, and several parts of it measure EXACTLY zero over 374
labels:

    construction, renovation, building         P(scheme) 0.000  over 25 rows
    strengthening, modernisation               P(scheme) 0.000  over 19
    training, seminar, capacity building       P(scheme) 0.000  over 17
    road, bridge, airport, rail, irrigation    P(scheme) 0.000  over  8

FIVE MORE NEGATIVES THE CENSUS FOUND, and the order matters. The stratified sample put
precision at 1.000 and the census brought it to 0.817: 33 errors, none of them random.
They were places being developed (Rurban, Atal Gramothan, Agri Smart Village), electricity
being supplied (IPDS, DDUGJY, Atal Grameen Jyoti), buildings people live in (Balika
Awasiya, Sakhi Niwas, Adarsh Vidyalaya), utilities and networks (rural pipe water supply,
fisheries marketing, riverside plantation), and the administration of a scheme rather than
the scheme (PMKSY - ADMINISTRATION, IM and kind grants). Each group was then measured over
all 374 labels and each came out at P(scheme) 0.000; together they are 46 rows and not one
of them is a scheme.

THE WORD "SCHEME" IS A SIGNAL HERE, which it would not be in a state whose book is a
budget. Jharkhand names 26 of the sampled rows "... SCHEME" and 22 of those are schemes,
P 0.846. It survives because the negatives are strong enough to overrule it: ARCHAEOLOGICAL
ACTIVITIES AND SCHEMES and LEGISLATURE SCHEME both carry it and both are caught elsewhere.
"""

import argparse
import re

from classify_common import classify, norm, report

BENEFIT = re.compile(
    r"\b(yojana|yojna|scholarship|stipend|pension|insurance|distribution|free|scheme|"
    r"schemes|subsidy|incentive|compensation|nutrition|mdm|poshan|mission|awas|aawas|"
    r"awaas|aajeevika|ajeevika|kalyanarth)\b", re.I)

# Building it, running it, studying it, or moving along it.
ASSET = re.compile(
    r"\b(construction|renovation|building|buildings|godown|strengthening|strenthening|"
    r"strengthing|modernisation|modernization|establishment|office|offices|directorate|"
    r"institute|institutes|university|college|colleges|share capital|loan|loans|"
    r"grants.in.aid|training|seminar|capacity building|research|survey|census|road|roads|"
    r"bridge|bridges|airport|airports|rail|irrigation|electrification|hostel|hostels|"
    r"computeri[sz]ation|consultancy|maintenance|purchase|land acquisition|infrastructure|"
    r"action plan|waste management|conservation|afforestation|tourism|publicity|exhibition|"
    r"outsourcing|gram sadak|gramsadak|jan vikas|multisectoral)\b", re.I)

# A programme whose beneficiary is a system.
SYSTEM = re.compile(
    r"\b(gram vikas|forestry|mme|police|extension and technology|jan vikas|"
    r"swachhata action|model panchayat|urban forestry)\b", re.I)

# The five groups the audit census turned up, all at P(scheme) 0.000: a place developed,
# electricity supplied, a building lived in, a network run, and a scheme administered.
PLACE = re.compile(
    r"\b(village|villages|rurban|gramothan|gram setu|gram jyoti|panchayat|basti|"
    r"power|jyoti|distribution sector|electric|transmission|"
    r"awasiya|vidyalaya|niwas|sadan|residential|"
    r"water supply|plantation|marketing|cultural|archaeolog|ambulance|weighing machine|"
    r"administration|im and kind|monitoring|evaluation|sponsored by|legislature|aside)\b",
    re.I)

PUBLISH_THRESHOLD = 3
LISTING_THRESHOLD = 1


def score(r):
    n = norm(r["name"])
    s, ev = 0, []
    if BENEFIT.search(n):
        s += 3
        ev.append(("+3", "a benefit word in the name"))
    if ASSET.search(n):
        s -= 4
        ev.append(("-4", "the line builds, runs or studies something"))
    if SYSTEM.search(n):
        s -= 4
        ev.append(("-4", "the beneficiary is a system rather than a person"))
    if PLACE.search(n):
        s -= 4
        ev.append(("-4", "a place, a network or the running of a scheme, not a benefit"))
    return s, ev


REJECTED = [
    {"signal": "the word hostel in the name",
     "measured": {"P_scheme": 0.200, "base_rate": 0.297, "n": 5},
     "why": ("Below the base rate but weakly, and every hostel row is already caught by "
             "construction or by residential. Left out rather than double-counted.")},
    {"signal": "the department that funds the line",
     "measured": {"P_scheme": None, "base_rate": 0.297, "n": 852},
     "why": ("Not usable. Jharkhand's departments are 20 to 40 lines each and every one "
             "of them funds both: the Scheduled Tribe department pays post-matric "
             "scholarships and buys hostel utensils under the same head.")},
    {"signal": "the statement the line appears under",
     "measured": {"P_scheme": None, "base_rate": 0.297, "n": 852},
     "why": ("Used to STRATIFY the sample and deliberately not scored. State Schemes, "
             "Central Assistance and Central Sector say who pays, and who pays says "
             "nothing about whether a citizen can apply.")},
]


def main():
    argparse.ArgumentParser(description="Classify Jharkhand's scheme codes.").parse_args()
    report("jharkhand", *classify("jharkhand", "Jharkhand", score, PUBLISH_THRESHOLD,
                                  LISTING_THRESHOLD, REJECTED,
                                  row_fields=lambda r: {
                                      "department": (r.get("departments") or [None])[0],
                                      "statements": r.get("statements") or [],
                                  }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
