"""
Classify Uttar Pradesh's grant-volume lines: welfare scheme, or budget head?

AGENT-EDITABLE (PLAN.md §7). Reads data/ only. Never fetches. Chrome from
classify_common.py; every signal below is Uttar Pradesh's own.

    data/uttarpradesh/labels.json          hand ground truth, the input
    data/uttarpradesh/classification.json  the verdicts, the output

528 hand labels: a 289-row stratified sample on whether the scheme code is two digits or
four, then every row at the publishing bar labelled so precision is a COUNT. 184 of 5,831
lines clear it, precision 0.940 with eleven named errors, recall 0.436.

BOTH OF THOSE NUMBERS MOVED, AND FOR THE SAME REASON. Recall was published as 0.869 while
the sweep was counting the audit census, which is chosen on this classifier's own output;
classify_common now sweeps the stratified sample alone and the honest figure is 0.436.
Precision was published as 0.935 as though it were a count, and it was not: grant, code and
page do not identify a row here, so 15 rows at the bar were being given a hand label
somebody wrote about a different line. They are labelled now, and 0.940 is a count.

THIS FILE IS WRITTEN IN DEVANAGARI AND THAT IS THE POINT. Uttar Pradesh publishes its
budget in Hindi and in nothing else, so every regex below matches Hindi, and the labels
were read in Hindi. The romanisation parse/devanagari.py produces is for JOINING to
myScheme and is not used here: a classifier that read the transliteration would be
measuring a derived field when the state's own words are right there.

    छात्रवृत्ति  scholarship     P(scheme) 1.000
    बीमा         insurance       P(scheme) 1.000
    प्रोत्साहन   incentive       P(scheme) 1.000
    पुरस्कार     award           P(scheme) 1.000
    निदेशालय etc directorate,
                 institute,
                 university      P(scheme) 0.000  over 34 rows
    अनुदान       grant           P(scheme) 0.000  over 10
    भवन          building        P(scheme) 0.000  over  5
    ऋण           loan            P(scheme) 0.000  over  7

योजना IS ONLY WORTH +1, the same demotion Uttarakhand's needed and for a different reason.
It measures 0.400 against a base of 0.135, which is a real lift and not a strong one,
because Uttar Pradesh calls a great many things a yojana that nobody applies to: शहरी
विस्तारीकरण प्रोत्साहन योजना is a new-town programme and स्वच्छ शौचालय का निर्माण is
household toilets, and both carry it.

SEVEN GROUPS THE CENSUS FOUND, together P(scheme) 0.000 over 61 labels, and the sample had
missed all of them because it is 5% of a 5,831-row book:

  * PENSIONS FOR THE STATE'S OWN PEOPLE, and there are many. पेंशनरों की अधिवर्षता पेंशन,
    पारिवारिक पेंशन, कर्मचारी सामूहिक बीमा योजना, पेंशन तथा उपदान के लिये अंशदान. पेंशन and
    बीमा are two of the strongest positives in the file.
  * घटाएं एस.एन.ए. से वेतन की प्रतिपूर्ति, a DEDUCTION line reversing salary paid through
    the single nodal agency. It carries प्रतिपूर्ति, reimbursement, which is a positive.
  * नेशनल मिशन ऑन एग्रीकल्चर एक्सटेंशन एण्ड टेक्नोलाजी, seventeen rows of it, which is
    extension machinery and not a payment to a farmer.
  * Power distribution: उदय, रिवैम्प्ड, संचरण तथा वितरण. वितरण means distribution and is a
    positive when it distributes seed or textbooks.
  * A prize for an INSTITUTION or a teacher: राज्य अध्यापक पुरस्कार, मुख्यमंत्री पंचायत
    प्रोत्साहन पुरस्कार योजना.
  * Honorarium to staff: रसोइयॉ मानदेय, शिक्षा मित्रों को मानदेय.
  * A place being expanded: विस्तारीकरण, नमामि गंगे.

Every one of them is a positive word doing something else, which is what makes a book this
size hard: the vocabulary is right and the subject is not.
"""

