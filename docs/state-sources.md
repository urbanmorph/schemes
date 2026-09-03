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

## Scoreboard, every state surveyed

**This table is generated from `data/legibility.json` by `parse/legibility.py`; do not edit
it by hand.** The per-round scoreboards further down are the record of what each round
found and are left as they were written. This one is the current answer, and the parser
that writes it refuses to run if a verdict here disagrees with that state's own output.

The five tests are asked in order and a state that fails one is never asked the rest, so
&middot; means *never reached* and is not counted as a failure. That is why the scores are
out of different numbers.

| State | Publishes a scheme list | The names are text | A name has an end | Named in English | The book proves itself | Cleared | Schemes named |
|---|---|---|---|---|---|---|---|
| West Bengal | yes | yes | yes | yes | yes | 5 of 5 | 9,024 |
| Tamil Nadu | yes | yes | yes | yes | yes | 5 of 5 | 6,220 |
| Punjab | yes | yes | yes | yes | yes | 5 of 5 | 2,961 |
| Kerala | yes | yes | yes | yes | yes | 5 of 5 | 2,629 |
| Telangana | yes | yes | yes | yes | yes | 5 of 5 | 2,039 |
| Maharashtra | yes | yes | yes | yes | yes | 5 of 5 | 1,956 |
| Odisha | yes | yes | yes | yes | yes | 5 of 5 | 1,628 |
| Haryana | yes | yes | yes | yes | yes | 5 of 5 | 970 |
| Jharkhand | yes | yes | yes | yes | yes | 5 of 5 | 852 |
| Tripura | yes | yes | yes | yes | yes | 5 of 5 | 134 |
| Uttarakhand | yes | yes | yes | yes | **no** | 4 of 5 | 2,324 |
| Delhi | yes | yes | yes | yes | **no** | 4 of 5 | 1,578 |
| Karnataka | yes | yes | yes | yes | **no** | 4 of 5 | 969 |
| Andhra Pradesh | yes | yes | yes | yes | **no** | 4 of 5 | 552 |
| Uttar Pradesh | yes | yes | yes | **no** | **no** | 3 of 5 | 5,831 |
| *Surveyed, does not yield* | | | | | | | |
| Gujarat | yes | yes | **no** | &middot; | &middot; | 2 of 3 | &middot; |
| Rajasthan | yes | yes | **no** | yes | &middot; | 3 of 4 | &middot; |
| Bihar | yes | **no** | &middot; | &middot; | &middot; | 1 of 2 | &middot; |
| Chhattisgarh | yes | **no** | &middot; | &middot; | &middot; | 1 of 2 | &middot; |
| Madhya Pradesh | yes | **no** | &middot; | &middot; | &middot; | 1 of 2 | &middot; |
| Assam | **no** | &middot; | &middot; | &middot; | &middot; | 0 of 1 | &middot; |
| Himachal Pradesh | **no** | &middot; | &middot; | &middot; | &middot; | 0 of 1 | &middot; |

15 of 22 states surveyed yield a machine-readable scheme list, between them naming
39,667 lines. All 15 carry a classifier built and validated against
that state's own hand labels, so every absence claim on the site has counted precision
behind it and named errors beside it.

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

## Telangana: WORKS, and the state's own Finance Department is a year behind

`collect/telangana.py`, `parse/telangana.py`. **2,039 schemes** by department and name
against myScheme's **22** and DBT Bharat's 152. 1,498 carry money, 407 are funded at nil,
1,641 carry a head of account.

The survey found the Scheduled Castes Special Development Fund statement, which is a clean
English-only table and does yield 161 schemes. The bigger document is beside it, and it is
the reason Telangana is now the third largest list in this register: **Volume VII/1, the
Pragathi Paddu (Scheme Expenditure)**, 117 pages, is the state's whole scheme expenditure
in one book, sector by sector and department by department, with a head of account and
three years of figures against every scheme. 1,947 rows. The Scheduled Tribes fund adds
160 more.

**Which index, and it is not the Finance Department's.** Telangana publishes the same
volumes twice and only one of them is current:

| Page | Cycles it carries |
|---|---|
| `finance.telangana.gov.in/budget-volumes.jsp` | 2014-15 to **2025-26**, and no 2026-27 directory at all |
| `ifmis.telangana.gov.in/budget_volumes` | 2025-26 and **2026-27** |

A register built from the Finance Department's own budget page would have published
Telangana's 2025-26 allocations as this year's. The 2026-27 filenames on IFMIS carry a
unix timestamp at both ends, `1773983749_Pragathi_Paddu__VII-I_1773983748_.pdf`, and the
two differ by a second, so nothing about them can be constructed.

Reconciles **320 of 320** printed totals in all three money columns, including the
Pragathi Paddu's own Grand Total of 18,431,570.27 lakh over 1,890 rows and the SCSDF's of
3,774,122.17 lakh. Getting there found the two things a reader of these books has to know.
A scheme printed **without a head of account** is a parent, and its breakdown may carry
serial numbers and names of its own. On page 41 the Forest College's 10,299.41 is
63.00 + 3,141.00 + 1,000.00 + 6,095.41, and the last two of those are printed as schemes 5
and 6 with names of their own, Infrastructure Development and Civil Works for Sanctuaries.
Nothing in the layout separates that from two genuinely new schemes; the book's own
arithmetic does, so the breakdown ends where its rows add up to the parent in all three
columns at once and nowhere else. And the Irrigation chapter wraps heads of account so
wide that the money row
is left with nothing beside it, which looks identical to an unlabelled sub-total that must
not be counted at all; the difference is 29.00 lakh on one page, small enough to read as
rounding.

The scheme names are cells **vertically centred** in their rows, so 734 of them run over
more than one line and 683 put no part of the name on the row that carries the money. They
are put back together by symmetry rather than proximity, which is what the parser's
docstring is mostly about.

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

# The four states where myScheme is furthest behind DBT Bharat

Surveyed 2026-09-03, chosen because myScheme is furthest behind DBT Bharat in each:
Chhattisgarh 106 against 216, Jharkhand 96 against 156, Assam 78 against 157, Himachal
Pradesh 75 against 174. One yields. The three that do not fail in a way this file has not
recorded before, and two of them fail with the table already correctly laid out.

---

## Jharkhand: WORKS, and its banner line is the cleanest terminator yet

`collect/jharkhand.py`, `parse/jharkhand.py`. **852 schemes** against myScheme's **96**
and DBT Bharat's 156.

36 per-department Detailed Demands for Grants books at
`finance.jharkhand.gov.in/budget2026.aspx`, plain static hrefs under a heading that names
them, no postback. Every structural line is printed as `<Hindi> / <English>`, which is
Karnataka's bilingual slash, and every scheme opens with a banner printed in English
capitals with the state's own 4-digit scheme code in brackets at the end:

    STATE SCHEME        MINORITY HOSTEL NUTRITION SCHEME(2073)
    STATE SCHEME        REPAIR AND RENOVATION OF BUILDING BUILT UNDER DEPARTMENT AS
                        HAJ HOUSE, KADRU, RANCHI MINORITY RESIDENTIAL SCHOOL ETC.(2231)

