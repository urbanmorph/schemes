"""
Which schemes the Comptroller and Auditor General has audited.

AGENT-EDITABLE (PLAN.md §7). Reads data/cag/reports.json, data/registry.json,
data/classification.json and data/cag/join_labels.json; writes data/cag/join.json.
Never fetches.

Scope, and it is narrow on purpose. This establishes that an audit EXISTS on a scheme
and nothing else. No finding is read, quoted, summarised or characterised anywhere in
this file or its output: the CAG's conclusions are the CAG's to publish. What is added
is the pointer, which is not published as a pointer anywhere: this scheme has been
audited, here is the report number, the date it was tabled and the link.

The join, and why it is hard
----------------------------
2,260 of the 2,798 catalogued reports carry a `subject`, the title with its boilerplate
stripped. Running parse/match.py's generous matcher over those against the 5,478
registry entries produces 398 pairs across 145 reports. Every one of those 398 is hand
labelled in data/cag/join_labels.json, and 50 are sound. The raw join is therefore
12.6 per cent precise, which is not a number anything can be published on.

That is not a surprise and it is not the matcher failing at its job. probably_same is
built to be GENEROUS, because it exists to decide absence: claiming a scheme is missing
from a portal is an accusation and should require that even a generous matcher finds
nothing. Pointed at a corpus of audit titles rather than scheme names it behaves exactly
as designed and exactly wrongly, because an audit title is a sentence about government,
not the name of a programme. "PA on functioning of KARNATAKA STATE ROAD SAFETY
AUTHORITY" is not a scheme name; it collects 29 joins.

So this file does not adjust the matcher. It reads all 398 joins, measures what
separates a sound one from a wrong one, and publishes the surviving joins together with
the two wrong ones that survive.

What separates them, measured on the census of 398
--------------------------------------------------
Base rate: 0.126.

    the reason probably_same returned is name evidence,
        that is similarity, content-word containment or transliteration
                                                          P(sound) 0.512 over  82
    the reason is one of the two acronym rules             P(sound) 0.019 over 258
    the reason is the prefix rule                          P(sound) 0.052 over  58
    the report is a Performance audit                      P(sound) 0.211 over 228
    the report is a Compliance audit                       P(sound) 0.012 over 164
    the entry is a union budget line the classifier
        calls a budget head                                P(sound) 0.029 over  70
    ...and one it calls a scheme                           P(sound) 0.386 over  57
    the entry is a Central myScheme record                 P(sound) 0.201 over 134
    the entry is a state myScheme record                   P(sound) 0.058 over 208
    the entry is a state record for a different state
        from the one the report covers                     P(sound) 0.068 over 146
    the CAG subject has two content words or fewer         P(sound) 0.057 over  70
    every content word of the registry name appears
        in the CAG subject                                 P(sound) 0.680 over  50

The strongest single signal in that table is the last one, direction: the registry name
sitting wholly inside the audit subject, lift +0.634. That is the shape of a real join,
an audit title made of a scheme name plus report furniture. The opposite shape, the
subject sitting inside a longer registry name, is the shape of a component or an award
hanging off the audited thing.

Two things in that table are worth naming because they were guessed the other way round.

The length of the subject is NOT a signal. Subjects of 60 characters or fewer are 0.131
sound against 0.122 for longer ones, a lift of +0.009 over 398 pairs. The reason is that
both ends of the range are bad: the long tail is shouted titles and derived initialisms,
and the short tail is bare state names. Only the very short end discriminates, and it
discriminates negatively, which is what the two-content-word row measures.

The audit type is a strong signal and it is not circular. A Performance audit is a study
OF something and its title tends to name that something; a Compliance or Financial audit
is a sweep of a department's books and its title names the department. Every sound join
inside the name-evidence families is a Performance audit, 42 of 42.

The rule
--------
Ordered, and each clause carries what it costs. See RULE below. On the census it keeps
37 of the 398 joins, 35 of them sound: 94.6 per cent precision, counted and not
estimated, and 70.0 per cent recall against the hand labels. The two survivors that are
wrong are in KNOWN_ERRORS rather than patched out, and the 15 sound joins the rule drops
are in `recall_lost` for the same reason: a list that hides what it got wrong cannot be
audited.

Precision is bought with recall here on purpose. Saying "the CAG has audited this
scheme" beside a scheme name is a claim about a constitutional auditor's work programme,
and one wrong claim of that kind costs more than ten missing ones. The surviving list is
a floor.

Matcher defects
---------------
Seven holes in parse/match.py have been found by people reading joins on new corpora,
one per corpus and then some. Reading this one found six more. They are recorded in
MATCHER_DEFECTS with the exact pair and the exact reason string, and are NOT fixed
here. parse/match.py feeds published absence claims across the whole register, so a
change to it moves numbers on every page, and the evidence should be looked at before
that happens.

A note on the numbers printed above, which have moved
-----------------------------------------------------
Everything in this docstring down to here was measured on a 398-pair join. parse/match.py
was then changed, in commit "Four more matcher defects, one of them mine from this
morning", which is exactly the change the MATCHER_DEFECTS section above asked somebody
to make. The generous join it produces is now smaller and cleaner, and the consequence
is that data/cag/join_labels.json is STALE: a large share of its 398 labels no longer
correspond to any join, and a handful of new joins carry no label, among them the FAME
audit that the plural defect used to hide and two Mid Day Meals audits. The run prints
both counts every time. The counted precision and recall of the rule are therefore
measured on the labels that still apply, and the census claim they rest on is not true
again until those new joins are labelled. That is the one thing to fix before this page
is published, and it is a labelling job, not a code job.

The citizen test, and why the absent list is two lists
-----------------------------------------------------
The rule above finds the schemes the CAG has audited, and several of them myScheme does
not list. Publishing those under one heading would say the same thing about Samagra
Shiksha, a Rs 42,100 crore school education programme every parent in India has a
stake in, and about the Duty Drawback Scheme, which refunds customs duty to the
exporter who paid it. One of those is a gap in a citizen portal. The other is a fact
about how a state spends money, and calling it a gap would weaken the first claim by
sitting next to it.

So there is a second question, and it is answered the same way as the first: hand
labels as ground truth, every signal published with its measured strength, the
rejected signals published with the measurement that rejected them, accuracy counted
over an audited set rather than estimated, and the surviving errors named rather than
patched out. data/cag/citizen_labels.json carries 153 hand labels: a census of the
audited schemes plus a stratified sample of the 701 register rows myScheme does not
list, which is the population the test gets applied to. 60 are citizen schemes and 93
are budget lines, a base rate of 0.392, and 36 are marked borderline with the argument
the other way written on the row. The audited schemes are all hand labelled, so the
PUBLISHED split is the hand labels, and the rule's measured accuracy is what says those
labels are not arbitrary: a mechanical test reconstructs them from published evidence
92.8 per cent of the time. Where the two disagree the row says so. If the join above
ever produces an audited scheme with no citizen label, the run prints that too.

THE LABEL, and it is deliberately about the beneficiary and not about the portal.
    citizen_scheme  the benefit reaches an identified person or household, or a group
                    of individuals such as a self-help group: cash, an in-kind good, a
                    scholarship, a pension, an insurance cover, a subsidy on something
                    they buy, a treatment, a house, a connection, a wage, a training
                    place, a loan or a fee waiver. Somebody could produce the list of
                    who received it.
    budget_line     the recipient of record is a government, a public body, an
                    institution, a firm acting as a firm, an asset or a work. Citizens
                    benefit from what it buys, often enormously, but no individual is a
                    beneficiary of record and no list of individuals exists.
A budget_line label says nothing against the spending. Roads, courts, research and
rolling stock are what a state is for. It says only that a portal built for citizens to
look schemes up is not where you would look for them.

THE INTUITIVE TEST DOES NOT WORK, AND THAT IS THE FIRST FINDING. "Could a citizen apply
for it" reads like the right question. Measured on the 20 audited schemes as a census,
P(citizen scheme | an application exists) is 0.667 over 9 against 0.727 over 11 where
none does, a lift of -0.061. No signal, and slightly the wrong sign. The reason is
plain once counted: the schemes that reach the most people, PMAY-Gramin, Ayushman
Bharat and Jal Jeevan Mission, select their beneficiaries from a list rather than take
applications, while the Duty Drawback Scheme and the Ex-Servicemen Contributory Health
Scheme both have a form to fill in. The test is also not computable for the 701 rows
myScheme does not list, which is the population that matters.

WHAT ACTUALLY DISCRIMINATES, measured on the 153 hand labels against a base rate of
0.392. Each signal alone, on the rows where it fires:

    myScheme's own beneficiary tag says a person       P 1.000 over  11
    a person or household named in the name            P 0.875 over  24
    a benefit phrase in the name                       P 0.865 over  37
    DBT Bharat lists it                                P 0.820 over  50
    an asset or works word in the name                 P 0.115 over  26
    a research or capacity word in the name            P 0.107 over  28
    the sector is Business, Science and IT,
        Transport or Banking                           P 0.053 over  38
    the name says the money goes to a body             P 0.000 over   4
    an employer obligation                             P 0.000 over   3

Two of those are worth pausing on. The FIRST is myScheme's own targetBeneficiaries
tag, carried into the register by parse/checks.py. It is not "is this on myScheme",
which would be circular for a question about myScheme's gaps and is rejected below on
exactly that ground. It is what myScheme SAYS about a row it does list, and it points
both ways: it tags AMRUT's beneficiaries State Government and Government Organisation,
and the Export Promotion Capital Goods Scheme's Business Entity, so two of the audited
schemes myScheme does list fail this test. A test that agreed with myScheme
every time would be a proxy for myScheme and worth nothing. The SECOND is DBT Bharat.
It is the government's own statement that money reaches identified individuals, and at
0.820 over 50 rows it is strong but not clean: it also lists grants to bodies that pay
a stipend inside them, which is how the VV Giri National Labour Institute and the
Rajiv Gandhi National Institute of Youth Development reach it.

THE ONE EXCLUSION, AND IT IS BORROWED RATHER THAN INVENTED. An employer obligation is
not a citizen scheme: the government pays it as an employer to its own serving or
retired staff and their families. parse/classify_tamilnadu.py established that line
over 829 hand labels and this register already publishes it, so applying it at the
union is consistency rather than a new judgement. It is what decides the Ex-Servicemen
Contributory Health Scheme, and it is the closest call in this file. An ex-serviceman
is a person and does receive treatment. What settles it is myScheme's own catalogue:
the portal lists neither ECHS nor CGHS, the two contributory health schemes that come
with a government pension, and all six of its central records for ex-servicemen are
discretionary grants from the Armed Forces Flag Day Fund and the Raksha Mantri's
Ex-Servicemen Welfare Fund, one of them explicitly for NON-pensioner ex-servicemen.
myScheme draws the line in the same place. A reader who disagrees has a
real argument and it is recorded in `contested` rather than argued away.

THE OPERATING POINT IS THE ACCURACY-MAXIMISING ONE, and that is a departure from the
rest of this repository which should be stated. parse/classify.py, the state
classifiers and the join rule above all buy precision with recall, because each of them
decides an ABSENCE CLAIM and one wrong accusation costs more than ten missing ones.
This test decides no absence. Both sides of the split are published, both under their
own heading, and a row put on the wrong side is a miscategorised entry rather than an
accusation. The cost is therefore symmetric, and the threshold is set where accuracy
peaks:

    threshold 1   62 called citizen schemes, 8 wrong    accuracy 0.908
    threshold 2   59 called citizen schemes, 5 wrong    accuracy 0.928
    threshold 3   53 called citizen schemes, 3 wrong    accuracy 0.915

Threshold 2. On the 153 labels: precision 0.915, recall 0.900, accuracy 0.928, all
counted. On the audited schemes, which are a census of what actually gets published, it
disagrees with the hand label twice. One is Tea Board, which is already a known error of
the join rule above and already removed from the absent list before this test runs. The
other is Rashtriya Krishi Vikas Yojna, a brand name with no benefit word and no
beneficiary in it, whose components pay farm mechanisation subsidies to identified
farmers; the hand label is published and the disagreement is printed on the row.

THE ELEVEN ERRORS have a shape and it is the same one parse/sector.py found: a brand
name says nothing. All six of the schemes the rule wrongly calls budget lines are brands
or acronyms carrying no benefit word and no beneficiary: SBM-Grameen, VB-G-RAM-G, Skill
India Programme, Rashtriya Krishi Vikas Yojna, the Legal Aid Defense Counsel System, and
Pradhan Mantri Krishi Sinchai Yojna, whose only readable word is an irrigation one that
scores against it. Four of the five in the other direction are rows DBT Bharat lists for
a payment made inside a grant to an institution; the fifth, Schemes for Safety of Women,
names a beneficiary class in a line that buys forensic laboratories and cyber crime
systems. Both sets are in CITIZEN_KNOWN_ERRORS.

THE ABSENT LIST, SPLIT. The membership moves whenever the join above moves, so the two
lists are computed rather than typed, and the run prints them. As this file is written
the first list is Samagra Shiksha, the National Mission for a Green India, FAME and
Rashtriya Krishi Vikas Yojna: programmes that pay identified people, audited by the CAG,
and not on the portal built for citizens to find schemes. The second is the Duty
Drawback Scheme, whose claimant is a firm recovering duty it paid; the Ex-Servicemen
Contributory Health Scheme, an employer obligation; MPLADS, whose unit of spending is a
work in a constituency with no list of individual beneficiaries; and Pradhan Mantri
Swasthya Suraksha Yojana, which builds and upgrades medical colleges. Most of both lists
is marked borderline in the labels, and the closest calls are named in `contested` with
the argument both ways, because a distinction this close should be published with its
arguments rather than with its conclusion alone.
"""

