"""
Devanagari to Latin, for matching rather than for scholarship.

AGENT-EDITABLE (PLAN.md §7). Pure function, no I/O. Self-tests: `python3 parse/devanagari.py`.

WHY THIS EXISTS. Uttar Pradesh is the largest state in India and publishes its entire
scheme universe in Hindi and only in Hindi: 65 Latin tokens across four budget volumes and
not one an English word. Its names extract perfectly and cannot be joined to myScheme,
which lists in English. That was recorded as a refusal, and the refusal was half right.

It is half right because myScheme does NOT list Uttar Pradesh's schemes in English. It
lists them in ROMANISED HINDI: "Kanya Sumangala Yojana", "Berojgari Bhatta Yojna",
"Gambhir Bimari Sahayata Yojana", "Mukhyamantri Samuhik Vivah Yojana". Roughly two thirds
of its 47 Uttar Pradesh records are a Hindi name written in Latin letters. So the join does
not need translation at all. It needs a change of SCRIPT, and that is a different kind of
operation with a different kind of error.

    Transliteration is deterministic, reversible in principle, and checkable: कन्या is
    kanya whatever the word means. Translation is a claim about MEANING, and a register
    whose whole argument is that it publishes only what it can check has no business
    making one in its own voice. So this converts script and never translates, and the
    Hindi text stays in the record as what Uttar Pradesh actually published.

HOW MUCH OF IT HAS TO BE RIGHT, which is the part worth understanding before editing this.
The output is not read by a person. It is fed to `parse.match.probably_same`, whose
`skeleton()` strips EVERY vowel and folds aspiration:

    कन्या सुमंगला योजना  ->  kanya sumangala yojana  ->  {kny, smngl, yjn}
    "Kanya Sumangala Yojana"                          ->  {kny, smngl, yjn}

For a word of any length the vowels therefore do not matter, which is lucky, because every
axis on which two offices disagree when they romanise the same Hindi word is a vowel axis
or an aspiration axis. myScheme alone writes Yojana and Yojna, Sahayta and Sahayata,
Protsahan and Protsaahan, Ravidas and Ravidaas, in one file. The skeleton was already built
to absorb exactly that, for Karnataka's Gruha Lakshmi against the portal's Griha Lakshmi.

SHORT WORDS ARE THE EXCEPTION, and they are why this file follows romanisation convention
instead of emitting a literal transcription. `skeletons()` falls back to the RAW token
whenever a skeleton comes out under three characters, deliberately: "old" de-vowels to
"ld" and "age" to "g", and a matcher that compared those would call National Old Age
Pension a subset of National Widow Pension. The fallback is load-bearing and correct. But
it means that for a short word the raw Latin is compared directly, so "baala" and "bal" do
NOT match while "bal" and "bal" do. Uttar Pradesh Mukhyamantri **Bal Seva** Yojana turns on
two such words.

So three conventions are applied, and each is a rule rather than a guess:

  * Long vowels are written short (आ as a, ई as i, ऊ as u). No romaniser of Hindi
    marks length consistently and myScheme does not either.
  * The word-final inherent vowel is dropped. Hindi does not pronounce it (प्रदेश is
    pradesh) and every romanisation follows the speech. This is applied only word-finally,
    where the rule is near-exceptionless; medial schwa deletion is real but irregular, and
    a medial vowel is one the skeleton discards anyway.
  * The anusvara is written m before a labial and n elsewhere, so गंभीर is gambhir rather
    than ganbhir. That is the phonological rule, not a preference, and unlike a vowel a
    nasal survives the skeleton and so decides matches.

None of this is translation and none of it looks at meaning.
"""

import re
import sys
import unicodedata

# Consonants. The value is the consonant cluster, never the inherent vowel; the caller
# adds that. Nukta forms are listed where they are conventionally romanised differently
# (ज़ is z, फ़ is f), because those are consonant distinctions and therefore survive the
# skeleton, unlike vowel length.
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    # Precomposed nukta consonants.
    "क़": "k", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
    "ऩ": "n", "ऱ": "r", "य़": "y",
}

INDEPENDENT_VOWELS = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ऋ": "ri", "ॠ": "ri", "ऌ": "li", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ऍ": "e", "ऎ": "e", "ऑ": "o", "ऒ": "o",
}

