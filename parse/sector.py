"""
Give a sector to the register rows myScheme does not list.

AGENT-EDITABLE (PLAN.md SS7). Reads data/ and archive/. Never fetches.

    data/sector_labels.json   hand ground truth and the hand audits, the input
    data/sector.json          one sector plus its evidence per scheme key, the output

WHY THIS FILE EXISTS. Sector is the register's primary filter and a third of the register
could not use it. myScheme sets one of 15 sector values on every one of its 4,771 records
and parse/checks.py carries it through as `category`, so the 4,771 filter fine. The rows
with no sector are the ones myScheme does not list: the budget-only and outcome-only
entries in data/registry.json, and the state budget rows in data/{karnataka,andhra,
kerala,tamilnadu}/classification.json. Those are the rows this register exists to surface,
so leaving exactly them unfilterable put the whole gap in the worst possible place.

THE TAXONOMY IS myScheme's AND IT IS NOT NEGOTIABLE. The 15 values are read at run time
out of data/checks.json rather than typed here, because a filter with two vocabularies in
it is not a filter. Kerala files a sector of its own, 37 values wide across the rows here
and 83 across its whole book, and it is deliberately NOT merged: "Social Justice
Programme" and "Social welfare & Empowerment" are different vocabularies and a reader
picking one would silently exclude the other's schemes. Kerala's own string is used only
as a signal, and it was measured and rejected. See below.

HOW THIS DIFFERS FROM THE OTHER CLASSIFIERS IN THIS DIRECTORY, and it changes the whole
trade-off. parse/classify_tamilnadu.py, parse/classify_kerala.py, parse/classify_andhra.py
and parse/classify_karnataka.py answer "is this row a welfare scheme or an establishment
head?", and a false positive there is an accusation: it names a government as hiding a
scheme it does not have. Those files therefore run at precision above 0.95 and throw away
most of their recall to get it. THIS FILE IS NOT THAT. A wrong sector is a browsing
annoyance: a reader filtering Health & Wellness sees a scheme that is really Education, or
misses one. So the operating point here is chosen for usefulness, not for safety, and the
accuracy is stated plainly rather than pushed up by abstaining. The one rule kept from the
others is that a row that cannot be classified confidently stays unset, because a wrong
sector IS worse than a missing one for a reader filtering by it: a missing one is visibly
missing, a wrong one is silently wrong.

WHAT ACTUALLY DISCRIMINATES, and the first finding is that the expected order is
backwards. The ministry or department name looks like the strongest signal and is not.
Each signal used ALONE, on the hand-labelled rows where it fires. Alone and not in the
cascade, because a signal measured only on the rows the stronger ones left behind is
measured on the hardest rows there are, which flatters the strong one and buries the weak:

    a benefit phrase in the scheme name            0.957  fires on 233 of 301
    a topic word in the scheme name                0.714  fires on  77 of 301
    the ministry or department name                0.694  fires on 186 of 301
    the Karnataka purpose line                     0.667  fires on  21 of 301
    the major head of account                      0.648  fires on 210 of 301
    Kerala's own sector string                     0.444  fires on  45 of 301

And counted, not estimated, on audit 2's 178 hand-read published answers, by the signal
that actually decided each one:

    a benefit phrase in the name       93 right of 100 audited   0.930
    a topic word in the name           21 right of  25 audited   0.840
    the department or ministry         36 right of  50 audited   0.720
    the purpose line                    3 right of   3 audited

The name wins because these are BUDGET HEADS, not portal listings. myScheme lists brands
("Bhagya Lakshmi", "Aadarana") and a brand name says nothing; a Demand Book prints "Post-
Matric Scholarship to Scheduled Caste Students" and "Feeding Children in the age group of
5-9 under Puratchi Thalaivar MGR Nutritious Meals Programme", which say everything. The
signal the brief expected to be weakest is the one carrying this file, and it is weakest
only in the corpus where names are brands.

WHY THE DEPARTMENT IS WEAK, measured rather than asserted. myScheme is itself a labelled
corpus for this question: 4,767 of its records carry both an organisation and a sector.
Memorising the modal sector of each of the 386 distinct organisations and applying it back
to the same records scores 0.695. That is a CEILING for any department-only rule, on
myScheme's own data, with the answers in hand, and this file's own department rules
reach 0.694 on the hand sample and 0.720 on the 50 audit 2 rows where they decided. The
reason for the ceiling is structural: a department is not a sector. The biggest failure
is that welfare departments pay scholarships. myScheme files 79 of the 212 schemes of the
"Social Justice and Empowerment Department" under Education & Learning and 65 under Social
welfare & Empowerment; "Labour Department" is 53% Social welfare, not Skills & Employment.
The state books do the same thing under major head 2225: 22 of the hand-labelled
Education & Learning rows carry a head of account that says Social welfare & Empowerment,
and 20 of those 22 are under 2225.

That is also why the major head is weak and worth the fewest points here. 2210 and 2211
really are health, 2401 and 2405 really are agriculture, and the mapping below is the
List of Major and Minor Heads, not a guess. But 2225 (Welfare of SC/ST/OBC) and 2235
(Social Security and Welfare) hold 675 of the 1,821 rows that carry a head at all, and
they are the two heads whose contents are most mixed: scholarships, hostels, pensions,
marriage assistance, child protection and self-employment loans all sit under them.

SIGNALS MEASURED AND REJECTED, with the measurement that rejected them:

  Kerala's own sector string, its 37 values mapped onto the 15.   0.444 over 45 rows
      Rejected, and it is the interesting rejection. Kerala's largest bucket is "Welfare
      of SCs, STs, OBCs, Minorities and Forward" with 78 of its 399 rows, and most of
      those rows are scholarships, which the shared vocabulary files under Education &
      Learning. Kerala's axis is WHO the money is for; myScheme's axis is WHAT it buys.
      Mapping one onto the other therefore fails hardest exactly where Kerala files most
      of its schemes. Once the name, the department and the head are in place it fired as
      the deciding signal on 1 row out of 2,599, so it is not in the scorer at all.

  The demand number on its own, without resolving it to a ministry.   not usable
      A Union Budget demand number is a ministry identifier and nothing else; used as a
      category it is 74 categories, none of them a sector. It is resolved to the printed
      ministry name (see demand_ministries) and then fed to the same department rules.

  Bare topic words with high measured lift on myScheme names.   rejected on inspection
      "more", "system", "area", "post", "pre", "class", "case", "duty", "start" and "old"
      all score above 0.80 for some sector on myScheme's 4,771 names, purely because they
      are fragments of other words and of scheme brands. The trap this repository keeps
      finding is real and it bit twice during development: the pattern `\\bculture|art\\b`
      matches "start", "smart" and "part", and `\\bhouse\\b` gave "National Test House"
      the sector Housing & Shelter. Every pattern below is a phrase that names a benefit
      or a domain, never a bare common word, and the two that slipped through were caught
      by the audit and are recorded there.

THE OPERATING POINT, and the weights are the measurements above rather than a feeling.
Signals score, they do not veto: a benefit phrase in the name is worth 5, a topic word in
the name and the department are worth 2, the purpose line and the major head are worth 1.
A row publishes when the leading sector scores at least MIN_SCORE (2) and leads the
runner-up by MARGIN (1). In plain words that means:

    a benefit phrase in the name publishes on its own              0.930, audit 2
    a topic word in the name publishes on its own                  0.840, audit 2
    the department publishes on its own                            0.720, audit 2
    the major head alone does NOT publish                          0.533, audit 1
    the purpose line alone does NOT publish                        0.550, audit 1
    a head or a purpose line publishes when a second signal agrees with it
    two signals of equal weight that disagree publish nothing

The last two are measured on audit 1, against the first working version, where a lone head
and a lone purpose line did publish: 16 right of 30 and 11 right of 20. The head is the
one signal deliberately demoted below its own standalone number. It scores 0.648 across
all the rows that have one, but the rows where it is the ONLY thing available are the rows
whose name says nothing and that have no department, and those are the 30 rows just
counted. That is the definition of a row that cannot be classified confidently, so 312
rows stay unset. The full sweep over MIN_SCORE and MARGIN is published in data/sector.json
under threshold_sweep. The chosen point is not the accuracy-optimal one: on the hand
sample, 7 and 1 scores 0.975 over 40% of the rows, and at that setting most of the gap
this file exists to close stays open.

THE LABELLING RULE, applied to every hand label and recorded in data/sector_labels.json:
the sector is the domain of the benefit the row buys, chosen from the 15 and following
myScheme's own conventions where they are consistent, which were read off its 4,771
records before labelling began:

    a scholarship, stipend, fee or textbook to a student is Education & Learning whatever
      department pays it  (myScheme: "scholarship" 0.93 Education, "matric" 0.95)
    a pension, marriage assistance, funeral grant or relief payment is Social welfare &
      Empowerment  ("pension" 0.86, "marriage" 0.85, "widow" 0.88)
    anything for a farmer, fisherman or animal is Agriculture,Rural & Environment
      ("farmers" 0.96, "fishermen" 0.95, "livestock" 0.84)
    child feeding, anganwadi, creche and maternity are Women and Child
    a loan, insurance or interest subvention is Banking,Financial Services and Insurance
      ("cooperative" 0.78, "loan/credit" 0.49 with BFSI the mode)
    Social welfare & Empowerment is the residual, never the first choice

Two conventions were genuinely undecidable and are recorded as such rather than hidden.
SCHOOL FEEDING: myScheme's own 12 mid-day-meal records split 4 Women and Child, 3 Health,
2 Social welfare, 2 Education with no majority, so the rule here is that feeding a child is
Women and Child and feeding an old age pensioner is Social welfare. Two hand labels were
corrected mid-development to make the sample obey that rule, and both are flagged in
data/sector_labels.json. LIVELIHOOD MISSIONS: myScheme files "Deendayal Antyodaya Yojana -
National Rural Livelihoods Mission" itself under Social welfare & Empowerment, so NRLM,
NULM and Aajeevika follow it there rather than into Skills & Employment.

THE TWO LABEL SETS AND WHAT EACH ONE ANSWERS.
  stratified, 320 rows   A systematic sample across the five source families, drawn on the
                         sorted key so it is reproducible. 301 carry a sector, 10 are
                         labelled `none` because no sector fits ("Actual Recoveries",
                         "Mauritius", "Other works") and 9 `uncertain` because the row's
                         own evidence did not settle it. Only the 301 count towards
                         accuracy; the other 19 are reported separately, because a
                         classifier that assigns a sector to "Onetime payment of Arrears."
                         is wrong in a way an accuracy figure hides.
  audit, 478 rows        Two hand audits of the classifier's own published answers, drawn
                         stratified by DECIDING SIGNAL so each signal's precision is a
                         count and not an estimate. Audit 1 (300 rows) was read against
                         the first working version and its findings WERE fed back: nine
                         pattern defects it exposed are fixed in the tables below, and the
                         six that are one-line fixes carry the row that exposed them. 65
                         of its 300 rows therefore no longer describe the answer they were
                         read against, and are dropped from its count rather than credited
                         to a reading nobody did. Audit 2 (178 rows, disjoint from audit 1
                         and from the stratified sample) was read against the shipped
                         version and was NOT fed back. Audit 2 is the number to quote: 153
                         right of 178, precision 0.860 over the rows audited and 0.877
                         re-weighted to the mix of deciding signals in the 2,287 rows
                         actually published.

WHAT IT STILL GETS WRONG is in data/sector.json, named row by row: known_errors from the
stratified sample, and known_errors_audit_2 for the 25 errors audit 2 counted, grouped by
failure mode. None of the audit 2 findings is patched, because a classifier tuned on the
sample that measures it is measuring itself.

THE KEY, so the site can look a row up without guessing. data/sector.json is keyed on the
row's own identity in the file it came from, never on a slug, because slugs are assigned
by site/build.py at render time and collide:

    a registry entry     "registry|" + entry["name"], counting ONLY the entries with no
                         myscheme source, in registry order, with "|2" appended to the
                         second entry of a repeated name and so on. Two names repeat:
                         "PM Uchchatar Shiksha Protsahan (PM-USP) Yojna" and "Capacity
                         Development (CD)".
    a state budget row   state key + "|" + str(entry["key"] or entry["hoa"]). Karnataka
                         files an hoa and no key; the other three file a key. All four
                         are unique within their own file.

Every one of the 2,233 rows the site currently shows with no sector resolves to a key
here, and 1,958 of them get a sector.

THE SCOPE, and why data/sector.json is a superset of what the site shows. This file covers
every register row that can lack a myScheme category: the 680 registry entries with no
myScheme source, and every state classification row at or above that state's listing bar
that myScheme does not already list. It does NOT replicate site/build.py's de-duplication
of centrally sponsored state shares, which drops a further 366 rows, because that is the
site's decision and copying it here would put the same rule in two places. Keys not used by
the site are harmless; a key the site wants and cannot find shows as "Not stated", which is
the honest degradation.
"""