import argparse
import collections
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "collect"))
from common import ROOT, utcnow, write_json  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# Loaded by path, the way the rest of parse/ loads it, so nothing depends on sys.path
# order. probably_same returns a TUPLE (bool, why) and a tuple is always truthy, so the
# [0] in joins() is load bearing: without it every candidate pair matches.
_m = _load("scheme_match", os.path.join(HERE, "match.py"))
acronyms, norm, probably_same = _m.acronyms, _m.norm, _m.probably_same
skeletons, tokens = _m.skeletons, _m.tokens


# ---------------------------------------------------------------------------
# Producing the joins.
# ---------------------------------------------------------------------------
# 2,260 subjects against 5,476 distinct names is 12.4 million probably_same calls and
# about five minutes of CPU. The blocking index below cuts that to 90 seconds by only
# comparing pairs that share a key, where the keys are chosen to be a superset of
# everything probably_same can match on:
#
#   content tokens          covers the similarity and containment rules, both of which
#                           need at least one shared content word to clear their floors
#   consonant skeletons     covers the transliteration rule
#   acronyms, plus every
#     substring of length 4
#     or more of each        covers the acronym match rule and the acronym containment
#                           rule, whose two sides need not be equal
#   the first 8 characters
#     of the normalised name covers the prefix rule, which can fire on a name whose
#                           content tokens are all stop words
#
# Verified equal to the brute force product on this snapshot: same 398 pairs, no
# additions and no losses. If a new rule is ever added to probably_same this index has
# to grow with it, so the check is worth rerunning rather than trusting.

def _keys(s):
    k = set(tokens(s)) | skeletons(s)
    for a in acronyms(s):
        k.add(a)
        for length in range(4, len(a) + 1):
            for i in range(0, len(a) - length + 1):
                k.add(a[i:i + length])
    n = norm(s)
    if len(n) >= 8:
        k.add("^" + n[:8])
    return k


def joins(reports, names):
    """Every (report, registry entry) pair the generous matcher accepts. Sorted."""
    index = collections.defaultdict(set)
    for n in names:
        for k in _keys(n):
            index[k].add(n)
    out = []
    for r in reports:
        candidates = set()
        for k in _keys(r["subject"]):
            candidates |= index.get(k, set())
        for n in sorted(candidates):
            ok, why = probably_same(r["subject"], n)
            if ok:
                out.append({"cag_id": r["id"], "registry_name": n, "why": why})
    out.sort(key=lambda x: (x["cag_id"], x["registry_name"]))
    return out


# ---------------------------------------------------------------------------
# Features. Everything the rule reads, computed once per pair.
# ---------------------------------------------------------------------------
# Words that a longer scheme name may add to a shorter one without becoming a different
# scheme. "Green India Mission" and "National Mission for a Green India" are the same
# programme and the only word between them is "national". Kept deliberately short and
# deliberately generic: add a substantive word here and the register starts claiming
# that an audit of a parent covered its children.
GENERIC_EXTRA = {"national", "state", "central", "scheme", "schemes", "mission",
                 "programme", "program", "yojana", "yojna", "abhiyan", "india",
                 "indian", "bharat", "new", "revised"}

# Words that subordinate what precedes them. A subject that reads "Skill Development
# under Pradhan Mantri Kaushal Vikas Yojana" names PMKVY as the scheme and skill
# development as its purpose, so the prefix rule must not read the purpose as the name.
SUBORDINATORS = {"under", "through", "within", "as"}

STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
          "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
          "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
          "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
          "Uttarakhand", "West Bengal", "Lakshadweep", "Chandigarh", "Puducherry",
          "Pondicherry", "Daman", "Diu"]


def _family(why):
    """Which of probably_same's rules fired, as a family name."""
    if why.startswith("similarity"):
        return "similarity"
    if why.startswith("all "):
        return "containment"
    if why.startswith("one name begins"):
        return "prefix"
    if why.startswith("transliteration"):
        return "skeleton"
    if why.startswith("acronym containment"):
        return "acronym containment"
    if why.startswith("acronym match"):
        return "acronym match"
    return "other"


def _state_in_name(name):
    for s in STATES:
        if re.search(r"[-,:(]\s*" + re.escape(s) + r"\b", name, re.I):
            return s
    return None


def features(report, name, why, verdict, ms_level, ms_state):
    subject = report["subject"]
    ts, tn = set(tokens(subject)), set(tokens(name))
    ss, sn = skeletons(subject), skeletons(name)
    ns, nn = norm(subject), norm(name)
    sim = re.search(r"similarity ([\d.]+)", why)
    skel = re.findall(r"'([a-z0-9]+)'", why) if why.startswith("transliteration") else []
    reg_is_prefix = (len(nn) >= 8 and ns.startswith(nn)
                     and ns[len(nn):len(nn) + 1] in ("", " ") and len(tn) >= 2)
    rest = ns[len(nn):].strip().split(" ")[0] if reg_is_prefix else ""
    return {
        "family": _family(why),
        "audit_type": report.get("audit_type"),
        "government": report.get("government"),
        "verdict": verdict,
        "myscheme_level": ms_level,
        "myscheme_state": ms_state,
        "state_in_name": _state_in_name(name),
        "subject_content_words": len(ts),
        "name_content_words": len(tn),
        "subject_chars": len(subject),
        "similarity": float(sim.group(1)) if sim else 0.0,
        # Direction. The registry name sitting wholly inside the subject is the shape of
        # a real join: the audit title is the scheme name plus report furniture. The
        # subject sitting inside a longer registry name is the shape of a false one: the
        # entry is a component, an award or an internship hanging off the audited thing.
        "name_inside_subject": bool(tn) and tn <= ts,
        "subject_inside_name_generically": bool(ts) and ts <= tn and (tn - ts) <= GENERIC_EXTRA,
        "names_equal": ns == nn,
        "skeletons_inside_subject": (bool(sn) and sn <= ss
                                     and len([k for k in sn if len(k) >= 3]) >= 3),
        "skeleton_evidence_thin": (bool(skel)
                                   and (len(skel) < 3 or any(len(k) < 3 for k in skel))),
        "registry_name_is_prefix": reg_is_prefix,
        "prefix_is_subordinated": rest in SUBORDINATORS,
    }


# ---------------------------------------------------------------------------
# The rule.
# ---------------------------------------------------------------------------
RULE = [
    {"clause": "the matcher's reason is name evidence, not an acronym",
     "detail": ("similarity, content-word containment or transliteration; or the prefix "
                "rule where the REGISTRY name is the prefix of the subject rather than "
                "the other way round, and is not subordinated by a following under, "
                "through or within"),
     "measured": ("the two acronym rules are P(sound) 0.019 over 258 pairs and the "
                  "prefix rule as probably_same applies it is 0.052 over 58. Taking the "
                  "name-evidence families alone lifts precision from 0.126 to 0.512 and "
                  "costs 8 sound joins, of which the PAHAL and UDAN compliance audits "
                  "are the two real losses.")},
    {"clause": "the report is a Performance audit",
     "detail": ("a Performance audit is a study OF something and its title names that "
                "something. A Compliance or Financial audit is a sweep of a department "
                "and its title names the department."),
     "measured": ("P(sound) 0.211 over 228 against 0.012 over 164 for Compliance. "
                  "Inside the name-evidence families every one of the 42 sound joins is "
                  "a Performance audit and all 10 non-Performance joins are wrong.")},
    {"clause": ("the registry entry is not a union budget line the classifier calls "
                "a budget head"),
     "detail": ("data/classification.json, keyed on the budget name the registry merged "
                "from. This is the schemes-versus-budget-heads test that made "
                "Karnataka's 621 and Andhra Pradesh's 552 unpublishable, arriving here "
                "as National Highways Authority of India, Estates Management, Projects "
                "of the Air Force, Electrification Projects and Recapitalization of "
                "Public Sector Banks."),
     "measured": ("P(sound) 0.029 over the 70 pairs whose entry is a classified budget "
                  "head. It costs 2 sound joins, Border Area Development Programme and "
                  "Modernisation of Police Forces, both of which the classifier itself "
                  "gets wrong at score 0.")},
    {"clause": "the two names agree in the right direction",
     "detail": ("every content word of the REGISTRY name appears in the subject; or the "
                "names are equal once normalised; or similarity is 0.78 or better; or "
                "the registry name's consonant skeletons are inside the subject's with "
                "at least three skeletons of three characters or more; or the subject's "
                "words are all inside the registry name and the only extra words are "
                "generic ones such as national or mission."),
     "measured": ("takes precision from 0.667 to 0.800 inside the earlier clauses. It "
                  "is the clause that rejects a component wearing its parent's name: "
                  "the EPFO internship scheme under an audit of the EPFO, one "
                  "displaced-families line under an audit of the whole Prime Minister's "
                  "Development Package, Samagra Shiksha's uniform intervention under an "
                  "audit of Samagra Shiksha.")},
    {"clause": "a state myScheme record must belong to the government the report covers",
     "detail": ("a record myScheme tags State or State/ UT is that state's listing. "
                "Where the report is a state report and the record is another state's, "
                "the two are different schemes that share a generic name."),
     "measured": ("P(sound) 0.068 over the 146 pairs where the states disagree. This is "
                  "the most expensive clause in the rule: it removes 6 wrong joins, the "
                  "three Chhattisgarh social security pension joins among them, and "
                  "costs 7 sound ones, because myScheme lists two national schemes, "
                  "ICDS and Deendayal Upadhyay Gram Jyoti Yojana, only under a single "
                  "state's page. Both losses are named in recall_lost.")},
]


