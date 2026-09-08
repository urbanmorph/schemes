# schemes

A monthly, machine-built register of Indian government schemes, assembled from official
sources, recording what each source publishes and what it leaves out.

> Karnataka runs 60 welfare schemes. Or 501. It depends which government portal you ask.

**10,749 schemes.** 5,478 named by at least one of the four national sources; the other
5,271 read out of sixteen state budget books, where no national source names them at all.
**1,661 are funded by a state and listed by no national portal**, worth ₹3.18 lakh crore.

Live at **<https://india-schemes.pages.dev>**.

It is meant to be read two ways. As a **reckoner**: what schemes exist, who they are for,
what they give, what they cost, and which government source says so, including the ones no
citizen-facing portal lists. And as an **audit**: what each source publishes about them and
what it leaves out. Every scheme page leads with the first and carries the second below it,
and the whole register downloads as one CSV.

Everything here is about *the data about* schemes, never about whether a scheme works.
"No end date published" is a fact about a database field. It is not a judgment on the
scheme, and every flag is worded so that distinction survives being screenshotted
without its caption.

**New here?** Read [PLAN.md](PLAN.md) first — it is the contract this repository follows,
and `collect/` is frozen for a reason. Then
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) if you are going to write code, or
[docs/MAINTAINING.md](docs/MAINTAINING.md) if you are going to run it. `./check.sh` runs
everything that can be checked without the network.

---

## What it found

Nobody had put these sources side by side, so the disagreements had never been counted.

**The portals disagree about how many schemes exist.**

| | myScheme | DBT Bharat | Union Budget |
|---|---|---|---|
| Central sector | 543 | | **637** |
| Centrally sponsored | 146 | | 86 |
| Karnataka | 60 | **501** | |
| Gujarat | **643** | 394 | |
| All states | 4,058 | **5,589** | |

These count different things, and none of them says so. A state's DBT figure reflects
how much that state has onboarded onto the DBT platform, not how many schemes it runs.

**Major schemes are funded and monitored but never announced to citizens.** Samagra
Shiksha (₹42,100 cr), Krishionnati Yojana (₹11,200 cr), Rashtriya Krishi Vikas Yojana,
National AYUSH Mission and the National Social Assistance Programme each carry a Union
Budget line and an Outcome Budget framework, and none appears on myScheme. 36 such
schemes, ₹2,20,750 cr, published at the classifier's high-precision threshold.

**A state's own budget names schemes its citizens cannot look up.** Karnataka publishes
Gender, Child and SCSP/TSP budgets naming 969 heads. myScheme lists 56 schemes for
Karnataka. 72 of the state's own, worth ₹9,453 cr, read as schemes and appear on the
national portal nowhere, at 97.3% precision counted against hand labels rather than
estimated. That is a floor: Gruha Lakshmi, the state's largest welfare scheme, is not in
it, because 580 of the 969 rows carry no purpose line for a classifier to read.

**Sixteen states now have their own budgets read against the portal**, and 1,661 of their
schemes reach no national portal at all: Telangana 267, Tamil Nadu 235, Uttar Pradesh 184,
Punjab 140, Jharkhand 124, Haryana 108, and ten more. Those numbers are floors set by how
much evidence each state prints and must not be added or ranked against each other, which
the site says wherever it shows them.

**Six states publish a budget no machine can read, and that is the finding.** DBT Bharat
counts 1,255 state schemes between them and myScheme lists 1,368; those two are the only
sources anybody has for these states and they agree about none of them, because the
document that would settle it is the one that cannot be read. Bihar converts its budget to
vector curves before publishing it: 108 pages yield 108 extractable characters. Himachal
Pradesh publishes thirty documents and serves none of them. Each refusal is published with
the measurement behind it and the single change that would undo it.

**The register remembers what it accused.** 1,690 schemes are on a watchlist with the date
each was first named as funded-and-unlisted, re-checked every cycle against the portal. A
scheme moving from unlisted to listed is recorded as two dates and nothing else: the portal
publishes no reason, and inferring one would be the move this project documents in others.

**Where records are thin, across all 4,771 myScheme entries:**