import argparse
import collections
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT_DIR, "collect"))
from common import ROOT, read_json, utcnow, write_json  # noqa: E402

# The listing bars are site/build.py's, mirrored rather than imported so that parse/ does
# not depend on site/. They decide which state rows the register shows at all, and the
# accuracy below is quoted on that population because that is what a reader filters.
# Must match site/build.py's own LISTING_BAR and STATE_OF. Three states were added there
# and not here, which left 1,974 of 8,748 site rows unfilterable by the register's primary
# filter: the classifier had simply never been shown them. Duplicated rather than imported
# because parse/ does not import from site/, and a mismatch is now a visible regression in
# the not-stated count rather than a silent one.
LISTING_BAR = {"karnataka": 1, "andhra": 0, "kerala": 3, "tamilnadu": 5,
               "maharashtra": 2, "odisha": 4, "westbengal": 3}
STATE_OF = {"karnataka": "Karnataka", "andhra": "Andhra Pradesh",
            "kerala": "Kerala", "tamilnadu": "Tamil Nadu",
            "maharashtra": "Maharashtra", "odisha": "Odisha",
            "westbengal": "West Bengal"}

# Scoring. A benefit phrase in the name is worth more than everything else put together,
# because it measured 0.865 alone against 0.659 for the department and 0.652 for the head.
W_NAME, W_WEAK, W_PURPOSE, W_DEPT, W_HEAD = 5, 2, 1, 2, 1
MIN_SCORE, MARGIN = 2, 1