KNOWN_ERRORS = [
    {"cag_id": 2240,
     "subject": "Role of Tea Board in Tea Development",
     "registry_name": "Tea Board",
     "why_it_survives": ("the Tea Board is a statutory body and the registry row is a "
                         "grant to it. The classifier calls that row a scheme at score "
                         "3, so the budget-head clause does not catch it, and the "
                         "audit's own subject contains both its words."),
     "what_it_costs": "one body listed as an audited scheme"},
    {"cag_id": 55961,
     "subject": "Pradhan Mantri Ujjwala Yojana, Ministry of Petroleum and Natural Gas",
     "registry_name": "Pradhan Mantri Ujjwala Yojana 2.0",
     "why_it_survives": ("PMUY 2.0 is the 2021 second phase and the audit was tabled in "
                         "December 2019, so the audit cannot have covered it. Nothing "
                         "in either name says so: normalisation drops the 2 and the 0 "
                         "as too short to be content words, leaving two identical "
                         "names. Only the dates separate them and the rule does not "
                         "read dates."),
     "what_it_costs": ("one scheme shown as audited two years before it existed. The "
                       "same report's join to Pradhan Mantri Ujjwala Yojana itself is "
                       "sound, so the scheme is not wrongly added to the list, only a "
                       "second row of it.")},
]


# Holes found in parse/match.py by reading this corpus. NOT fixed here: probably_same
# decides absence claims across the whole register, so changing it moves published
# numbers on every page, and each of these should be looked at first. Every entry is a
# real pair from this snapshot with the reason string probably_same actually returned.
MATCHER_DEFECTS = [
    {"defect": "acronym containment accepts a derived initialism on the unwritten side",
     "where": "probably_same, the acronym containment rule",
     "what": ("the rule requires one side to be an acronym somebody wrote, `x in wa or "
              "y in wb`. It does not require the OTHER side to be one, so a written "
              "acronym matches any long initialism that happens to contain those four "
              "letters anywhere. Initialisms derived from audit titles are long, and "
              "audit titles are sentences, so the collisions are constant: this rule "
              "produced 153 of the 398 joins and 150 of those are wrong, P(sound) "
              "0.020."),
     "examples": [
         {"a": "Storage Management and Movement of Food Grains in Food Coporation of India",
          "b": ("Sub-Mission on Agricultural Mechanization (SMAM) for Custom "
               "Hiring Centres / Big Farmers - Uttarakhand"),
          "returned": "acronym containment: smamofgifcoi / smam"},
         {"a": ("Public Private Partnership Project at Chhatrapati Shivaji "
                "International Airport, Mumbai"),
          "b": ("Finance Assistant to PACS for Computerization and Integration of "
               "PACS through Core Banking System with District Cooperative Banks"),
          "returned": "acronym containment: ppppacsiam / pacs"},
         {"a": ("of Comptroller and Auditor General of India: Composite Audit "
                "Report - Civil of UT of Jammu and Kashmir for the period ended "
                "March 2022"),
          "b": "ICAR Emeritus Professor",
          "returned": "acronym containment: ocaagoicarcouojakftpem2 / icar"},
         {"a": ("Deendayal Upadhyaya Gram Jyoti Yojana (DDUGJY)/ Pradhan Mantri "
                "Sahaj Bijli Har Ghar Yojana (SAUBHAGYA), Government of "
                "Karnataka."),
          "b": "Utility Based Handicrafts Award",
          "returned": "acronym containment: saubhagya / ubha"},
     ],
     "note": ("the legitimate case the rule exists for, DAY-NRLM against its expansion, "
              "has the same shape: one written acronym inside one derived initialism. "
              "What separates them is that nrlm is the TAIL of daynrlm and covers most "
              "of it, while smam is four letters of twelve. A position and coverage "
              "test would keep DAY-NRLM and reject all four pairs above, but it is not "
              "made here.")},

    {"defect": "the shouted-title guard is all or nothing",
     "where": "acronyms and written_acronyms, the `shouted` branch",
     "what": ("the guard stands the caps rule down only when the WHOLE string is "
              "capitals. A title that quotes a name in capitals inside ordinary text "
              "defeats it, and every capitalised word of that name becomes an acronym. "
              "One report did this 29 times."),
     "examples": [
         {"a": "PA on functioning of KARNATAKA STATE ROAD SAFETY AUTHORITY",
          "b": "National Highways Authority of India",
          "returned": "acronym match: authority"},
         {"a": "PA on functioning of KARNATAKA STATE ROAD SAFETY AUTHORITY",
          "b": "Santwana Scheme - Karnataka",
          "returned": "acronym match: karnataka"},
     ],
     "note": ("STATE is already in NOT_ACRONYMS, which is why the list catches one of "
              "the five words and not the other four. A rule that measured the "
              "proportion of shouted words in the string, rather than requiring all of "
              "them, would close this without a longer list.")},

    {"defect": "ordinary English words shouted by a scheme name are still read as acronyms",
     "where": "NOT_ACRONYMS",
     "what": ("the same hole the word `sector` opened, in two more instances found on "
              "this corpus. `power` collects 36 joins and `phase` collects 4."),
     "examples": [
         {"a": ("Expansion and Utilization of Power Equipment Manufacturing "
                "Capacity in BHEL of"),
          "b": "SERB - POWER Fellowship",
          "returned": "acronym match: power"},
         {"a": ("Planning and Implementation of Phase III Expansion Project of "
                "Mangalore Refinery and Petrochemicals Limited"),
          "b": "Swachh Bharat Mission – Grameen PHASE I",
          "returned": "acronym match: phase"},
     ],
     "note": ("this one bites inside data/registry.json already, not only here. The "
              "registry merged the budget line `Solar Power (Grid)` into `SERB - POWER "
              "Fellowship`, `Nuclear Power Projects` into `SERB - POWER Research "
              "Grants`, and `e-Courts Phase II` into `Swachh Bharat Mission – Grameen "
              "PHASE I`, so a rupee figure is already attached to the wrong scheme "
              "name.")},

    {"defect": "the prefix rule fires on a bare place name",
     "where": "probably_same, the `one name begins with the whole of the other` rule",
     "what": ("the rule asks only that the shorter name be 8 characters or more. A "
              "state name clears that and prefixes every scheme that state has "
              "registered. Two subjects that reduce to a state name produced 49 joins "
              "between them."),
     "examples": [
         {"a": "Uttarakhand", "b": "Uttarakhand Oon Yojana",
          "returned": "one name begins with the whole of the other"},
         {"a": "West Bengal", "b": "West Bengal Student Credit Card Scheme",
          "returned": "one name begins with the whole of the other"},
     ],
     "note": ("the containment rule next to it already demands two or three content "
              "words. The prefix rule demands none, and 8 characters is not the same "
              "bar.")},

    {"defect": "two-character skeletons count as transliteration evidence",
     "where": "probably_same, the skeleton rule",
     "what": ("the rule needs two or more matching skeletons but sets no floor on their "
              "length, and a two-letter consonant skeleton carries almost no "
              "information."),
     "examples": [
         {"a": "MEIS and SEIS", "b": "Scheme for SSI / MSI Sector (PIPDIC)",
          "returned": "transliteration variant: ['ms', 'ss']"},
     ],
     "note": "the module's own comment says a skeleton is lossy; it does not act on it."},

    {"defect": "a plural defeats every rule, including the ones that decide absence",
     "where": "tokens and skeleton, which do no singularisation",
     "what": ("`vehicles` and `vehicle` are different tokens and different skeletons, so "
              "content-word containment fails, the skeleton rule fails, and similarity "
              "carries the pair alone. This is a FALSE NEGATIVE and therefore the "
              "expensive direction: probably_same exists to decide absence, and a "
              "missed match is a claim that a portal omits something."),
     "examples": [
         {"a": ("Scheme for Faster Adoption and Manufacturing of (Hybrid &) "
                "Electric Vehicles"),
          "b": ("Scheme for Faster Adoption and Manufacturing of (Hybrid and) "
               "Electric Vehicle in India - (FAME - India)."),
          "returned": "no match"},
         {"a": "Mid Day Meal", "b": "Mid Day Meals Scheme",
          "returned": "no match"},
     ],
     "note": ("FAME is one of the two absences this register has verified by hand, and "
              "the CAG audited it: report 125966. The audit and the scheme do not join, "
              "and the only difference between the shared halves of the two names is a "
              "trailing s. Folding a plural is the single cheapest change available to "
              "the matcher and 15 pairs on this corpus turn on it.")},
]


REJECTED_SIGNALS = [
    {"signal": "the length of the CAG subject",
     "measured": ("P(sound) 0.131 for subjects of 60 characters or fewer against 0.122 "
                  "for longer ones, a lift of +0.009 over 398 pairs. Both ends of the "
                  "range are bad and they cancel: the long tail is shouted titles and "
                  "derived initialisms, the short tail is bare state names."),
     "why_not": ("no signal at the threshold anyone would pick. The short end alone is "
                 "a signal and a negative one, which the two-content-word measurement "
                 "records, and the rule picks it up through the containment and "
                 "prefix clauses rather than through a length cut.")},
    {"signal": "the report covers the Union rather than a state",
     "measured": "P(sound) 0.085 over 188 against 0.162 over 210, lift -0.077",
     "why_not": ("confounded. The union reports in this corpus include the ministry "
                 "sweeps whose titles name a ministry rather than a scheme, so the "
                 "signal is really the audit type wearing a different hat, and the "
                 "audit type is measured directly.")},
    {"signal": "the registry entry carries a myScheme source at all",
     "measured": "P(sound) 0.096 over 271 against 0.189 over 127 for budget-sourced rows",
     "why_not": ("circular for the question this file exists to answer. The finding "
                 "worth having is which audited schemes are ABSENT from myScheme, and "
                 "scoring myScheme presence would push down exactly the rows the answer "
                 "is made of. The same reasoning is set out in "
                 "parse/classify_andhra.py's why_not_myscheme.")},
]


