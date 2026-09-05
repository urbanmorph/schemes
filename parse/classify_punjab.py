"""
Classify Punjab's Demand for Grants sub-heads: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Punjab's own.

    data/punjab/labels.json          hand ground truth, the input
    data/punjab/classification.json  the verdicts, the output

457 hand labels: a 302-row stratified sample on the level of the head of account, then
every row at the publishing bar labelled so precision is a COUNT. 144 of 2,961 lines clear
it, precision 0.972 with four named errors, recall 0.590.

RECALL WAS PUBLISHED TOO HIGH UNTIL NOW, and by a lot. The sweep was counting the
audit census, which is selected on this classifier's own output -- every row in it is
at or above the bar -- so it added true positives to the numerator and the denominator
together and rose with the size of the audit rather than with the quality of the
scoring. classify_common sweeps the stratified sample alone now. The old figure was
0.904.

BASE RATE 0.136. Punjab's demand books are the full detailed accounts, so the sample is
mostly the state running itself: Computer Stationery and Consumable Items, Manpower,
Direction and Administration, Development of Hosting the Website, AMC for IT related items,
Debit to Miscellaneous Advance. Four negative groups measure EXACTLY zero over 302 labels:

    computers, software, stationery, AMC        P(scheme) 0.000  over 38 rows
    direction, administration, secretariat      P(scheme) 0.000  over 16
    construction, lining, repair, purchase      P(scheme) 0.000  over 47
    canals, distributaries, watercourses        P(scheme) 0.000  over 31

That last group is Punjab's own shape. The books itemise canal work by name -- Lining and
allied works of Dhipali Disty System, Rehabilitation of Kakrala Minor, Cement Concrete
Lining of Sodhiwala Disty System -- so disty, minor and watercourse have to be words here.
"Minor" as a canal is also a minor head, which is why the word is only ever a negative and
never read as structure.

WHAT THE CENSUS FOUND, and it is the same lesson as everywhere else in this directory: the
stratified sample said 0.862 and labelling every row at the bar said 0.815, with 34 errors
in four recognisable shapes.

  * PENSIONS AND REIMBURSEMENTS FOR THE STATE'S OWN PEOPLE. Family Pension, Pension to
    Legislators, Commuted Value of Pensions, Reimbursement of Medical Charges to Punjab
    Government Pensioners, Reimbursement of Travel Expenses to Ex-M.L.As, and free travel
    for police "from the Rank of Constable to Inspector". Pension and reimbursement are two
    of the strongest positives in the file and these are staff terms.
  * AWARDS TO INSTITUTIONS. Award for Best Government Middle School in Each District is a
    prize for a school; Encouragement Award to SC Girl Students is a prize for a person.
  * A SCHEME NAME ON INFRASTRUCTURE. Maintenance of Roads under Pradhan Mantri Gram Sadak
    Yojana, Integrated Watershed Management under PMKSY, Pradhan Mantri Adarsh Gram Yojana
    in SC Villages.
  * BORROWING. UDAY Bonds and Off Budget Borrowing Reimbursement.

Grouped, they measure P(scheme) 0.000 over 30 rows.
"""

import argparse
import re

from classify_common import classify, norm, report

BENEFIT = re.compile(
    r"(scholarship|stipend|pension|insurance|subsidy|subsidies|incentiv|award|awards|"
    r"reimbursement|free text|free travel|helpline|help line|poshan|nutrition|livelihood|"
    r"aajeevika|awas|awaas|sashaktikaran|yojana|yojna|shaktikaran)", re.I)

ASSET = re.compile(
    r"(computer|software|stationery|consumable|manpower|man power|amc for|hosting|website|"
    r"computeri[sz]ation|direction and administration|administrative|administration|"
    r"secretariat|establishment|construction|renovation|upgradation|up-gradation|building|"
    r"buildings|repair|lining|remodelling|infrastructure|works expenditure|purchase|"
    r"assistance to|grant in aid|grant-in-aid|grants to|loans to|\bloan|margin money|"
    r"university|college|colleges|institute|board|corporation|society|commission|authority|"
    r"council|federation|canal|disty|minor|watercourse|water supply|distributary|nabard|"
    r"ridf|police|jail|jails|court|courts|vigilance|home guards|debit to|credit to|"
    r"interest on|market loans|bus stand|memorial|monument)", re.I)

# The four shapes the audit census turned up. Together P(scheme) 0.000 over 30 rows: a
# pension for the state's own people, a prize for an institution, a scheme's name attached
# to a road or a watershed, and the state's borrowing.
CENSUS_FOUND = re.compile(
    r"(government pensioners|ex m\.l\.a|ex-m\.l\.a|pension to legislators|family pension|"
    r"commuted value|defined contribution pension|pension to employees|"
    r"constable to inspector|user services|"
    r"best government|award of parman|"
    r"watershed|gram sadak|maintenance of roads|adarsh gram|garima gram|"
    r"digital agriculture|reform incentive|homoeopathic dispensaries|"
    r"uday bonds|off budget borrowing|election expenditure)", re.I)

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
        ev.append(("-4", "an object head, a work, a canal or an institution"))
    if CENSUS_FOUND.search(n):
        s -= 4
        ev.append(("-4", "a staff pension, a prize for an institution, or borrowing"))
    return s, ev


REJECTED = [
    {"signal": "the level of the head of account (sub-head or sub-sub-head)",
     "measured": {"P_scheme": None, "base_rate": 0.136, "n": 2961},
     "why": ("Used to STRATIFY the sample and deliberately not scored. Punjab's own "
             "caveat says the sub-head is the scheme and the object head is not, and the "
             "parser already applies that: everything in this file is at or above sub-head "
             "level, so the level separates nothing that is left.")},
    {"signal": "which book the line appears in",
     "measured": {"P_scheme": None, "base_rate": 0.136, "n": 2961},
     "why": ("The Gender Budget's 190 rows are the women's share of provisions the demand "
             "books state in full, so a line's presence there says it has a women's "
             "component and not that it is a scheme. Published on the scheme page as the "
             "state's own filing and not scored.")},
    {"signal": "police, jails and courts",
     "measured": {"P_scheme": 0.083, "base_rate": 0.136, "n": 12},
     "why": ("Below the base rate and folded into the asset group rather than kept "
             "separate; on its own it is one row of twelve away from the base rate and "
             "would not carry its own weight.")},
]


def main():
    argparse.ArgumentParser(description="Classify Punjab's demand-book sub-heads.").parse_args()
    report("punjab", *classify("punjab", "Punjab", score, PUBLISH_THRESHOLD,
                               LISTING_THRESHOLD, REJECTED,
                               row_fields=lambda r: {
                                   "demand": r.get("demand"),
                                   "minor_head_name": r.get("minor_head_name"),
                                   "books": r.get("books") or [],
                                   "level": r.get("level"),
                               }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