The closing bracket is the terminator the test asks for. A wrapped banner runs on and the
code closes it, so a name is never truncated and never runs into the head of account.
Below the banner sits the full bill code, `30-S-2225-04-796-01-00-06-79`, which is the
demand, the fund, and the head of account to the object head, and four money columns in
lakh headed Actual 2024-25, Budget Estimate 2025-26, Revised Estimate 2025-26 and Budget
Estimate 2026-27.

**The Devanagari is damaged and it does not matter.** `pdftotext` drops matras and
collapses conjuncts, so स्थापना व्यय arrives as "थापना यय" and विस्तृत splits over two
lines. That is Rajasthan's lossy-font problem and it costs nothing here, because every
name published comes from the English half of the slash or from the all-caps banner.

Three things about these books a reader has to know, each of which was measured rather
than assumed and each of which silently corrupts the figures if read the obvious way:

  1. **A printed total covers the rows since the last time that same total was printed**,
     not everything read so far. Minor head 796 under 2225-02 in the Welfare book is
     totalled at 7,98.49 and again at 93,63.07, and the second figure is the rows between
     the two prints. Read as cumulative, 202 of that book's 308 checks fail.
  2. **A sub head total spans minor heads.** Scheme 0158's sub head total is 3,87.53,
     which is its general-education row (90.46) plus its Tribal Area Sub-Plan row
     (2,97.07). A sub head is the scheme; the same scheme is funded under both minor
     heads.
  3. **The `**` rule.** An object head broken down by sub-scheme prints its own total with
     `**` in the sub-scheme position, then the word "In Which", then one row per
     sub-scheme. Counting both puts the scheme at nearly twice its provision.

Reconciles twice and both hold. **2,888 of 2,888** printed totals, at major head, sub
major head, minor head and sub head, in all four money columns. And **82 of 82**
Contents-page statement totals: the front matter of every book prints one Budget Estimate
2026-27 figure per demand per statement, naming the statements in English, and that is a
separately typeset account of the same money rather than a sum of this parser's own
reading. The second check earned its keep twice on the first correct run. It found that a
deduct head belongs beside a scheme's provision and not inside it, and it found that a
negative is written `(-)7,20,00.00`, with the sign in brackets and no minus sign anywhere,
so the State Disaster Response Fund's deduct arrives as +Rs 720 crore instead of -Rs 720
crore. Neither error is visible to the internal totals, because the internal totals
contain both of them symmetrically.

Two more traps, both encoded. A bill code runs straight into the object head's name when
the name fills its column (`Rent, Rate, Tax03-S-2059-80-001-17-00-03-16`), which is
Maharashtra's `1101010028World Agriculture Census` in another state's typesetting; and the
books use a hyphen, an en dash and an em dash interchangeably in the same total line.

Checked against the outside world as well as against the books: Mukhyamantri Mainyan
Samman Yojana comes out at 14,06,557.63 lakh, Rs 14,066 crore, the order Jharkhand states
publicly for it; Abua Aawas Yojana at Rs 4,100 crore and Mukhyamantri Sarvajan Pension at
Rs 3,517 crore are the same order as the state's own announcements.

**Not free.** The 36 books are **318 MiB**, more than the whole rest of `archive/` put
together, and there is no smaller document that carries the same list: the Gender Budget
2026-27 and the Child Budget 2026-27 are SCANS (`pdftotext` returns 34 characters from the
34-page Gender Budget and 26 from the 26-page Child Budget, `pdffonts` no rows,
`pdfimages` one 150 dpi JPEG per page), which is West Bengal's BP-30 again.

`finance.jharkhand.gov.in` also serves an incomplete certificate chain, a leaf under
"GlobalSign GCC R46 OV TLS CA 2025" with no intermediate attached, exactly as
`finance.karnataka.gov.in` does. Python fails where a browser succeeds; the missing
intermediate already in `collect/certs/` is carried and verification stays on.

---

## Chhattisgarh: DOES NOT WORK, and the English edition it advertises has never existed

Chhattisgarh's index is the easiest static one in this file:
`finance.cg.gov.in/budget_doc/Budget.asp` links `main_budget.asp?year1=2026`, which is
plain HTML with 56 direct PDF hrefs, and `Dem_grant.asp?year1=2026` lists 44 department
books with five volumes each, one of them headed "Scheme".

**The scheme books are exactly the right shape and cannot be read.** Each `S-NN.pdf`
prints `<4-digit scheme code>  <name>  <provision in thousands>`, one row per scheme.
Measured across all 44: **2,429 scheme rows, 1,563 distinct 4-digit scheme codes**, and
every figure extracts perfectly. **Not one of the 2,429 names does.** Every book embeds
`Krishna` and `Chanakya`, WinAnsi and Builtin encodings with no ToUnicode map, so

    ¿UàÃË‚ª…U∏ÿÊ ∑§˝Ë«UÊ ¬˝Êà‚Ê„UŸ ÿÊ¡ŸÊ     is    छत्तीसगढ़िया क्रीड़ा प्रोत्साहन योजना

Not one non-ASCII character in the whole set lands in the Devanagari block. The Outcome,
Gender, Youth and Child budgets at `outcome.asp?year1=2026` are worse: `TT5676t00` and
friends, custom-encoded TrueType subsets, also with no ToUnicode.

**The English editions are advertised and 404.** The 2026-27 index links twelve English
files beside their Hindi twins: the seven Annual Financial Statement volumes, three
Receipt Budget volumes, `English/E-headwise breakup.pdf`, `Newitem-E.pdf`,
`Sechdule of Appropiration-VOA.pdf` and `Summary of Grants-VOA.pdf`. Every one returns
404 while every corresponding Hindi file returns content. `E-headwise breakup.pdf` was
checked for 2020-21, 2022-23, 2023-24, 2024-25 and 2025-26 as well and is 404 in every
year, so this is not a broken upload for one cycle.

That leaves Chhattisgarh as Madhya Pradesh with a working index: the layout is excellent,
the numbers are perfect, the names are drawn in a font from before Unicode, and the
English volumes the state's own page offers have never been on the server.

**What would make Chhattisgarh work:** the state uploading the twelve English files it
already links, or a Chanakya-to-Unicode table, which like KrutiDev is a deterministic
transform complicated by matra reordering and which even done correctly yields Hindi names
that cannot be joined to myScheme's English ones.

---

## Assam: DOES NOT WORK for this cycle, because the documents stop