import argparse
import json
import os
import re

from classify_common import ROOT, classify, report

POSITIVE = re.compile(
    "छात्रवृत्ति|बीमा|प्रोत्साहन|पुरस्कार|पेंशन|आवास योजना|आजीविका|पुष्टाहार|कल्याण निधि|"
    "स्वरोजगार|क्षतिपूर्ति|प्रतिपूर्ति|कैश ट्रान्सफर|शौचालय|पालनहार|सशक्तिकरण|मानदेय|"
    "वितरण|उपलब्ध कराने|मिशन ऑन|मिशन फॉर")

YOJANA = re.compile("योजना")

ASSET = re.compile(
    "निदेशालय|संस्थान|विश्वविद्यालय|कालेज|महाविद्यालय|परिषद|अकादमी|समिति|बोर्ड|प्राधिकरण|"
    "निगम|अनुदान|भवन|ऋण|सुदृढ़ीकरण|आधुनिकीकरण|कम्प्यूटरीकरण|मरम्मत|अनुरक्षण|सफाई|निर्माण|"
    "नहर|सिंचाई|बांध|पम्प|कार्यालय|मुख्यालय|अधिष्ठान|स्थापना|व्यय|कार्य|अस्पताल|चिकित्सालय|"
    "विद्यालय|पुस्तकालय|संग्रहालय|एक्सप्रेस-वे|सड़क|मार्ग|पर्यटन|प्रबन्ध|प्रबंधन|सर्वेक्षण|"
    "जनगणना|आयोग|न्यायालय|पुलिस|कारागार|अभिकरण|केन्द्र|यूनिट|परियोजना")

# The seven groups the audit census turned up. Each is a positive word attached to
# something that is not a benefit; together P(scheme) 0.000 over 61 labels.
CENSUS_FOUND = re.compile(
    "पेंशनरों|पारिवारिक पेंशन|कर्मचारी सामूहिक बीमा|पेंशन तथा उपदान|अंशदान|उपादान|"
    "एवज में पेंशन|अधिवर्षता|कम्युटेड|राशिमूल्य|जमा सम्बद्ध बीमा|बीमा निधि|राज्य कर्मचारियों|"
    "सैनिक स्कूल|अशक्तता पेंशन|नियत परिचर|पेंशन दायित्|विधायको को पेंशन|"
    "घटाएं|घटायें|एस\\.एन\\.ए\\.|"
    "एग्रीकल्चर एक्सटेंशन|एक्सटेंशन एण्ड टेक्नोलाजी|"
    "उदय|रिवैम्प्ड|संचरण तथा वितरण|विद्युत वितरण|"
    "अध्यापक पुरस्कार|शिक्षकों को राज्य पुरस्कार|पंचायत प्रोत्साहन|पंचायत प्रतिपूर्ति|"
    "उच्च शिक्षा प्रोत्साहन|गुणवत्ता संवर्धन|दक्षता परीक्षा|"
    "रसोइयॉ|रसोइया|शिक्षा मित्र|अतिथि विषय|"
    "विस्तारीकरण|नमामि गंगे")

PUBLISH_THRESHOLD = 3
LISTING_THRESHOLD = 1


def _base(r):
    """Uttar Pradesh's code is unique only within a grant volume: 04 exists in all 91."""
    return f"{r['grant']}|{r['code']}|{r['page']}"


