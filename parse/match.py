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
import functools
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
    # Who announced it, which in India is who pays for it. "Mukhyamantri Matsya Sampada
    # Yojana" is Haryana's and "Pradhan Mantri Matsya Sampada Yojana" is the Union's, and
    # they reduce to mmsy and pmmsy: one dropped letter carrying the whole state-versus-
    # central distinction, which acronym containment then bridged in 7 joins. Treating it
    # as an axis rather than a spelling is what makes the pair disagree instead of match.
    {"mukhyamantri", "mukhya mantri", "mukhya"},
    {"pradhanmantri", "pradhan mantri", "pradhan"},
    {"primary"}, {"secondary"}, {"higher"},
]


# What kind of programme a name says it is. These are stop words, so the content-word
# rules never see them, and a containment match could join a Mission to a Scheme that
# shares its subject: the Union Budget's Export Promotion Mission was joined to myScheme's
# Export Promotion Capital Goods Scheme, a duty-exemption licence. Mission and abhiyan are
# one kind (Poshan Abhiyaan is the National Nutrition Mission); scheme, yojana and
# programme are the other.
KINDS = [{"mission", "abhiyan", "abhiyaan"},
         {"scheme", "schemes", "yojana", "yojna", "programme", "program"}]


# Every feature of a name is a pure function of the name, and the same few thousand names
# are compared hundreds of thousands of times: the registry, the site build and the Union
# classifier spent most of their time recomputing them (registry 77 s, classify 63 s).
# Cached as immutable values; callers get a fresh list or set, so one that edits its copy
# cannot change what the next caller sees.
_CACHE = 1 << 16


def _as_list(f):
    cached = functools.lru_cache(maxsize=_CACHE)(lambda s: tuple(f(s)))
    return functools.wraps(f)(lambda s: list(cached(s)))


def _as_set(f):
    cached = functools.lru_cache(maxsize=_CACHE)(lambda s: frozenset(f(s)))
    return functools.wraps(f)(lambda s: set(cached(s)))


def kind_conflict(a, b):
    """Both names declare a kind, and no kind is common to them."""
    ka = {i for i, k in enumerate(KINDS) if k & set(norm(a).split())}
    kb = {i for i, k in enumerate(KINDS) if k & set(norm(b).split())}
    return bool(ka and kb and not ka & kb)


@functools.lru_cache(maxsize=_CACHE)
def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _singular(t):
    """Crude but safe: a trailing s on a long word carries no meaning here.

    "Electric Vehicles" against "Electric Vehicle in India" scored no match at all, so FAME
    failed to join its own expansion and was reported absent from a portal that lists it.
    That is the expensive direction, because an absence claim is an accusation. Guarded to
    words over four letters and not ending in ss, so "less", "gross" and "PACS" survive.
    """
    return t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t


@_as_list
def tokens(s):
    return [_singular(t) for t in norm(s).split() if t not in STOP and len(t) > 2]


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


@_as_set
def skeletons(s):
    # A two-character skeleton is noise: "MEIS and SEIS" against "Scheme for SSI / MSI
    # Sector" agreed on ['ms', 'ss'] and matched. But DROPPING those, which is what this
    # did first, deletes the word instead of the noise: "old" de-vowels to "ld" and "age"
    # to "g", so National Old Age Pension reduced to {ntnl, pnsn}, a strict subset of
    # National Widow Pension, and the two matched on brand words alone. Falling back to the
    # raw token keeps the word distinguishing while still refusing the vowel-less pair.
    return {k if len(k) >= 3 else t for t, k in
            ((t, skeleton(t)) for t in tokens(s))}