# Dependent vowel signs (matras). Same values as the independent vowels they stand for.
MATRAS = {
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "ॄ": "ri",
    "ॢ": "li", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ॅ": "e", "ॆ": "e", "ॉ": "o", "ॊ": "o",
}

VIRAMA = "्"     # halant: kills the inherent vowel
NUKTA = "़"
ZWJ, ZWNJ = "‍", "‌"

# Anusvara and chandrabindu are a nasal, visarga an h. WHICH nasal the anusvara stands for
# is decided by the consonant after it, and unlike a vowel a nasal survives the skeleton,
# so it decides matches: गंभीर romanised ganbhir gives the skeleton gnbr and myScheme's
# Gambhir gives gmbr, and the scheme is reported missing from a portal that lists it.
NASALS = {"ं": "n", "ँ": "n", "ः": "h"}
LABIALS = set("पफबभम")          # anusvara before one of these is m, everywhere else n

DIGITS = {"०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
          "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"}

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# Danda and double danda are full stops; the abbreviation sign appears in के० for केन्द्र.
PUNCTUATION = {"।": ".", "॥": ".", "॰": "."}


def has_devanagari(s):
    return bool(DEVANAGARI.search(s or ""))


def transliterate(s):
    """Devanagari to Latin. Text already in Latin passes through unchanged.

    Characters outside Devanagari are kept as they are, so a mixed string such as
    "0108- प्रधानमंत्री मातृ वन्दना योजना (के.60/रा.40)" keeps its codes and its
    punctuation and converts only the Hindi.
    """
    if not s:
        return s
    # Compose first: the same syllable can arrive as a precomposed क़ or as क + nukta, and
    # only one of those is in the table. NFC settles it before anything is looked up.
    s = unicodedata.normalize("NFC", s)
    out, i, n = [], 0, len(s)

    def letter(j):
        """Is s[j] a Devanagari letter, i.e. does the current word continue?"""
        return j < n and (s[j] in CONSONANTS or s[j] in INDEPENDENT_VOWELS
                          or s[j] in MATRAS or s[j] in NASALS
                          or s[j] == VIRAMA or s[j] == NUKTA)

    def nasal(j, mark):
        """n or m, decided by the consonant the nasal sits in front of."""
        if mark != "ं":
            return NASALS[mark]
        k = j
        while k < n and s[k] in NASALS:
            k += 1
        return "m" if k < n and s[k] in LABIALS else "n"

    while i < n:
        c = s[i]
        if c in (ZWJ, ZWNJ, NUKTA):
            i += 1
            continue
        if c in CONSONANTS:
            base = CONSONANTS[c]
            i += 1
            if i < n and s[i] == NUKTA:      # decomposed nukta on a consonant with no
                i += 1                       # precomposed form: a distinction not modelled
            if i < n and s[i] == VIRAMA:
                out.append(base)
                i += 1
                continue
            if i < n and s[i] in MATRAS:
                out.append(base + MATRAS[s[i]])
                i += 1
            elif i < n and s[i] in NASALS:
                out.append(base + "a")       # the inherent vowel, then the nasal below
            elif letter(i):
                out.append(base + "a")       # inherent vowel, word continues
            else:
                out.append(base)             # WORD-FINAL: Hindi does not say this vowel
            while i < n and s[i] in NASALS:
                out.append(nasal(i + 1, s[i]))
                i += 1
            continue
        if c in INDEPENDENT_VOWELS:
            out.append(INDEPENDENT_VOWELS[c])
            i += 1
            while i < n and s[i] in NASALS:
                out.append(nasal(i + 1, s[i]))
                i += 1
            continue
        if c in NASALS:
            out.append(nasal(i + 1, c))
            i += 1
            continue
        if c in DIGITS:
            out.append(DIGITS[c])
            i += 1
            continue
        if c in PUNCTUATION:
            out.append(PUNCTUATION[c])
            i += 1
            continue
        # A matra or virama with no consonant before it is a broken cluster, not a letter.
        # Dropping it silently is right: it carries no consonant and the skeleton would
        # discard whatever it produced.
        if c in MATRAS or c == VIRAMA:
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ------------------------------------------------------------------ self-tests