def keep(f):
    """The rule. Returns True for a join worth publishing."""
    fam_ok = f["family"] in ("similarity", "containment", "skeleton") or (
        f["family"] == "prefix" and f["registry_name_is_prefix"]
        and not f["prefix_is_subordinated"])
    if not fam_ok:
        return False
    if f["audit_type"] != "Performance":
        return False
    if f["verdict"] == "budget head":
        return False
    if f["skeleton_evidence_thin"]:
        return False
    if not (f["name_inside_subject"] or f["names_equal"] or f["similarity"] >= 0.78
            or f["skeletons_inside_subject"] or f["subject_inside_name_generically"]
            or (f["family"] == "prefix" and f["registry_name_is_prefix"])):
        return False
    if f["myscheme_level"] in ("State", "State/ UT"):
        st, gov = f["myscheme_state"], (f["government"] or "")
        if not (st and st[:5].lower() in gov.lower()):
            return False
    return True


# ---------------------------------------------------------------------------
# The citizen test. Does the money reach an identified person or household?
# ---------------------------------------------------------------------------
# Ground truth is data/cag/citizen_labels.json, 153 hand labels. Everything below is
# scored against those and nothing below is tuned on anything else. See the docstring
# for the measurements; the strings in CITIZEN_RULE carry them into the output.
#
# Every pattern here is a phrase that names a benefit, a beneficiary, an asset or a
# body, and never a bare common word. That rule is parse/sector.py's, learned the hard
# way: an unbounded `port` matched "Sportspersons" and "Export" on the first pass of
# this file and cost two rows before the word boundaries went in.

CITIZEN_PERSON = re.compile(
    r"\b(students?|scholars?|farmers?|child|children|women|woman|girls?|youth|patients?"
    r"|famil(?:y|ies)|households?|labour|labourers?|workers?|sportspersons?|servicemen"
    r"|beneficiar\w*|candidates?|interns?|widows?|victims?|divyangjan|differently abled"
    r"|handicapped|tribal groups?|weavers?|artisans?|mothers?|senior citizens?"
    r"|employees?)\b", re.I)

CITIZEN_BENEFIT = re.compile(
    r"\b(scholarships?|fellowships?|stipends?|pensions?|cash awards?|cash transfers?"
    r"|compensation|rehabilitation|insurance|bima|awaas|awas|ujjwala|wages?"
    r"|employment guarantee|internships?|assistance|subsidy|subsidies|incentives?"
    r"|annuity|free)\b", re.I)

CITIZEN_ASSET = re.compile(
    r"\b(works|rolling stock|corridors?|infrastructure|buildings?|projects?|grid"
    r"|test bed|networks?|yard|metro|roads?|ports?|refinery|habitats?|housing"
    r"|non-residential|electrification|sinchai|construction|stock)\b", re.I)

CITIZEN_CAPACITY = re.compile(
    r"\b(research|census|capacity|awareness|publicity|strengthening|modernization"
    r"|modernisation|management|digital|survey|consultancy|enforcement|mausam"
    r"|technology|computeris\w*)\b", re.I)

# "Assistance to National Sports Federations" is a grant to a body that happens to
# carry a payment inside it. The pattern needs the preposition, because "Rehabilitation
# Assistance under the Scheme of Rehabilitation of Bonded Labour" must not fire.
_A_BODY = (r"(?:boards?|councils?|institutes?|institutions?|federations?|agenc(?:y|ies)"
           r"|centres?|societ\w*|states?|schools?|colleges?|universit\w*|enterprises?"
           r"|industr\w*|providers?|companies|corporations?|kendras?|academ\w*"
           r"|authorit\w*|commissions?|departments?|ministr\w*|organisations?)")
CITIZEN_TO_A_BODY = re.compile(
    r"\b(?:assistance|grants?|support|compensation|payments?|reimbursement) to\b"
    r"[^,]{0,44}\b" + _A_BODY + r"\b", re.I)

CITIZEN_EMPLOYER = re.compile(
    r"\b(ex-? ?servicemen contributory health|central government health"
    r"|human resource management|joint staff|government servants?)\b", re.I)

# Only ever used to REJECT. A body word loose in a name carries no signal, because
# board, centre, institute and school sit inside the names of schemes that pay people.
CITIZEN_BODY_ANYWHERE = re.compile(r"\b" + _A_BODY + r"\b", re.I)

# Outcome Budget indicator text that names a person as the unit of the target. Used only
# to reject: the framework fires on too few register rows and its indicator text in
# data/outcome is the first line of a wrapped cell, so the unit is often the part that
# was cut off.
CITIZEN_PERSON_UNIT = re.compile(
    r"\b(students?|children|child|beneficiar\w*|farmers?|women|girls?|youth|patients?"
    r"|famil(?:y|ies)|households?|persons?|workers?|labour|candidates?|trainees?"
    r"|entrepreneurs?|artisans?|weavers?|mothers?|citizens?|people|scholars?)\b", re.I)

# The four myScheme sectors whose contents are overwhelmingly firms and assets. Read as
# a sector name and not as a guess: P(citizen scheme) 0.053 over the 38 labelled rows in
# them, against 0.504 over the 115 outside. myScheme's own category is used where it
# lists the row and parse/sector.py's where it does not.
CITIZEN_FIRM_SECTORS = {"Business & Entrepreneurship", "Science, IT & Communications",
                        "Transport & Infrastructure",
                        "Banking,Financial Services and Insurance"}

# parse/checks.py's PERSON_BENEFICIARIES, plus "All". checks.py's audience field reads
# "All" as an institution because it is not in its person list, which makes Pradhan
# Mantri Suraksha Bima Yojana, an accident cover on a person's bank account, read as an
# institution scheme. That is a defect in that field rather than in the scheme, it is
# fixed here and only here, and parse/checks.py is deliberately not edited from this
# file because its audience counts are published on their own page.
CITIZEN_PERSON_BENEFICIARIES = {
    "Individual", "Family", "Artists", "Sportsperson", "Journalist", "Visitor",
    "Self Help Groups (SHGS)", "Joint Liability Groups (JLGS)", "All",
}

CITIZEN_WEIGHTS = {
    "myscheme_tags_a_person": 3,
    "a_person_or_household_in_the_name": 3,
    "listed_by_dbt_bharat": 3,
    "a_benefit_phrase_in_the_name": 2,
    "an_asset_or_works_word_in_the_name": -2,
    "a_research_or_capacity_word_in_the_name": -2,
    "myscheme_tags_only_an_institution": -3,
    "a_firm_or_asset_sector": -1,
}
CITIZEN_THRESHOLD = 2


def citizen_features(name, entry, sector, ms_beneficiaries):
    """Everything the citizen test reads, computed once per register entry."""
    ms = None
    if ms_beneficiaries:
        ms = ("person" if any(b in CITIZEN_PERSON_BENEFICIARIES for b in ms_beneficiaries)
              else "institution")
    return {
        "myscheme_tags_a_person": ms == "person",
        "myscheme_tags_only_an_institution": ms == "institution",
        "listed_by_dbt_bharat": "dbt" in entry["sources"],
        "a_person_or_household_in_the_name": bool(CITIZEN_PERSON.search(name)),
        "a_benefit_phrase_in_the_name": bool(CITIZEN_BENEFIT.search(name)),
        "an_asset_or_works_word_in_the_name": bool(CITIZEN_ASSET.search(name)),
        "a_research_or_capacity_word_in_the_name": bool(CITIZEN_CAPACITY.search(name)),
        "a_firm_or_asset_sector": sector in CITIZEN_FIRM_SECTORS,
        "the_name_says_the_money_goes_to_a_body": bool(CITIZEN_TO_A_BODY.search(name)),
        "an_employer_obligation": bool(CITIZEN_EMPLOYER.search(name)),
        "sector": sector,
        "myscheme_beneficiaries": sorted(ms_beneficiaries or []),
    }


CITIZEN_EVIDENCE_TEXT = {
    "myscheme_tags_a_person": "myScheme's own record tags a person or household beneficiary",
    "myscheme_tags_only_an_institution": ("myScheme's own record tags only an "
                                          "institutional beneficiary"),
    "listed_by_dbt_bharat": "DBT Bharat lists it, so the government says money reaches individuals",
    "a_person_or_household_in_the_name": "a person or household named in the name",
    "a_benefit_phrase_in_the_name": "a benefit phrase in the name",
    "an_asset_or_works_word_in_the_name": "an asset or works word in the name",
    "a_research_or_capacity_word_in_the_name": "a research or capacity word in the name",
    "a_firm_or_asset_sector": "the sector is one myScheme fills with firms and assets",
}


def citizen_score(f):
    return sum(w for k, w in CITIZEN_WEIGHTS.items() if f[k])


def citizen_evidence(f):
    """The arithmetic, in the order the weights are declared. Deterministic."""
    out = []
    for k in sorted(CITIZEN_WEIGHTS, key=lambda k: (-CITIZEN_WEIGHTS[k], k)):
        if f[k]:
            w = CITIZEN_WEIGHTS[k]
            out.append([("+" if w > 0 else "") + str(w), CITIZEN_EVIDENCE_TEXT[k]])
    if f["an_employer_obligation"]:
        out.append(["veto", "an employer obligation to the government's own staff"])
    if f["the_name_says_the_money_goes_to_a_body"]:
        out.append(["veto", "the name says the money goes to a body"])
    return out


def citizen_verdict(f):
    """True where the benefit reaches an identified person or household."""
    if f["an_employer_obligation"]:
        return False
    if f["the_name_says_the_money_goes_to_a_body"]:
        return False
    return citizen_score(f) >= CITIZEN_THRESHOLD