| | | |
|---|---|---|
| No end date published | 4,721 | 99.0% |
| No start date published | 3,723 | 78.0% |
| No implementing agency | 3,248 | 68.1% |
| No way to apply published | 1,727 | 36.2% |
| Benefit not quantified | 695 | 14.6% |
| Malformed URL in a stored field | 187 | 3.9% |
| Closed but still listed | 44 | 0.9% |

Those malformed URLs are worth looking at directly. They include a
`file:///C:/Users/…/Downloads/` path on a civil servant's own laptop, published as a
citizen-facing reference; a URL copied out of a Chrome PDF-viewer extension; two URLs
pasted into one field; and a numbered-list marker left inside a URL.

**77% of central schemes have no published outcome framework**, and the Outcome Budget
carries targets with no achieved-versus-promised column for any scheme. So this register
can tell you what a scheme promised and cannot tell you whether it delivered. That gap
is the government's, and it is now visible beside the promise.

**myScheme is not only a citizen portal.** 614 of its records (13%) reach no individual
at all: firms, industries, registered societies, universities and NGOs.

---

## How it works

```
  GitHub Actions, monthly on the 3rd
        |
        +--  collect/   FROZEN. Raw bytes to archive/. Never parses, never adapts.
        |
        +--  verify/    deterministic assertions. Writes status.json. Exits 1 on failure.
        |
        +--  parse/     replayable. archive/ to data/. An agent may fix this half.
        |
        +--  enrich/    secondary sources, kept strictly apart from the record.
        |
        +--  site/      static build to site/_out/, deployed to Cloudflare Pages by hand.
```

The rules below are the short form. [PLAN.md](PLAN.md) is the long one, and it is what the
76 files saying "read PLAN.md §7 before editing" are pointing at.

**`git log` is the change feed.** One file per scheme, overwritten each month, so
`git log -p data/myscheme/schemes/pm-kisan.json` is that scheme's history and
`git show <sha>:<path>` is any past snapshot. There is no diff engine to maintain.

### Three rules, each learned by getting it wrong

**A repair agent may fix `parse/`. It may never touch `collect/`.** The value here is a
*comparable* time series. A collector that breaks leaves a hole you can see and date. A
collector that quietly adapts leaves a seam you cannot: month 7 gathered under different
semantics than month 6, looking perfectly continuous. Parsing is replayable against the
archive; collection is not.

**Completeness is asserted, not assumed.** The failure mode is not a missing file, it is
a *present* file with the wrong bytes: a 401 body, a WAF interstitial, page 34 of 48. All
are valid writes. Every run is checked independently of the collector's own bookkeeping,
and a snapshot that fails is committed but marked `INCOMPLETE`, with `parse/` refusing to
build from it. An incomplete snapshot does not merely lose records, it *manufactures*
false change events.

**Matching a name is two different questions.** Deciding a budget line's money belongs to
a scheme should bias toward no, because a wrong yes publishes a rupee figure under the
wrong name. Deciding a scheme is *missing* from a portal should bias toward yes, because
a wrong yes accuses a portal of omitting something it lists. Using one threshold for both
inflated every absence claim here until it was caught. See `parse/match.py`, which has
self-tests for each failure that prompted it.

---

## Running it

```bash
./run.sh                 # collect, verify, parse, enrich, build
./run.sh --skip-collect  # rebuild everything from the existing archive, no network
./serve.sh               # build and serve at 127.0.0.1:8788
./check.sh               # every check that needs no network; run before pushing

# deploy (see PLAN.md §10; .dev.vars is gitignored and holds the token)
set -a && . ./.dev.vars && set +a
npx wrangler pages deploy site/_out --project-name=india-schemes --branch=main
```

`--skip-collect` is the one to reach for: it replays the whole pipeline against bytes
already in `archive/` and touches no government server.

No dependencies beyond the Python standard library, plus `poppler-utils` for the Budget
PDFs. A full census is about 4,820 paced requests, roughly an hour. `--limit N` caps the
detail crawl for smoke tests, and a limited run is deliberately marked `INCOMPLETE` so it
can never be mistaken for a real snapshot.

---

## Things learned the hard way

Each of these is encoded in the code with its measurement in a comment, because every one
of them silently produced wrong output first.