# Words that scheme names shout and that are not acronyms. "PMAY-URBAN-BLC Scheme" yields
# "urban" from the caps rule, which then matches every scheme with the word urban in it,
# and "Mission Shakti - SAMARTHYA - NATIONAL HUB" yields "national" the same way. Six of
# the seven false joins found on the Andhra Pradesh corpus came from this one hole, all of
# them from an ordinary English word that happened to be capitalised.
#
# QUALIFIERS already records that urban and rural describe a scheme rather than name it, so
# the list starts there and adds the descriptive words these books capitalise. It is a
# judgement list and deliberately visible as one: the alternative is a dictionary, and a
# dictionary would also throw away SAMARTHYA, POSHAN and VATSALYA, which are exactly the
# coined words that make good acronyms.
NOT_ACRONYMS = ({w for group in QUALIFIERS for w in group} |
                {"national", "state", "central", "centre", "center", "government",
                 "women", "woman", "child", "children", "girls", "boys", "youth",
                 "welfare", "development", "empowerment", "assistance", "subsidy",
                 "pension", "scholarship", "insurance", "housing", "health", "education",
                 "employment", "training", "mission", "scheme", "schemes", "programme",
                 "yojana", "hub", "other", "others", "general", "special", "total",
                 "component", "components", "share", "grant", "grants", "fund", "funds",
                 # Geography and filler, from "Competitive Exams of ALL INDIA level",
                 # which made "india" an acronym and matched Green India Mission.
                 "india", "indian", "bharat", "level", "exams", "examination",
                 "examinations", "college", "school", "schools", "district", "districts",
                 "rural", "urban", "board", "corporation", "department", "ministry",
                 # Seventh instance, from the CAG catalogue. Budget statements append a
                 # shouted category to a scheme name, "Bharat-VISTAAR CENTRAL SECTOR
                 # SCHEMES", and every word of it became an acronym: "sector" alone
                 # produced 297 false joins against audit titles.
                 "sector", "sectors", "finance", "financial", "micro", "macro",
                 "economic", "social", "revenue", "civil", "defence", "railway",
                 "railways", "works", "public", "sanction", "sanctions"}
                # Roman numerals. Indian budget documents are full of them, standards VI to
                # VIII and Chapter XVII, and every one was being read as a written acronym.
                | {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi",
                   "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"}
                # Community abbreviations. The same axis QUALIFIERS already knows as sc, st
                # and obc, but written as initials, so they read as acronyms and carried
                # matches on their own: VJNT alone produced 125 wrong joins on Maharashtra,
                # the largest single hole found. A community is who a scheme is for and
                # never which scheme it is.
                | {"vjnt", "sbc", "sbs", "dnt", "ebc", "nt", "obc", "sebc", "bpl", "apl"}
                # State and city names, for the same reason india and bharat are here.
                # "SWACHHA ODISHA" made odisha an acronym and matched six unrelated rows.
                | {"odisha", "orissa", "bengal", "maharashtra", "karnataka", "kerala",
                   "gujarat", "rajasthan", "punjab", "haryana", "assam", "bihar",
                   "telangana", "andhra", "tamil", "nadu", "pradesh", "delhi", "goa",
                   "sikkim", "manipur", "mizoram", "tripura", "meghalaya", "nagaland",
                   "jharkhand", "chhattisgarh", "uttarakhand", "ladakh", "kashmir"}
                # Tax and fund abbreviations that are not schemes.
                | {"sgst", "cgst", "igst", "gst", "sdrf", "ndrf", "cess"}
                # A ministry, a lender, a budget cut and a person are none of them a scheme.
                # ayush produced 16 wrong joins in Tripura, nabard 22, and scsp is a
                # Scheduled Caste Sub Plan cut that every state books under.
                | {"ayush", "nabard", "nabard", "scsp", "tsp", "sccs", "gandhi",
                   "ambedkar", "padma", "medical", "hospital", "college", "nskfdc"}
                # Eighth and ninth instances, and these two were already corrupting the
                # registry rather than merely inflating a join. "Solar Power (Grid)" was
                # merged into "SERB - POWER Fellowship" and its Rs 1,775 cr published under
                # that name; "e-Courts Phase II" was merged into "Swachh Bharat Mission
                # Grameen PHASE I".
                | {"power", "phase", "grid", "energy", "solar", "wind", "water",
                   "health", "roads", "authority", "council", "committee", "society"}
                # Tenth, from the acronym rewrite of 2026-10-30. SEED is the DNT scheme's
                # acronym and also the word in "Seed Program", a record that is nothing but
                # the word: Rs 101 cr moved between two unrelated Seed schemes on it.
                | {"seed"})


@_as_set
def written_acronyms(s):
    """Only acronyms the source actually WRITES as one: bracketed, or in capitals.

    Separate from the initials this project derives, because the two are not equally good
    evidence. An initialism computed from a long name collides constantly: "Faster Adoption
    and Manufacturing of Hybrid and Electric Vehicles" gives famhev and "Financial
    Assistance for Marriage" gives famh, and one contains the other. Neither name was
    written that way by anybody.
    """
    out = set()
    for m in re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{2,12})\)", s or ""):
        if m == m.upper() and norm(m).replace(" ", "") not in NOT_ACRONYMS:
            out.add(norm(m).replace(" ", ""))
    letters = re.sub(r"[^A-Za-z]", "", s or "")
    if not (letters and letters == letters.upper() and len(norm(s).split()) >= 3):
        for w in re.findall(r"\b([A-Z][A-Z0-9]{3,8})\b", s or ""):
            if w.lower() not in NOT_ACRONYMS:
                out.add(w.lower())
    return {a for a in out if len(a) >= 4}