CITIZEN_RULE = [
    {"clause": "an employer obligation is never a citizen scheme",
     "detail": ("the government pays it as an employer to its own serving or retired "
                "staff and their families. Not invented here: "
                "parse/classify_tamilnadu.py established this over 829 hand labels and "
                "the register already publishes it, so applying it at the union is "
                "consistency rather than a fresh judgement."),
     "measured": ("P(citizen scheme) 0.000 over the 3 labelled rows it fires on, which "
                  "is a small number and is stated as one. The weight of the evidence "
                  "is Tamil Nadu's 829 labels and myScheme's own catalogue: the portal "
                  "lists neither ECHS nor CGHS, and all six of its central records for "
                  "ex-servicemen are discretionary grants from the Armed Forces Flag "
                  "Day Fund and the Raksha Mantri's Ex-Servicemen Welfare Fund, one of "
                  "them explicitly for non-pensioner ex-servicemen.")},
    {"clause": "a grant to a body is not a benefit to a person, even when a payment sits inside it",
     "detail": ("the name has to say so with a preposition: assistance, grants, "
                "support, compensation, payments or reimbursement TO a board, council, "
                "institute, federation, agency, state, school, company or industry."),
     "measured": ("P(citizen scheme) 0.000 over 4. It is what separates Assistance to "
                  "National Sports Federations and Grants to VV Giri National Labour "
                  "Institute, both of which DBT Bharat lists because a stipend is paid "
                  "inside them, from the schemes that pay a person directly.")},
    {"clause": "otherwise the signals score and the total decides",
     "detail": ("weights are the measurements rounded, not a feeling: the three signals "
                "above 0.82 are worth 3, the benefit phrase at 0.865 is worth 2 because "
                "it overlaps the beneficiary word, the two name signals near 0.11 are "
                "worth -2, and the sector at 0.053 is worth -1 because it fires on more "
                "rows than any of them and should not decide a row alone."),
     "measured": ("threshold 2. On the 153 hand labels precision 0.915, recall 0.900, "
                  "accuracy 0.928, counted and not estimated.")},
    {"clause": "the threshold is the accuracy-maximising one, not the precision-buying one",
     "detail": ("every other classifier in this repository trades recall away for "
                "precision, because each of them decides an absence claim and one wrong "
                "accusation costs more than ten missing ones. This test decides no "
                "absence: both sides of the split are published, each under its own "
                "heading, so a row on the wrong side is miscategorised rather than "
                "accused. The cost is symmetric and the operating point follows."),
     "measured": ("accuracy 0.908 at threshold 1, 0.928 at 2, 0.915 at 3. Threshold 3 "
                  "would move FAME to the wrong side of the published split.")},
]


CITIZEN_KNOWN_ERRORS = [
    {"name": "Indian Knowledge Systems", "rule_says": "citizen_scheme",
     "hand_label": "budget_line",
     "why": ("DBT Bharat lists it for the fellowships inside it and the name carries no "
             "other signal at all. Research and curriculum work in institutions.")},
    {"name": "Prime Minister School for Rising India", "rule_says": "citizen_scheme",
     "hand_label": "budget_line",
     "why": ("DBT Bharat lists it and the name says nothing. It upgrades existing "
             "schools; the recipient of record is the school and the child is already "
             "enrolled in it. The label is marked borderline for that reason.")},
    {"name": "Schemes for Safety of Women", "rule_says": "citizen_scheme",
     "hand_label": "budget_line",
     "why": ("a beneficiary class is named in the name and the money buys safe city "
             "projects, forensic capacity and cyber crime systems. The one case in the "
             "census where naming a person in the name is not evidence that a person "
             "receives anything.")},
    {"name": "Tea Board", "rule_says": "citizen_scheme", "hand_label": "budget_line",
     "why": ("a statutory commodity board that DBT Bharat lists. It is already a known "
             "error of the join rule above and is already removed from the absent list "
             "before this test runs, so it does not reach a published list twice.")},
    {"name": "Vigyan Dhara", "rule_says": "citizen_scheme", "hand_label": "budget_line",
     "why": ("DBT Bharat lists it for the INSPIRE fellowship inside it; the money is "
             "science and technology research grants to institutions.")},
    {"name": "Legal Aid Defense Counsel System (LADCS)", "rule_says": "budget_line",
     "hand_label": "citizen_scheme",
     "why": ("a brand and an acronym. It pays salaried defence counsel so that an "
             "identified accused who cannot afford a lawyer gets one, which the name "
             "does not say and no source records. Marked borderline in the labels.")},
    {"name": "Pradhan Mantri Krishi Sinchai Yojna", "rule_says": "budget_line",
     "hand_label": "citizen_scheme",
     "why": ("sinchai is an irrigation word and scores as an asset, correctly for the "
             "accelerated irrigation component and wrongly for Per Drop More Crop, "
             "which pays a micro-irrigation subsidy to an identified farmer.")},
    {"name": "Rashtriya Krishi Vikas Yojna", "rule_says": "budget_line",
     "hand_label": "citizen_scheme",
     "why": ("a brand name. A flexible fund released to states whose named components "
             "pay farm mechanisation and horticulture subsidies to identified farmers.")},
    {"name": "SBM-Grameen", "rule_says": "budget_line", "hand_label": "citizen_scheme",
     "why": ("an acronym. The scheme pays an incentive to an identified household that "
             "builds a toilet, and the four letters say none of it.")},
    {"name": "Skill India Programme.", "rule_says": "budget_line",
     "hand_label": "citizen_scheme",
     "why": ("a brand name. Training in which the identified trainee is the "
             "beneficiary, which is Tamil Nadu's rule applied at the union.")},
    {"name": "VB-G-RAM-G", "rule_says": "budget_line", "hand_label": "citizen_scheme",
     "why": ("an acronym, and the largest one: guaranteed wage employment paid to an "
             "identified rural household. The same programme appears in "
             "data/registry.json at Rs 95,692 crore under its full name, and the "
             "outcome statement prints only the initials.")},
]


# Where a reader could reasonably flip the HAND LABEL, not where the rule disagrees with
# it. Published because a distinction this close should carry its arguments.
CITIZEN_CONTESTED = [
    {"name": "Ex- Servicemen Contributory Health Scheme",
     "labelled": "budget_line",
     "the_argument_for_the_label": ("the Union pays it as an employer to its own retired "
                                    "soldiers, which parse/classify_tamilnadu.py "
                                    "established over 829 labels is not a welfare "
                                    "scheme. myScheme has no record for this or for "
                                    "CGHS, and its six central records for "
                                    "ex-servicemen are all discretionary welfare-fund "
                                    "grants, one explicitly for non-pensioner "
                                    "ex-servicemen."),
     "the_argument_against": ("an ex-serviceman and his dependants are people, they "
                              "enrol, they hold a card, and they receive treatment. "
                              "myScheme lists 52 ex-servicemen schemes, so it plainly "
                              "serves this population."),
     "what_would_flip_it": ("myScheme listing CGHS or any other health scheme whose "
                            "eligibility is government service. It lists none today.")},
    {"name": "Duty Drawback Scheme",
     "labelled": "budget_line",
     "the_argument_for_the_label": ("the claimant is a firm and the payment is a refund "
                                    "of customs and excise duty the firm itself paid, "
                                    "not a benefit conferred on a beneficiary."),
     "the_argument_against": ("myScheme does list exporter schemes, the Export Promotion "
                              "Capital Goods Scheme among them, and the CAG audited that "
                              "one too. So the portal has a place for a scheme of this "
                              "shape, and its absence is not nothing."),
     "what_would_flip_it": ("treating a firm as a citizen for this purpose. The register "
                            "does not, and neither does myScheme's own beneficiary "
                            "vocabulary, which separates Individual and Family from "
                            "Business Entity and Industries.")},
    {"name": "Member of Parliament Local Area Development Scheme (MPLAD)",
     "labelled": "budget_line",
     "the_argument_for_the_label": ("released to a district authority for works a Member "
                                    "of Parliament recommends. The unit of spending is a "
                                    "work in a constituency and no list of individual "
                                    "beneficiaries exists. myScheme lists no "
                                    "constituency development scheme of any kind, at the "
                                    "union or in any state."),
     "the_argument_against": ("the money reaches individuals through what the works "
                              "build, and a citizen can ask an MP for a work."),
     "what_would_flip_it": ("a beneficiary list. Asking an MP is not an application and "
                            "produces no record a register could read.")},
    {"name": "National Mission for a Green India",
     "labelled": "citizen_scheme",
     "the_argument_for_the_label": ("DBT Bharat lists it and the mission's own design "
                                    "pays forest-dependent households for plantation and "
                                    "protection work."),
     "the_argument_against": ("most of the money buys forest cover on public land, which "
                              "is an asset, and the recipient of record is a state "
                              "forest department."),
     "what_would_flip_it": ("dropping the DBT listing as evidence. It is the strongest "
                            "government-supplied signal in this file at 0.820 over 50, "
                            "and this is the row where it is doing the most work.")},
    {"name": "Samagra Shiksha",
     "labelled": "citizen_scheme",
     "the_argument_for_the_label": ("DBT Bharat lists its textbook intervention and the "
                                    "Outcome Budget counts students given free "
                                    "textbooks, children given transport and children "
                                    "given escorts. A child is the beneficiary of "
                                    "record for those."),
     "the_argument_against": ("most of the Rs 42,100 crore is teacher salaries and "
                              "school infrastructure, and no parent applies to Samagra "
                              "Shiksha."),
     "what_would_flip_it": ("labelling umbrella programmes by where most of the money "
                            "goes rather than by whether a person is a beneficiary of "
                            "record anywhere in them. That rule would also move "
                            "Rashtriya Krishi Vikas Yojna and Pradhan Mantri Krishi "
                            "Sinchai Yojna, and it is stated as the tie-break in "
                            "data/cag/citizen_labels.json so it can be reversed in one "
                            "place.")},
    {"name": ("Scheme for Faster Adoption and Manufacturing of (Hybrid and) Electric "
              "Vehicle in India - (FAME - India)."),
     "labelled": "citizen_scheme",
     "the_argument_for_the_label": ("the demand incentive lowers the price an identified "
                                    "buyer pays and the buyer is verified before it is "
                                    "paid. DBT Bharat lists the delivery mechanism by "
                                    "name."),
     "the_argument_against": ("it is routed through the manufacturer, who is reimbursed, "
                              "and the buyer never handles the money."),
     "what_would_flip_it": ("requiring the payment to land in the beneficiary's own "
                            "hands. That would also move the free textbooks under "
                            "Samagra Shiksha and every in-kind transfer DBT Bharat "
                            "lists.")},
]