def _test():
    ok = True

    def eq(got, want, what):
        nonlocal ok
        if got != want:
            ok = False
            print(f"  FAIL {what}\n    got  {got!r}\n    want {want!r}")

    eq(transliterate("कन्या"), "kanya", "conjunct with virama")
    eq(transliterate("योजना"), "yojana", "matra is kept where the inherent vowel is not")
    eq(transliterate("मुख्यमंत्री"), "mukhyamantri", "anusvara inside a word")
    eq(transliterate("प्रदेश"), "pradesh", "word-final inherent vowel is dropped")
    eq(transliterate("बाल"), "bal", "and dropped after a long vowel too")
    eq(transliterate("सेवा"), "seva", "but a final MATRA is not an inherent vowel")
    eq(transliterate("मातृ"), "matri", "vocalic r matra")
    # The nasal is decided by what follows it, and it survives the skeleton.
    eq(transliterate("गंभीर"), "gambhir", "anusvara before a labial is m")
    eq(transliterate("दिव्यांग"), "divyang", "anusvara elsewhere is n")
    eq(transliterate("०१२"), "012", "Devanagari digits")
    eq(transliterate("Gr49 2026-27"), "Gr49 2026-27", "pure Latin passes through")
    eq(transliterate("04- कन्या सुमंगला योजना"),
       "04- kanya sumangala yojana", "mixed codes and Hindi")
    # A word that ends in an explicit virama has no inherent vowel to drop and must not
    # lose a consonant to the rule that drops one.
    eq(transliterate("परिषद्"), "parishad", "explicit virama at the end of a word")
    # A decomposed nukta must give the same answer as the precomposed character.
    eq(transliterate("ज़"), transliterate("ज़"), "nukta normalisation")
    eq(has_devanagari("Kanya"), False, "has_devanagari on Latin")
    eq(has_devanagari("कन्या"), True, "has_devanagari on Hindi")

    # The tests that matter: does the output JOIN myScheme's own romanisation? These are
    # real pairs, the Devanagari from Uttar Pradesh's grant volumes and the Latin from
    # myScheme's Uttar Pradesh records, and they are the whole reason this module exists.
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from match import probably_same
    pairs = [
        ("कन्या सुमंगला योजना", "Kanya Sumangala Yojana"),
        ("उत्तर प्रदेश मुख्यमंत्री बाल सेवा योजना",
         "Uttar Pradesh Mukhyamantri Bal Seva Yojana (Genearal)"),
        ("मुख्यमंत्री सामूहिक विवाह योजना", "Mukhyamantri Samuhik Vivah Yojana"),
        ("बेरोजगारी भत्ता योजना", "Berojgari Bhatta Yojna"),
        ("गंभीर बीमारी सहायता योजना", "Gambhir Bimari Sahayata Yojana"),
        ("कौशल विकास योजना", "Kaushal Vikas Yojana"),
        ("दिव्यांग पेंशन योजना", "Divyang Pension Yojana"),
    ]
    for dev, en in pairs:
        lat = transliterate(dev)
        hit, why = probably_same(lat, en)
        if not hit:
            ok = False
            print(f"  FAIL no join\n    {dev}\n    -> {lat}\n    vs {en}")

    # And the direction that costs more: two DIFFERENT schemes must not collapse into one
    # just because transliteration threw away the vowels that told them apart.
    apart = [
        ("विधवा पेंशन योजना", "Divyang Pension Yojana"),
        ("कन्या सुमंगला योजना", "Kanya Vivah Sahayta Yojana"),
        ("मुख्यमंत्री सामूहिक विवाह योजना", "Mukhyamantri Svadeshi Gau Samvardhan Yojana"),
    ]
    for dev, en in apart:
        lat = transliterate(dev)
        hit, why = probably_same(lat, en)
        if hit:
            ok = False
            print(f"  FAIL false join\n    {dev}\n    -> {lat}\n    == {en}   [{why}]")

    print(("all devanagari self-tests pass" if ok else "SELF-TESTS FAILED")
          + f"  ({len(pairs)} join pairs, {len(apart)} must-not-join pairs)")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _test() else 1)