SW = "Social welfare & Empowerment"
ED = "Education & Learning"
AG = "Agriculture,Rural & Environment"
BE = "Business & Entrepreneurship"
SE = "Skills & Employment"
BF = "Banking,Financial Services and Insurance"
SC = "Sports & Culture"
HW = "Health & Wellness"
WC = "Women and Child"
HS = "Housing & Shelter"
TT = "Travel & Tourism"
IT = "Science, IT & Communications"
TI = "Transport & Infrastructure"
PS = "Public Safety,Law & Justice"
US = "Utility & Sanitation"

# ---------------------------------------------------------------------------
# What the name says. ORDER IS THE TIE-BREAK and it is not alphabetical: the first rule
# that matches wins, so a rule placed above another means "when both fit, prefer this one".
# Every ordering below was fixed by a measured error in the hand sample, named beside it.
# ---------------------------------------------------------------------------
NAME_RULES = [
    # Above everything, because "Feeding Old Age Pensioners under the Puratchi Thalaivar
    # M.G.R. Nutritious Meal Programme" is a pension row wearing a nutrition row's name.
    (SW, r"\bpensions?\b|\bpensionary\b|\bpensioners?\b|old age|\bnsap\b|"
         r"\bignoaps\b|\bigndps\b|senior citizens?"),
    # "\bhouse\b" alone gave Ministry of Consumer Affairs' "National Test House" the sector
    # Housing & Shelter (audit 1). Housing now needs a housing word, not the word house.
    (HS, r"\bhousing\b|\bhouses\b|house (?:site|building|construction)|\bawas\b|"
         r"\bawaas\b|\bgruha\b|\bghar\b|\bshelter|\bpmay\b|\bdwelling|\bhuts?\b"),
    # Above Women and Child, because "Nutrition Programme for ITI Trainees" is a trainee
    # benefit; below it would be, and was, filed as child nutrition.
    (SE, r"\bskills?\b|kaushal|vocational|apprentice|\biti\b|"
         r"industrial training institute|employment exchange|\bplacement\b|"
         r"unemploy|retrain|redeploy|\bddu-?gky\b|\bddugky\b"),
    # "mat(?:h)?ru vandana" because Karnataka prints "Pradhan Manthri Maatru Vandana" and
    # Kerala "Mathru Vandana"; the single spelling missed 1 row in 200 (audit 1).
    # "feeding|breakfast" because Tamil Nadu writes "New Programme for feeding poor
    # children in the age group of 5 to 9" with no nutrition word in it (audit 1).
    (WC, r"anganwadi|\bicds\b|integrated child|child protection|vatsalya|"
         r"supplementary nutrition|poshan|nutritious meal|nutrition programme|"
         r"feeding (?:of |poor |to )?children|breakfast|mid ?day meal|noon meal|"
         r"mat(?:h)?ru vandana|\bpmmvy\b|lactating|pregnant wom|\bcreche|\bpalna\b|"
         r"shakti sadan|shakthi sadan|swadhar|ujjawala|ujawala|one stop cent|"
         r"women helpline|nari adal|girl child|\bbalika\b|beti bachao|\borphan|"
         r"adolescent girls?|women empowerment|empowerment of women|"
         r"hub for empowerment|foster care|non.?institutional care"),
    (ED, r"scholarship|schollarship|\bstipends?\b|fellowship|pre[- ]?matric|"
         r"post[- ]?matric|tuition fee|fee reimbursement|fee concession|"
         r"fee waiver|school fee|hostel fee|note ?books?|text ?books?|"
         r"educational assistance|samagra shiksha|uchchatar|uchhatar|\brusa\b|"
         r"free coaching|\bcoaching\b|literacy|shiksha|siksha|\bvidya\b|"
         r"research schola|doctoral|\bmatriculation\b"),
    # Above Health & Wellness, because "National Mission For Sustainable Agriculture -
    # Soil Health Card" is not a health scheme. "farming" as well as "farmers" because
    # "National Mission on Natural Farming under Tribal Sub-Plan" carried neither (audit 1).
    (AG, r"\bfarmers?\b|\bfarming\b|\bkisan\b|\bkrishi\b|agricultur|horticultur|"
         r"\bcrops?\b|\bpaddy\b|\bseeds?\b|oilseed|\bpulses\b|irrigation|"
         r"\bfisher(?:y|ies)\b|fisherm|fisherwom|\bmatsya\b|\bpmmsy\b|"
         r"animal husband|\bcattle\b|\bdairy\b|livestock|\bfodder\b|veterinar|"
         r"\bpoultry\b|\bforest|wildlife|watershed|soil health|\bmanure\b|"
         r"fertilis|fertiliz|plantation|\brkvy\b|\bnfsm\b|\bpmksy\b|\bmgnreg|"
         r"employment guarantee|pump ?sets?|pumping system|price support|"
         r"market intervention|\bsinchai|\bsinchayee|\belephant\b|\btiger\b|"
         r"green india"),
    # The lookbehind is there for "Soil Health Card" and nothing else.
    (HW, r"(?<!soil )\bhealth\b|\bhospital|\bmedical\b|\bmedicines?\b|dispensar|"
         r"ayushman|\barogya|\bnrhm\b|\bnhm\b|immunis|immuniz|tuberculosis|"
         r"malaria|\bhiv\b|\bcancer\b|dialysis|ambulance|pharmac|\bnutrition\b"),
    # Above Business, because "Co-operative Handloom Weavers Thrift Fund" and "National
    # Export Insurance Account" are both financial instruments wearing a trade's name.
    (BF, r"\binsurance\b|\bbh?ima\b|\bthrift\b|interest subven|interest subsid|"
         r"co-?operative bank|finance corporation|\bmargin money\b|"
         r"\bsubvention\b|\bbonds?\b|economic support scheme|\bcredit\b|"
         r"\bloans?\b|life assurance"),
    (BE, r"\bmsmes?\b|micro,? small|small (?:scale )?industr|\bindustri(?:es|al)\b|"
         r"entrepreneur|\bstart[- ]?ups?\b|\bstartup|incubat|\bkhadi\b|handloom|"
         r"powerloom|handicraft|\bweavers?\b|\bcoir\b|\btextile|manufactur|"
         r"\bexports?\b|\binvestors?\b|investment promotion|capital subsidy|"
         r"food processing|sericultur|street vendor|swanidhi|make in india"),
    # "sportsperson" spelled out because \bsports?\b does not reach inside it, and
    # "National welfare fund for sportspersons" was filed as Social welfare (hand sample).
    (SC, r"\bsports?\b|sportsperson|\bathlet|\bgames\b|\bstadium|\bkhelo\b|"
         r"youth (?:policy|affairs|welfare|services)|\bculture\b|\bcultural\b|"
         r"\bmuseum|archaeolog|\bheritage\b|\blibrar|\bmusic\b|\bdance\b|"
         r"\bdrama\b|\bfestival\b|art gallery|\bakademi\b"),
    (TT, r"\btourism\b|\btourists?\b|swadesh darshan|\bpilgrim"),
    # "\bscience\b" alone gave "Government Arts and Science College" the sector Science,
    # IT & Communications (audit 1); it now needs the phrase, not the word.
    (IT, r"e-?governance|\bsatellite\b|\bspace\b|\bcyber\b|information technolog|"
         r"\bsoftware\b|\bbroadband\b|telecom|\b5g\b|artificial intelligence|"
         r"scientific|science and technolog|remote sensing|\bmausam\b|meteorolog"),
    (TI, r"\broads?\b|\bhighway|\bbridges?\b|\bbuses\b|\be-?buses?\b|metro rail|"
         r"\brailway|track renewal|\bnew lines\b|\bports?\b|\bharbour\b|"
         r"waterway|\bairport|transport corporation|\bpmgsy\b"),
    (PS, r"\bpolice\b|\bprison|\bjail\b|\bcourts?\b|judicial|legal aid|"
         r"\badvocates?\b|\blawyers?\b|law and order|fire service|home guard"),
    # "\belectrification\b" was here and gave Ministry of Railways' "Electrification
    # Projects" the sector Utility & Sanitation (hand sample); it is gone. "\bsbm\b"
    # because the Department of Drinking Water writes "SBM-Grameen" (audit 1).
    (US, r"\bsanitation\b|\btoilets?\b|swachh|swachha|swachata|\bsbm\b|"
         r"drinking water|water supply|\bsewer|solid waste|power system|"
         r"power (?:supply|grid|transmission|distribution)|service connection|"
         r"\bddugjy\b|saubhagya|solar power|off-?grid|renewable energy|\blpg\b|"
         r"gas connection|ujjwala"),
    # The residual, so it runs last. "livelihood" sits here and not in Skills & Employment
    # because myScheme files DAY-NRLM itself under Social welfare & Empowerment.
    (SW, r"\bwidows?\b|\bdestitute\b|\bdisab|differently abled|\bmarriage\b|"
         r"\bvivah\b|kalyana|funeral|ex-?gratia|social security|freedom fighter|"
         r"transgender|beggar|social assistance|\bvictims?\b|\bwelfare fund\b|"
         r"livelihood|aajeevika|ajeevika|\bnulm\b|\bnrlm\b|antyodaya|"
         r"\bbonded labour\b|\brelief\b"),
]