# Rejected signals. The prose is fixed; the numbers beside it are measured at run time
# from the same 153 labels, so a signal cannot quietly stop being rejected when the
# register moves. `key` names the test computed in run().
CITIZEN_REJECTED = [
    {"signal": "whether a citizen can apply for it",
     "key": "an_application_exists",
     "measured_over": ("the schemes the join listed as audited when these labels were "
                       "made, hand read one by one as a census of that list. It is the "
                       "only signal here that no source in the register carries."),
     "why_not": ("no signal and slightly the wrong sign. The schemes that reach the most "
                 "people select beneficiaries from a list rather than take applications, "
                 "and PMAY-Gramin, Ayushman Bharat and Jal Jeevan Mission all fall on "
                 "the no-application side while the Duty Drawback Scheme and the "
                 "Ex-Servicemen Contributory Health Scheme both have a form. It is also "
                 "not computable for the 701 rows myScheme does not list, which is the "
                 "population the test is for.")},
    {"signal": "the union budget's own Statement 4A against Statement 4B",
     "key": "statement_4a",
     "why_not": ("no signal. Centrally Sponsored against Central Sector says who "
                 "delivers the money, states or the union directly, and nothing about "
                 "who receives it. Statement 4B holds Pradhan Mantri Ujjwala Yojana and "
                 "Rolling Stock alike.")},
    {"signal": "an Outcome Budget target counted in people",
     "key": "an_outcome_target_counted_in_people",
     "why_not": ("no signal, and it fires on 10 of 153 rows because only 111 register "
                 "entries carry an outcome framework at all. The indicator text in "
                 "data/outcome/2026.json is also the first line of a wrapped cell, so "
                 "'Number of children provided Transport' and 'Number of schools covered "
                 "under' are both truncated mid-phrase and the unit is often the part "
                 "that was cut.")},
    {"signal": "the size of the budget line, Rs 1,000 crore or more",
     "key": "a_large_budget_line",
     "why_not": ("no signal at any threshold, which is worth publishing because it is "
                 "the assumption a reader brings. Rolling Stock is Rs 52,109 crore and "
                 "reaches nobody as a beneficiary; the Sugar Subsidy under the Public "
                 "Distribution System is Rs 200 crore and reaches Antyodaya households.")},
    {"signal": "data/classification.json's own scheme-versus-budget-head score, 4 or more",
     "key": "the_classifier_score_is_4_or_more",
     "why_not": ("weak, and circular for this question. parse/classify.py states in its "
                 "own docstring that it is validated against myScheme membership as the "
                 "proxy for citizen-facing. Scoring a row on a classifier trained to "
                 "agree with myScheme, in order to decide whether myScheme should have "
                 "listed it, answers the question with itself. The same reasoning is set "
                 "out in parse/classify_andhra.py's why_not_myscheme and in "
                 "signals_rejected above.")},
    {"signal": "whether myScheme lists the row at all",
     "key": "myscheme_lists_it",
     "why_not": ("the strongest circular signal there is. The finding this file exists "
                 "to publish is which audited schemes are ABSENT from myScheme, so "
                 "scoring myScheme presence would push down exactly the rows the answer "
                 "is made of. What IS used is different and is stated as such: myScheme's "
                 "own targetBeneficiaries tag on the rows it does list, which disagrees "
                 "with myScheme's inclusion decision twice among the audited schemes it "
                 "does list, at AMRUT and at the Export Promotion Capital Goods "
                 "Scheme.")},
    {"signal": "a body word anywhere in the name",
     "key": "a_body_word_anywhere_in_the_name",
     "why_not": ("no signal in either direction, because board, centre, institute and "
                 "school appear inside "
                 "the names of schemes that pay people: the Master Control Facility "
                 "scholarships, the residential education scheme for Scheduled Caste "
                 "students, the stipend paid through Vocational Rehabilitation Centres. "
                 "The narrower pattern that does work needs the preposition and is the "
                 "second clause of the rule.")},
]


# ---------------------------------------------------------------------------
# Measurement.
# ---------------------------------------------------------------------------
def measure(rows, name, test):
    """P(sound) with and without a condition, counted over the labelled census."""
    a = [r for r in rows if test(r)]
    b = [r for r in rows if not test(r)]
    pa = sum(1 for r in a if r["label"] == "sound") / len(a) if a else 0.0
    pb = sum(1 for r in b if r["label"] == "sound") / len(b) if b else 0.0
    return {"signal": name, "n_with": len(a), "n_without": len(b),
            "p_sound_with": round(pa, 3), "p_sound_without": round(pb, 3),
            "lift": round(pa - pb, 3)}


