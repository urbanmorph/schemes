"""
Classify Telangana's Pragathi Paddu lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Telangana's own.

    data/telangana/labels.json          hand ground truth, the input
    data/telangana/classification.json  the verdicts, the output

566 hand labels: a 287-row stratified sample on the plan group the book files each line
under, then every row at the publishing bar labelled so precision is a COUNT. 283 of 2,039
lines clear it, precision 0.989 with three named errors, recall 0.909. That is the largest
published set of any state here, and it is large because the Pragathi Paddu really is a
scheme volume: Telangana's own caveat says it files establishment heads at the same level,
and it files a great many schemes beside them.

WHAT THE VOLUME MAKES EASY. The negative vocabulary is unusually literal, because the book
puts its offices and its dams in the same list as its pensions and names them plainly:

    an office, building or establishment word   P(scheme) 0.000  over 30 rows
    police, court, security                     P(scheme) 0.000  over 10
    a college, board, commission or academy     P(scheme) 0.043  over 23
    an irrigation project by name               P(scheme) 0.054  over 37

That last one is a category of its own here and nowhere else. Telangana lists its
irrigation works individually and by local name -- Peddavagu near Jagganathpur, Ralivagu,
Ramappa Lake, Laknavaram, Nelwai -- so the file needs vagu, sagar and lake as words. Those
are place names, not vocabulary, and a state that did not itemise its dams would not need
them.

WHAT THE CENSUS COST AND BOUGHT. The stratified sample put precision at 1.000; labelling
every row at the bar brought it to 0.859, and the 46 errors were five recognisable shapes.
Lift irrigation schemes named "... LI Scheme". Shelters and hostels (Swadhar Greh, Babu
Jagjeevan Ram chhatrawas). Headings the parser could not tell from lines ("State Sector
Schemes", "Centrally Sponsored Schemes"). Stores and equipment (stationary stores, rescue
boats, barricading). And the health SYSTEM: National Health Mission is not a benefit, but
"National Health Mission (Incentives to ASHA Workers)" is, and the negative is written to
let that one through.

MISSION IS A POSITIVE HERE and it is worth saying why, because it is a negative in
Tripura's file. Telangana's missions are National Horticulture Mission, National Bamboo
Mission, National Mission on Natural Farming and the Skill Development Mission: farmers and
trainees get things. Tripura's abhiyans and missions run systems. The same word, measured
on two corpora, lands on opposite sides, which is the argument against a shared classifier
in one line.
"""

import argparse
import re

from classify_common import classify, norm, report

BENEFIT = re.compile(
    r"\b(scholarship|scholarships|stipend|stipends|pension|pensions|insurance|bima|"
    r"subsidy|incentive|welfare of|distribution of|supply of|free|yojana|yojna|scheme|"
    r"schemes|mission|bharosa|indlu|arogya|poshan|meals)\b", re.I)

# Offices, works, and the named dams.
ASSET = re.compile(
    r"\b(office|offices|head quarter|head quarters|headquarter|establishment|construction|"
    r"building|buildings|infrastructure|c/o|renovation|upgradation|up-gradation|"
    r"furnishing|furnishings|irrigation|project|lis|vagu|sagar|lake|canal|road|roads|"
    r"railway|metro|airstrip|police|court|courts|extremist|extremism|security|college|"
    r"university|academy|institute|commission|corporation|society|board|circle|museum|"
    r"training|survey|computeri[sz]ation|technology|digital|modernisation|modernization|"
    r"capacity building|finance commission|works|capital|equity|zoological|parks|"
    r"laborator)\b", re.I)

# Money to a local body, or a programme that runs a network.
SYSTEM = re.compile(
    r"\b(bhagiradha|ayush|marketing|gram sadak|li schemes|mi scheme|loans|loan|neeranchal|"
    r"amrut|smart city|swachh|nagarabhivrudhi|community polic|disaster response|"
    r"left wing)\b|assistance to\s+(the\s+)?(municipal|ghmc|zilla|gram|panchayat|"
    r"corporation|mandal|khammam|state)", re.I)

# The five shapes the audit census turned up, together P(scheme) 0.020 over 50 rows. The
# health clause is deliberately written to let one row through: National Health Mission is
# a system and "National Health Mission (Incentives to ASHA Workers)" pays a worker.
CENSUS_FOUND = re.compile(
    r"kakatiya|rurban|adarsh gram|abhyuday|\bajay\b|rental housing|"
    r"basic services for urban|rural water supply|"
    r"\bli\b|\bl\.i\b|lift irrigation|flood control|"
    r"swadhar|greh|chhatrawas|chatrawas|bharosa centres|"
    r"^(state sector|centrally sponsored) schemes$|^bharosa$|^shakti nirman|"
    r"^allied subsidy|^produces |"
    r"research schemes|stationary stores|barricading|rescue boats|discom|uday scheme|"
    r"biomass|educational istitutions|srcw|"
    r"national health mission(?!.*incentiv)|\bnhm\b|public health scheme|mortuary|"
    r"supply of medicines", re.I)

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
        ev.append(("-4", "an office, a work or a named project"))
    if SYSTEM.search(n):
        s -= 4
        ev.append(("-4", "money to a local body, or a network being run"))
    if CENSUS_FOUND.search(n):
        s -= 4
        ev.append(("-4", "a shelter, a heading, a store or a health system"))
    return s, ev


REJECTED = [
    {"signal": "the plan group the line is filed under",
     "measured": {"P_scheme": None, "base_rate": 0.261, "n": 2039},
     "why": ("Used to STRATIFY the sample and deliberately not scored. State Sector, "
             "Centrally Sponsored and Matching State Share say who pays, and 1,407 of "
             "2,039 lines are in one of them, so it separates almost nothing.")},
    {"signal": "the sector the book prints against the line",
     "measured": {"P_scheme": None, "base_rate": 0.261, "n": 1723},
     "why": ("Telangana's sector is where the money sits in its own plan, not what the "
             "money does: WEAKER SECTION HOUSING PROGRAMME is its largest at 397 lines "
             "and holds construction and cash transfers alike. It is published on the "
             "scheme page as the state's own filing and is not scored.")},
    {"signal": "the department that funds the line",
     "measured": {"P_scheme": None, "base_rate": 0.261, "n": 2039},
     "why": ("Not usable. Telangana names an executing officer rather than a department: "
             "'CE SRSP-I', 'Commissioner, Godavari Basin -Project Estt', 'DG & IG of "
             "Police'. Several hundred distinct values, most of them one line each.")},
]


def main():
    argparse.ArgumentParser(description="Classify Telangana's Pragathi Paddu lines.").parse_args()
    report("telangana", *classify("telangana", "Telangana", score, PUBLISH_THRESHOLD,
                                  LISTING_THRESHOLD, REJECTED,
                                  row_fields=lambda r: {
                                      "department": r.get("department"),
                                      "sector": r.get("sector"),
                                      "books": r.get("books") or [],
                                      "group": r.get("group"),
                                  }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