@_as_set
def acronyms(s):
    """Acronyms this name could be written as, plus any it already contains.

    "Mahatma Gandhi National Rural Employment Guarantee Act" -> "mgnrega", and a
    bracketed "(PMAY)" is picked up directly.
    """
    out = set()
    # Initials are taken from the WORDS, never from an acronym the name already prints.
    # "State Disaster Response Fund (SDRF)" was yielding sdrfs, its own initials with its
    # own acronym appended, which then equalled the real acronym of "Stamp Duty and
    # Registration Fee Subsidy (SDRFS)". An acronym counted as a letter of itself.
    # The RAW extraction, not written_acronyms(), which filters through NOT_ACRONYMS and so
    # returns nothing for an abbreviation listed there: sdrf is on that list as a fund name,
    # which left it in the word list and rebuilt the very initialism this excludes.
    printed = {norm(m).replace(" ", "") for m in
               re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{2,12})\)", s or "") if m == m.upper()}
    printed |= {w.lower() for w in re.findall(r"\b([A-Z][A-Z0-9]{3,})\b", s or "")}
    words = [w for w in norm(s).split() if len(w) > 1 and w not in printed]
    if len(words) >= 3:
        out.add("".join(w[0] for w in words))
        big = [w for w in words if w not in STOP]
        if len(big) >= 3:
            out.add("".join(w[0] for w in big))
    # The caps rule below applies here too. A bracketed word is an acronym when it is
    # written as one, "(PMAY)", and is a qualifier when it is not, "(Rural)". Taking every
    # bracketed word made "rural" an acronym of "INDIRAMMA Disabled Pension (Rural)", which
    # then matched any name containing the word rural. Found while joining Andhra Pradesh,
    # where it produced 22 of 31 false matches.
    for m in re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{2,12})\)", s or ""):
        if m == m.upper() and norm(m).replace(" ", "") not in NOT_ACRONYMS:
            out.add(norm(m).replace(" ", ""))
    # Only genuine acronym forms. An earlier version added any word of four or more
    # letters, which made "Shiksha" an acronym and matched "Samagra Shiksha" to the
    # unrelated "Samaaveshit Shiksha". A word counts only if the source writes it in
    # caps — MGNREGA, PMAY, JJM — which is what an acronym actually looks like.
    # ...and the caps rule needs case to exist before it can read anything from it. Andhra
    # Pradesh prints many scheme names entirely in capitals, where "NATIONAL RURAL
    # LIVELIHOOD MISSION" yielded national, rural, livelihood and mission as acronyms and
    # matched almost anything. When a source shouts every word it has said nothing about
    # which are acronyms, so this branch stands down and only the initials survive.
    #
    # Length is what separates the two cases. An acronym is short by construction, so
    # "DAY-NRLM" and "PMAY" are upper case BECAUSE they are acronyms and must keep working:
    # suppressing those broke the DAY-NRLM test below.
    #
    # TWO refinements, both from states that shout their scheme names.
    #
    # Two space-separated words of unbroken capitals is already a shouted title, not a code.
    # Requiring three let "KIYOSK CONSTRUCTION" through, and Jharkhand prints every banner
    # in capitals: acronyms("KIYOSK CONSTRUCTION") gave construction and kiyosk while
    # acronyms("Kiyosk Construction") gave nothing, which is a controlled pair showing the
    # rule keys on typography rather than meaning. DAY-NRLM survives because it carries no
    # space.
    #
    # And a caps word over 8 letters is not an acronym in any case. That is what catches
    # the names this guard cannot see at all, where one lower-case fragment anywhere makes
    # the whole string mixed case: Delhi appends "GIA-Capital" and "Dr." to shouted names,
    # so CONSTRUCTION, PROCUREMENT, INSTITUTE, EXTENSION and TRANSPORT all read as acronyms.
    # The longest real acronym in this corpus is HPBOCWWB at 8.
    letters = re.sub(r"[^A-Za-z]", "", s or "")
    shouted = bool(letters) and letters == letters.upper() and len((s or "").split()) >= 2
    if not shouted:
        for w in re.findall(r"\b([A-Z][A-Z0-9]{3,8})\b", s or ""):
            if w.lower() not in NOT_ACRONYMS:
                out.add(w.lower())
    return {a for a in out if len(a) >= 4}


@_as_set
def qualifier_groups(s):
    """Which qualifier axes a name actually names."""
    n = norm(s)
    out = set()
    for i, group in enumerate(QUALIFIERS):
        if any(re.search(rf"\b{re.escape(w)}\b", n) for w in group):
            out.add(i)
    return out


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
    # A group must be listed on an axis or qualifier_conflict never fires for it: adding
    # the two to QUALIFIERS alone fixed MRKVY against RKVY, which goes through a different
    # rule, and left MMSY against PMMSY matching.
    [{"mukhyamantri", "mukhya mantri", "mukhya"},
     {"pradhanmantri", "pradhan mantri", "pradhan"}],
]


def _same_axis(g1, g2):
    for axis in _AXES:
        if any(g1 == g for g in axis) and any(g2 == g for g in axis):
            return True
    return False


# THE ACRONYM RULE, REWRITTEN ON 2026-10-30 AGAINST 1,310 HAND-LABELLED PAIRS.
#
# The rules this replaced accepted a pair whenever some acronym lined up: a capitalised
# word against the same word in another name (MANTRI, POSHAN, BIRSA), two initialisms that
# happen to coincide (PMSS is both "Prime Ministers Scholarship Scheme" and "Post Matric
# Scholarship Scheme"), or an umbrella acronym shared by siblings (two AICTE scholarships,
# 131 pairs of MSME schemes). Of the 1,310 pairs they accepted alone, 912 were different
# schemes. tests/test_match_acronyms.py holds the labels and holds this rule to them.
#
# An acronym is evidence of exactly one thing: that a short form and a long form name the
# same words. So it counts only when one name WRITES it (bracketed, in capitals, or is
# nothing but it, "Svamitva") and the other writes it too or spells it out, and then two
# things must hold:
#
#   1. If both names spell it out, the spellings agree word for word, allowing for
#      transliteration (Maatru / Matru) and a word inside a longer one (Dayal / Deendayal).
#      That is what rejects PMSS, STARS, and Silk against Sugar.
#   2. What is left of the two names once the acronym and its spelling are removed agrees:
#      empty on one side (the parent and its component, "PMMSY: Insulated Vehicles"), or one
#      inside the other. That is what rejects the umbrella siblings and the names that only
#      mention a body, an Act or a person.
#
# A qualifier left over on one side (Mukhyamantri, Urban) is a variant unless the other name
# carries it too; that is what rejects the state's Mukhyamantri Rajya Krishi Vikas Yojana
# against the Union's RKVY, which spell RKVY the same way. And a body (an agency, a
# university, a corporation) is not the schemes it runs.