`finassam.in`, the department's old domain, has an MX record and no A record, so nothing
serves on it. The live site is `finance.assam.gov.in`, and its
Assam Budget 2026-27 portlet carries exactly **seven documents**: the budget speech in
Assamese and in English, the highlights, the AFRBM statements, the transfer budget, a
summary and a revenue receipt statement. None of them is a scheme list.

The only detailed one, `transfer_budget_2026-27.pdf`, is 155 pages of devolution to
Panchayati Raj Institutions and Urban Local Bodies, in clean English with a head of
account down to the object head and figures in Rs lakh. It names no scheme: its rows are
Salaries, Travel Expenses, Office Expenses under a 4-digit sub-head code.

**Everything else Assam publishes scheme-wise is out of date.**

| Document | Cycle | Shape |
|---|---|---|
| Grants Wise Budget, ~80 grant books (`node/90094`) | **2016-17** | bilingual, English in its own column, Plan/Non-Plan |
| Outcome Budget (`menu/document/outcome_budget.pdf`, unlinked) | 2020-21 | scheme name, objective, three years, SDG mapping |
| Gender Budget FY 2024-25 | 2024-25 | the best table Assam has, see below |
| Outcome Budget 2024-25 | 2024-25 | scheme names in bold prose, no allocations |

The Gender Budget FY 2024-25 passes the field test outright. Its annexure prints the full
head of account (`2235-03-796-2657-927-32-99-CSS-GA-V`), the scheme name in English in its
own column, the targeted group, a one-line objective and four years of figures. There is
no 2025-26 or 2026-27 edition: both filenames 404 and no documents page exists for either
year. Press reporting puts the Gender Budget 2026-27 at Rs 12,160 crore over about 300
schemes; it is not published.

So Assam's failure is neither layout nor encoding. Assam lays its tables out correctly,
writes them in English, and stops publishing them. **What would make Assam work:** reading
the Gender Budget FY 2024-25 as an off-cycle, gender-only slice, which is a decision this
register has not taken for any other state and which would put a 2024-25 figure beside
seven states' 2026-27 ones.

---

## Himachal Pradesh: DOES NOT WORK, and the reason is that every document link is dead

Himachal has the best-shaped documents of the four surveyed here and they cannot be
fetched.

The budget portal is `ebudget.hp.nic.in`. Its home page offers thirty-odd documents by
name, including Annual Financial Statement, Demands for Grants and Appropriations
Statement, Demand Estimates, Detail of Estimates, HOD Estimates, Part-I and Demand SOE.
**Every one is a `javascript:__doPostBack` and every one 302s to `/BudHome.aspx`, which
renders the same portal page again.** Measured on three targets (`lnkDmdNote`,
`lnkBtnDmdRep_Estm`, `lnkAFS`), with and without a session cookie taken from a prior GET;
the reply is byte-identical to `Default.aspx` but for the VIEWSTATE. The only 2026-27
document reachable by GET is `Aspx/Anonymous/Pdf/BIB.pdf`, the 15-page Budget in Brief,
and it embeds **`Kruti Dev 010`** with no ToUnicode: Madhya Pradesh's font.

`buddocs.aspx` offers one zip per year and the newest it links is `Bud_2023.zip`, FY
2023-24. `Bud_2024.zip` (107,812,000 bytes, first entry `BUDGET IN BRIEF 2024-25.pdf`) and
`Suppl_2023.zip` are on the server and are **not linked**; `Bud_2025.zip` and
`Bud_2026.zip` do not exist. That is Odisha's unlinked-file fault with no second index to
fall back on.

The FY 2023-24 zip is 95 MB and does contain the per-department Demands for Grants, five
PDFs each, and their **Detail of Estimates passes the field test cleanly**:

    2225-01-001-01-S00N     [T] ֒֞᭔֑᭭շᳱ֐          42168    45602    46643    47014
                            V   STATE SCHEMES      42168    45602    46643    47014
    ID:{11864}    01        [T] ֧֗ֆ֊               22427    30572    31272    31585
                            V   SALARIES           22427    30572    31272    31585

English on its own `V` row, so no column can be confused with any other; the head of
account to the sub-head with `S00N` marking a state scheme; an object-head id; four money
columns headed **Rs. In Thousands**, which is the Kerala unit trap waiting to be walked
into. The Hindi `[T]` rows are an `Arial Unicode MS` Identity-H subset with no ToUnicode
and garble harmlessly beside it, exactly as Tamil Nadu's Tamil does.

`himachal.nic.in/finance` is a separate MVC portal whose file links are opaque encrypted
query strings (`ControlsAsync/ViewFTPFile?qs=KI3g...`) and it carries circulars, not budget
volumes.

**What would make Himachal Pradesh work:** the portal serving its documents to a GET, or
`Bud_2026.zip` appearing where the previous nine years' zips are. Neither is a parsing
problem, and driving the postback is not an option here: these collectors only ever GET,
by design, for the same reason Madhya Pradesh's POST-only index was left alone.

---

## What these four add to the test

**Before asking whether the name is there, ask whether the DOCUMENT is there.** Himachal
Pradesh's Detail of Estimates and Assam's Gender Budget both pass the field test outright
and neither can be had for the current cycle: Himachal's portal answers every one of its
thirty document links with a 302 back to its own home page, and Assam publishes seven
documents for 2026-27, none of them a scheme list. That is a different failure from
Gujarat's, Madhya Pradesh's, Bihar's or Rajasthan's, and it is the cheapest of all of them
to check, because it costs one GET. Chhattisgarh is a variant: it links twelve English
volumes beside their Hindi twins and every one of the twelve has been a 404 in every year
checked back to 2020-21.

Jharkhand adds the other half of the lesson. Its Devanagari extracts as badly as
Rajasthan's, its scheme names are typeset in capitals in a way that breaks `match.py`'s
acronym rule, and it still yields 852 schemes cleanly, because the state prints the name
in English with a bracketed code that says where it ends. **What decides a state is not
how well it renders Hindi. It is whether anything in the row says where the name stops.**

---

## Scoreboard