# A topic word rather than a benefit word: worth 2, not 5. Measured 0.800 over the 40 rows
# of audit 1 where it decided, against 0.960 for the benefit phrases.
WEAK_NAME_RULES = [
    (ED, r"\bstudents?\b|\bpupils?\b|school going|\bcolleges?\b|universit|"
         r"\bschools?\b|education|\btrainees?\b"),
    (WC, r"\bmothers?\b|\binfants?\b|\bchildren\b|\bchild\b|"
         r"women (?:commission|development)"),
    (BF, r"\bco-?operatives?\b|co-?operation"),
    (AG, r"\bvillages?\b|gram(?:een|in)\b|\bpanchayat|rural development|"
         r"\brural\b|\bwater resource"),
    (SW, r"scheduled caste|scheduled tribe|backward class|\bminorit|"
         r"\btribals?\b|\badi dravidar\b"),
]

# ---------------------------------------------------------------------------
# What the ministry or department says. Measured 0.659 over the 179 hand-labelled rows
# where it fires, against a memorised ceiling of 0.695 on myScheme's own 4,767 records.
# ---------------------------------------------------------------------------
DEPT_RULES = [
    (AG, r"agricultur|farmer|horticultur|fisher|animal husband|dairy|"
         r"forest|environment|water resource|irrigation|rural development|"
         r"panchayat|land resource"),
    (ED, r"education|literacy|school"),
    (HW, r"health|family welfare|medical|ayush|drugs control|pharmaceutical"),
    (WC, r"women (?:and|&) child|child (?:development|welfare)|women development"),
    (SW, r"social justice|social welfare|social security|welfare of sc|"
         r"backward class|minorit|tribal welfare|adi dravidar|differently abled|"
         r"empowerment of persons|scheduled caste|scheduled tribe|weaker section|"
         r"economically weaker|senior citizen|disaster management|"
         r"natural calamit|relief on account|pension and other|"
         r"food and public distribution|food and consumer"),
    (SE, r"skill|employment|labour"),
    (BE, r"industr|commerce|micro, small|msme|handloom|textile|khadi|"
         r"food processing|mines|steel|petroleum|corporate affairs|"
         r"promotion of industry|heavy industr|sericultur"),
    (BF, r"financial services|economic affairs|co-?operation|public enterprise|"
         r"\bfinance\b"),
    (SC, r"sports|youth affairs|culture|tamil development"),
    (TT, r"tourism"),
    (IT, r"science|technolog|electronics|telecommunicat|\bspace\b|atomic energy|"
         r"biotechnolog|statistic|\bposts\b|earth science|information and broadcast"),
    (TI, r"road transport|railway|shipping|civil aviation|ports|transport"),
    (HS, r"housing"),
    (PS, r"police|home affair|prison|\blaw\b|justice|prohibition and excise|"
         r"vigilance|consumer affairs"),
    (US, r"drinking water|sanitation|new and renewable|water supply|\bpower\b|energy"),
]

# ---------------------------------------------------------------------------
# What the major head of account says. This is the state's own chart of accounts, from the
# List of Major and Minor Heads, and it is the only signal many state rows carry: 1,821 of
# the 2,599 rows here have one, 1,703 have a department, and 141 have neither.
#
# Measured 0.648 alone, and the failure is concentrated: 2225 and 2235 together hold 675
# of the 1,821 rows that carry a head, and both are mixed baskets. That is why the head is
# worth 1 point rather than 2: on its own it does not publish. The heads deliberately left
# out are the ones that name no sector: 2047 Other Fiscal Services, 2070 Other
# Administrative Services, 2075 Miscellaneous General Services, 2217 Urban Development,
# 3604 Compensation to Local Bodies and the 2011-2059 organs-of-state block.
# ---------------------------------------------------------------------------
HEAD_SECTOR = {
    "2014": PS, "2055": PS, "2056": PS, "2062": PS,
    "2071": SW, "2202": ED, "2203": ED, "2204": SC, "2205": SC,
    "2210": HW, "2211": HW, "2215": US, "2216": HS, "2220": SC,
    "2225": SW, "2230": SE, "2235": SW, "2236": WC, "2245": SW,
    "2250": SW, "2401": AG, "2402": AG, "2403": AG, "2404": AG,
    "2405": AG, "2406": AG, "2407": AG, "2408": SW, "2415": AG,
    "2425": BF, "2435": AG, "2501": AG, "2505": AG, "2506": AG,
    "2515": AG, "2551": AG, "2552": AG, "2575": AG, "2700": AG,
    "2701": AG, "2702": AG, "2705": AG, "2711": AG, "2801": US,
    "2810": US, "2851": BE, "2852": BE, "2853": BE, "3054": TI,
    "3055": TI, "3056": TI, "3425": IT, "3435": AG, "3452": TT,
    "3454": IT, "3456": SW, "3475": BE, "4202": ED, "4210": HW,
    "4215": US, "4216": HS, "4225": SW, "4235": SW, "4250": SW,
    "4401": AG, "4405": AG, "4515": AG, "4801": US, "4851": BE,
    "5054": TI,
}

NAME_SIGNAL = "a benefit phrase in the name"
WEAK_SIGNAL = "a topic word in the name"
PURPOSE_SIGNAL = "the purpose line"
DEPT_SIGNAL = "the department or ministry"
HEAD_SIGNAL = "the major head of account"

