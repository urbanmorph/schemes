# State scheme sources: what each state actually publishes

Central schemes can be checked against an independent list of names, because the Union
Budget publishes one. That is the only reason this register can say 64 funded schemes are
missing from myScheme and name them.

States have no equivalent. DBT Bharat publishes a per-state *count* and no list, so the
2,474-scheme shortfall visible on `/divergence` cannot be itemised from anything central.
Naming those schemes means going state by state, and this file records what each state was
found to publish, including the ones that do not work.

A negative result here is worth as much as a positive one. Three earlier dead ends in this
project (Wikidata, `allsbe.pdf`, data.gov.in) each cost a day and were each nearly built
before being measured properly.

---

## Karnataka — WORKS

`collect/karnataka.py`, `parse/karnataka.py`. 969 heads of account, 865 with an
allocation, 389 with a one-line English statement of purpose.

Three scheme-wise books, all English-first with the Kannada alongside:

| Book | What it lists |
|---|---|
| Gender Budget | every scheme with a women-oriented allocation |
| Child Budget | every scheme with a child-oriented allocation |
| SCSP/TSP Allocations | scheme-wise by statute |

**Why it works: the bilingual slash.** Every scheme is printed as
`English Name / ಕನ್ನಡ`, so the name field has an unambiguous terminator. Everything
before the slash is the name, and the Kannada legacy font is separable because it extracts
as Latin Extended characters that no English name contains. Nothing else in this file has
that property, and it is the single reason Karnataka parsed cleanly.

Keyed on the head of account (`2401-00-102-0-27`), which is the state's own scheme
identifier and far more stable than a name retyped by every office that touches it.

---

## Gujarat — DOES NOT WORK, and here is exactly why

Gujarat was chosen as the second state deliberately: it is the one state where myScheme
lists *more* schemes (641) than DBT Bharat (394), so it tests the opposite direction. It
does not yield a usable list.

**What Gujarat publishes in English**

| Publication | What it is | Usable? |
|---|---|---|
| No. 56, Outcome Budget | 257pp, 978 funding lines, tabular | No, see below |
| No. 35, Development Programme | 730pp of policy prose, zero scheme tables | No |
| Budget in Brief / Highlights | summary documents | No |
| Gender Budget | published in Gujarati only | Not attempted |

**The Outcome Budget has no reliable name field.** Four extraction strategies were tried
and measured:

1. `pdftotext -layout` with text heuristics. 1,413 distinct "names", heavily contaminated:
   the Physical Target column merges into the name column, so `Research Park`,
   `TUTION FEE (No. of Students)` and `No of Works` are recorded as schemes.
2. Character-column slicing at the financial column (found at columns 52 to 63). 868
   names. Better, still carrying account heads like
   `03 State Highway 101 Birdge Works 11 RBD 2(b)`.
3. `pdftotext -bbox-layout`, extracting only words whose x lies in the Name column
   (x 100 to 318, with targets starting at x 420). 818 names, and cleaner, but physical
   targets such as `2082 GPs connected in Gujarat through Phase II Network` still land in
   the name column on pages where the table is laid out differently.
4. Per-page column boundaries computed from each page's own financial column. No better:
   the header fragment `(Rs.` leaks in and separate schemes merge into one block.

The root cause is structural, not a matter of more effort. The name, the head of account
and sometimes the target text share one column; the column boundaries move between pages;
and there is no separator anywhere that says where a name ends. Karnataka's slash has no
counterpart here.

**Measured consequence.** Matching the least-bad list (834 filtered names) against
myScheme's 641 Gujarat schemes returned 216 matches, and inspection shows most are false:
`AIDS Control Programme Assistance For Transportation` joined to
`COP-37 (General Area) 50% Capital Subsidy`, and
`Administrative Structure for Gujarat Landless Labourers` to
`Free Medical Assistance (Gujarat)`. A list that produces joins like that cannot support a
claim in either direction, so no Gujarat figure is published.

**The site also resists listing.** `financedepartment.gujarat.gov.in/Budget.html` is
ASP.NET WebForms whose year selector is a `__doPostBack`. The served page carries a
92-character `__VIEWSTATE` and an empty `__EVENTVALIDATION`, and POSTs to both
`Budget.html` and `Budget.aspx` return 404. Document URLs
(`Documents/Bud-Eng_1596_2026-2-18_626.pdf`) carry an unguessable trailing id, so they
cannot be constructed and have to be discovered another way.

**What would make Gujarat work:** its Demand for Grants or detailed expenditure volumes,
if they are structured like Karnataka's, or the Gujarati Gender Budget if scheme names are
transliterated in Latin script. Neither has been checked.