| State | Verdict | Best document | What makes it work, or not |
|---|---|---|---|
| Kerala | yes | Annual Plan statements, 1,639 codes vs 81 on myScheme | scheme code, English column, Unicode Malayalam, objectives |
| Andhra Pradesh | yes | Gender Budget, 223 names vs 51 | plain English, single script |
| Karnataka | **built** | Gender, Child, SCSP/TSP, 969 heads vs 56 | the `English / Kannada` slash |
| Telangana | **built** | Pragathi Paddu + the SC and ST fund volumes, 2,039 schemes vs 22 | plain English table; the current cycle is on IFMIS and not on the Finance Department's page |
| Tamil Nadu | yes | ~50 department Demand Books, vs 234 | bilingual, English in its own column |
| Maharashtra | **built** | Annual Scheme Deptwise, 1,956 schemes vs 84 | an English edition of a Marathi book, plus a 10-digit scheme code |
| Odisha | **built** | 44 Demand for Grants books, 1,628 codes vs 83 | English above Unicode Odia, totals at every level |
| West Bengal | **built** | Detailed Demands BP-11 to BP-26, 9,024 sub-heads vs 109 | English throughout, keyed on the head of account |
| Gujarat | **no** | Outcome Budget | no separator, columns move between pages |
| Madhya Pradesh | **no** | Volume-06 Gender Budget | KrutiDev legacy font, no Unicode; index is POST-only |
| Bihar | **no** | Gender / Child / Parinam Budget | 2026-27 converted to vector curves, zero text; no English names |
| Rajasthan | **no, for now** | Output-Outcome Budget | English, but names wrap mid-word with no hyphen and no totals to check against |
| Jharkhand | **built** | 36 Detailed Demands books, 852 schemes vs 96 | `STATE SCHEME <NAME>(<code>)` in English capitals, plus the `Hindi / English` slash |
| Chhattisgarh | **no** | 44 department Scheme books, 1,563 codes | Krishna and Chanakya legacy fonts, no Unicode; every English edition it links is 404 |
| Assam | **no, for now** | Gender Budget FY 2024-25 | passes the field test and stops: the 2026-27 set is seven documents and none is a scheme list |
| Himachal Pradesh | **no** | Detail of Estimates, FY 2023-24 zip | passes the field test and cannot be fetched: every document link 302s back to the portal home |

As of the second round, eight of twelve states surveyed yielded a machine-readable
scheme list. The four that did not
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

---

# The third round: two of the smallest and two where the portal looked ahead

Surveyed 2026-09-03, in the order Tripura, Delhi, Haryana, Uttarakhand. All four yield and
all four are built, which makes this the first round with no dead end in it. Two of them
answer questions the earlier rounds could not.

**Tripura and Delhi were picked for the gap.** myScheme lists 37 state schemes for Tripura
against DBT Bharat's 209, a ratio of 5.6 to one and the widest in the register; Delhi is
53 against 114.

**Haryana and Uttarakhand were picked for the opposite.** They are two of only three states
where myScheme claims MORE than DBT counts: 249 against 171 for Haryana, 446 against 225
for Uttarakhand. Uttarakhand lists more schemes on myScheme than any state except Gujarat
despite being a tenth of Uttar Pradesh by population. The question was whether the portal
is ahead of the state's own books anywhere. It is not, in either.

---

## Tripura: WORKS, and its book very nearly reproduces the DBT count

`collect/tripura.py`, `parse/tripura.py`. **134 State Level Schemes and 74 Centrally
Sponsored Schemes, 208 together**, against DBT Bharat's **209** and myScheme's **37**.

`CSS & SLS- BUDGET OVERVIEW 2026-27`, 154 pages, is titled on its own cover *Details of
Centrally Sponsored Schemes onboarded on SNS SPARSH*. SNS is the Single Nodal Agency
system through which centrally sponsored money flows and through which DBT counts, and
208 against 209 is the closest any state document in this file has come to reproducing a
DBT number. That is not proof and this register does not claim it is. It is the first time
the question has been answerable at all.

The book is a clean three-level tree, all English, with a printed total at every level:

    CSS 3194   MODERNISATION OF POLICE FORCES
    SLS TR89   ASUMP Main Plan Tripura
    4055 00 207 90 48 60      23.1300
    4055 00 207 91 48 60     208.0000
        SLS TR89  Total :    231.1300
        CSS 3194  Total :    231.1300
        Grand Total for Demand no. 10   231.1300

Every non-header line in it matches one of six shapes. Reconciles **134 of 134** SLS
totals, **76 of 76** CSS totals and **30 of 30** demand totals.

**THE JOIN IS ZERO, AND THAT IS THE FINDING.** A generous matcher over 37 myScheme records
and 134 state scheme names produces no join at all. The two lists describe different
halves of Tripura: myScheme's 37 are welfare-board benefits and state pensions
(Mukhyamantri Samajik Sahayata Prakalpa in four variants, six Building and Other
Construction Workers Welfare Board benefits, the Journalist Health Insurance Scheme), and
this book is the centrally sponsored route. Neither contains the other.

**Tripura's Gender Budget cannot be read, for a reason not yet seen in this file.** It is
the only Tripura document that names the state schemes myScheme does list, and its text
stream carries spaces INSIDE words:

    Mukhya Mantri Scholars hip for Achiecer s Towards Higher Educatio n-CM SATH

`Academi c Excellen ce`, `Examina tion` and `Minister’ s` come out the same way, and
`pdftotext -raw` and the default mode return the identical breaks, so the spaces are in
the PDF and not in the extraction. That is neither Bihar's curves nor Madhya Pradesh's
font: the text layer is correct Unicode and the words are broken in it. The book is
archived because the finding needs its evidence, and it is not parsed.

---

## Delhi: WORKS, and the whole scheme budget is one file

`collect/delhi.py`, `parse/delhi.py`. **1,578 scheme rows** against myScheme's **53** and
DBT Bharat's **114**.

Delhi publishes no per-department demand volumes. `Scheme-wise Budget 2026-27` is 131
pages headed `SCHEME/PROGRAMME/PROJECTS WISE OUTLAY 2026-27`, plain English, sector by
department by scheme, four years of figures in `(₹ in Lakh)` and a printed subtotal at
every level up to a Grand Total of 62,55,000 lakh.

**Not from the Finance Department.** `finance.delhi.gov.in` has pages titled *Demand for
Grants year 2026-27* and *Detailed Demands for Grants* and both are empty of documents.
The budget is published by the Planning Department at
`delhiplanning.delhi.gov.in/planning/2026-27`.

**The filename and the metadata both lie about the year.** The served file is
`scheme_wise_6.pdf` and its PDF `/Title` is `Scheme Wise 2025-26 10.03.2026 1.58 PM.xlsx`,
while all 131 table pages are headed 2026-27. The cycle is read from the page banner and a
book whose pages say anything else is a hard error.

**Three things about this file are worth carrying to the next state.**

`pdftotext -bbox` and `-bbox-layout` both CRASH on it (poppler 25.x, `std::out_of_range`,
zero words returned), so the real x of a word is not available at all. What saves it is a
strip of column numbers `1 2 3 ... 15` printed under the header of every table page; those
markers move by up to five characters between pages and are read per page.

A logical row is spread over three printed lines with the money on a different line from
the name, and a name-column line with no serial is a continuation of the row above EXCEPT
when a blank line separates them, in which case it is a heading. Without that rule
`AGRICULTURE & ALLIED ACTIVITIES` is appended to the last scheme of the previous sector.

