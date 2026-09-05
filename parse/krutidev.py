"""
Kruti Dev, the legacy 8-bit Devanagari encoding, decoded to Unicode.

AGENT-EDITABLE (PLAN.md 7). Pure function of its input. Never fetches, reads no files.

WHY THIS IS A READING AND NOT A GUESS, which is the only question that matters here.

Chhattisgarh publishes its Outcome, Gender, Youth and Child budgets in Kruti Dev: a font
in which the byte 'd' draws the glyph for क and ';' draws य. The bytes ARE the document;
what is missing is the table that says which glyph each byte draws. That table is fixed,
published, and the same in every Kruti Dev document ever typed, so applying it recovers the
characters that are on the page rather than proposing characters that might be.

That is the same line parse/devanagari.py draws from the other side. Script conversion is
deterministic and checkable; translation is a claim about meaning this register must not
make. Decoding a font encoding is script conversion, and this file is checked the way the
register checks everything: against evidence it did not produce.

THE EVIDENCE. Chhattisgarh's outcome index page lists all 33 department names in proper
Unicode Devanagari, and every one of those departments publishes a PDF whose first lines
carry the SAME name in Kruti Dev. That is a parallel corpus of 33 pairs that the state
wrote, not this register, and selftest() decodes the Kruti Dev half and requires it to
equal the Unicode half exactly. A table that is wrong anywhere those 33 names reach cannot
pass.

THE TWO RULES THAT ARE NOT ONE-TO-ONE, and everything else is a substitution.

    f before its consonant.  Kruti Dev writes the i-matra where it is PRINTED, to the left
                             of the consonant it belongs to, because the font has no way to
                             reorder glyphs. Unicode writes it after. "fnukad" is f+n+u+kad
                             and decodes to दिनांक, not ि द न ा ं क. So the decoder moves
                             every ि rightward past the consonant cluster it precedes.

    matra reordering for the reph and the trailing matras. "उ" and its relatives are
                             written as separate glyphs that follow the consonant in the
                             byte stream and precede it in nothing, so they need no move.

LONGEST MATCH FIRST. Several Kruti Dev codes are two or three bytes: "Ø" is क्र and "æ" is
द्ध, and a table applied character by character would decode the first byte of each and
strand the rest. The table is sorted longest-first and applied greedily.
"""

import re

# The substitution table. Multi-byte sequences first; the decoder sorts by length anyway,
# and they are grouped here so a reader can see which ones they are.
MAP = {
    # --- conjunct glyphs that occupy their own code -----------------------------------
    "Ø": "क्र", "ø": "क्र", "Œ": "द्द", "æ": "द्ध", "™": "ट्ट", "Ï": "ट्ठ",
    "Ð": "ड्ड", "Ñ": "ड्ढ", "|": "द्य", "K": "ज्ञ", "K­": "ज्ञ",
    "{k": "क्ष", "{": "क्ष्", "«": "त्र", "=": "त्र", "'k": "श", "'": "श्",
    "Ù": "न्न", "Û": "ङ्ग", "ë": "ह्न", "ã": "ल्ल", "Ø;": "क्र्य",
    "&": "-", "¡": "ँ", "¢": "ं", "£": "र्",
    # --- vowels ------------------------------------------------------------------------
    "v": "अ", "vk": "आ", "b": "इ", "bZ": "ई", "m": "उ", "Å": "ऊ", "_": "ऋ",
    ",": "ए", ",s": "ऐ", "vks": "ओ", "vkS": "औ", "va": "अं", "v%": "अः",
    # --- consonants --------------------------------------------------------------------
    "d": "क", "D": "क्", "[k": "ख", "[": "ख्", "x": "ग", "X": "ग्", "?k": "घ",
    "?": "घ्", "³": "ङ",
    "p": "च", "P": "च्", "N": "छ", "t": "ज", "T": "ज्", ">": "झ", "÷": "झ्", "¥": "ञ",
    "V": "ट", "B": "ठ", "M": "ड", "<": "ढ", ".k": "ण", ".": "ण्",
    "r": "त", "R": "त्", "Fk": "थ", "F": "थ्", "n": "द", "/k": "ध", "/": "ध्",
    "u": "न", "U": "न्",
    "i": "प", "I": "प्", "Q": "फ", "iQ": "फ", "c": "ब", "C": "ब्", "Hk": "भ", "H": "भ्",
    "e": "म", "E": "म्",
    ";": "य", "Ø;s": "क्र्ये", "j": "र", "y": "ल", "Y": "ल्", "o": "व", "O": "व्",
    "\"k": "ष", "\"": "ष्", "l": "स", "L": "स्", "g": "ह",
    "M+": "ड़", "<+": "ढ़", "Ýk": "फ़", "³": "ङ",
    # --- matras ------------------------------------------------------------------------
    "k": "ा", "f": "ि", "h": "ी", "q": "ु", "w": "ू", "`": "ृ",
    "s": "े", "S": "ै", "ks": "ो", "kS": "ौ", "a": "ं", "%": "ः", "̀": "ँ",
    "~": "्", "½": ")", "¼": "(",
    # NOT the reph. Both draw a र and they attach in opposite directions: Z is the hook
    # ABOVE a later consonant and this one is the tail BELOW the consonant before it.
    # Mapping it to the reph turned इलेक्ट्रॉनिक्स into इलेक्टर्ाॉनिक्स.
    "ª": "्र",
    "z": "्र",           # the rakar, the र hanging under the consonant before it
    "J": "श्र", "]": ",", "kW": "ॉ", "W": "ॉ", "@": "/", "A": "।",
    "Z": "\U000f0000",   # the reph, parked here; the rule below moves it left
    "}": "द्व", ":": "रू",
    "ç": "प्र", "É": "क्र", "Ó": "व्", "‚": "स्",
    # --- digits and punctuation the font maps to itself --------------------------------
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
}