---

## Kerala — WORKS, and publishes more than anyone

Not built yet. Surveyed and measured.

Every budget document sits on one index page at the Legislature
(`niyamasabha.org/codes/15kla/Session_16/Budget doc 2026.htm`), 36 direct PDF links, no
postback and no session. Kerala publishes more scheme-wise cuts than any other state
found: Gender & Child, Environment, Elderly, R&D and SDG budgets, Annual Plan statements,
and per-department Performance Budgets.

**Annual Plan 2026-27 (Statements) Vol I**, 529 pages, is the comprehensive list:
**1,808 scheme rows, 1,639 distinct scheme codes**, against the **81** Kerala schemes
myScheme lists. Each row carries a scheme code (`ATC 021`), the name in Malayalam and
again in English in its own column, the head of account, and six years of figures. The
Malayalam is proper Unicode rather than a legacy font, so the scripts separate on
character range alone: easier than Karnataka's slash.

The **Gender & Child Budget** is richer still, carrying a full `Objectives` column in
English: *"Scheme aims to provide day care facilities to children (0-6 years), specific to
children of working mothers"*. That is a better description than myScheme publishes for
many schemes it does list.

## Andhra Pradesh — WORKS, and is the easiest to parse

Not built yet. Surveyed and measured.

36 volumes on one page, all English: Gender, Child, Backward Classes and Minorities
budgets, Scheduled Castes and Scheduled Tribes Component volumes, an Outcome Budget, and
17 per-department detailed volumes.

The Gender Budget is a plain two-column table, `Name of the Department and Scheme` against
`Amount allocated`, with no second script to separate at all: **283 rows, 223 distinct
scheme names** in that one cut, against the **51** AP schemes on myScheme.

Note the URL: the budget path is literally `https://apfinance.gov.in/...Bud@et26-27/`,
with three leading dots and an `@`. It cannot be guessed and has to be read off the
homepage. The same documents on the S3 bucket behind the site return 403.

## Telangana — WORKS

Not built yet. Surveyed and measured.

The Scheduled Castes Special Development Fund statement is headed
`Department wise/Scheme wise Allocations` and is a clean English-only table: department,
scheme, state sector, centrally sponsored, matching share, total. Names wrap across lines,
which is the same solved problem as everywhere else. There is a Scheduled Tribes
equivalent.

Telangana is the sharpest case in the country for this register: myScheme lists **22**
schemes for Telangana against DBT Bharat's **152**, and this single fund statement already
names more than either.

## Tamil Nadu — WORKS

Not built yet. Surveyed and measured.

Roughly 50 per-department Demand Books at
`financedept.tn.gov.in/en/budget-publications/` (1,414 PDF links on that page, so the
index needs filtering rather than reading). Bilingual, with English in its own column and
the Tamil in a legacy font that garbles harmlessly beside it.

Rows carry a sub-head scheme code, the English name, four years of figures and the full
head of account:

    AB  Upgradation of Adi Dravidar Welfare Hostels   14,99,18 ... 4225 01 277 AB 40000

myScheme lists 234 Tamil Nadu schemes, the second highest of any state, so this is the
place where the portal is least behind. Whether the Demand Books still exceed it is the
open question, and the reason Tamil Nadu is worth doing early rather than last.

---

# The second round: the six largest states outside the south

Surveyed 2026-09-02, in the order Maharashtra, Odisha, Rajasthan, Madhya Pradesh, West
Bengal, Bihar. Three yield and are built. Three do not, and the reasons are different
from each other and different from Gujarat's.

---

## Maharashtra: WORKS, and is the cleanest document in this file

`collect/maharashtra.py`, `parse/maharashtra.py`. **1,956 schemes** against myScheme's
**84** and DBT Bharat's 308.

The budget is not on the Finance Department's website. It is on BEAMS, the Budget
Estimation, Allocation and Monitoring System run by the Directorate of Accounts and
Treasuries, behind a page whose filename says 2021 and whose content is current:

    https://beams.mahakosh.gov.in/Beams5/BudgetMVC/MISRPT/HomePage2021.html

**ANNUAL SCHEME 2026-2027 (Departmentwise), English edition**, 752 pages, is an English
edition of a book that also exists in Marathi, so there is no second script in it at all.
One row per scheme, with the state's own **10-digit scheme code**, an 8-character budget
code, the source of fund and four years of figures, in seven statements: state schemes in
General, Scheduled Caste and Tribal cuts (GN2), physical targets (GN3), centrally
sponsored (GN4), externally aided (GN5), domestic financial institutions (GN6), and women
and child and human development cross-cuts (GN7, GN8).