And Delhi's book does not fully balance to itself: 263 of 282 printed totals resolve
against the items directly above them, and the Grand Total is 3.2 per cent under the sum
of the scheme rows. At least 1,14,031 lakh of that gap is one identified memo line,
`OAS(Other than Minorities)`, printed under `TOTAL [OTHER ADMN. SERVICES]` as a
restatement with no word in its name to mark it as a total. The rest is not traced. Row
arithmetic passes on 1,577 of 1,578 rows, so the money is sound per row and approximate in
aggregate, and `data/delhi/schemes.json` says so.

---

## Haryana: WORKS, and settles the question it was chosen for

`collect/haryana.py`, `parse/haryana.py`. **970 schemes with the state's own code**, 824
of them with a paragraph of purpose, against myScheme's **249** and DBT Bharat's **171**.

`Explanatory Memorandum on Welfare & Development Schemes (Plan Memo)`, 491 pages, is a
scheme register in two halves per department: a table with a scheme code and the central
and state share, and a narrative entry carrying Haryana's own description of the scheme.
The narrative code is the table code with its `P-0` prefix removed, which is how they
join. It reconciles completely: **970 of 970** rows on their own arithmetic, **192 of 192**
printed Part totals, **117 of 117** units.

**Three units in one book, and that is the whole trap.** The per-department Summary is
headed `(Amount in ₹ )` and prints full rupees to eleven digits; the scheme table is
`(₹ In Lakhs)`; the narrative `Outlay` line is full rupees again. Read as one unit, every
figure would be out by a factor of 100,000. Page 110 prints the words `LIST OF SCHEMES
BUDGET ESTIMATE 2026-27` over a table of major heads in rupees, so the banner cannot be
trusted either and the unit is read from each page's own header. The Summary in rupees is
then used to CHECK the table in lakh, which is the strongest units check in this file.

Two more things a reader has to know. A continuation page prints no column header and is
not aligned with the page before it, so the columns are recovered from the page's own
figures by whichever mapping makes the most rows satisfy Total = Central + State. And one
department's table is headed `LISTOFSCHEMESBUDGETESTIMATE2025-26`, spaces and all missing,
inside a 2026-27 book; its figures are 2026-27, which is exactly what the rupee Summary
proves.

**On the portal being ahead: it is not.** 53 of myScheme's 249 Haryana records join to
this register at all, and 32 of the 60 joins are wrong. Eighteen of those 32 are a single
budget line for PMMSY matched to eighteen myScheme records that are components of it,
which says the 249 is partly built of sub-schemes a budget states once.

---

## Uttarakhand: WORKS, and is the weakest reconciliation in this register

`collect/uttarakhand.py`, `parse/uttarakhand.py`. **2,324 scheme codes, 2,302 with an
English name**, against myScheme's **446** and DBT Bharat's **225**.

Uttarakhand writes its budget in Hindi and typesets it in KrutiDev. `pdffonts` on Volume 2
and on the Gender Budget shows `Kruti Dev 010` and `Kruti Dev 016` in WinAnsi with no
ToUnicode, and Volume 2's notes extract as `o"kZ 2026&27` where the state wrote 2026-27.
That is the Madhya Pradesh failure, and on Volume 2 it is fatal.

**Volume 5, `Head wise details of accounts`, is a different book,** and it is the reason
Uttarakhand is here at all. It prints every line of the detailed estimates twice, the
Hindi first and the English underneath. The Hindi is damaged the way everything
Uttarakhand typesets is damaged and it does not matter: it is Devanagari Unicode, so it
cannot share a line with the Latin, and the English beneath is clean. That is the Odisha
property arriving by a different route, and it is worth stating as a rule, because it
means **a state whose Hindi extracts as garbage is not automatically a dead end. Look for
the volume that prints English underneath.**

    2011  Parliament/State/Union Territory Legislatures
      02  State /Union Territory/Legislatures
       101  Legislative Assembly
        03  Legislative Assembly
        01  Pay
        खयग/Total 03  ...  731493

Three things had to be worked out that the document does not say. The figures for a row
are printed on their own line BEFORE the two that name it, and reading them the other way
gives the Legislative Assembly Rs 11.5 crore of Medicines and Chemicals and nothing for
Grant in Aid. A `Total` line names a code and nothing else and the same two-digit code can
be open twice in one path, so the node it closes is chosen by whichever open node's
subtree adds up. And the level that is a scheme is told from the level that is an item of
expenditure by a property of the document rather than a word list: the book prints a total
for a level with children and never for Pay or Office Expenses.

**It reconciles 3,686 of 4,492 printed totals, 82 per cent, and that is the weakest number
in this file.** The failures are more page layouts than the reader knows: a section whose
figures share a line with the code and the name, a node stated with two codes at once, and
totals whose code is not open when they arrive. `be_lakh` is the figure the book prints on
that node's own Total line, read directly, and every row carries `total_reconciled` saying
whether the rows beneath it were also read correctly; 2,209 of 2,324 are true. The units
are checked from outside and pass **13 of 13**: each grant's cover page prints its Revenue
and Capital provision in FULL RUPEES while every detail page is in thousands.

Half of the 13-digit scheme codes this parser builds out of the account tree match the
codes Volume 5's own front matter prints as `Scheme Code`. That is reported rather than
hidden, and it is the same 18 per cent of broken tree: where a layout breaks the tree, the
path walked up to build the code breaks with it. Join on the name, not the code.

**The Gender Budget is archived and not read.** It restates the same estimates in a denser
layout that puts the money, the code and the name on one line; read with the Volume 5
reader it reconciled 209 of its 1,782 totals against 82 per cent for Volume 5, and a book
that will not reconcile is a book this register does not publish figures from.

**On the portal being ahead: it is not, and the 446 is partly an artefact.** Only 67 of
myScheme's 446 Uttarakhand records join at all against a register of 2,302 names, and 81
of the 196 joins are wrong. Nine of the 446 are services of one institution: *Aromatic
Awareness Programme - Centre for Aromatic Plants*, *Quality Test Report - Centre for
Aromatic Plants*, *Registration of Aromatic Plant Farmers - Centre for Aromatic Plants*
and six more, all of them one budget head.

---

## What the joins in this round say about parse/match.py

289 joins were produced across the four states and every one was read. 119 are wrong, and
they fall into shapes worth naming because the same shapes will recur:

- **A ministry, a lender or an agency read as a scheme acronym.** AYUSH produced 24 joins
  on Uttarakhand and NABARD 23, matching every budget line that mentions them. NOT_ACRONYMS
  holds sectors and states and communities; it does not hold institutions.
- **A derived initialism containing a written one, where the dropped letter is the whole
  point.** `mmsy` sits inside `pmmsy`, so Uttarakhand's Mukhyamantri Matsya Sampada Yojana
  matched the Union's Pradhan Mantri Matsya Sampada Yojana seven times, and `mrkvy` inside
  `rkvy` did the same seventeen times. Mukhyamantri against Pradhan Mantri is exactly the
  state-versus-central distinction this register exists to draw.