# Words a budget line adds that say nothing about which scheme it is.
_LEFTOVER_NOISE = ({"share", "central", "centre", "state", "states", "general", "scsp", "scp",
                    "tsp", "css", "gia", "salary", "capital", "centrally", "sponsored",
                    "assisted", "sector", "ocasps", "sna", "committed", "liabilities", "under",
                    "including", "with", "through", "from", "amount", "met", "transfer",
                    "transfers", "deduct", "payment", "grant", "grants", "erstwhile",
                    "india", "union", "territory", "chandigarh", "puducherry", "pondicherry",
                    "daman", "diu", "dadra", "nagar", "haveli", "dnh", "lakshadweep",
                    "andaman", "nicobar", "jammu", "uttar", "madhya", "himachal", "arunachal",
                    "west", "sca", "yojan", "yojane", "yojona", "plan", "sparsh"}
                   | {w for w in NOT_ACRONYMS if w in {
                       "odisha", "orissa", "bengal", "maharashtra", "karnataka", "kerala",
                       "gujarat", "rajasthan", "punjab", "haryana", "assam", "bihar",
                       "telangana", "andhra", "tamil", "nadu", "pradesh", "delhi", "goa",
                       "sikkim", "manipur", "mizoram", "tripura", "meghalaya", "nagaland",
                       "jharkhand", "chhattisgarh", "uttarakhand", "ladakh", "kashmir"}})


_CODE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z]{2,})+\b")


def _codes(s):
    """Codes written in capitals with hyphens, "DAY-NRLM", joined: daynrlm."""
    return {c.replace("-", "").lower() for c in _CODE.findall(s or "")}


def _code_parts(s):
    """The pieces of those codes: day, nrlm."""
    return {part.lower() for c in _CODE.findall(s or "") for part in c.split("-")}


@functools.lru_cache(maxsize=_CACHE)
def _words(s, joined=False):
    """The words of a name with the acronyms it prints taken out, as acronyms() does.
    joined reads a hyphenated word as one ("Ex-servicemen"), which is how RMEWF spells."""
    printed = {norm(m).replace(" ", "") for m in
               re.findall(r"\(([A-Za-z][A-Za-z0-9\-]{2,12})\)", s or "") if m == m.upper()}
    printed |= {w.lower() for w in re.findall(r"\b([A-Z][A-Z0-9]{3,})\b", s or "")}
    printed |= _code_parts(s)
    text = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", "", s or "") if joined else s
    out = []
    for w in norm(text).split():
        if w == "pm":
            out += ["pradhan", "mantri"]       # PM-USP spells Pradhan Mantri, two letters
        elif w not in printed:
            out.append(w)
    return tuple(out)


def _spelling(words, x, whole=frozenset()):
    """The run of words whose initials spell x, or None. Four readings: every word; every
    word but the stop words; every word but stop words and words of two letters (the ka of
    "Ude Desh ka Aam Nagrik"); and every word but of, for, and (YASASVI keeps its Scheme)."""
    for skip in (lambda w: len(w) < 2, lambda w: w in STOP or len(w) < 2,
                 lambda w: w in STOP or len(w) < 3, lambda w: w in _FUNCTION or len(w) < 2):
        for i, first in enumerate(words):
            if skip(first) or first[0] != x[0]:
                continue
            got, j = "", i
            while j < len(words) and len(got) < len(x):
                if not skip(words[j]):
                    # A word that is itself a written acronym gives all its letters: "Mahatma
                    # Gandhi NREGA" spells MGNREGA.
                    got += words[j] if words[j] in whole else words[j][0]
                    if not x.startswith(got):
                        break
                j += 1
            if got == x:
                return words[i:j]
    return None


_FUNCTION = {"the", "of", "for", "and", "a", "an", "in", "to", "on"}
_SYNONYMS = [{"prime", "pradhan", "pradhana"}, {"minister", "ministers", "mantri", "manthri"},
             {"rural", "gramin", "grameen", "grameena", "gramina"}, {"urban", "shahari", "shehari"}]


@functools.lru_cache(maxsize=_CACHE)
def _letters(s):
    """Every letter a spelling of s could use, in order: the first of each word, all of a
    written acronym, and both of PM. A spelling of x needs x in order among them."""
    whole = written_acronyms(s)
    return "".join(w if w in whole else "pm" if w == "pm" else w[0] for w in norm(s).split())


def _in_order(x, letters):
    it = iter(letters)
    return all(c in it for c in x)


@functools.lru_cache(maxsize=1 << 18)
def _spelt(s, x):
    """x spelt out in s, as a tuple of words, or None: the three readings of s in turn."""
    if not _in_order(x, _letters(s)):
        return None
    whole = frozenset(w for w in written_acronyms(s) if x not in w)
    got = (_spelling(_words(s), x) or _spelling(_words(s, True), x)
           or _spelling(norm(s).split(), x, whole))
    return tuple(got) if got else None


@functools.lru_cache(maxsize=1 << 18)
def _word_like(u, v):
    return (u == v or any(u in g and v in g for g in _SYNONYMS) or skeleton(u) == skeleton(v)
            or (min(len(u), len(v)) >= 4 and (u in v or v in u))
            or difflib.SequenceMatcher(None, u, v).ratio() >= 0.75)


def _inside(small, large):
    """Every word of small has a counterpart in large."""
    return all(any(_word_like(u, v) for v in large) for u in small)


def _content(words):
    return [_singular(w) for w in words if w not in STOP and len(w) > 2]


