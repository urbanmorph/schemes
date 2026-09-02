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

    by_id = {r["id"]: r for r in reports_doc["entries"]}
    subjects = [r for r in reports_doc["entries"] if r.get("subject")]
    entries = {}
    for e in registry["entries"]:
        entries.setdefault(e["name"], e)
    names = sorted(entries)

    verdicts = {}
    for line in classification["all_lines"]:
        verdicts[line["name"]] = line["verdict"]

    # myScheme's own level and state for each entry, read from the archived record. A
    # record myScheme tags State is that state's listing, and the rule needs to know
    # whose.
    level_state = {}
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
                "note": ("12.6 per cent. Not a publishable number and not a matcher "
                         "failure: probably_same is generous by design because it "
                         "decides absence claims, and an audit title is a sentence "
                         "about government rather than the name of a programme."),
            },
            "ground_truth": {
                "file": "data/cag/join_labels.json",
                "labelled": labels_doc["labelled"],
                "sound": labels_doc["sound"],
                "wrong": labels_doc["wrong"],
                "census_note": ("every join is hand labelled, so precision below is "
                                "counted and not estimated. Recall is counted too, "
                                "against the same census; what cannot be counted is "
                                "recall against schemes the matcher never joined at "
                                "all, which is measured separately in "
                                "matcher_recall_check."),
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
                "note": ("precision is a count over a census of all "
                         + str(len(labelled_rows)) + " joins, not an estimate from a "
                         "sample. The two joins it gets wrong are named in "
                         "known_errors and the sound joins it drops are named in "
                         "recall_lost."),
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
    for n in doc["absent_from_myscheme_after_known_errors"]:
        print(f"     {n}")
    print(f"  matcher misses a plural alone explains: "
          f"{doc['matcher_recall_check']['n']} pairs")
    if doc["ground_truth"]["unlabelled_joins"]:
        print(f"  UNLABELLED joins: {len(doc['ground_truth']['unlabelled_joins'])}. "
              f"data/cag/join_labels.json is stale against this snapshot.")
    if doc["ground_truth"]["labels_with_no_join"]:
        print(f"  labels with no join: {len(doc['ground_truth']['labels_with_no_join'])}")


if __name__ == "__main__":
    main()