- **One lower-case letter defeating the shouted-name guard.** `match.acronyms` stands down
  on three or more words of unbroken capitals. Delhi appends `GIA-Capital` and `Dr.` to
  shouted names, and one lower-case letter turns every capitalised word back into an
  acronym: `RAJIV GANDHI SUPER SPECIALITY HOSPITAL AT TAHIR PUR GIA-Capital` matched Rajiv
  Gandhi Swavlamban Rojgar Yojna three times, on the surname.
- **A community budget cut written as an acronym.** SCSP is the Scheduled Caste Sub Plan
  and is a cut of a budget, never a scheme; NOT_ACRONYMS already holds sc, st and obc for
  that reason and does not hold scsp or tsp.
- **One budget line against many myScheme components.** Haryana's PMMSY line absorbed
  eighteen myScheme records and Uttarakhand's National Livestock Mission six. Not wrong in
  direction, useless for attribution, and a real measurement of how a portal count is
  built.

`parse/match.py` was not edited. These are reported against it, with the exact pair and
reason string, in the `myscheme_join_defects` block of each state's `schemes.json`.

---

## Scoreboard, third round

| State | Verdict | Best document | Register vs myScheme vs DBT | Reconciliation |
|---|---|---|---|---|
| Tripura | **built** | CSS & SLS Budget Overview, 154pp | 208 vs 37 vs 209 | 240 of 240 printed totals |
| Delhi | **built** | Scheme-wise Budget, 131pp | 1,578 vs 53 vs 114 | 263 of 282; Grand Total 3.2% short |
| Haryana | **built** | Plan Memo, 491pp | 970 vs 249 vs 171 | 970/970 rows, 192/192 parts, 117/117 units |
| Uttarakhand | **built** | Volume 5 Head wise details, 4 parts | 2,324 vs 446 vs 225 | 3,686 of 4,492; units 13 of 13 |

Twelve states are now built and four measured but not built. The two findings from this
round that generalise:

**A state that publishes in a legacy Hindi font is not automatically a dead end.**
Uttarakhand's Volume 2 is unreadable KrutiDev and its Volume 5 prints English under the
Hindi on every line. Before writing a state off on `pdffonts`, check every volume, not the
first one.

**The number a portal publishes can be an artefact of how it lists things.** Haryana's 249
and Uttarakhand's 446 both looked like states where myScheme was ahead. Reading the joins
shows both counts include sub-schemes and institutional services that a budget states
once, and both states' own books name three to five times as many schemes as the portal
does.

---

# Punjab and Uttar Pradesh

Surveyed and settled 2026-09-03, alongside the build of Telangana. One yields and is
built. The other passes the field test cleanly, more cleanly than most states in this
file, and still cannot enter this register, for a reason none of the earlier failures
has: it is not the layout, the font or the text layer. It is the language.

---

## Punjab: WORKS, and the script separation is only half of it

`collect/punjab.py`, `parse/punjab.py`. **2,961 schemes** against myScheme's **41** and DBT
Bharat's 128, 2,486 of them with money against them.

404 rows are read and NOT published as schemes, because they name none: "No detailed head"
is what Punjab writes where a sub-sub-head does not exist, 378 times, and "State Share" and
"Central Share" split a provision rather than naming one. Their money is counted and the
totals below still balance; publishing them would have put 404 nameless entries into a
register of 3,365, an eighth of it.

One static index, `finance.punjab.gov.in/StateBudget/Index`, 193 PDF links covering
2022-23 to 2026-27, no postback and no session; the Finance Department's home page carries
exactly one budget link and it points there. Every file is served as
`/uploads/<uuid>_<human name> FY 2026-27.pdf` with a fresh random uuid per upload, so the
addresses have to be read off the index, and the names contain spaces the page prints raw.

Five books are read and a sixth is archived without being read:

| Book | Pages | Named rows |
|---|---|---|
| Demand for Grants Vol-I | 732 | 1,220 |
| Demand for Grants Vol-II | 633 | 1,184 |
| Demand for Grants Vol-III | 701 | 1,187 |
| Central Sponsored Scheme Budget Book | 427 | 580 |
| Gender Budget, Parts A, B and C | 47 | 190 |
| Special Component Plan (English) | 162 | archived, not parsed: its schemes sit in narrative rather than in a table |

**Why it works, and where the obvious version of that reason stops.** The demand books are
bilingual and Gurmukhi occupies U+0A00 to U+0A7F, a block no English scheme name borrows
from, so the two scripts separate on codepoint alone. That is the whole of the field test
and it passes. It is not enough to parse the books, because the **Punjabi column carries
Latin of its own**, `(100%`, `GoI)`, `60:40`, bare numerals, and on a wrapped name that
Latin lands on the same text line as the English continuation. Delete the Gurmukhi and one
scheme comes out as `Strengthening of Seed Quality (100 Control Components (100% GoI)
under NFSNM: Seed Components )`. So the parser reads word coordinates after all and takes
the English half of the page as everything from the code column rightwards, x 250 in the
demand volumes and 234 in the CSS book, measured off each book's own object-head codes.

The same applies to the words that mark the money rows. `Voted`, `Charged`, `State` and
`CSS` are also parts of scheme names, `Setting/Upgrading of State Soil Testing labs`,
`Computerization in the State`, and a text-only test took a word off 89 rows of the CSS
book before they were read by column instead.

**The units trap is a factor of a thousand inside one file.** The Statement of Demands for
Grants at the front of Volume II prints `(In ₹)` over figures like 362,814,569,000; the
detailed accounts that follow print `(₹ Thousands)` over figures like 4,25,77,24. Read
together, that front statement's Grand Total would enter this register as 4.76 crore
crore. A page is read only if it names thousands in its own header. The digit grouping is
Indian and not three-digit, so commas are stripped and never counted.

Reconciles **6,234 of 6,234** printed totals in all four money columns: every sub-sub-head
total, every sub-head total, every minor head total and every demand's own grand total,
plus the Gender Budget's three Part totals. The major and sub-major head totals are the
one level left unchecked, and that is a property of the books: Volume III prints
`Total 2225 Welfare of Scheduled Castes` twice inside one demand, once against 81,83,129
and once against 71,46, so a major head total is the sum of a section the book does not
delimit anywhere a reader can see. 493 totals are left alone for that reason.

Two things the reconciliation caught. Suspense heads credit stock back with **negative**
provisions, `-3,79,96`, and a money pattern without a minus sign made four printed Suspense
totals come out too high by exactly the credits. And the head-of-account banner is
reprinted at the top of every continuation page, so treating it as a change of head threw
away the accumulator of every group that runs over a page break, which is most of them , 
the CSS book splits an object head's `Voted State` and `Voted CSS` lines across that
break.