def run():
    def load(rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return json.load(fh)

    reports_doc = load("data/cag/reports.json")
    registry = load("data/registry.json")
    classification = load("data/classification.json")
    labels_doc = load("data/cag/join_labels.json")
    citizen_labels_doc = load("data/cag/citizen_labels.json")
    sector_doc = load("data/sector.json")

    by_id = {r["id"]: r for r in reports_doc["entries"]}
    subjects = [r for r in reports_doc["entries"] if r.get("subject")]
    entries = {}
    for e in registry["entries"]:
        entries.setdefault(e["name"], e)
    names = sorted(entries)

    verdicts, scores = {}, {}
    for line in classification["all_lines"]:
        verdicts[line["name"]] = line["verdict"]
        scores[line["name"]] = line["score"]

    # myScheme's own level and state for each entry, read from the archived record. A
    # record myScheme tags State is that state's listing, and the rule needs to know
    # whose.
    # myScheme's own beneficiary tags and sector for the rows it lists, from the same
    # archived record. The citizen test reads the tags; see CITIZEN_PERSON_BENEFICIARIES
    # for the one place they are corrected.
    level_state = {}
    ms_extra = {}
    for name, e in entries.items():
        ms = e["sources"].get("myscheme")
        if not ms:
            level_state[name] = (None, None)
            continue
        path = os.path.join(ROOT, "data/myscheme/schemes", ms["slug"] + ".json")
        state = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            m = re.search(r'"state"\s*:\s*\{[^}]*?"label"\s*:\s*"([^"]+)"', body)
            state = m.group(1) if m else None
            rec = json.loads(body)
            basic = (rec.get("en") or {}).get("basicDetails") or {}
            bens = [(t.get("label") if isinstance(t, dict) else t)
                    for t in (basic.get("targetBeneficiaries") or [])]
            cat = ((rec.get("_list") or {}).get("schemeCategory")
                   or [None])[0] if isinstance((rec.get("_list") or {}).get(
                       "schemeCategory"), list) else (rec.get("_list") or {}).get(
                           "schemeCategory")
            ms_extra[name] = {"beneficiaries": sorted(b for b in bens if b),
                              "category": cat}
        level_state[name] = (ms.get("level"), state)

    def verdict_of(name):
        b = entries[name]["sources"].get("budget")
        if not b:
            return None
        return verdicts.get(b.get("name") or name) or verdicts.get(name)

    raw = joins(subjects, names)

    labelled = {(x["cag_id"], x["registry_name"]): x for x in labels_doc["labels"]}
    rows = []
    for j in raw:
        name = j["registry_name"]
        lvl, st = level_state[name]
        f = features(by_id[j["cag_id"]], name, j["why"], verdict_of(name), lvl, st)
        lab = labelled.get((j["cag_id"], name))
        rows.append({
            "cag_id": j["cag_id"], "registry_name": name, "why": j["why"],
            "features": f,
            "label": (lab or {}).get("label"),
            "label_reason": (lab or {}).get("reason"),
            "kept": keep(f),
        })

    unlabelled = [r for r in rows if r["label"] is None]
    stale = [k for k in labelled if k not in {(r["cag_id"], r["registry_name"]) for r in rows}]

    labelled_rows = [r for r in rows if r["label"]]
    sound = sum(1 for r in labelled_rows if r["label"] == "sound")

    kept = [r for r in rows if r["kept"]]
    tp = sum(1 for r in kept if r["label"] == "sound")
    fp = sum(1 for r in kept if r["label"] == "wrong")
    fn = sum(1 for r in labelled_rows if r["label"] == "sound" and not r["kept"])

    sig = [
        measure(labelled_rows, "the matcher's reason is name evidence",
                lambda r: r["features"]["family"] in ("similarity", "containment", "skeleton")),
        measure(labelled_rows, "the matcher's reason is one of the two acronym rules",
                lambda r: r["features"]["family"] in ("acronym match", "acronym containment")),
        measure(labelled_rows, "the matcher's reason is the prefix rule",
                lambda r: r["features"]["family"] == "prefix"),
        measure(labelled_rows, "the report is a Performance audit",
                lambda r: r["features"]["audit_type"] == "Performance"),
        measure(labelled_rows, "the report is a Compliance audit",
                lambda r: r["features"]["audit_type"] == "Compliance"),
        measure(labelled_rows, "the entry is a union budget line classified a budget head",
                lambda r: r["features"]["verdict"] == "budget head"),
        measure(labelled_rows, "the entry is a union budget line classified a scheme",
                lambda r: r["features"]["verdict"] == "scheme"),
        measure(labelled_rows, "the entry is a Central myScheme record",
                lambda r: r["features"]["myscheme_level"] == "Central"),
        measure(labelled_rows, "the entry is a state myScheme record",
                lambda r: r["features"]["myscheme_level"] in ("State", "State/ UT")),
        measure(labelled_rows, "the entry is a state record for a different government",
                lambda r: (r["features"]["myscheme_level"] in ("State", "State/ UT")
                           and r["features"]["myscheme_state"]
                           and r["features"]["myscheme_state"][:5].lower()
                           not in (r["features"]["government"] or "").lower())),
        measure(labelled_rows, "the CAG subject has two content words or fewer",
                lambda r: r["features"]["subject_content_words"] <= 2),
        measure(labelled_rows, "the CAG subject is 60 characters or fewer",
                lambda r: r["features"]["subject_chars"] <= 60),
        measure(labelled_rows, "the registry name lies wholly inside the subject",
                lambda r: r["features"]["name_inside_subject"]),
    ]

    def report_pointer(cid):
        r = by_id[cid]
        return {"cag_id": cid, "title": r["title"], "subject": r["subject"],
                "audit_type": r.get("audit_type"), "government": r.get("government"),
                "tabled": r.get("tabled"), "report_no": r.get("report_no"),
                "report_year": r.get("report_year"),
                "detail_url": r.get("detail_url"), "pdf_url": r.get("pdf_url")}

    audited = collections.defaultdict(list)
    for r in kept:
        audited[r["registry_name"]].append(report_pointer(r["cag_id"]))
    audited_out = []
    for name in sorted(audited):
        e = entries[name]
        srcs = sorted(e["sources"])
        audited_out.append({
            "scheme": name,
            "sources": srcs,
            "on_myscheme": "myscheme" in srcs,
            "audits": sorted(audited[name], key=lambda a: a["cag_id"]),
        })

    absent = [a for a in audited_out if not a["on_myscheme"]]
    bad_schemes = {e["registry_name"] for e in KNOWN_ERRORS}
    absent_clean = [a for a in absent if a["scheme"] not in bad_schemes]

    # ---- the citizen test -------------------------------------------------
    sectors = sector_doc["sectors"]

    def sector_of(name):
        x = ms_extra.get(name) or {}
        if x.get("category"):
            return x["category"]
        s = sectors.get("registry|" + name)
        return s.get("sector") if s else None

    def citizen_of(name):
        return citizen_features(name, entries[name], sector_of(name),
                                (ms_extra.get(name) or {}).get("beneficiaries"))

    # The audited set is read live rather than from the `audited` flag frozen into the
    # labels file, because the join above moves whenever parse/match.py or the register
    # moves and the flag would then be measuring yesterday's census.
    audited_names = {a["scheme"] for a in audited_out}
    # Outcome Budget indicator text, read only to reject a signal. The cycle names the
    # file: registry.json's "2026-27" is data/outcome/2026.json.
    outcome_by_name = {}
    op = os.path.join(ROOT, "data", "outcome",
                      str(registry["cycle"]).split("-")[0] + ".json")
    if os.path.exists(op):
        with open(op, encoding="utf-8") as fh:
            outcome_by_name = {s["name"]: s for s in json.load(fh)["schemes"]}

    def outcome_counts_people(name):
        o = entries[name]["sources"].get("outcome")
        if not o:
            return False
        od = outcome_by_name.get(o.get("name"))
        if not od:
            return False
        return any(CITIZEN_PERSON_UNIT.search(i.get("indicator") or "")
                   for k in ("outputs", "outcomes") for i in od.get(k, []))

    cz_rows, cz_stale = [], []
    for lab in citizen_labels_doc["labels"]:
        n = lab["name"]
        if n not in entries:
            cz_stale.append(n)
            continue
        f = citizen_of(n)
        b = entries[n]["sources"].get("budget") or {}
        cz_rows.append({"name": n, "label": lab["label"],
                        "borderline": lab["borderline"],
                        "audited": n in audited_names,
                        "features": f, "score": citizen_score(f),
                        "rule_says": citizen_verdict(f),
                        "rejected_features": {
                            "an_application_exists": lab.get("a_citizen_applies"),
                            "statement_4a": b.get("statement") == "stat4a",
                            "an_outcome_target_counted_in_people":
                                outcome_counts_people(n),
                            "a_large_budget_line": (b.get("be_cr") or 0) >= 1000,
                            "the_classifier_score_is_4_or_more":
                                (scores.get(b.get("name") or n)
                                 if scores.get(b.get("name") or n) is not None
                                 else -99) >= 4,
                            "myscheme_lists_it": "myscheme" in entries[n]["sources"],
                            "a_body_word_anywhere_in_the_name":
                                bool(CITIZEN_BODY_ANYWHERE.search(n)),
                        }})
    cz_stale.sort()
    cz_unlabelled = sorted(audited_names - {r["name"] for r in cz_rows})

    def cz_measure(label, test):
        a = [r for r in cz_rows if test(r["features"])]
        b = [r for r in cz_rows if not test(r["features"])]
        pa = sum(1 for r in a if r["label"] == "citizen_scheme") / len(a) if a else 0.0
        pb = sum(1 for r in b if r["label"] == "citizen_scheme") / len(b) if b else 0.0
        return {"signal": label, "n_with": len(a), "n_without": len(b),
                "p_citizen_with": round(pa, 3), "p_citizen_without": round(pb, 3),
                "lift": round(pa - pb, 3)}

    cz_signals = [
        cz_measure("myScheme's own record tags a person or household beneficiary",
                   lambda f: f["myscheme_tags_a_person"]),
        cz_measure("myScheme's own record tags only an institutional beneficiary",
                   lambda f: f["myscheme_tags_only_an_institution"]),
        cz_measure("DBT Bharat lists it", lambda f: f["listed_by_dbt_bharat"]),
        cz_measure("a person or household named in the name",
                   lambda f: f["a_person_or_household_in_the_name"]),
        cz_measure("a benefit phrase in the name",
                   lambda f: f["a_benefit_phrase_in_the_name"]),
        cz_measure("an asset or works word in the name",
                   lambda f: f["an_asset_or_works_word_in_the_name"]),
        cz_measure("a research or capacity word in the name",
                   lambda f: f["a_research_or_capacity_word_in_the_name"]),
        cz_measure("the sector is Business, Science and IT, Transport or Banking",
                   lambda f: f["a_firm_or_asset_sector"]),
        cz_measure("the name says the money goes to a body",
                   lambda f: f["the_name_says_the_money_goes_to_a_body"]),
        cz_measure("an employer obligation",
                   lambda f: f["an_employer_obligation"]),
    ]

    # The rejected signals, measured rather than typed, so a rejection cannot go stale.
    # A signal that fires on only some rows is measured only on those rows: the
    # application test is hand read and covers the schemes the join listed as audited
    # when the labels were made, and nothing else.
    cz_rejected = []
    for spec in CITIZEN_REJECTED:
        k = spec["key"]
        sub = [r for r in cz_rows if r["rejected_features"][k] is not None]
        a = [r for r in sub if r["rejected_features"][k]]
        b = [r for r in sub if not r["rejected_features"][k]]
        pa = sum(1 for r in a if r["label"] == "citizen_scheme") / len(a) if a else 0.0
        pb = sum(1 for r in b if r["label"] == "citizen_scheme") / len(b) if b else 0.0
        out = {"signal": spec["signal"],
               "n_with": len(a), "n_without": len(b),
               "p_citizen_with": round(pa, 3), "p_citizen_without": round(pb, 3),
               "lift": round(pa - pb, 3),
               "why_not": spec["why_not"]}
        if spec.get("measured_over"):
            out["measured_over"] = spec["measured_over"]
        cz_rejected.append(out)

    def cz_at(thr):
        def says(r):
            f = r["features"]
            if f["an_employer_obligation"] or f["the_name_says_the_money_goes_to_a_body"]:
                return False
            return r["score"] >= thr
        tp = sum(1 for r in cz_rows if says(r) and r["label"] == "citizen_scheme")
        fp = sum(1 for r in cz_rows if says(r) and r["label"] == "budget_line")
        fn = sum(1 for r in cz_rows if not says(r) and r["label"] == "citizen_scheme")
        tn = len(cz_rows) - tp - fp - fn
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        return {"threshold": thr, "called_citizen_schemes": tp + fp,
                "true_positive": tp, "false_positive": fp,
                "false_negative": fn, "true_negative": tn,
                "accuracy": round((tp + tn) / len(cz_rows), 4) if cz_rows else None,
                "precision": round(prec, 4) if prec is not None else None,
                "recall": round(rec, 4) if rec is not None else None}

    cz_sweep = [cz_at(t) for t in range(-1, 7)]
    cz_val = cz_at(CITIZEN_THRESHOLD)
    cz_audited = [r for r in cz_rows if r["audited"]]
    cz_val["on_the_audited_census"] = {
        "n": len(cz_audited),
        "rule_agrees_with_the_hand_label": sum(
            1 for r in cz_audited
            if r["rule_says"] == (r["label"] == "citizen_scheme")),
        "audited_schemes_with_no_hand_label": cz_unlabelled,
        "note": ("the audited schemes are a census of what this file publishes and every "
                 "one of them is hand labelled, so the published split below is the hand "
                 "labels themselves and the rule's job here is to show that a mechanical "
                 "test reconstructs them from published evidence. Where the two "
                 "disagree the hand label is published and the disagreement is named on "
                 "the row, which is how KNOWN_ERRORS is already treated by "
                 "absent_from_myscheme_after_known_errors."),
    }
    cz_val["disagreements"] = sorted(
        [{"name": r["name"], "rule_says":
          "citizen_scheme" if r["rule_says"] else "budget_line",
          "hand_label": r["label"], "score": r["score"],
          "borderline": r["borderline"], "audited": r["audited"]}
         for r in cz_rows if r["rule_says"] != (r["label"] == "citizen_scheme")],
        key=lambda x: x["name"])

    hand = {lab["name"]: lab for lab in citizen_labels_doc["labels"]}
    for a in audited_out:
        f = citizen_of(a["scheme"])
        h = hand.get(a["scheme"])
        by_rule = citizen_verdict(f)
        a["reaches_individuals"] = (h["label"] == "citizen_scheme") if h else by_rule
        a["decided_by"] = ("the hand label in data/cag/citizen_labels.json" if h
                           else "the rule, because no hand label covers this row")
        a["by_the_rule"] = by_rule
        a["hand_label"] = h["label"] if h else None
        a["citizen_score"] = citizen_score(f)
        a["citizen_evidence"] = citizen_evidence(f)

    reaching, not_reaching = [], []
    for a in absent_clean:
        h = hand.get(a["scheme"]) or {}
        row = {"scheme": a["scheme"], "score": a["citizen_score"],
               "evidence": a["citizen_evidence"],
               "decided_by": a["decided_by"],
               "hand_label": a["hand_label"],
               "hand_reason": h.get("reason"),
               "borderline": h.get("borderline"),
               "the_rule_disagrees": a["hand_label"] is not None
                                     and a["by_the_rule"] != a["reaches_individuals"],
               "audits": len(a["audits"])}
        (reaching if a["reaches_individuals"] else not_reaching).append(row)
    reaching.sort(key=lambda x: x["scheme"])
    not_reaching.sort(key=lambda x: x["scheme"])

    misses = recall_check(subjects, names)

    return {
        "doc": {
            "built": utcnow(),
            "snapshot": reports_doc["snapshot"],
            "source": ("Comptroller and Auditor General of India, audit report index, "
                       "joined to data/registry.json"),
            "what": ("Which schemes the CAG has audited. A pointer and nothing more: "
                     "that a report exists on this scheme, its number, the date it was "
                     "tabled and where to read it. No audit finding is read, quoted or "
                     "characterised anywhere in this file. Those are the CAG's to "
                     "publish."),
            "corpus": {
                "reports_catalogued": reports_doc["reports"],
                "reports_with_a_subject": reports_doc["with_a_subject"],
                "registry_entries": registry["total_entries"],
                "distinct_registry_names": len(names),
            },
            "raw_join": {
                "pairs": len(rows),
                "distinct_reports": len({r["cag_id"] for r in rows}),
                "distinct_schemes": len({r["registry_name"] for r in rows}),
                "labelled": len(labelled_rows),
                "sound": sound,
                "precision": round(sound / len(labelled_rows), 4) if labelled_rows else None,
                "note": ("not a publishable number and not a matcher failure: "
                         "probably_same is generous by design because it decides "
                         "absence claims, and an audit title is a sentence about "
                         "government rather than the name of a programme. It was 0.126 "
                         "when this file was written and rises as parse/match.py's "
                         "defects are closed, because the joins that go are the wrong "
                         "ones."),
            },
            "ground_truth": {
                "file": "data/cag/join_labels.json",
                "labelled": labels_doc["labelled"],
                "sound": labels_doc["sound"],
                "wrong": labels_doc["wrong"],
                "census_holds": not unlabelled,
                "census_note": ("the labels are a census of the joins ONLY while "
                                "unlabelled_joins is empty, and precision below is a "
                                "count rather than an estimate only then. Recall is "
                                "counted against the same census; what cannot be "
                                "counted is recall against schemes the matcher never "
                                "joined at all, which is measured separately in "
                                "matcher_recall_check."
                                + ("" if not unlabelled else
                                   " IT DOES NOT HOLD ON THIS SNAPSHOT: parse/match.py "
                                   "has been changed since these labels were made, so "
                                   + str(len(unlabelled)) + " joins carry no label and "
                                   + str(len(stale)) + " labels no longer correspond to "
                                   "a join. The numbers below are measured on the "
                                   "labels that still apply and the census claim is not "
                                   "true again until the new joins are labelled.")),
                "rule": labels_doc["rule"],
                "unlabelled_joins": sorted((r["cag_id"], r["registry_name"])
                                           for r in unlabelled),
                "labels_with_no_join": sorted(stale),
            },
            "signals": sig,
            "signals_rejected": REJECTED_SIGNALS,
            "rule": RULE,
            "validation": {
                "kept": len(kept),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "precision": round(tp / len(kept), 4) if kept else None,
                "recall": round(tp / sound, 4) if sound else None,
                "distinct_reports": len({r["cag_id"] for r in kept}),
                "distinct_schemes": len({r["registry_name"] for r in kept}),
                "unlabelled_among_the_kept": sorted(
                    (r["cag_id"], r["registry_name"]) for r in kept if not r["label"]),
                "note": ("precision is counted over the " + str(len(labelled_rows))
                         + " labelled joins rather than estimated from a sample. The "
                           "joins it gets wrong are named in known_errors and the sound "
                           "joins it drops are named in recall_lost. Any kept join with "
                           "no hand label is listed above and is counted in neither."),
            },
            "known_errors": KNOWN_ERRORS,
            "recall_lost": sorted(
                [{"cag_id": r["cag_id"], "registry_name": r["registry_name"],
                  "why_the_matcher_joined": r["why"],
                  "why_the_rule_dropped_it": _dropped_by(r["features"])}
                 for r in labelled_rows if r["label"] == "sound" and not r["kept"]],
                key=lambda x: (x["cag_id"], x["registry_name"])),
            "matcher_defects": MATCHER_DEFECTS,
            "matcher_recall_check": {
                "what": ("pairs whose content words agree once a crude English plural "
                         "is folded, and which probably_same still rejects. A rejection "
                         "is an absence claim, so these are the expensive misses."),
                "n": len(misses),
                "pairs": misses,
                "note": ("this is the sixth defect in matcher_defects, counted. It is "
                         "not a full recall measurement: it finds only the misses a "
                         "plural causes, and says nothing about the ones caused by "
                         "abbreviation, word order or an audit title that never names "
                         "its scheme."),
            },
            "audited_schemes": len(audited_out),
            "audited_schemes_absent_from_myscheme": len(absent),
            "absent_from_myscheme": [a["scheme"] for a in absent],
            "audited_schemes_absent_from_myscheme_after_known_errors": len(absent_clean),
            "absent_from_myscheme_after_known_errors": [a["scheme"] for a in absent_clean],
            "citizen_test": {
                "question": ("Of the things a government funds, which reach an "
                             "identified person or household, so that a portal built "
                             "for citizens to look schemes up would have a page for "
                             "them? This decides whether 'absent from myScheme' is a "
                             "criticism of the portal or a fact about the spending, and "
                             "it is why the absent list below is two lists."),
                "why_it_is_here": ("publishing Samagra Shiksha, a Rs 42,100 crore school "
                                   "education programme, under the same heading as the "
                                   "Duty Drawback Scheme, which refunds customs duty to "
                                   "the exporter who paid it, would overstate the second "
                                   "and weaken the first by sitting next to it."),
                "what_a_budget_line_label_does_not_say": ("nothing against the spending. "
                                                          "Roads, courts, research and "
                                                          "rolling stock are what a "
                                                          "state is for. The label says "
                                                          "only that a citizen scheme "
                                                          "portal is not where you would "
                                                          "look for them."),
                "ground_truth": {
                    "file": "data/cag/citizen_labels.json",
                    "labelled": citizen_labels_doc["labelled"],
                    "citizen_scheme": citizen_labels_doc["citizen_scheme"],
                    "budget_line": citizen_labels_doc["budget_line"],
                    "base_rate": citizen_labels_doc["base_rate"],
                    "borderline": citizen_labels_doc["borderline"],
                    "population": citizen_labels_doc["population"],
                    "rule": citizen_labels_doc["rule"],
                    "labels_with_no_register_row": cz_stale,
                },
                "signals": cz_signals,
                "signals_rejected": cz_rejected,
                "rule": CITIZEN_RULE,
                "weights": CITIZEN_WEIGHTS,
                "threshold": CITIZEN_THRESHOLD,
                "threshold_sweep": cz_sweep,
                "validation": cz_val,
                "known_errors": CITIZEN_KNOWN_ERRORS,
                "contested": CITIZEN_CONTESTED,
            },
            "absent_from_myscheme_reaching_individuals": reaching,
            "absent_from_myscheme_not_reaching_individuals": not_reaching,
            "absent_split_note": ("the same 20 audits and the same absence claim, "
                                  "divided by who the money reaches. The first list is "
                                  "the one that says something about myScheme: a "
                                  "programme that pays identified people, audited by the "
                                  "CAG, and not on the portal built for citizens to find "
                                  "schemes. The second is not a lighter version of the "
                                  "first, it is a different statement: these are audited "
                                  "and funded, and a citizen portal is not where they "
                                  "belong. Every row carries its arithmetic, and the "
                                  "cases where a reader could reasonably disagree are in "
                                  "citizen_test.contested with the argument both ways."),
            "absence_note": ("absence is what data/registry.json's own clustering says: "
                             "the entry reached the register from the union budget, "
                             "DBT Bharat or the outcome statements and no myScheme "
                             "record merged into it under the same generous matcher. "
                             "These are schemes a government funds, an auditor has "
                             "studied, and a citizen cannot look up on the portal built "
                             "for looking schemes up."),
            "audited": audited_out,
            "scope_note": ("A pointer, not a verdict. This says an audit exists on a "
                           "scheme and where to find it. It says nothing about what the "
                           "audit found, whether the scheme works, or whether the "
                           "auditor was satisfied, and nothing in this pipeline reads "
                           "an audit report body."),
        },
        "rows": rows,
        "kept": kept,
        "absent": absent,
        "audited_out": audited_out,
    }


def _singular(t):
    """Crude English plural fold. Only used to MEASURE what the matcher misses."""
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("es") and t[-3] in "sxzh":
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def recall_check(subjects, names):
    """Pairs whose content words agree once plurals are folded and that STILL do not join.

    This is the only measurement of the matcher's misses available without a second
    census, and it is the direction that matters most: probably_same decides absence
    claims, so a missed match is an accusation. Deliberately narrow, one crude plural
    fold and nothing else, so that every pair it returns is one a reader can check by
    eye in a second.
    """
    fold = {}
    index = collections.defaultdict(list)
    for n in names:
        s = {_singular(t) for t in tokens(n)}
        fold[n] = s
        for t in s:
            index[t].append(n)
    out = []
    for r in subjects:
        ss = {_singular(t) for t in tokens(r["subject"])}
        if len(ss) < 3:
            continue
        cand = set()
        for t in ss:
            cand.update(index.get(t, ()))
        for n in sorted(cand):
            tn = fold[n]
            agree = (len(tn) >= 3 and tn <= ss) or (ss <= tn and len(tn) <= 2 * len(ss))
            if agree and not probably_same(r["subject"], n)[0]:
                out.append({"cag_id": r["id"], "subject": r["subject"],
                            "registry_name": n, "returned": probably_same(r["subject"], n)[1]})
    out.sort(key=lambda x: (x["cag_id"], x["registry_name"]))
    return out


def _dropped_by(f):
    """The first rule clause that rejects a pair, for the recall_lost listing."""
    fam_ok = f["family"] in ("similarity", "containment", "skeleton") or (
        f["family"] == "prefix" and f["registry_name_is_prefix"]
        and not f["prefix_is_subordinated"])
    if not fam_ok:
        return "the matcher's reason is an acronym rule, not name evidence"
    if f["audit_type"] != "Performance":
        return "the report is not a Performance audit"
    if f["verdict"] == "budget head":
        return ("the registry entry is a union budget line the classifier calls a "
                "budget head")
    if f["skeleton_evidence_thin"]:
        return ("the transliteration evidence is thinner than three skeletons of "
                "three characters")
    if not (f["name_inside_subject"] or f["names_equal"] or f["similarity"] >= 0.78
            or f["skeletons_inside_subject"] or f["subject_inside_name_generically"]
            or (f["family"] == "prefix" and f["registry_name_is_prefix"])):
        return "the two names do not agree in the right direction"
    return ("the myScheme record belongs to a different government from the one the "
            "report covers")


def main():
    ap = argparse.ArgumentParser(description="Join the CAG catalogue to the scheme register.")
    ap.add_argument("--print-joins", action="store_true",
                    help="print every join with its hand label, for reading")
    a = ap.parse_args()

    out = run()
    doc = out["doc"]
    write_json("data/cag/join.json", doc)

    if a.print_joins:
        for r in out["rows"]:
            mark = "keep" if r["kept"] else "    "
            print(f"{mark} {str(r['label']):<6} {r['cag_id']:<7} {r['why'][:44]:<46}"
                  f" {r['registry_name'][:56]}")
        return

    v, raw = doc["validation"], doc["raw_join"]
    print(f"CAG join: {raw['pairs']:,} joins over {raw['distinct_reports']} reports")
    print(f"  hand labelled {raw['labelled']}, sound {raw['sound']}"
          f"  -> raw precision {raw['precision']:.1%}")
    print(f"  rule keeps {v['kept']}: {v['true_positive']} sound, "
          f"{v['false_positive']} wrong  -> precision {v['precision']:.1%}, "
          f"recall {v['recall']:.1%}")
    print(f"  {v['distinct_schemes']} schemes audited across {v['distinct_reports']} reports")
    print(f"  of those, {doc['audited_schemes_absent_from_myscheme_after_known_errors']}"
          f" are absent from myScheme once the known errors are removed:")
    ct = doc["citizen_test"]
    print("   reaching an identified person or household:")
    for a in doc["absent_from_myscheme_reaching_individuals"]:
        print(f"     {'*' if a['borderline'] else ' '} {a['scheme'][:74]}")
    print("   not reaching one:")
    for a in doc["absent_from_myscheme_not_reaching_individuals"]:
        print(f"     {'*' if a['borderline'] else ' '} {a['scheme'][:74]}")
    print("   (* marks a call the labels mark borderline, with the argument the other way)")
    cv = ct["validation"]
    print(f"  citizen test: {ct['ground_truth']['labelled']} hand labels, base rate "
          f"{ct['ground_truth']['base_rate']:.1%}  -> accuracy {cv['accuracy']:.1%}, "
          f"precision {cv['precision']:.1%}, recall {cv['recall']:.1%}")
    print(f"   on the audited census it agrees with the hand label "
          f"{cv['on_the_audited_census']['rule_agrees_with_the_hand_label']} times "
          f"of {cv['on_the_audited_census']['n']}; "
          f"{len(ct['known_errors'])} errors survive, {len(ct['contested'])} calls contested")
    if cv["on_the_audited_census"]["audited_schemes_with_no_hand_label"]:
        print(f"   AUDITED SCHEMES WITH NO CITIZEN LABEL: "
              f"{len(cv['on_the_audited_census']['audited_schemes_with_no_hand_label'])}. "
              f"data/cag/citizen_labels.json is stale against this snapshot.")
    print(f"  matcher misses a plural alone explains: "
          f"{doc['matcher_recall_check']['n']} pairs")
    if doc["ground_truth"]["unlabelled_joins"]:
        print(f"  UNLABELLED joins: {len(doc['ground_truth']['unlabelled_joins'])}. "
              f"data/cag/join_labels.json is stale against this snapshot.")
    if doc["ground_truth"]["labels_with_no_join"]:
        print(f"  labels with no join: {len(doc['ground_truth']['labels_with_no_join'])}")


if __name__ == "__main__":
    main()