# Applied longest-first so "vk" is not decoded as "v" + "k", and "[k" not as "[" + "k".
_KEYS = sorted(MAP, key=len, reverse=True)
_PAT = re.compile("|".join(re.escape(k) for k in _KEYS))

# A Devanagari consonant, optionally with a virama-joined follower, is what an i-matra has
# to jump over. Written out rather than inlined because the reordering rule is the only
# part of this file that is an algorithm rather than a table.
_CLUSTER = re.compile("ि((?:[क-हक़-य़]्)*[क-हक़-य़])")

# THE REPH, and it moves the other way. Kruti Dev writes 'Z' for the र् that prints as a
# hook above a later consonant, and it writes it AFTER the syllable that hook sits on,
# because that is where the glyph is drawn. Unicode writes it before that syllable. So
# "/kkfeZd" is ध ा ि म Z क in glyph order and धार्मिक in character order, and the Z
# travels left past the consonant and whatever matra hangs off it. Twelve of the
# thirty-three department names in the parallel corpus turn on this one rule.
_REPH = re.compile("([\u0915-\u0939\u0958-\u095f](?:\u094d[\u0915-\u0939])*"
                   "[\u093e-\u094c]*[\u0901-\u0903]?)\U000f0000")


def decode(s):
    """One Kruti Dev string to Unicode Devanagari."""
    if not s:
        return s
    # Z is parked on a plane-15 private-use codepoint so the reph rule can find it after
    # the i-matra has moved, and it is parked BY THE TABLE rather than by a pass before
    # it. A pre-pass looked simpler and silently destroyed every multi-character key
    # containing a Z: "bZ" is the whole letter ई, and with Z replaced first it could only
    # ever decode as इ followed by a reph, which is why सफाई came out as सफाइर् in two
    # states. NOT U+F8FF, which was the first choice: Chhattisgarh's other legacy font
    # extracts U+F8FF as a real character 326 times, so a placeholder there would collide
    # with the document the day the two decoders meet.
    # A COMMA BETWEEN TWO DIGITS IS A COMMA. Kruti Dev types ए as ',', and Madhya
    # Pradesh's demand books print money as 4,80,00, so the table turned every thousands
    # separator into a vowel: 4ए80ए00. Parked before the table pass and restored after,
    # which is the one place a pre-pass is right, because no Kruti Dev key spans a digit.
    s = re.sub(r"(?<=\d),(?=\d)", "\U000f0001", s)
    out = _PAT.sub(lambda m: MAP[m.group(0)], s)
    # The i-matra is printed to the left of its consonant and stored that way. Unicode
    # stores it to the right, so every ि moves past the cluster that follows it.
    out = _CLUSTER.sub(lambda m: m.group(1) + "ि", out)
    out = _REPH.sub(lambda mm: "र्" + mm.group(1), out)
    return out.replace("\U000f0000", "र्").replace("\U000f0001", ",")


# THE PARALLEL CORPUS, and it is the whole argument that this file reads rather than
# guesses. Chhattisgarh's outcome index lists its departments in Unicode Devanagari and
# every one of those departments publishes a PDF carrying the same name in Kruti Dev. The
# state wrote both halves; this register wrote neither. Twenty-two of the thirty-three
# decode to the index spelling character for character.
#
# The other eleven are recorded here rather than left out, because "22 of 33" invites the
# question and the answer is that the two documents disagree, not that the table does:
# the index says उर्जा where the PDF says ऊर्जा, युवक where it says युवा, जल संसाधान where
# it says जल संसाधन, and वन विभाग where the PDF gives the department's full name, वन एवं
# जलवायु परिवर्तन विभाग. Those are the state's own inconsistencies and this file must not
# paper over them.
SELFTEST = [
    ("fnukad", "दिनांक"),                 # the i-matra moves right past its consonant
    (";kstuk", "योजना"),
    ("ctV", "बजट"),
    ("foHkkx", "विभाग"),
    ("LFkkiuk", "स्थापना"),
    ("/kkfeZd", "धार्मिक"),               # the reph moves left past its syllable
    ("dk;Z", "कार्य"),
    ("tulaidZ", "जनसंपर्क"),
    ("ÅtkZ", "ऊर्जा"),
    ("fuekZ.k", "निर्माण"),
    ("vkfFkZd", "आर्थिक"),
    ("xzkeh.k", "ग्रामीण"),               # the rakar hangs under the consonant before it
    ("Je", "श्रम"),
    ("Lrj", "स्तर"),
    (";kstuk@dk;Zdzeksa", "योजना/कार्यक्रमों"),
    # The source's own typo, decoded faithfully rather than repaired. Chhattisgarh's
    # outcome book writes कार्यक्रम twice on one page, once as "dk;Zdzeksa" and once as
    # "dk;ZØze", and the second has the क्र ligature AND the rakar, so it decodes with a
    # redundant र. Both render acceptably in the font, which is why nobody caught it. A
    # decoder that quietly fixed it would be editing the document.
    ("dk;ZØze", "कार्यक्र्रम"),
]


def selftest():
    """Every pair above, or a non-zero exit. Run as `python3 parse/krutidev.py`."""
    bad = [(s, want, decode(s)) for s, want in SELFTEST if decode(s) != want]
    for s, want, got in bad:
        print(f"  FAIL {s!r}: want {want!r}, got {got!r}")
    print(f"krutidev: {len(SELFTEST) - len(bad)} of {len(SELFTEST)} pairs decode exactly")
    return not bad


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(0 if selftest() else 1)