---

## Uttar Pradesh: recorded as DOES NOT WORK, and revisited. It is built.

**The verdict below was reversed on 2026-09-03 and the reasoning is kept as it was written, because the survey's mistake is the useful part. What it got right is that Uttar Pradesh publishes no English. What it got wrong is the assumption that myScheme does. See 'The reversal' at the end of this section.**

### The original finding, as recorded

This is the largest state in India, and its portal listing is smaller than Kerala's:
myScheme lists **46** schemes for Uttar Pradesh against DBT Bharat's **193**.

**It passes the field test, and passes it better than most states here.** The register is
`budget.up.nic.in`. Its Khand-5 grant-wise volumes are built in JavaScript rather than
linked, `https://budget.up.nic.in/PDF{YY_YY}/Gr{NN}.pdf`, and **91 of 97 grants return 200
for 2026-27**, with the series going back to 1999-2000. There is also a 186-page
Memorandum on Grant-Wise Demand.

Every one of the three diagnostics comes back clean:

| Test | Result |
|---|---|
| `pdftotext` characters per page | 2,768 to 2,933 across four documents. Not drawn to curves |
| `pdffonts` | six `CIDFont+F1..F6`, Identity-H, embedded, **uni=yes**, carrying the table body |
| the legacy-font hazard | `BCDHEE+KrutiDev010`, WinAnsi, uni=no, is present and confined to **pages 1 and 2** of each grant volume, the title page and the officer list. The 186-page Memorandum has none at all |
| Devanagari round-trip | intact. `कन्या सुमंगला योजना` keeps its virama and its conjunct; in `ति` the i-matra is U+093F **after** the consonant, logical order, not visual |

And the name field has a findable end. Measured with `pdftotext -bbox-layout` on a 612-point
page: the amounts are right-aligned at x 106, 166 and 226, the **name column runs x 256 to
499**, and the last money column sits at 510 to 564. The name-column code token sits at
xMin 304 to 306 across pages 6 to 20, a two-point spread. Per-row collision test, does name
text ever cross into an amount column on the same row:

| Document | Rows with a name | Collisions |
|---|---|---|
| Gr49, Women & Child Welfare | 535 | **0** |
| Gr80, Social Welfare | 746 | **0** |
| Khand-2 part 2, 186pp | 4,572 | **0** |
| total | **5,853** | **0** |

The head of account is on its own line above the name, so the two never share a cell. That
is a better-behaved table than Gujarat's, Rajasthan's or Madhya Pradesh's, and it would
yield on the order of 8,000 scheme rows.

**It fails on the one thing this register cannot work around: no English.** Across four
budget documents there are 65 distinct Latin tokens and, checked against a dictionary, not
one of them is an English word. They are KrutiDev 8-bit bytes leaking through as Latin , 
`foHkkx` is विभाग, `mRrj izns'k` is उत्तर प्रदेश, and they are confined to the two
front pages. Uttar Pradesh publishes its scheme universe in Hindi and only in Hindi.

That is the same wall Madhya Pradesh hit, arrived at from the opposite direction. Madhya
Pradesh's names cannot be READ; Uttar Pradesh's can be read perfectly and cannot be
JOINED, because myScheme lists in English and a Devanagari name has nothing to match
against. A register that published 8,000 Hindi names and called the difference against
myScheme's 46 an absence would be publishing a claim it cannot check.

**The one English source, and why it is not a substitute.** *Highlights & Salient Features
of UP Budget 2026-27*, 24 pages, zero Devanagari, names schemes inside single quotes, which
is a clean delimiter: 53 distinct English names come out of it, Mukhyamantri Kanya Sumangala
Yojana and Mahila Samarthya Yojana among them. Three problems. It is 53 names against about
8,000 budget lines. Its transliteration is inconsistent **within the same file**, `Shaadi`
and `Shadi Anudan Yojana`, `Sookshm Khaadya Udyog Unaayan` and `Sukshma Khadya Udyog
Unnayan`, so it cannot even be used as a crosswalk without a matcher. And it is hosted on
the information department under a timestamped filename, not indexed from finance, so the
address is not reconstructible from one year to the next.

**What would make Uttar Pradesh work:** a transliteration match between Devanagari scheme
names and myScheme's English ones. That is a real deliverable and a different job from
this one; the state's own English document shows it is not consistent even when a
government does it by hand.

### The reversal

The line above says "myScheme's English ones", and that is the assumption that was never
checked. myScheme does not list Uttar Pradesh's schemes in English. Of its 47 records,
roughly two thirds are a Hindi name written in Latin letters:

    Kanya Sumangala Yojana          Berojgari Bhatta Yojna
    Gambhir Bimari Sahayata Yojana  Mukhyamantri Samuhik Vivah Yojana
    Jyotiba Phule Shramik Kanyadan Yojana

So the two lists are in the same LANGUAGE and different SCRIPTS, and what stands between
them is a transliteration. That matters for whether this register may do it at all:
transliteration is deterministic and checkable, कन्या is kanya whatever the word means,
while translation is a claim about meaning that a register built on publishing only what
it can check has no business making in its own voice.

`parse/devanagari.py` does the conversion and `collect/uttarpradesh.py` and
`parse/uttarpradesh.py` build the state: **5,831 scheme-level nodes across 91 grant
volumes**, with 4,087 of 4,198 printed totals reconciling. The names are published in
Hindi, which is what the state wrote, with the romanisation beside each one and labelled
as derived.

**How much of the transliteration has to be right, which was the surprise.**
`match.probably_same` already strips every vowel and folds aspiration, so for a word of
any length the vowels do not matter, which is lucky: every axis on which two offices
disagree when romanising is a vowel or aspiration axis, and myScheme alone writes Yojana
and Yojna, Sahayta and Sahayata, Ravidas and Ravidaas, in one file. SHORT words are the
exception, because `skeletons()` falls back to the raw token under three characters, so
"baala" and "bal" do not match. Three conventions close it: long vowels written short, the
word-final inherent vowel dropped, and the anusvara written m before a labial so गंभीर is
gambhir and not ganbhir. A nasal, unlike a vowel, survives the skeleton.

**The join is 5 pairs, 2 of them sound, and the script was never the reason it is small.**
कन्या सुमंगला योजना to Kanya Sumangala Yojana and मुख्यमंत्री सामूहिक विवाह योजना to
Mukhyamantri Samuhik Vivah Yojana, both at similarity 1.00, neither reachable before.
Against that, Berojgari Bhatta, Gambhir Bimari Sahayata, Kanya Vivah Sahayta and Panchayat
Kalyan Kosh return **zero rows on a plain substring search of the Hindi**: they are not in
the grant volumes under those names at all, and like Tripura's several are welfare-board
benefits paid from a board's own fund rather than from a demand. Others are English
descriptions rather than names, "Marriage Grant Scheme" and "Widow Pension", which no
transliteration reaches and which only translation would.

