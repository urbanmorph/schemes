"""
Classify Chhattisgarh's outcome budget lines: welfare scheme, or something else?

AGENT-EDITABLE (PLAN.md 7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Chhattisgarh's own.

    data/chhattisgarh/labels.json          hand ground truth, the input
    data/chhattisgarh/classification.json  the verdicts, the output

THIS STATE IS READ FROM THE WRONG BOOKS ON PURPOSE, and the state page says so. Its 44
department scheme books name 2,562 schemes and set every one in the Chanakya legacy font,
whose encoding cannot be recovered from the PDF. What is read instead is the Outcome,
Gender, Youth and Child budgets, which are in Kruti Dev and which parse/krutidev.py decodes
against a table checked on the state's own Unicode department index. Fewer schemes, and
more about each: a name, an objective, a provision and a deliverable.

WHAT THE SIGNALS MEASURED, over 197 stratified labels, base rate 0.284:

    scholarship                            P(scheme) 1.000  over  6 rows
    incentive or award                     P(scheme) 1.000  over  5
    supplied or distributed to somebody    P(scheme) 0.727  over 11
    the word yojana                        P(scheme) 0.550  over 60
    an institution                         P(scheme) 0.000  over 22
    builds something                       P(scheme) 0.000  over  9
    infrastructure, running, research      P(scheme) 0.000  over  9
    a project, reservoir or dam            P(scheme) 0.000  over  8
    establishes something                  P(scheme) 0.000  over  6
    strengthening or upgrading             P(scheme) 0.000  over  4

THE NEGATIVES DO THE WORK HERE, which is the opposite of what an outcome budget looks like
it should need. These books are supposed to be lists of schemes, and 22 of 197 sampled rows
name a university, a college, a dispensary, a laboratory or a centre. Chhattisgarh files
the institution that delivers a service at the same level as the benefit, exactly as
Telangana's Pragathi Paddu does, and the register's rule separates them.

214 hand labels: a 197-row stratified sample on the book crossed with allocation quartile,
then every row at the publishing bar labelled so precision is a COUNT. 29 of 574 lines
clear it, precision 0.966 with one named error, recall 0.268 on the stratified sample alone.

THE ONE ERROR STAYS AN ERROR. "shikshakon ko puraskar", a prize to the state's own
teachers, clears the bar on the award word and is not a scheme by the register's rule.
Uttar Pradesh measured teacher prizes at P(scheme) 0.000 over 61 labels and this file has
exactly one such row, which is not enough to score. Patching a weight to remove a single
row that the evidence in THIS state cannot support would be fitting the classifier to its
own audit, so it is in known_errors instead.
"""

import argparse
import re

from classify_common import classify, norm, report

BENEFIT = re.compile(r"छात्रवृत्ति|वजीफा|प्रोत्साहन|पुरस्कार")
GIVEN = re.compile(r"प्रदाय|वितरण|निःशुल्क|सब्सिडी|रिबेट|भत्ता")
YOJANA = re.compile(r"योजना")

# Builds it, establishes it, strengthens it, or runs it.
ASSET = re.compile(
    r"निर्माण|भवन|सड़क|मार्ग|पुल|पुलिया|जलाशय|बांध|बॉंध|परियोजना|"
    r"स्थापना|गठन|सुदृढ़ीकरण|उन्नयन|मरम्मत|अधोसंरचना|संचालन|प्रबंधन|अनुसंधान|"
    r"विस्तार|खनन|वृक्षारोपण|प्लांटेशन")

# A place a service is delivered from, which is not the service and is not the benefit.
INSTITUTION = re.compile(
    r"विश्वविद्यालय|महाविद्यालय|विद्यालय|संस्थान|संस्था|संस्थाएं|केन्द्र|केंद्र|"
    r"चिकित्सालय|औषधालय|अस्पताल|प्रयोगशाला|पुस्तकालय|संग्रहालय|अकादमी|"
    r"छात्रावास|आश्रम|निवास|सदन|परिसर|कालेज|कॉलेज|पॉलिटेक्निक")

