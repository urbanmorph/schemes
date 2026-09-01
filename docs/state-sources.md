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

## Scoreboard

| State | Verdict | Best document | What makes it work, or not |
|---|---|---|---|
| Kerala | yes | Annual Plan statements, 1,639 codes vs 81 on myScheme | scheme code, English column, Unicode Malayalam, objectives |
| Andhra Pradesh | yes | Gender Budget, 223 names vs 51 | plain English, single script |
| Karnataka | **built** | Gender, Child, SCSP/TSP, 969 heads vs 56 | the `English / Kannada` slash |
| Telangana | yes | SCSDF scheme-wise, vs 22 | plain English table |
| Tamil Nadu | yes | ~50 department Demand Books, vs 234 | bilingual, English in its own column |
| Gujarat | **no** | Outcome Budget | no separator, columns move between pages |

Five of five southern states yield a machine-readable scheme list. Gujarat does not. That
is a smaller sample than it looks, because all five publish in a Dravidian or Malayalam
script that cannot share a column with Latin text, which forces the English into a column
of its own. Gujarati is also non-Latin, so script alone is not the explanation, but the
southern states have each chosen a layout that keeps the two apart and Gujarat has not.

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

Order to work in, by gap size against myScheme and by how little parsing each needs:
Andhra Pradesh and Telangana first because they are plain English, then Kerala because it
is the largest gap in the country and the richest document, then Tamil Nadu. Karnataka is
done.

A state that does not yield is a finding about that state's transparency, and belongs on
the site as one. Gujarat publishes a great deal and still cannot be read by a machine,
which is a different and more interesting failure than publishing nothing.