- **`size` caps at 100.** 200, 500 and 1000 return `data: null`. A full list is 48 pages.
- **`401` means rate-limited, not rotated.** After ~15 rapid requests the API 401s;
  re-extracting the key from the JS bundle returns a byte-identical key and the original
  works again about three minutes later. A 401 is never on its own evidence of rotation.
- **The default sort is not stable across requests.** Paging 48 pages under relevance
  sort returned 4,772 records but 4,735 distinct slugs: 37 duplicates straddling page
  boundaries, which means 37 schemes were never returned at all. Under `schemename-asc`
  it is 1.
- **Never HEAD a government URL.** `indiabudget.gov.in` returns 404 to HEAD and 200 to
  GET; `dbtbharat.gov.in` returns 403; `myscheme.gov.in` returns 405. Measured across 186
  real scheme URLs, HEAD misclassifies 18% of live pages as dead, so 42% of everything it
  flagged would have been wrong.
- **`indiabudget.gov.in` 403s any User-Agent that is not a bare browser string.** Not
  just bot keywords: appending a project URL is enough.
- **`pdftotext` drops rows silently.** Items 28 and 31 of Budget Statement 4A vanish from
  the extracted text in both `-layout` and plain mode, 84 rows where the document numbers
  86, with no error. Worse, the 84 rows still sum to the printed Grand Total exactly,
  because both lost rows carry a nil allocation. Reconciling the money would have passed
  while the scheme count was short by two, so row contiguity is a separate assertion.
- **`beneficiaryState` is returned by the search endpoint and not by the detail
  endpoint.** Building records from details alone drops the state dimension entirely.

---

## Data and sources

| Source | What it gives | Licence |
|---|---|---|
| [myScheme](https://www.myscheme.gov.in/) | scheme descriptions, eligibility, benefits | Government of India |
| [Union Budget](https://www.indiabudget.gov.in/) Statements 4A/4B | per-scheme allocations | Government of India |
| Union Budget Outcome Budget | output and outcome targets | Government of India |
| [DBT Bharat](https://dbtbharat.gov.in/) | DBT scheme lists and state counts | Government of India |

| [CAG audit reports](https://cag.gov.in/) | that an audit exists, never what it found | Government of India |
| Sixteen state budgets | each state's own scheme list, with allocations | the state that published it |

State sources are surveyed one at a time and the results, including the states that do
not yield a usable list, are recorded in [docs/state-sources.md](docs/state-sources.md).
There is no generic state parser and there should not be one: Karnataka's books carry an
`English / Kannada` separator that makes the scheme name unambiguous, and Gujarat's do
not, which is the whole difference between the two. Two states publish in legacy
Devanagari fonts rather than Unicode; `parse/krutidev.py` decodes one of them and the
other is unfinished.

Collected monthly and politely: one pass, paced, identified in the User-Agent wherever
the host permits it. Nothing here is scraped faster than it changes.

Derived datasets under `data/` are published CC BY 4.0. Code is MIT. Source material
carries the terms of the department that published it.

The API key in `collect/myscheme.py` is myScheme's own public client key, read from the
JS bundle their website serves to every visitor. It is public by construction, not a
credential.

## Status

Collection, verification, parsing, enrichment, the site and the monthly job are built and
running. The site is deployed at <https://india-schemes.pages.dev>; deployment is by hand
and documented in [PLAN.md §10](PLAN.md).

Sixteen states are read, six refuse and are published as refusals. Link reachability
(Tier 2) is deliberately not shipped: it carries a real error rate and belongs behind a
methodology page that does not exist yet.

Two things are knowingly unfinished, both recorded in the repository rather than in
somebody's head:

- **Chanakya**, the legacy font Chhattisgarh sets its department scheme books in, is not
  decoded. 2,562 scheme names are behind it. `parse/chanakya_derive.py` holds the
  derivation and `data/chhattisgarh/chanakya_corpus.json` the parallel corpus that any
  table has to satisfy. Nothing consumes its output and nothing should until it does.
- **The archive grows about 790 MB a year** and nothing is restructured for that yet. The
  reasoning, and the number the decision should be made against, are in
  [docs/MAINTAINING.md](docs/MAINTAINING.md).

Corrections are welcome, and the ones about a scheme's own record are the most useful. If
this register says something wrong about a scheme, the archive under `archive/` holds the
bytes it was derived from, so the error can be traced to the fetch that produced it.