**Two traps, both encoded.** The PDF directory returns 404 without a `Referer` header
pointing inside `/Beams5/BudgetMVC/MISRPT/`; the bare host does not work. And the index
carries a large block of commented-out HTML with dead 2022-23 links, one of them labelled
2025-2026 and pointing at a 2026-2027 file.

Reconciles twice and both hold: all **382** printed Sub Sector Totals against the rows
read under them in all four money columns, and all **487** schemes printed in both GN2 and
GN4 with the two statements agreeing figure for figure. The second check earned its keep
on the first correct run: it caught page 528, where `1101010028World Agriculture Census`
is printed with the scheme code run into the name, which had silently moved that scheme's
whole provision onto the scheme above it.

---

## Odisha: WORKS, and the state's own budget portal is the thing to avoid

`collect/odisha.py`, `parse/odisha.py`. **1,628 scheme codes** against myScheme's **83**
and DBT Bharat's 173.

44 per-department Demand for Grants books, each row printed in English with the Odia
beneath it in proper Unicode, so the scripts separate on character range alone. The
hierarchy is the state's own: a 4-digit scheme code, 5-digit sub-schemes under it, 3-digit
object heads under those, and a printed TOTAL at every level.

**Not from budget.odisha.gov.in.** That portal has three faults. Its `*.odisha.gov.in`
certificate is served without its intermediate, so Python fails where a browser succeeds.
It lists all 44 demands twice, the second listing being last year's VOLUME - II. And for
Demand 34, Co-operation, it links the **2025-2026** book while the 2026-2027 one, 107
pages, sits on the server unlinked. The Finance Department's own publication page,
`finance.odisha.gov.in/en/publication/finance-budget`, has none of those faults.

Reconciles **17,859 of 17,859** printed totals in all four money columns. Getting there
turned up the one thing about these books a reader has to know: Odisha prints the VOTED
total on the TOTAL line and the CHARGED total on the next line with nothing but the word
CHARGED to identify it, except where a whole sub-tree is charged, when the TOTAL line
carries the word itself. Read without that distinction, 60 totals fail by a single
thousand rupees, which is small enough to look like rounding and is not.

---

## West Bengal: WORKS, and its best document is a scan

`collect/westbengal.py`, `parse/westbengal.py`. **9,024 sub-heads** against myScheme's
**109**.

`wbfin.wb.gov.in` does not resolve and `wbfin.nic.in` times out. The live page is
`finance.wb.gov.in/Fin_New/Pages/Budget_Publication.aspx`, ASP.NET WebForms whose year
selector is a `__doPostBack` that does not have to be driven: a plain GET renders the
current year with static hrefs. Filenames cannot be constructed across years, because the
BP numbering shifts (2024_bp30.pdf exists, 2023_bp30.pdf and 2025_bp30.pdf are 404).

BP-11 to BP-26 are the Detailed Demands for Grants, English throughout, keyed on the full
head of account. Reconciles **5,521 of 5,521** sub-head totals and **1,768 of 1,768**
minor head totals, in all four columns.

**BP-30, the Gender and Child Budget, is the best-shaped scheme table West Bengal
publishes and it cannot be read by a machine.** 46 MB, 65 pages; `pdftotext` over the
whole file returns 65 characters, one form feed per page; `pdffonts` returns no rows at
all; `pdfimages` shows a 300 dpi JPEG per page. Rendering page 46 shows exactly the table
this register wants. BP-31, the SDG Budget, is the same. That is a different failure from
Gujarat's: West Bengal has laid the table out correctly and then photographed it.

---

## Madhya Pradesh: DOES NOT WORK, and the reason is a font

`finance.mp.gov.in` is up but intermittent: it refused connections on port 443 for a full
hour during this survey and answered normally afterwards, and archive.org has not
succeeded in crawling it since **2023-03-10**. Its budget index is a CodeIgniter page
whose listing arrives by **POST** to `/budget/ajaxPaginationData/` with a CSRF token; a
GET returns `503 Unable to locate the specified class: Session.php`. The collectors here
only ever GET, by design, so that index cannot be driven at all.