MAJOR = re.compile(r"^\s*(\d{4})")
DEMAND_LINE = re.compile(r"^\s*Demand\s*No\.?\s*(\d+)")
NUMBERED_ROW = re.compile(r"^\s*\d+\.")


def demand_ministries(cycle=None):
    """Demand number -> the ministry the Budget prints under it.

    A budget-only row carries a demand number and nothing else, and a demand number is a
    ministry identifier, so on its own it is 74 categories rather than a sector. Statement
    4A and 4B print the ministry name on the line after each "DemandNo. N" header, so the
    name is the document's own and not a table typed here. 543 of the 680 central rows
    reach a department this way; the other 137 are DBT-only or outcome-only and have none.

    Reads archive/ only. Returns {} rather than failing if pdftotext is absent, because a
    missing tool should cost coverage on 543 rows, not the whole run.
    """
    if not shutil.which("pdftotext"):
        return {}
    base = os.path.join(ROOT, "archive", "budget")
    if cycle is None:
        # The newest archived cycle, so a new Budget does not need this file edited.
        years = sorted(d for d in os.listdir(base)) if os.path.isdir(base) else []
        if not years:
            return {}
        cycle = years[-1]
    out = {}
    for stmt in ("stat4a", "stat4b"):
        src = os.path.join(base, cycle, stmt + ".pdf.gz")
        if not os.path.exists(src):
            continue
        with tempfile.TemporaryDirectory() as td:
            pdf, txt = os.path.join(td, "d.pdf"), os.path.join(td, "d.txt")
            with gzip.open(src, "rb") as fh, open(pdf, "wb") as dst:
                shutil.copyfileobj(fh, dst)
            subprocess.run(["pdftotext", "-layout", pdf, txt],
                           check=True, capture_output=True, timeout=180)
            with open(txt, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        for i, line in enumerate(lines):
            m = DEMAND_LINE.match(line)
            if not m:
                continue
            no = int(m.group(1))
            for nxt in lines[i + 1:i + 6]:
                name = nxt.strip()
                if name and not NUMBERED_ROW.match(name):
                    # Demand 62's name wraps across two lines in 4A and not in 4B, so the
                    # longer of the two readings is the complete one.
                    if len(name) > len(out.get(no, "")):
                        out[no] = name
                    break
    return out


def major_heads(heads):
    """The 4-digit major head off each head of account, in first-seen order."""
    out = []
    for h in heads or []:
        m = MAJOR.match(str(h))
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def universe(demands):
    """Every register row that can lack a myScheme sector, with its evidence.

    Sorted on the key, so the file and every sample drawn from it are reproducible.
    """
    rows = []
    reg = read_json("data/registry.json", {}) or {}
    seen = collections.Counter()
    for en in reg.get("entries", []):
        srcs = en.get("sources") or {}
        if "myscheme" in srcs:
            continue                      # parse/checks.py already carries its category
        name = en["name"]
        seen[name] += 1
        # Two of these names are held by two entries each: "PM Uchchatar Shiksha
        # Protsahan (PM-USP) Yojna" and "Capacity Development (CD)". The suffix keeps the
        # key unique without inventing an identifier the registry does not have.
        key = "registry|" + name + ("" if seen[name] == 1 else "|%d" % seen[name])
        demand = (srcs.get("budget") or {}).get("demand_no")
        rows.append({
            "key": key, "family": "central", "name": name,
            "org": demands.get(demand) if demand is not None else None,
            "org_from": "budget demand %s" % demand if demand is not None else None,
            "heads": [], "major": [], "purpose": None, "own_sector": None,
            "sources": sorted(srcs),
        })
    for state, bar in sorted(LISTING_BAR.items()):
        cls = read_json("data/%s/classification.json" % state, {}) or {}
        for e in cls.get("all_entries") or []:
            if e.get("score", -99) < bar or e.get("in_myscheme_%s" % state):
                continue
            heads = e.get("hoas") or ([e["hoa"]] if e.get("hoa") else [])
            rows.append({
                "key": state + "|" + str(e.get("key") or e.get("hoa")),
                "family": state, "name": e["name"],
                "org": e.get("department"),
                "org_from": "department" if e.get("department") else None,
                "heads": heads, "major": major_heads(heads),
                "purpose": e.get("purpose"), "own_sector": e.get("sector"),
                "sources": [state], "score": e.get("score"),
            })
    rows.sort(key=lambda r: r["key"])
    return rows


def _match(table, text):
    if not text:
        return None
    for sector, pattern in table:
        if re.search(pattern, text, re.I):
            return sector, pattern
    return None


def score(row):
    """Every signal that fires, with its points, its sector and what it saw."""
    hits = []
    m = _match(NAME_RULES, row["name"])
    if m:
        hits.append((W_NAME, m[0], NAME_SIGNAL, "a benefit phrase in the name"))
    m = _match(WEAK_NAME_RULES, row["name"])
    if m:
        hits.append((W_WEAK, m[0], WEAK_SIGNAL, "a topic word in the name"))
    m = _match(NAME_RULES, row.get("purpose"))
    if m:
        hits.append((W_PURPOSE, m[0], PURPOSE_SIGNAL,
                     "a benefit phrase in the purpose line"))
    m = _match(DEPT_RULES, row.get("org"))
    if m:
        hits.append((W_DEPT, m[0], DEPT_SIGNAL,
                     "the department or ministry: %s" % row["org"]))
    for head in row.get("major") or []:
        if head in HEAD_SECTOR:
            hits.append((W_HEAD, HEAD_SECTOR[head], HEAD_SIGNAL,
                         "major head %s" % head))
            break
    return hits


def deciding_signal(row, sector):
    """The highest-scoring signal that pointed at the sector this row got."""
    hits = [h for h in score(row) if h[1] == sector]
    return max(hits)[2] if hits else None


def classify(row):
    """(sector or None, evidence). Abstains rather than guess: see MIN_SCORE, MARGIN."""
    hits = score(row)
    if not hits:
        return None, []
    totals = collections.Counter()
    for points, sector, _, _ in hits:
        totals[sector] += points
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    top, top_score = ranked[0]
    runner = ranked[1][1] if len(ranked) > 1 else 0
    evidence = sorted(("+%d" % p, sector, why) for p, sector, _, why in hits)
    if top_score < MIN_SCORE or top_score - runner < MARGIN:
        return None, evidence
    return top, evidence


def sweep(rows_by_key, labels):
    """Accuracy against coverage over the hand sample, at every operating point."""
    global MIN_SCORE, MARGIN
    keep, out = (MIN_SCORE, MARGIN), []
    graded = [x for x in labels if x["label"] not in ("none", "uncertain")]
    for min_score in (2, 3, 4, 5, 7):
        for margin in (0, 1, 3):
            MIN_SCORE, MARGIN = min_score, margin
            right = fired = 0
            for x in graded:
                got, _ = classify(rows_by_key[x["key"]])
                if got is None:
                    continue
                fired += 1
                right += got == x["label"]
            out.append({"min_score": min_score, "margin": margin,
                        "classified": fired, "of": len(graded),
                        "right": right,
                        "accuracy": round(right / fired, 3) if fired else None,
                        "coverage": round(fired / len(graded), 3)})
    MIN_SCORE, MARGIN = keep
    return out


def per_signal(rows_by_key, labels):
    """Each signal used ALONE, on the hand-labelled rows where it fires.

    Alone, not in the cascade: a signal measured only on the rows the stronger signals
    left behind is measured on the hardest rows there are, which flatters the strong one
    and buries the weak one. Both numbers are published, this one and the audit's.
    """
    graded = [x for x in labels if x["label"] not in ("none", "uncertain")]
    tables = [
        ("a benefit phrase in the name",
         lambda r: (_match(NAME_RULES, r["name"]) or [None])[0]),
        ("a topic word in the name",
         lambda r: (_match(WEAK_NAME_RULES, r["name"]) or [None])[0]),
        ("the Karnataka purpose line",
         lambda r: (_match(NAME_RULES, r.get("purpose")) or [None])[0]),
        ("the ministry or department name",
         lambda r: (_match(DEPT_RULES, r.get("org")) or [None])[0]),
        ("the major head of account",
         lambda r: next((HEAD_SECTOR[h] for h in (r.get("major") or [])
                         if h in HEAD_SECTOR), None)),
    ]
    out = []
    for name, fn in tables:
        right = fired = 0
        for x in graded:
            got = fn(rows_by_key[x["key"]])
            if got is None:
                continue
            fired += 1
            right += got == x["label"]
        out.append({"signal": name, "fires_on": fired, "of": len(graded),
                    "right": right,
                    "accuracy": round(right / fired, 3) if fired else None})
    return out


# Measured once against data/checks.json and quoted in the docstring; recomputed here so
# the published number is the file's own and not a memory of one.
def myscheme_department_ceiling(checks):
    by_org = collections.defaultdict(collections.Counter)
    for s in (checks or {}).get("schemes", []):
        if s.get("org"):
            by_org[s["org"]][s.get("category")] += 1
    total = sum(sum(c.values()) for c in by_org.values())
    right = sum(max(c.values()) for c in by_org.values())
    return {"records": total, "distinct_organisations": len(by_org),
            "right_if_each_organisation_took_its_modal_sector": right,
            "accuracy": round(right / total, 3) if total else None,
            "why": "A ceiling for any department-only rule, measured on myScheme's own "
                   "records with its own answers in hand. A department is not a sector."}


KNOWN_ERRORS = [
    {"row": "Chief Minister Marunthagam (Tamil Nadu, 2210)",
     "assigned": BF, "should_be": HW,
     "why": "Marunthagam is Tamil for pharmacy and no rule knows the word. The "
            "department is Co-operation, which runs the shops, so the department "
            "signal actively misleads. A one-word rule for one row would be "
            "over-fitting, so it is left wrong."},
    {"row": "Transportation of deceased Non Resident Tamils / Repatriation of Tamil "
            "Nationals in distress/ medical invalidation (Tamil Nadu, 2235)",
     "assigned": HW, "should_be": SW,
     "why": "The ordinary-word trap this repository keeps finding. The benefit is "
            "repatriation; the word 'medical' appears only in the phrase 'medical "
            "invalidation', naming a reason a worker is sent home."},
    {"row": "NTR Vidyonnathi (Andhra Pradesh, 2225)",
     "assigned": SW, "should_be": ED,
     "why": "Civil services coaching for Scheduled Caste students. The name is a coined "
            "word, the head is SC welfare and the department is Social Welfare, so every "
            "signal points at the beneficiary group and none at the benefit."},
    {"row": "Power Cost subsidy to Saloons (Andhra Pradesh, 2225)",
     "assigned": SW, "should_be": BE,
     "why": "A trade subsidy filed by the Backward Classes Welfare Department. Reading "
            "'power' as Utility & Sanitation was worse: it broke 'Free power to Weavers' "
            "and 'Subsidy for free Power to Irrigation Pumpsets' as well."},
    {"row": "Lawyers Welfare Fund (Karnataka, 2014)",
     "assigned": PS, "should_be": SW,
     "why": "Income support to advocates, filed under Administration of Justice. Both "
            "readings are defensible and the head agrees with the wrong one."},
    {"row": "Jan Shikshan Sansthan (central, no demand number)",
     "assigned": ED, "should_be": SE,
     "why": "A vocational institute whose name contains the word for education."},
    {"row": "Establishment of Centre of Excellence in Artificial Intelligence for "
            "Education (central, Department of Higher Education)",
     "assigned": IT, "should_be": ED,
     "why": "Genuinely both. The name carries a Science, IT & Communications phrase and "
            "an Education & Learning one, and the ordering prefers the first."},
    {"row": "Unspent SCSP-TSP Amount as per the SCSP-TSP Act 2013 (Karnataka, 2225 and "
            "2851)",
     "assigned": "varies with the purpose line", "should_be": "nothing",
     "why": "One of the rows no sector fits. The classifier has no way to know that and "
            "reads whatever the purpose line happens to mention. 312 rows abstain for "
            "want of any confident signal; rows like this one have a signal and it is "
            "noise."},
]

# The 25 errors audit 2 counted, grouped. DELIBERATELY NOT PATCHED: audit 2 is the number
# quoted for the shipped classifier, and a classifier tuned on the sample that measures it
# is measuring itself. Every one of these is a real, reproducible defect and the fix for
# each is obvious; they belong in the next revision with a fresh audit behind it, not in
# this one.
AUDIT_2_ERRORS = [
    {"pattern": "a coined brand name that means the opposite of what it looks like",
     "count": 2,
     "rows": ["Thallikivandanam (Andhra Pradesh) is a payment to mothers to keep a child "
              "in school, so Education & Learning; assigned Social welfare & Empowerment "
              "from the department",
              "Ganga Kalyana - for Schedule Tribe (Karnataka, 2225) is borewells for "
              "farmers, so Agriculture,Rural & Environment; assigned Social welfare & "
              "Empowerment because 'kalyana' is in the welfare pattern"],
     "why": "No signal in the row disagrees with the wrong answer. This is the residual "
            "the name signal cannot reach."},
    {"pattern": "the bare word 'nutrition' falls through to Health & Wellness",
     "count": 2,
     "rows": ["National Food Security and Nutrition Mission (Kerala, 2401) is "
              "Agriculture,Rural & Environment",
              "Ensure Nutrition Scheme - Uttasathai Uruthi Sei (Tamil Nadu, 2236) is "
              "Women and Child"],
     "why": "Women and Child catches the named nutrition programmes and Health & Wellness "
            "catches whatever is left, which is wrong in both directions. The word needs "
            "to be dropped from Health & Wellness, not moved."},
    {"pattern": "'orphan' assumes a child",
     "count": 1,
     "rows": ["Psycho Social Programme for Orphaned Mentally Ill Persons (Kerala, 2235) "
              "is Health & Wellness, not Women and Child"],
     "why": "The same ordinary-word failure as the rest, one level up: the word is right "
            "and the inference from it is not."},
    {"pattern": "a topic word decides a row whose subject is elsewhere in the name",
     "count": 2,
     "rows": ["Dr. Ambedkar Village Development Scheme (Kerala, 2225 and 4225) read "
              "'village' and answered Agriculture,Rural & Environment",
              "Silk Samagra-Central Share Rural Development (Kerala, 2515) read 'rural "
              "development' and answered Agriculture,Rural & Environment; silk is "
              "Business & Entrepreneurship"],
     "why": "The topic-word tier measured 0.840 and these are what the other 0.160 look "
            "like."},
    {"pattern": "a welfare department paying a student benefit, with nothing in the name "
                "to say so",
     "count": 3,
     "rows": ["Prize Money Award Scheme for Scheduled Caste Students (Tamil Nadu, 2225)",
              "Free supply of Bicycles to Backward Classes Girls Students (Tamil Nadu, "
              "2225)",
              "Free Supply of Uniform to Students (Tamil Nadu, 2235, Social Welfare and "
              "Women Empowerment Department)"],
     "why": "The single biggest failure mode in the whole file and the one the docstring "
            "opens with. All three are Education & Learning and all three were assigned "
            "Social welfare & Empowerment by the department. The name carries the word "
            "'Students' but not a benefit phrase, so the topic-word tier ties with the "
            "department at 2 points each and the tie is broken alphabetically, which is "
            "not a reason. Giving the topic word 3 points would fix all three and has to "
            "be measured against what it breaks."},
    {"pattern": "the ministry owns the commodity but not the sector",
     "count": 3,
     "rows": ["Spices Board (Department of Commerce) is Agriculture,Rural & Environment, "
              "not Business & Entrepreneurship",
              "Price Stabilisation Fund (Department of Consumer Affairs) is "
              "Agriculture,Rural & Environment, not Public Safety,Law & Justice",
              "Training/Human Resource Development (Ministry of Railways) is Skills & "
              "Employment, not Transport & Infrastructure"],
     "why": "Exactly the 0.720 the department signal measured, seen from the inside."},
    {"pattern": "a budget line no sector fits, given one anyway",
     "count": 4,
     "rows": ["Additional Amount met from Reserve fund (Ministry of Petroleum)",
              "Payment to ISPRL for Crude Oil Reserve (Ministry of Petroleum)",
              "International Relations (Ministry of New and Renewable Energy)",
              "Computerisation (Ministry of Railways)"],
     "why": "The register carries these rows because the Budget prints them, and the "
            "department is the only thing they have. Nothing here can tell a scheme from "
            "an office expense; parse/classify_*.py can, and wiring their verdict in as a "
            "gate is the obvious next move for the central rows."},
    {"pattern": "the delivery agency rather than the benefit",
     "count": 2,
     "rows": ["Stree Shakti Scheme - providing Free Bus Travel for Women (Andhra Pradesh, "
              "Public Transport Department) is Social welfare & Empowerment",
              "Insurance coverage for Anganwadi workers and helpers (Kerala, 2235) is "
              "about the worker, not the child"],
     "why": "A free bus pass is booked to the transport corporation that loses the fare, "
            "and the department signal reads the corporation."},
    {"pattern": "an employer obligation read as the benefit it resembles",
     "count": 1,
     "rows": ["Payment of Medical Reimbursement Charges to Retired All India Service "
              "Officers (Tamil Nadu, 2071) is Social welfare & Empowerment by the same "
              "rule that puts every other 2071 pension row there"],
     "why": "'medical' outranks the pension rule here because the pension rule needs the "
            "word pension and this row says 'Retired'."},
    {"pattern": "genuinely two sectors",
     "count": 5,
     "rows": ["Aqua Produce Processing (Fish and Shrimp), Interest Subsidy for Crop Loan, "
              "Fast Reactor Fuel Cycle Projects, Other Disaster Management Schemes and "
              "'Residential' were each counted against the classifier in audit 2 on a "
              "strict reading, and each has a defensible second answer"],
     "why": "Recorded so the 0.860 is read as a floor rather than a point estimate."},
]


def build(write=True):
    checks = read_json("data/checks.json", {}) or {}
    vocabulary = sorted({s.get("category") for s in checks.get("schemes", [])
                         if s.get("category")})
    known = {SW, ED, AG, BE, SE, BF, SC, HW, WC, HS, TT, IT, TI, PS, US}
    unknown = known - set(vocabulary)
    if unknown:
        # A sector this file emits that myScheme does not use would silently add a value
        # to the register's filter, which is the one thing the taxonomy rule forbids.
        raise SystemExit("sectors not in data/checks.json: %s" % sorted(unknown))

    demands = demand_ministries()
    rows = universe(demands)
    by_key = {r["key"]: r for r in rows}
    labels = (read_json("data/sector_labels.json", {}) or {}).get("labels", [])
    labels = sorted(labels, key=lambda x: x["key"])
    labels = [x for x in labels if x["key"] in by_key]

    sectors, by_family, by_sector, deciding = {}, collections.Counter(), \
        collections.Counter(), collections.Counter()
    for r in rows:
        sector, evidence = classify(r)
        by_family[(r["family"], bool(sector))] += 1
        by_sector[sector or "not stated"] += 1
        if sector:
            deciding[deciding_signal(r, sector)] += 1
            sectors[r["key"]] = {"sector": sector, "evidence": evidence,
                                 "name": r["name"], "family": r["family"]}

    graded = [x for x in labels if x["label"] not in ("none", "uncertain")]
    right = sum(1 for x in graded
                if classify(by_key[x["key"]])[0] == x["label"])
    fired = sum(1 for x in graded if classify(by_key[x["key"]])[0])
    ungradeable = [x for x in labels if x["label"] in ("none", "uncertain")]
    assigned_anyway = sum(1 for x in ungradeable if classify(by_key[x["key"]])[0])

    audits = (read_json("data/sector_labels.json", {}) or {}).get("audits", {})
    audit_out = {}
    for name, verdicts in sorted(audits.items()):
        per = collections.defaultdict(lambda: [0, 0])
        stale = 0
        for key, verdict in sorted(verdicts.items()):
            if key not in by_key:
                continue
            sector, evidence = classify(by_key[key])
            # A hand verdict is a verdict on the ANSWER that was audited. Where a later
            # fix changed the answer the verdict no longer applies to it, so the row drops
            # out of the count rather than being credited to a reading nobody did. This is
            # only ever non-zero for audit 1, whose findings were fed back.
            if sector != verdict["sector"]:
                stale += 1
                continue
            step = deciding_signal(by_key[key], sector)
            per[step][1] += 1
            per[step][0] += 1 if verdict["correct"] else 0
        audited = sum(v[1] for v in per.values())
        correct = sum(v[0] for v in per.values())
        # Stratified by deciding signal, so the raw figure over-weights the rare signals.
        # Re-weighting to the mix of the population is the number a reader experiences.
        weighted = sum(deciding[s] * v[0] / v[1] for s, v in per.items() if v[1]) \
            / sum(deciding[s] for s in per if per[s][1]) if per else None
        audit_out[name] = {
            "audited": audited, "right": correct, "wrong": audited - correct,
            "dropped_because_the_answer_changed_after_the_audit": stale,
            "precision_over_the_audited_rows":
                round(correct / audited, 3) if audited else None,
            "precision_reweighted_to_the_published_rows":
                round(weighted, 3) if weighted else None,
            "by_deciding_signal": {s: {"audited": v[1], "right": v[0],
                                       "precision": round(v[0] / v[1], 3)}
                                   for s, v in sorted(per.items()) if v[1]},
        }

    out = {
        "built": utcnow(),
        "question": "Which of the 15 myScheme sectors does each register row belong to, "
                    "for the rows myScheme does not list and which therefore carry no "
                    "sector of their own?",
        "taxonomy": vocabulary,
        "taxonomy_source": "data/checks.json, the sector myScheme sets on all 4,771 of "
                           "its records. Not extended, not merged with Kerala's own 36 "
                           "values: one filter, one vocabulary.",
        "scope": "The 680 registry entries with no myScheme source, plus every state "
                 "classification row at or above site/build.py's listing bar that "
                 "myScheme does not list. A superset of what the site shows by 366 "
                 "centrally sponsored state shares that site/build.py folds into their "
                 "parent scheme.",
        "counting_basis": "One row per key. A state votes a scheme's revenue head and its "
                          "capital head separately and both are separate rows here, "
                          "exactly as they are separate rows in the register.",
        "operating_point": {
            "min_score": MIN_SCORE, "margin": MARGIN,
            "weights": {"a benefit phrase in the name": W_NAME,
                        "a topic word in the name": W_WEAK,
                        "the purpose line": W_PURPOSE,
                        "the department or ministry": W_DEPT,
                        "the major head of account": W_HEAD},
            "why": "Chosen for usefulness, not for safety. A wrong sector is a browsing "
                   "annoyance, not a false accusation, so this file does not run at the "
                   "0.95 precision bar the scheme-or-not classifiers in this directory "
                   "use. It still abstains where nothing but one weak signal fires, "
                   "because a wrong sector is worse than a missing one for a reader "
                   "filtering by it.",
        },
        "rows": len(rows),
        "classified": len(sectors),
        "not_stated": len(rows) - len(sectors),
        "coverage": round(len(sectors) / len(rows), 3),
        "by_family": {fam: {"rows": sum(v for (f, _), v in by_family.items() if f == fam),
                            "classified": by_family[(fam, True)]}
                      for fam in sorted({f for f, _ in by_family})},
        "by_sector": dict(sorted(by_sector.items())),
        "deciding_signal": dict(sorted(deciding.items())),
        "signals": per_signal(by_key, labels),
        "signals_rejected": [
            {"signal": "Kerala's own sector string, its 36 values mapped onto the 15",
             "measured": "0.444 over the 45 hand-labelled Kerala rows where it fires, "
                         "against 0.865 for the name; and once the name, department and "
                         "head are in place it was the deciding signal on 1 row in 2,599",
             "why": "Kerala's axis is WHO the money is for and myScheme's is WHAT it "
                    "buys. Kerala's largest bucket, 'Welfare of SCs, STs, OBCs, "
                    "Minorities and Forward', is mostly scholarships, which the shared "
                    "vocabulary files under Education & Learning, so the mapping fails "
                    "hardest exactly where Kerala files most of its schemes. Merging the "
                    "two vocabularies into the filter was never an option; using one to "
                    "predict the other does not work either."},
            {"signal": "the Union Budget demand number, used as a category",
             "measured": "74 values, none of them a sector",
             "why": "It identifies a ministry, so it is resolved to the ministry name the "
                    "Budget prints beside it and fed to the department rules instead."},
            {"signal": "bare common words with high measured lift on myScheme's names",
             "measured": "'more' 0.93 Agriculture over 15 records, 'system' 0.88, 'area' "
                         "0.84, 'post' 0.80 Education, 'old' 0.84 Social welfare, all on "
                         "myScheme's 4,771 names",
             "why": "Every one is a fragment of another word or of a brand. Two got into "
                    "an early version and both were caught: '\\bhouse\\b' filed 'National "
                    "Test House' as Housing & Shelter, '\\bscience\\b' filed 'Government "
                    "Arts and Science College' as Science, IT & Communications. Every "
                    "pattern here is a phrase naming a benefit or a domain."},
            {"signal": "the department alone, where nothing else fires",
             "measured": "0.650 over the 60 rows of audit 1 where it decided",
             "why": "Not rejected but capped: it scores 2, so it publishes only when a "
                    "second signal agrees with it. On its own it is a coin weighted "
                    "two-to-one, which is not good enough to put in front of a reader."},
        ],
        "myscheme_department_ceiling": myscheme_department_ceiling(checks),
        "threshold_sweep": sweep(by_key, labels),
        "validation": {
            "hand_sample": {
                "labelled_with_a_sector": len(graded),
                "classified": fired,
                "right": right,
                "accuracy": round(right / fired, 3) if fired else None,
                "coverage": round(fired / len(graded), 3) if graded else None,
                "note": "Accuracy on a stratified sample of the population. The audits "
                        "below count errors on the published answers instead.",
            },
            "rows_no_sector_fits": {
                "hand_labelled_none_or_uncertain": len(ungradeable),
                "given_a_sector_anyway": assigned_anyway,
                "note": "10 of the 320 hand-labelled rows are budget lines no sector "
                        "fits ('Actual Recoveries', 'Mauritius', 'Other works') and 9 "
                        "could not be settled from the row's own evidence. They are out "
                        "of the accuracy figure and counted here instead, because a "
                        "classifier that files 'Onetime payment of Arrears.' under a "
                        "sector is wrong in a way accuracy hides.",
            },
            "audits": audit_out,
            "audit_note": "Both audits are hand readings of the classifier's own published "
                          "answer, drawn stratified by DECIDING SIGNAL so that each "
                          "signal's precision is a count. Audit 1 was read against the "
                          "first working version and its findings WERE fed back: eight "
                          "pattern defects it exposed are fixed and each is commented at "
                          "the pattern. Audit 2 is disjoint from audit 1 and from the "
                          "stratified sample, was read against the shipped version and "
                          "was NOT fed back. Quote audit 2.",
        },
        "known_errors": KNOWN_ERRORS,
        "known_errors_audit_2": AUDIT_2_ERRORS,
        "sectors": sectors,
    }
    if write:
        write_json("data/sector.json", out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    ap.add_argument("--dry-run", action="store_true",
                    help="report without writing data/sector.json")
    args = ap.parse_args()
    out = build(write=not args.dry_run)
    print("rows            %d" % out["rows"])
    print("classified      %d  (%.1f%%)" % (out["classified"], 100 * out["coverage"]))
    print("not stated      %d" % out["not_stated"])
    print()
    for fam, v in sorted(out["by_family"].items()):
        print("  %-12s %5d rows  %5d classified" % (fam, v["rows"], v["classified"]))
    print()
    print("each signal alone, on the hand-labelled rows where it fires")
    for s in out["signals"]:
        print("  %-34s %.3f  fires on %3d of %d"
              % (s["signal"], s["accuracy"] or 0, s["fires_on"], s["of"]))
    print()
    hs = out["validation"]["hand_sample"]
    print("hand sample     %d right of %d classified, accuracy %.3f, coverage %.3f"
          % (hs["right"], hs["classified"], hs["accuracy"], hs["coverage"]))
    for name, a in sorted(out["validation"]["audits"].items()):
        print("%-15s %d right of %d audited, precision %.3f "
              "(reweighted to the published rows %.3f)"
              % (name, a["right"], a["audited"],
                 a["precision_over_the_audited_rows"],
                 a["precision_reweighted_to_the_published_rows"] or 0))
        for step, v in sorted(a["by_deciding_signal"].items()):
            print("    %-26s %3d audited  %3d right  precision %.3f"
                  % (step, v["audited"], v["right"], v["precision"]))


if __name__ == "__main__":
    main()