@functools.lru_cache(maxsize=1 << 18)
def _leftover(s, x, spelt):
    """The content words of s that are neither the acronym nor its spelling."""
    n = norm(s)
    for cut in ("special component plan", "tribal area sub plan", "tribal sub plan",
                "scheduled caste sub plan", "scheduled tribe sub plan"):
        n = n.replace(cut, " ")
    if " renamed as " in f" {n} ":
        # "Development of Fresh Water Aquaculture Renamed as Pradhan Mantri Matsya Sampada
        # Yojana": a line that says it was renamed is its new name.
        n = n.split(" renamed as ", 1)[1]
    used = {_singular(w) for w in spelt or ()}
    codes = _code_parts(s)
    words = [_singular(w) for w in n.split()
             if (w not in STOP and len(w) > 2) or w in _SHORT_QUALIFIERS]
    return frozenset(w for w in words
                     if w not in used and x not in w and not (w in codes and w in x)
                     and w not in _LEFTOVER_NOISE and not w.isdigit())


# Qualifiers too short for a content word, which are exactly the ones that matter: "for ST
# students" against a generic Post-Matric Scholarship.
_SHORT_QUALIFIERS = {q for g in QUALIFIERS for q in g if len(q) <= 2}

_BODY = {"agency", "authority", "corporation", "council", "university", "board", "society",
         "department", "directorate", "institute", "institutes", "organisation",
         "organization", "trust", "limited", "ltd", "commission", "federation", "academy"}


def _added_qualifier(left, other, other_left):
    """A qualifier in what is left of one name that the other name does not carry.
    Who announced it (Mukhyamantri against the Union's RKVY), who it is for (ST against a
    generic Post-Matric Scholarship) and Special (against the plain CLCS) always make a
    different scheme. Urban does only when the other name adds something of its own:
    "PMAY Urban" is a component of plain PMAY."""
    if "special" in left and "special" not in norm(other).split():
        return True
    on = " " + norm(other) + " "
    if re.search(r" (pm|pradhanmantri|pradhanamantri|prime minister) ", on):
        on += " pradhan "
    if re.search(r" (cm|chief minister) ", on):
        on += " mukhya "
    text = " " + " ".join(sorted(left)) + " "
    # Who announced it, and the community, stage or sex a scheme is for, always make a
    # variant (the comment on probably_same's containment rule has the history). Rural and
    # urban make one only when the other side adds something of its own.
    # Pradhan Mantri added to a name silent on who announced it is the same Union scheme
    # written in full (KUSUM against PM-KUSUM); Mukhyamantri added is the state's own.
    always = [g for g in QUALIFIERS if not g & {"rural", "urban", "pradhan"}]
    return any(any(f" {q} " in text for q in g) and not any(f" {q} " in on for q in g)
               for g in (QUALIFIERS if other_left else always))


_FILLER = {"state", "central", "share", "general"}


def _bare(s):
    """A short name read as one word: "PM KISAN" -> pmkisan, "Svamitva Yojana" -> svamitva.
    Empty when that word is one NOT_ACRONYMS lists: "Seed Program" is not SEED."""
    b = "".join(w for w in norm(s).split() if w not in STOP and w not in _FILLER)
    return "" if b in NOT_ACRONYMS else b


def _side_by_side(s, x):
    """The words of a bare name stand next to each other in s: "PM KISAN" in "Pradhan
    Mantri Kisan Samman Nidhi (PM-Kisan)"."""
    words = norm(s).split()
    return any("".join(words[i:j]) == x for i in range(len(words))
               for j in range(i + 2, min(i + 4, len(words)) + 1))


def _stands_alone(s, x):
    """x is written as a name of its own somewhere in s, not as the tail of another name:
    "SAHAKAR MITRA" does not write MITRA the way "PM - MITRA" does."""
    for seg in re.split(r"[-:(),/\u2013\[\]]", s or ""):
        words = norm(seg).split()
        for i, w in enumerate(words):
            if w == x and (i == 0 or words[i - 1] in _FUNCTION | _FILLER | STOP
                           | {"pm", "pradhan", "mantri", "under", "through", "by", "national",
                              "rashtriya"}):
                return True
    return x in _codes(s) or x in {norm(m).replace(" ", "") for m in
                                   re.findall(r"\(([A-Za-z][A-Za-z0-9\- ]{2,14})\)", s or "")}


@functools.lru_cache(maxsize=_CACHE)
def _plain_initials(s):
    """Initials of a name without the words that say nothing about which scheme it is:
    "Paramparagat Krishi Vikas Yojana - Uttarakhand" is PKVY, not PKVYU."""
    words = [w for w in norm(s).split() if w not in _LEFTOVER_NOISE and len(w) > 1]
    out = {"".join(w[0] for w in words), "".join(w[0] for w in words if w not in STOP)}
    return frozenset(x for x in out if len(x) >= 4)


def _long_form(s, x):
    """The phrase a name brackets x after, "Strengthening Teaching-Learning and Results for
    States (STARS)": the words back to the previous dash, colon or bracket. None if x is not
    bracketed."""
    for m in re.finditer(r"\(([A-Za-z][A-Za-z0-9\- ]{2,14})\)", s or ""):
        if norm(m.group(1)).replace(" ", "") == x:
            before = re.split(r"[-:(/\u2013]", s[:m.start()])[-1]
            words = [w for w in _content(norm(before).split()) if w not in _LEFTOVER_NOISE]
            return words or None
    return None


