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

## What this means for the other 34

There is no generic state parser and there should be no attempt to write one. Karnataka
parsed in an afternoon because of one typographic accident. Gujarat resisted four
strategies because it lacks that accident, and it is not obviously the harder state: it
publishes more in English than many.

So the honest plan is per-state, with an explicit go or no-go recorded here after
measurement rather than after effort. A state that does not yield is a finding about that
state's transparency, and belongs on the site as one.