That is the smaller problem. The larger one is that **Madhya Pradesh publishes its 2026-27
budget in a legacy 8-bit font**. Volume-06 (Gender Budget), Volume-08 (Agriculture Budget)
and the Rolling Budget all embed `KrutiDev010` with a ToUnicode map back to KrutiDev
codepoints, not to Devanagari, so:

    ;kstuk Øekad ,oa uke        is    योजना क्रमांक एवं नाम   (scheme code and name)
    eq[;ea=h dkS'kY;k ;kstuk    is    मुख्यमंत्री कौशल्या योजना

The layout is otherwise excellent: `<4-digit scheme code> <name>` then the account type
and three years of figures, with `योग` subtotal rows that are trivially filtered. The
numbers extract perfectly. Only the names do not.

**What would make Madhya Pradesh work:** a KrutiDev-to-Unicode table, which is a known,
deterministic transform complicated by matra reordering (KrutiDev writes the *i* matra
before its consonant). Even done correctly it yields **Hindi** names, which cannot be
joined to myScheme's English ones, so the state would enter this register as a count and a
list of Devanagari names and not as an absence claim. That is a real deliverable and a
different job from the one this round did.

---

## Bihar: DOES NOT WORK, and the reason is deliberate

Bihar's index is the richest in the country: 749 PDF anchors, 441 unique files, bilingual
link text, 2011-12 through 2026-27, at

    state.bihar.gov.in/finance/SectionInformation.html?editForm&rowId=3373

(a cookie jar is needed; a plain curl hits a redirect loop). The PDFs need no session.
Bihar publishes a Gender Budget, a Bal Kalyan (Child) Budget and a Parinam (Outcome)
Budget every year, each with a scheme-wise annexure.

**The entire 2026-27 set has had its text converted to vector curves.** Measured on the
archived files:

| File | Pages | Extractable characters |
|---|---|---|
| `1_Demands For Grants Curve.pdf` (2025-26) | 108 | **108** |
| `Budget Capital Exp Detail_OK.pdf` (2025-26) | 268 | **268** |
| `Gender Budget 2026-27.pdf` | 178 | **452** |

One character per page is the form feed. `pdffonts` returns no rows. This is not a scan:
`pdfimages` finds no images either, so the glyphs are vector outlines. The state's own
metadata says so out loud, `/Title(1_Demands For Grants Curve.pdf)`, and the file sizes
follow, 448 MB for Revenue Expenditure Part I.

The years that *do* have a text layer do not help. The Gender Budget 2024-25's annexure
extracts as KrutiDev-family garble exactly like Madhya Pradesh's; the Parinam Budget
2025-26 extracts real Devanagari Unicode that is damaged in a characterisable way (virama
dropped, conjuncts collapsed to their first consonant, the pre-base *i* matra emitted in
visual order, inter-word spaces lost). And **no Bihar document prints a scheme name in
English**. English reaches the major-head level (`2402 Soil and Water Conservation`) and
the department level and stops. The Gender Budget's English narrative names schemes in
prose without allocations, which is a Hindi-to-English crosswalk and not a table.

---

## Rajasthan: MEASURED, NOT BUILT, and the obstacle is nameable

Rajasthan's budget index is the easiest to automate in this file: plain static PDFs at
`finance.rajasthan.gov.in/docs/budget/statebudget/2026-2027/`, 36 documents, no postback
for the document links. Everything else about it is against you.

**The detailed volumes cannot be read.** Vol-1 through Vol-4c are the Demands for Grants
in Hindi, produced by Microsoft Reporting Services, and their Devanagari text layer is
*lossy*: `pdffonts` shows an `Arial Unicode MS` subset in WinAnsi with no ToUnicode
alongside two Identity-H subsets that do have one, so consonants and matras drop out
silently and `2202-सामान्य शिक्षा` extracts as `2202-स श` and `विस्तृत लेखा` as
`व तृत ेख`. The figures are perfect. Unlike Madhya Pradesh this is not recoverable by a
transliteration table, because the characters are not encoded at all.

**The Output-Outcome Budget 2026-27 is the one English scheme-wise document** and it
passes the field test: a `Schemes` column at x 41-85 bounded by a Financial column
starting at x 90, on 207 of 336 pages, giving scheme names, a state and central split, a
total in crore, physical targets and outcome indicators, across 60+ departments.

It fails on something else. The Schemes column is 41 points wide and Word breaks words
across lines **without a hyphen**, so `Mukhyaman` / `tri` and `Annocumen` / `ts` sit in
the same column as `Rajasthan` / `Government` / `Health`. The obvious geometric rule does
not separate them: `Government` fills the column to 82 points and is a whole word, while
`Mukhyaman` fills it to 81 and is half of one. Measured over the whole book, **638 of
2,419 column fragments** are followed by a lowercase-initial fragment, and those 638 mix
mid-word breaks with ordinary ones. The document also prints **no totals of any kind**, so
there is nothing to reconcile a reconstruction against.

**What would make Rajasthan work:** joining a fragment pair when their concatenation
appears elsewhere in the same document as a whole word (`Administrati`+`on` gives
`Administration`, which the book uses hundreds of times; `office`+`expenses` gives
`officeexpenses`, which it never does). That rule is testable and was not built here,
because a name assembled by heuristic in a document with no printed totals is a name
published as fact with nothing behind it, and a wrong scheme name is a false accusation.

---

## Scoreboard

| State | Verdict | Best document | What makes it work, or not |
|---|---|---|---|
| Kerala | yes | Annual Plan statements, 1,639 codes vs 81 on myScheme | scheme code, English column, Unicode Malayalam, objectives |
| Andhra Pradesh | yes | Gender Budget, 223 names vs 51 | plain English, single script |
| Karnataka | **built** | Gender, Child, SCSP/TSP, 969 heads vs 56 | the `English / Kannada` slash |
| Telangana | yes | SCSDF scheme-wise, vs 22 | plain English table |
| Tamil Nadu | yes | ~50 department Demand Books, vs 234 | bilingual, English in its own column |
| Maharashtra | **built** | Annual Scheme Deptwise, 1,956 schemes vs 84 | an English edition of a Marathi book, plus a 10-digit scheme code |
| Odisha | **built** | 44 Demand for Grants books, 1,628 codes vs 83 | English above Unicode Odia, totals at every level |
| West Bengal | **built** | Detailed Demands BP-11 to BP-26, 9,024 sub-heads vs 109 | English throughout, keyed on the head of account |
| Gujarat | **no** | Outcome Budget | no separator, columns move between pages |
| Madhya Pradesh | **no** | Volume-06 Gender Budget | KrutiDev legacy font, no Unicode; index is POST-only |
| Bihar | **no** | Gender / Child / Parinam Budget | 2026-27 converted to vector curves, zero text; no English names |
| Rajasthan | **no, for now** | Output-Outcome Budget | English, but names wrap mid-word with no hyphen and no totals to check against |

Eight of twelve states surveyed yield a machine-readable scheme list. The four that do not
fail in four different ways, and only one of them is a layout problem:

- **Gujarat** cannot say where a name ends.
- **Madhya Pradesh** and **Bihar** encode their names so that a machine reads nothing, one
  through a legacy font and one by converting the text to drawings.
- **Rajasthan** publishes the names in English and breaks them across lines in a way that
  cannot be undone from geometry alone.

The southern states' advantage turns out not to be southern. Odisha and West Bengal work
for the same reason Kerala does, and Maharashtra works for a reason none of them has: it
publishes an **English edition** of a Marathi book rather than a bilingual one. Publishing
the same book twice, once per language, is the single most useful thing a state does for
anybody trying to read it.

---

## What this means for the other 34

There is no generic state parser and there should be no attempt to write one. What
generalises is not the parser but the *test*: before writing anything, find one document
and answer a single question, does the scheme name occupy a field a machine can find the
end of. A bilingual slash, a separate English column, a script that cannot share a column
with Latin, or plain English throughout all pass. A column that holds the name, the head
of account and sometimes the target text, with boundaries that move between pages, fails,
and no amount of effort fixes it.

That test takes about twenty minutes per state and costs one PDF. Writing the parser for
a state that passes takes an afternoon. Doing it in the other order cost a day on Gujarat.

The second round added a step to the test that Gujarat did not need, because Gujarat's
text layer was fine. **Before asking where the name ends, ask whether the name is there at
all**: run `pdffonts` and count the characters `pdftotext` returns. No rows from
`pdffonts` means the text has been drawn rather than written (Bihar, West Bengal's BP-30).
A font with a ToUnicode map that points at 8-bit codepoints means a legacy encoding
(Madhya Pradesh, Bihar's older years). A WinAnsi subset of a Unicode font with no
ToUnicode at all means characters that will simply vanish (Rajasthan). All three cost
nothing to check and each of them decides the state on its own.

Order to work in, by gap size against myScheme and by how little parsing each needs:
Andhra Pradesh and Telangana first because they are plain English, then Kerala because it
is the largest gap in the country and the richest document, then Tamil Nadu. Karnataka,
Maharashtra, Odisha and West Bengal are done.

A state that does not yield is a finding about that state's transparency, and belongs on
the site as one. Gujarat publishes a great deal and still cannot be read by a machine,
which is a different and more interesting failure than publishing nothing. Bihar is the
sharpest version of that: it publishes more budget documents than any other state in this
file, going back to 2011-12, and it converts them to curves before it does.