def acronym_evidence(a, b):
    """The reason an acronym shows a and b to be one scheme, or None. See above."""
    wa, wb = written_acronyms(a), written_acronyms(b)
    for p, q, wp, wq in ((a, b, wa, wb), (b, a, wb, wa)):
        short = [w for w in norm(p).split() if w not in STOP and w not in _FILLER]
        mine = set(wp) | _codes(p)
        if 1 <= len(short) <= 2 and _bare(p):
            mine.add(_bare(p))                # "PM KISAN", "Svamitva": the name is the acronym
        cands = set(mine)
        cands |= {x for x in acronyms(p) if len(x) >= 5}    # initialisms, spellings checked below
        cands |= _plain_initials(p)
        for x in sorted(cands):
            if len(x) < 4:
                continue
            spelt_p, spelt_q = _spelt(p, x), _spelt(q, x)
            q_writes = x in wq or x in _codes(q) or x == _bare(q) or (
                x == _bare(p) and _side_by_side(q, x))
            if x in mine:
                if not (q_writes or spelt_q):
                    continue
                # Written by both and spelt out by neither: each must write it as a name of
                # its own, or "PM - MITRA" is the same scheme as "SAHAKAR MITRA".
                if not (spelt_p or spelt_q) and not (
                        (_stands_alone(p, x) or x == _bare(p)) and
                        (_stands_alone(q, x) or x == _bare(q))):
                    continue
            elif not (spelt_p and spelt_q):
                continue                       # an initialism only counts if both spell it
            if spelt_p and spelt_q:
                cp = [w for w in spelt_p if len(w) > 2 and w not in _FUNCTION]
                cq = [w for w in spelt_q if len(w) > 2 and w not in _FUNCTION]
                if not (cp and cq and _inside(cp, cq) and _inside(cq, cp)):
                    continue
            elif spelt_p or spelt_q:
                # One spells x out and the other only brackets it after a phrase of its own:
                # that phrase is its long form, and the two long forms must agree.
                known = _content(spelt_p or spelt_q)
                other = _long_form(q if spelt_p else p, x)
                if other:
                    shared = sum(1 for u in known if any(_word_like(u, v) for v in other))
                    if shared < min(2, len(known)) or shared * 2 < min(len(known), len(other)):
                        continue
            # A name that brackets x after a phrase gives that phrase as its long form even
            # when its initials do not spell x, as a backronym's do not: "Atal Vayo Abhyuday
            # Yojana (AVYAY)". Two such phrases must agree, which is what rejects STARS.
            long_p = None if spelt_p else _long_form(p, x)
            long_q = None if spelt_q else _long_form(q, x)
            # ...giving up only words whose initials x uses: "Pradhanmanthri Awas Yojna Grami
            # (PMAY)" keeps Grami, which is what tells it from PMAY-Urban.
            long_p = [w for w in long_p if w[0] in x] if long_p else None
            long_q = [w for w in long_q if w[0] in x] if long_q else None
            if long_p and long_q and not (_inside(long_p, long_q) or _inside(long_q, long_p)):
                continue
            rp = _leftover(p, x, spelt_p or (tuple(long_p) if long_p else None))
            rq = _leftover(q, x, spelt_q or (tuple(long_q) if long_q else None))
            if rp and rq and not (_inside(rp, rq) or _inside(rq, rp)):
                continue
            adds_p = {u for u in rp if not any(_word_like(u, v) for v in rq)}
            adds_q = {u for u in rq if not any(_word_like(u, v) for v in rp)}
            if _added_qualifier(rp, q, adds_q) or _added_qualifier(rq, p, adds_p):
                continue
            # An initialism nobody wrote compares two spellings of one name. It may still
            # join a name to a longer one that OPENS with it, as the prefix rule above does
            # ("PKVY - RKVY (Green Revolution)"), but not to a component named at the end of
            # an umbrella: "Saksham Anganwadi and POSHAN 2.0 (..., Scheme for Adolescent
            # Girls)" is not the Scheme for Adolescent Girls.
            if x not in mine and x not in wq and bool(rp) != bool(rq):
                longer, spelt = (p, spelt_p) if rp else (q, spelt_q)
                opening = [w for w in norm(longer).split() if w not in _LEFTOVER_NOISE]
                if tuple(opening[:len(spelt)]) != tuple(spelt):
                    continue
            # A body is not a scheme it runs. "Grants to Tamil Nadu Agricultural University"
            # is not "Organizing Block Demonstration Through ... TNAU", so a name that is only
            # the body matches only another name that is only the body.
            body = any(w in _BODY for w in (spelt_p or ())[-1:] + (spelt_q or ())[-1:])
            if body and bool(rp) != bool(rq):
                continue
            how = ("spelt out by both" if spelt_p and spelt_q else
                   "written by one, spelt out by the other" if spelt_p or spelt_q else
                   "written by both")
            rest = ", the rest agrees" if rp and rq else ", nothing else on one side"
            return f"acronym {x}: {how}{rest}"
    return None