**One join is defeated by a typo in the portal.** उत्तर प्रदेश मुख्यमंत्री बाल सेवा योजना
matches "Uttar Pradesh Mukhyamantri Bal Seva Yojana" on all five content words. myScheme's
actual record is spelled **"Uttar Pradesh Mukhyamantri Bal Seva Yojana (Genearal)"**, and
Genearal is a content word no state book can contain. The scheme is in both lists and this
register cannot say so.

**What the parser had to learn, none of it about language.** The money renders on a
different baseline from the Devanagari, about 4pt below and up to 6.7 where a figure is too
wide for its column, so rows are grouped with a swept tolerance rather than by exact y. The
text stream splits words inside a syllable, `केन्द्र` as `के` + `न्द्र`, repaired by
geometry with a virama guard because a word ending in an explicit halant is complete. The
tree is read from the ACCOUNT-CODE GRAMMAR and not from the indent: Gr49 sets its minor
heads at x 244 and its schemes at 254, Gr40 sets a minor head at 254, and a threshold tuned
on one volume reparents subtrees in another. And मतदेय / भारित, Voted and Charged, sit in
the left margin at x 229, inside the name band and to the left of the code, so every voted
object head was dropped for not starting with a code.

---

## Scoreboard, Punjab and Uttar Pradesh

| State | Verdict | Best document | Register vs myScheme vs DBT | Reconciliation |
|---|---|---|---|---|
| Telangana | **built** | Pragathi Paddu VII/1, 117pp, plus the SC and ST fund volumes | 2,039 vs 22 vs 152 | 320 of 320 printed totals |
| Punjab | **built** | 3 Demand for Grants volumes + CSS book + Gender Budget, 2,540pp | 2,961 vs 41 vs 128 | 6,234 of 6,234 printed totals |
| Uttar Pradesh | **no**, and REVERSED the same day: see 'The reversal' above. Built, 5,831 schemes | 91 grant-wise volumes at `budget.up.nic.in/PDF26_27/Gr{NN}.pdf` | 5,831 vs 47 vs 193 | transliteration, not translation |

Uttar Pradesh adds a fifth way for a state to fail, and it is the only one that is not a
defect in the publishing. Gujarat cannot say where a name ends. Madhya Pradesh and Bihar
encode their names so that a machine reads nothing. Rajasthan breaks names across lines
irrecoverably. Uttar Pradesh does everything right and writes it in Hindi, which is its
own language and its own citizens' language, and the gap is on the joining side: the
national portal it would be compared against lists in English.

---

## What the Telangana and Punjab joins say about `parse/match.py`

Every join was read by eye, against the version of `parse/match.py` standing at the end of
this round. Telangana produced **5** pairs against myScheme's 22 non-central records and
**1 is wrong**; Punjab produced **16** against 41 and **8 are wrong**. Three holes in the
acronym rules and one in containment.

An earlier reading of the same two corpora found five more, all from two-word capital
titles: `SKILL UNIVERSITY` yielding `skill` and joining four `Skill Development Training`
records, `WORKS EXPENDITURE` yielding `expenditure`. Those are gone, closed by the guard
that now treats **two** space-separated words of unbroken capitals as a shouted title
rather than three. They are recorded here because the same corpus proves the fix: both
names are still in this register and neither joins anything now.

**1. The shouted-title guard is defeated by a single lower-case character.** Punjab prints
`IMPLEMENTATION OF PROTECTION OF CIVIL RIGHTS ACT-1955 AND THE SCHEDULED CASTES AND
SCHEDULED TRIBES (PREVENTION OF ATROCITIES) ACT 1989 (50:50)(EY-Ongoing)`. The
`(EY-Ongoing)` suffix makes `letters == letters.upper()` false, the guard does not fire, and
the name yields `scheduled`, `castes`, `rights` and `tribes` as acronyms. `scheduled` then
joins `Post Matric Scholarship For Scheduled Caste`. The tell is that Punjab prints the
same scheme a second time in Title Case, and that copy joins nothing.

The eight-letter ceiling added this round does not catch it: the pattern is
`[A-Z][A-Z0-9]{3,8}`, which is one leading letter plus up to eight more, so a NINE-letter
word still passes and `SCHEDULED` is nine. If the intent is what the comment says, that the
longest real acronym in this corpus is HPBOCWWB at eight, the quantifier wants to be `{3,7}`.

**2. A capitalised transliteration in brackets is not an acronym.**
`Universalisation of Secondary Education (ANDARIKI VIDYA)` yields `vidya` and `andariki`,
and `vidya` joins `Mahatma Jyothiba Phule Overseas Vidya Nidhi for BC and EBC`. The
bracketed-acronym rule is innocent here: `(ANDARIKI VIDYA)` contains a space and does not
match it. It is the capitals rule, on a name whose lower-case majority keeps the shouted
guard from firing. Telangana's only wrong join.

**3. Acronym containment accepts a substring at any offset, though its own comment says
tail.** The rule exists for `NRLM` inside `DAYNRLM`, and the code tests `x in y or y in x`.
`NDPS`, written in capitals in `Advisory Board under NDPS Act`, sits at offset 2 inside
`igndpsp`, the DERIVED initialism of `Indira Gandhi National Disability Pension Scheme
(Punjab)`, and covers 4 of its 7 letters, which clears the 0.5 ratio guard. Two wrong joins,
the second on the state's own typo, `Advisory Borad Under NDPS Act`.

**4. And one that is a judgement rather than a defect.** Five Punjab joins are a demand
book's generic head against a welfare board scheme of the same words: `Family Pension` to
`Family/ Widow Pension Scheme (P.B.O.C.W.W.B)`, `Old Age Pension` and `Indira Gandhi
National Old Age Pension` to `Old Age Pension Scheme (P.B.O.C.W.W.B)`, and `Maternity
Benefit Programme(60:40)(GoI-GoP))` to `Maternity Benefit Scheme (P.B.O.C.W.W.B)`. The
containment rule's comparability guard passes because the myScheme names are short too. The
Punjab Building and Other Construction Workers Welfare Board runs its own pension and
maternity schemes out of a cess, and they are not the state's. `Old Age Pension` also joins
`Indira Gandhi National Old Age Pension Scheme (Punjab)`, which is the central scheme and
not Punjab's own, though it correctly joins `Old Age Pension Scheme - Punjab` as well.

`parse/match.py` was NOT edited from here. Every one of these errors is a false MATCH,
which means a scheme is treated as present on myScheme and is therefore not claimed absent:
the cost is under-reported absence, not a false accusation, which is the asymmetry the
module is built on. The Telangana and Punjab absence counts in this register are floors
twice over.