# ...AND GRANT, CODE AND PAGE TOGETHER ARE STILL NOT UNIQUE. 486 of them name more than one
# row, covering 1,093 of the 5,831. The book really does print one scheme name under one
# code on one page twice with two different provisions: of the 202 collisions that survive
# adding the NAME as well, 132 differ only in the amount and 44 in the amount and the head
# it sits under. Two provisions, not one printed twice.
#
# The cost was silent and it was in the ground truth. classify_common assigns hand labels by
# looking the identifier up, so every row sharing an identifier was given the label somebody
# wrote for ONE of them: 289 sampled labels were landing on 370 rows, so 81 rows in the
# threshold sweep -- 22% of it -- carried a verdict written about a different line. At the
# publishing bar the damage is one pair, प्रादेशिक सेना डेकोरेशन and महारानी अहिल्याबाई
# होलकर पुरस्कार योजना, which share 84|05|7 and are plainly two different things.
#
# The ordinal is appended only from the SECOND occurrence, so every identifier that was
# already unique is unchanged and the labels written against it still match. Occurrences are
# ordered by the row's own printed content rather than by position in the file, because
# classify_common sorts on the identifier and so calls this during the sort, when file order
# is not available. Two rows identical in every field -- there are 8 such pairs -- are
# indistinguishable in the data and are left sharing an identifier rather than separated by
# an ordinal the book does not support.
def _ordinals():
    import collections
    d = json.load(open(os.path.join(ROOT, "data", "uttarpradesh", "schemes.json"),
                       encoding="utf-8"))
    groups = collections.defaultdict(list)
    for r in d["entries"]:
        groups[_base(r)].append(r)
    out = {}
    for base, rows in groups.items():
        if len(rows) == 1:
            continue
        for i, sig in enumerate(sorted({_sig(r) for r in rows})):
            if i:
                out[(base, sig)] = f"{base}#{i + 1}"
    return out


def _sig(r):
    return json.dumps(r, sort_keys=True, ensure_ascii=False)


_ORDINAL = None


def ident(r):
    global _ORDINAL
    if _ORDINAL is None:
        _ORDINAL = _ordinals()
    base = _base(r)
    return _ORDINAL.get((base, _sig(r)), base)


def score(r):
    n = r.get("name") or ""
    s, ev = 0, []
    if POSITIVE.search(n):
        s += 3
        ev.append(("+3", "a word that names a benefit"))
    if YOJANA.search(n):
        s += 1
        ev.append(("+1", "the word yojana, which this book uses loosely"))
    if ASSET.search(n):
        s -= 4
        ev.append(("-4", "an office, an institution, a work or a canal"))
    if CENSUS_FOUND.search(n):
        s -= 4
        ev.append(("-4", "a staff pension, a deduction, or a prize for an institution"))
    return s, ev


REJECTED = [
    {"signal": "the romanised name rather than the Hindi",
     "measured": {"P_scheme": None, "base_rate": 0.135, "n": 5831},
     "why": ("Available and deliberately unused. parse/devanagari.py romanises every name "
             "so it can be JOINED to myScheme, which lists Uttar Pradesh's schemes in "
             "romanised Hindi. Classifying on it would measure a derived field when the "
             "state's own words are in the row, and would inherit every ambiguity the "
             "transliteration introduces: प्रोजेक्ट comes back as projekt.")},
    {"signal": "the number of object heads under the line",
     "measured": {"P_scheme": None, "base_rate": 0.135, "n": 5831},
     "why": ("Tamil Nadu's strongest instrument and not usable here. 3,826 of 5,831 rows "
             "have exactly one object head and 555 have none, so it barely varies; and "
             "parse/uttarpradesh.py counts them rather than recording which they are, so "
             "the benefit-transfer test that carried Tamil Nadu cannot be run.")},
    {"signal": "the department that funds the line",
     "measured": {"P_scheme": None, "base_rate": 0.135, "n": 5831},
     "why": ("Not usable. The department is the grant volume's title, so it is one value "
             "per volume across 91 volumes, and every department funds both its schemes "
             "and its own establishment.")},
]


def main():
    argparse.ArgumentParser(description="Classify Uttar Pradesh's grant-volume lines.").parse_args()
    report("uttarpradesh",
           *classify("uttarpradesh", "Uttar Pradesh", score, PUBLISH_THRESHOLD,
                     LISTING_THRESHOLD, REJECTED, ident=ident,
                     row_fields=lambda r: {
                         "name_latin": r.get("name_latin"),
                         "department": r.get("department"),
                         "grant": r.get("grant"),
                         "head_of_account": r.get("head_of_account"),
                         "under": r.get("under"),
                     }),
           publish=PUBLISH_THRESHOLD)


if __name__ == "__main__":
    main()