@functools.lru_cache(maxsize=1 << 18)
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

    sim = similarity(a, b)
    if sim >= floor:
        return True, f"similarity {sim:.2f}"

    ta, tb = set(tokens(a)), set(tokens(b))
    if ta and tb:
        small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
        # Containment needs the two names to be comparable, not merely overlapping. A
        # two-word name is often a generic domain phrase that any long name in that domain
        # contains: "Animal Husbandry" sits inside "Buildings- Animal Husbandry
        # (Administered by Chief Engineer (Buildings))", which is a works head and not that
        # scheme. On the Tamil Nadu demand books this rule alone produced 63 of 118 wrong
        # joins, every one of them a short generic phrase swallowed by a long specific name.
        #
        # Three or more content words is specific enough to stand on its own. Two is only
        # evidence when the longer name is not much longer, so the pair has to be within a
        # factor of two.
        # A name that adds a community, a stage or a sex to another name is a VARIANT of
        # it, not the same scheme. qualifier_conflict above only fires when both names take
        # a side, so "Pre-Matric Scholarship Scheme" against "Pre-Matric Scholarship to
        # Scheduled Caste Students" slipped through and the generic name then matched the
        # SC, ST and OBC siblings alike, counting three schemes as one. Found on the Tamil
        # Nadu demand books, 9 joins.
        #
        # Containment is the rule that needs this guard, because it is satisfied by
        # definition when the longer name is the shorter plus a qualifier. A pair like Jal
        # Jeevan Mission against its own longer title is unaffected: it matches on the
        # prefix rule above, which fires first.
        adds_qualifier = bool(qualifier_groups(a) ^ qualifier_groups(b))
        if small <= large and not adds_qualifier and not kind_conflict(a, b) and (
                len(small) >= 3 or (len(small) >= 2 and len(large) <= 2 * len(small))):
            return True, f"all {len(small)} content words of the shorter name are present"

    # Same content words once transliteration is folded out. Two or more skeletons must
    # line up, because a skeleton is lossy enough that one alone proves little: mata,
    # mati and moti all reduce to mt. The exception is a name whose only content word is
    # the scheme's name, "Shakthi Scheme" against "Shakti Scheme", where there is no
    # second word to corroborate with. There the raw tokens must also look alike, which
    # shakthi/shakti does at 0.92 and mata/moti does not at 0.50.
    # A name that BEGINS with the whole of the other is a much stronger signal than one
    # that merely contains its words somewhere. "Jal Jeevan Mission (JJM) / National Rural
    # Drinking Water Mission" opens with "Jal Jeevan Mission" and is that scheme; "Buildings-
    # Animal Husbandry (Administered by Chief Engineer)" opens with Buildings and is a works
    # head that happens to mention the department. Word boundary enforced, so "Jal Jeevan"
    # does not prefix-match "Jal Jeevandhara".
    na, nb = norm(a), norm(b)
    if na and nb and na != nb:
        shortn, longn = (na, nb) if len(na) <= len(nb) else (nb, na)
        # Three words at least, counting the connectives. Asking only for eight characters
        # let a bare place name prefix anything: "West Bengal" against "West Bengal Student
        # Credit Card Scheme", 49 joins from two subjects.
        #
        # Three RAW words rather than two content words, because that is what separates the
        # two cases: "Jal Jeevan Mission" is three words of which Mission is a stop word, and
        # "West Bengal" is two. A state name is short and a scheme name says what it does.
        if len(shortn) >= 8 and longn.startswith(shortn) and \
                longn[len(shortn):len(shortn) + 1] in ("", " ") and \
                len(shortn.split()) >= 3:
            return True, "one name begins with the whole of the other"

    ta_, tb_ = tokens(a), tokens(b)
    sa, sb = skeletons(a), skeletons(b)
    if sa and sb:
        small, large = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
        # Same comparability guard as the content-word rule below it. Folding
        # transliteration does not make a short generic phrase any more specific, so
        # without this the skeleton rule simply catches what containment now rejects.
        # The same variant guard as the content-word rule below. Folding transliteration
        # does not make a Scheduled Tribe scholarship into its parent scheme, and without
        # this the skeleton rule simply catches what containment now rejects.
        if small <= large and not qualifier_groups(a) ^ qualifier_groups(b) \
                and not kind_conflict(a, b):
            if len(small) >= 3 or (len(small) >= 2 and len(large) <= 2 * len(small)):
                return True, f"transliteration variant: {sorted(small)[:3]}"
            if len(ta_) == 1 and len(tb_) == 1 and \
                    difflib.SequenceMatcher(None, ta_[0], tb_[0]).ratio() >= 0.8:
                return True, f"transliteration variant: {ta_[0]} / {tb_[0]}"

    why = acronym_evidence(a, b)
    if why:
        return True, why

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
    # A shouted title is not a code, and two words is already shouting. Jharkhand prints
    # every banner in capitals, and the controlled pair is the proof: "KIYOSK CONSTRUCTION"
    # yielded construction and kiyosk where "Kiyosk Construction" yielded nothing.
    ("Rearing Pond Construction Scheme", "KIYOSK CONSTRUCTION", False),
    # A ministry and a lender are not schemes. 16 and 22 wrong joins in Tripura.
    ("Healthy Lifestyle for School Children through Ayurvidya",
     "Establishment of National AYUSH Mission", False),
    ("Construction of NABARD-Funded Minor Irrigation Projects",
     "Redemeption of NABARD Loan", False),
    # Who announced it is who pays for it: one dropped letter between mmsy and pmmsy is a
    # state scheme against a central one.
    ("Mukhyamantri Matsya Sampada Yojana",
     "Pradhan Mantri Matsya Sampada Yojana (PMMSY)", False),
    ("Mukhyamantri Rajya Krishi Vikas Yojana", "Rastriya Krishi Vikas Yojana", False),
    # ...and the central family still matches itself.
    ("Pradhan Mantri Awas Yojana (PMAY)", "PMAY Urban", True),
]

