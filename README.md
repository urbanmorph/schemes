# schemes

A monthly archive of Indian government scheme data, and a record of what is missing
from it.

There are ~4,772 welfare schemes listed on myScheme, 723 scheme lines in the Union
Budget, and 5,909 schemes on DBT Bharat. No two of those sources agree, none of them
reconciles to the others, and **none of them keeps a record of what it said last month.**
This repository keeps that record.

> Karnataka runs 60 welfare schemes. Or 501. It depends which government portal you ask.

Everything published here is about **the data about** schemes — how completely each one
is documented, whether its official links resolve, whether sources contradict each other,
and what changed since last month. Nothing here is a judgment on whether a scheme works.
"No outcome framework published" is a fact about the Outcome Budget, not about PM-KISAN.

## Why this exists

India's scheme-tracking layer did not collapse — but its artifacts did. Open Budgets
India (CBGA + CivicDataLab, 20,000+ datasets) lost its domain; `openbudgetsindia.org`
now serves *"Best Online Casino India 2026"*. Both organisations are alive and shipping
code. Renewing a domain was simply nobody's job.

The lesson taken here is that **the dangerous failure state is not down, it is
up-and-stale** — so this repository reports its own freshness as prominently as it
reports anyone else's, and fails loudly when a monthly collection does not complete.

## How it works

```
  GitHub Actions (monthly)
        │
        ├─ collect/   frozen. raw bytes → archive/. never parses, never adapts.
        │
        ├─ verify/    deterministic assertions. writes status.json. exits 1 on failure.
        │
        └─ parse/     replayable. archive/ → data/. the only part an agent may fix.
```

**`git log` is the change feed.** One file per scheme, overwritten each month, so
`git log -p data/myscheme/schemes/pm-kisan.json` is that scheme's history and
`git show <sha>:<path>` is any past snapshot. There is no diff engine to maintain.

### The one rule

**The repair agent may fix `parse/`. It may never touch `collect/`.**

The value here is a *comparable* time series. A collector that breaks leaves a hole you
can see and date. A collector that quietly adapts leaves a seam you cannot — month 7
gathered under different semantics than month 6, looking perfectly continuous. That is
worse than a gap. Parsing is replayable against the archive; collection is not.

### Completeness is asserted, not assumed

The failure mode is not a missing file. It is a *present* file with the wrong bytes: a
401 body, a WAF interstitial, page 34 of 48. All are valid writes. So every run is
checked, independently of the collector's own bookkeeping:

| Assertion | Catches |
|---|---|
| list records == census total | paging drift, throttled pages |
| a detail for every slug | interrupted detail crawl |
| no error-shaped bodies | 401s and challenge pages archived as data |
| budget line items == printed Grand Total | silent row loss in PDF extraction |

A snapshot that fails is still committed — marked `INCOMPLETE`, with `parse/` refusing
to build from it. An incomplete snapshot does not merely lose records, it *manufactures*
false events: one dropped page reads downstream as "100 schemes removed this month".

## Running it

```bash
python3 collect/myscheme.py --date 2026-08-30      # raw bytes → archive/
python3 verify/verify.py    --date 2026-08-30      # assertions → status.json
python3 parse/explode.py    --date 2026-08-30      # archive/ → data/
```

No dependencies beyond the standard library. `--limit N` caps the detail crawl for smoke
tests; a limited run is deliberately marked `INCOMPLETE` so it can never be mistaken for
a real snapshot. A full census is ~4,820 paced requests, about an hour.

## Things learned the hard way

Each of these is encoded in the code, with the measurement in a comment:

- **`size` caps at 100.** 200, 500 and 1000 return `data: null`. A full list is 48 pages.
- **`401` means rate-limited, not rotated.** After ~15 rapid requests the API 401s;
  re-extracting the key from the JS bundle returns a byte-identical key, and the original
  works again ~3 minutes later. So a 401 is never on its own evidence of rotation — the
  collector re-extracts and *compares* before reporting a key event.
- **The default sort is not stable across requests.** Paging 48 pages under the default
  relevance sort returned 4,772 records but only 4,735 distinct slugs — 37 duplicates, 36
  of them straddling a page boundary, which means 37 schemes were never returned at all.
  Under `schemename-asc` it is 1. This is why the census assertion exists.
- **Never HEAD a government URL.** `indiabudget.gov.in` returns 404 to HEAD and 200 to
  GET; `dbtbharat.gov.in` returns 403; `myscheme.gov.in` returns 405. Measured across 186
  real scheme URLs, HEAD misclassifies 18% of *live* pages as dead — 42% of everything it
  flags would be wrong.
- **`pdftotext` drops rows silently.** Items 28 and 31 of Budget Statement 4A vanish from
  the extracted text in both `-layout` and plain mode — 84 rows where the document numbers
  86 — with no error. The printed Grand Total is the only independent witness the document
  offers, so the parse is held to it.

## Status

Phase 1 of [the plan](supporting-docs/PLAN.md): collector, verifier, manifest. The site,
the quality rubric and the cross-source join are later phases and deliberately not built
yet — the archive is the part that cannot be backfilled, so it starts first.

Current state is in [`status.json`](status.json).

## Licence

Code MIT. Collected data carries the terms of its source; derived datasets published
CC BY 4.0.