# A body, a fund, a campaign or a day. Money that moves to an institution or an occasion.
BODY = re.compile(
    r"बोर्ड|आयोग|परिषद|प्राधिकरण|अथॉरिटी|सोसायटी|निधि|मंडल|संघ|समिति|"
    r"कार्यक्रम|अभियान|शिविर|दिवस|महोत्सव|समारोह|प्रदर्शनी|हेल्पलाइर्न|हेल्प लाइर्न")

# TWO GROUPS THE CENSUS FOUND, and the order matters. The stratified sample put precision
# at the bar at 0.848; reading every row there showed five errors and three of them were
# one of these two shapes. Each was then measured over all 214 labels and both come out at
# P(scheme) 0.000.
#
#   WATER IS SUPPLIED, NOT GIVEN. "pradaya" is the word Chhattisgarh uses for handing
#   somebody a uniform or a bicycle, and it is also the word it uses for piping water to a
#   town. The first is a benefit and the second is a utility, and only the object of the
#   verb tells them apart.
#
#   PROMOTION WITHOUT A PERSON. "protsahan" is an incentive paid to a player, a student or
#   a weaver, and it is also what the state calls promoting investment, innovation and
#   industry. The register's rule is a benefit received by a person or a household, and an
#   investment incentive reaches a firm.
WATER = re.compile(r"जल प्रदाय|जल निकास|पेयजल|जल आवर्धन|जल प्रदाय व्यवस्था")
NOT_A_PERSON = re.compile(r"निवेश प्रोत्साहन|नवाचार|औद्योगिक|उद्योग")

PUBLISH_THRESHOLD = 4
LISTING_THRESHOLD = 1


def score(r):
    n = norm(r.get("name") or "")
    s, ev = 0, []
    if BENEFIT.search(n):
        s += 4
        ev.append(("+4", "a scholarship, an incentive or an award, which measured 1.000"))
    if GIVEN.search(n):
        s += 3
        ev.append(("+3", "something supplied or distributed to somebody"))
    if YOJANA.search(n):
        s += 1
        ev.append(("+1", "the word yojana, which this book uses loosely"))
    if ASSET.search(n):
        s -= 5
        ev.append(("-5", "the line builds, establishes, strengthens or runs something"))
    if INSTITUTION.search(n):
        s -= 5
        ev.append(("-5", "the money names the place a service is delivered from"))
    if BODY.search(n):
        s -= 4
        ev.append(("-4", "a body, a fund, a campaign or an occasion"))
    if WATER.search(n):
        s -= 5
        ev.append(("-5", "water supplied to a place, not something given to a person"))
    if NOT_A_PERSON.search(n):
        s -= 5
        ev.append(("-5", "promotion aimed at investment or industry, not at a person"))
    return s, ev


REJECTED = [
    {"signal": "the words pension and insurance",
     "measured": {"P_scheme": 0.400, "base_rate": 0.284, "n": 5},
     "why": ("The strongest positive in almost every other state here and barely a signal "
             "in this one, because Chhattisgarh's insurance rows are mostly the EMPLOYEES' "
             "STATE INSURANCE hospital and its dispensaries. The word names the institution "
             "as often as the entitlement, so it is left out rather than scored on five "
             "rows.")},
    {"signal": "the word anudan, a grant",
     "measured": {"P_scheme": 0.143, "base_rate": 0.284, "n": 7},
     "why": ("A real negative and already caught: every row it would catch is a grant to a "
             "commission, a mill, a society or a spinning unit, and each of those carries a "
             "body or an institution word of its own. Left out rather than double-counted.")},
    {"signal": "the book the line appears in",
     "measured": {"P_scheme": None, "base_rate": 0.284, "n": 574},
     "why": ("Used to STRATIFY the sample and deliberately not scored. Which of the four "
             "books a line is filed under says who the state counts it for, not whether a "
             "citizen can apply to it: the Outcome book carries both the scholarship and "
             "the university that awards it.")},
]


def main():
    argparse.ArgumentParser(description="Classify Chhattisgarh's outcome budget lines.").parse_args()
    report("chhattisgarh",
           *classify("chhattisgarh", "Chhattisgarh", score, PUBLISH_THRESHOLD,
                     LISTING_THRESHOLD, REJECTED,
                     row_fields=lambda r: {
                         "department": r.get("department"),
                         "book": r.get("book"),
                         "objective": r.get("objective"),
                     }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