SELFTEST += [
    # A community abbreviation is who a scheme is for, never which scheme it is. VJNT alone
    # produced 125 wrong joins on Maharashtra, the largest single hole found.
    ("Training Of Motor Driving To VJNT, SBS & OBC",
     "Tanda Vasti Sudhar Yojana For VJNT And SBC", False),
    # A skeleton must not delete the word that distinguishes. "old" de-vowels to "ld" and
    # "age" to "g", and dropping both made Old Age Pension a subset of Widow Pension.
    ("National Old Age Pension", "National Widow Pension", False),
    # A state's own name is not an acronym.
    ("SWACHHA ODISHA", "Odisha Cycle Scheme", False),
    # An acronym is not a letter of itself: "State Disaster Response Fund (SDRF)" was
    # yielding sdrfs, its initials with its own acronym appended.
    ("State Disaster Response Fund (SDRF)", "State Disaster Response Fund", True),
]

SELFTEST += [
    # A community variant is not the parent scheme. The generic name used to match all three
    # siblings, counting three schemes as one.
    ("Pre - Matric Scholarship to Scheduled Caste Students - State Share",
     "Pre-Matric Scholarship Scheme", False),
    ("Post Matric Scholarship to Scheduled Tribe Students",
     "Post Matric Scholarship Scheme", False),
    # ...and a longer title that adds no qualifier still matches.
    ("Jal Jeevan Mission (JJM) / National Rural Drinking Water Mission",
     "Jal Jeevan Mission", True),
]

SELFTEST += [
    # A trailing s must not defeat a match. FAME failed to join its own expansion.
    ("Scheme for Faster Adoption and Manufacturing of (Hybrid &) Electric Vehicles",
     "Scheme for Faster Adoption and Manufacturing of (Hybrid and) Electric Vehicle in India - (FAME - India).", True),
    ("Mid Day Meal", "Mid Day Meals Scheme", True),
    # An acronym buried in a long initialism is a coincidence of spelling.
    ("Storage Management and Movement of Food Grains in Food Coporation of India",
     "Sub-Mission on Agricultural Mechanization (SMAM) under Krishonnati Yojana", False),
    # A bare place name prefixes anything.
    ("West Bengal", "West Bengal Student Credit Card Scheme", False),
    # Two-character skeletons are not transliteration evidence.
    ("MEIS and SEIS", "Scheme for SSI / MSI Sector (PIPDIC)", False),
    # The live corruption: a shouted ordinary word merged a budget line into a fellowship.
    ("Solar Power (Grid)", "SERB - POWER Fellowship", False),
    ("e-Courts Phase II", "Swachh Bharat Mission - Grameen PHASE I", False),
]

SELFTEST += [
    # A short generic phrase inside a long specific name is not a match. 63 of Tamil Nadu's
    # 118 wrong joins were this shape.
    ("Buildings- Animal Husbandry (Administered by Chief Engineer (Buildings))",
     "Animal Husbandry", False),
    # ...while two comparable names still match on containment.
    ("Thalolam Scheme", "Thalolam", True),
    # A Roman numeral is not an acronym.
    ("Special incentive to scheduled caste girls studying VI standard to VIII standard",
     "Scholarship VIII", False),
]

SELFTEST += [
    # Capitalised geography is not an acronym. "Competitive Exams of ALL INDIA level" made
    # "india" one, which then matched Green India Mission.
    ("Green India Mission",
     "Coaching Assistance for Pre-preparation for Competitive Exams of ALL INDIA level", False),
    # Two DERIVED initialisms containing one another is not evidence. Neither of these was
    # written as an acronym by anybody.
    ("Faster Adoption and Manufacturing of Hybrid and Electric Vehicles",
     "Financial Assistance for Marriage (HPBOCWWB)", False),
]

SELFTEST += [
    # A capitalised ordinary word is not an acronym either. Both of these joined on one
    # shouted word, and between them they were six of seven false joins on Andhra Pradesh.
    ("PMAY-URBAN-BLC Scheme [AP345]", "INDIRAMMA Disabled Pension (Urban)", False),
    ("Mission Shakti - SAMARTHYA - NATIONAL HUB FOR WOMEN EMPOWERMENT",
     "National Mission on Edible Oils- Oil Palm", False),
    # ...while a coined caps word still is one, which is why this is a list and not a
    # dictionary lookup.
    ("MISSION VATSALYA", "Mission Vatsalya Scheme", True),
]

SELFTEST += [
    # A bracketed qualifier is not an acronym. This pair matched on "rural".
    ("INDIRAMMA Disabled Pension (Rural)", "Rural Water Supply Scheme", False),
    ("National Rural Livelihood Mission", "NATIONAL RURAL EMPLOYMENT GUARANTEE SCHEME", False),
    # ...while a bracketed acronym still is one.
    ("Pradhan Mantri Awas Yojana (PMAY)", "PMAY Urban", True),
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
    # Two words of a short name inside a longer one is weak evidence when the longer name
    # adds two more words that say what it is. The Union Budget's Export Promotion Mission
    # (a 2,300-crore line) was joined to myScheme's EPCG, a duty-exemption licence.
    ("Export Promotion Mission", "Export Promotion Capital Goods Scheme", False),
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
