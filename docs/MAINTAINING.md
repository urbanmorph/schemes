# Maintaining this register

Month to month, and what to do when it breaks. Read `PLAN.md` first; this is the operational
half of it.

---

## The monthly job

`.github/workflows/collect.yml` runs at **04:00 UTC on the 3rd**. It runs `./run.sh`, commits
`archive/`, `data/` and `status.json`, and fails loudly if any step failed.

It takes about an hour and a half. Most of that is paced HTTP: roughly 4,800 requests to
myScheme and 281 to the CAG catalogue, deliberately slow.

**It deploys itself.** The job calls `deploy.yml` after committing, so the month's data
reaches the site without anybody doing anything. That call is necessary rather than tidy: a
push made with `GITHUB_TOKEN` does not trigger other workflows, so the deploy has to be
invoked explicitly or the data would sit in the repository unpublished.

### When it fails

The job emails on failure. Read the log from the bottom:

```
1 step(s) failed:
    parse/dbt
the site was built from what succeeded. Fix the above before trusting this month.
```

`run.sh` names each failing step and keeps going, so one broken source costs that source and
not the month. Then:

1. `status.json` carries the verdict and any standing issues.
2. Re-run locally against the archive that was already committed:
   `./run.sh --skip-collect --date <the snapshot date>`. This touches no network.
3. If the fix is in `parse/`, fix it and re-run. If it is in `collect/`, read §7 before
   touching anything.

A source that has changed shape is **allowed** to leave a hole. Do not make the collector
adapt to keep the run green.

---

## The monthly checks worth doing by hand

- **Did the watchlist move?** `data/watchlist.json`. `since_listed` going above zero is the
  most interesting event this register can produce: a scheme it named as unlisted has
  appeared on the portal. Two dates, and no claim about what connects them.
- **Did any refusal change?** The six refused states are re-checkable in minutes and one of
  them has already changed reason once: Madhya Pradesh stopped being a font problem and
  became a cycle problem, and the survey said the wrong thing until it was rechecked.
  Especially worth checking after March, when states publish a new cycle.
- **Did `parse/ratios.py` pass?** It is in the run, so a failure is already loud. It exists
  because three separate bugs were the same shape: a number divided by a population it did
  not come from.
- **Did the archive grow as expected?** `run.sh` prints its size every run. Roughly 790 MB a
  year. See below.

---

## Adding a state

There is no generic state parser and there should not be one. Each state is:

1. `collect/<state>.py` — raw bytes to `archive/<state>/<date>/`, with a `_manifest.json`
   carrying the `cycle`. Frozen once written. Record what you did **not** take and why, in a
   `SKIPPED` dict: a document missing from the archive is otherwise indistinguishable from a
   collector that failed to find it.
2. `parse/<state>.py` — `archive/` to `data/<state>/schemes.json`, with a `caveat` saying what
   one row is in that state's own terms.
3. `data/<state>/labels.json` — hand labels. A stratified probability sample of the whole
   book, **plus an audit census of every row at the publishing bar**, each row carrying its
   `how`. The census is what makes precision a count; the sample is what makes recall
   honest. They must never be mixed in one denominator.
4. `parse/classify_<state>.py` — the state's own signals, each with the measurement that
   earned it, and a `signals_rejected` block with the measurement that killed the others.
5. Add it to `STATE_OF` in `site/build.py`, to the three state lists in `run.sh`, and to
   `SURVEY` in `parse/legibility.py`.

**Key the labels on the source's own identifier**, never on anything this register derives.
Chhattisgarh's labels were keyed on the decoded Hindi name, and improving the decoder by one
letter orphaned fifteen of them.

Budget: a state is a day or two, and the hand labels are most of it.

---

## The legacy Devanagari fonts

Two states publish in fonts that are not Unicode.

- `parse/krutidev.py` decodes **Kruti Dev**, which is ASCII and whose table is fixed. Used by
  Uttar Pradesh and Chhattisgarh, and it reads Madhya Pradesh unchanged. It has self-tests;
  run `python3 parse/krutidev.py`.
- **Chanakya** is not decoded. `parse/chanakya_derive.py` and
  `data/chhattisgarh/chanakya_corpus.json` hold an unfinished derivation and the parallel
  corpus to check it against. Nothing consumes its output, and nothing should until every
  pair in the corpus decodes exactly **and** a sample from outside it reads as Hindi to
  somebody who reads Hindi. 2,562 Chhattisgarh scheme names are behind it.

Decoding a font encoding is a reading; it recovers the characters that are on the page.
Translating is a claim about meaning and this register does not make one.

---

## The archive

`archive/` is the evidence and stays in git, so it only grows. Measured 2026-09: **0.69 GB**,
of which 676 MB is the fifteen state budget books. Those are annual, so growth is about
**790 MB a year** — GitHub's 1 GB warning inside a year and their 5 GB "please reduce" range
in about five.

Nothing is restructured for that yet, on purpose. `git-lfs` needs paid data packs above 1 GB,
and splitting the archive into its own repository costs the property that makes this
auditable: that the code and the bytes it read are one checkout. Both are worth doing when
the number says so. `run.sh` prints the number every run so the judgement is made against a
measurement.

---

## Things that will bite you

- **Never HEAD a government URL.** 404 from `indiabudget.gov.in`, 403 from `dbtbharat.gov.in`,
  405 from `myscheme.gov.in`, all on live pages.
- **`indiabudget.gov.in` 403s any User-Agent that is not a bare browser string**, including
  one with a project URL appended.
- **Three state finance sites serve an incomplete certificate chain.** The intermediates are
  carried in `collect/certs/` and registered per host in `collect/common.py`. Verification
  stays on; the gap is filled, not bypassed.
- **`pdftotext` drops rows silently** and the survivors can still sum to the printed total.
- **Set iteration is not stable across runs.** Hash randomisation reordered a `Counter`
  tie-break and moved the site's page count between builds on identical data; it also moved
  the *reason* recorded for a scheme match. Sort before taking a first element.
- **The Cloudflare edge serves stale after a deploy.** Check twice, or with a cache-buster.

---

## What this register will not do

- Say whether a scheme works, or characterise what an audit concluded (§1).
- Publish a name it cannot read.
- Publish a ratio whose numerator and denominator come from different populations.
- Adapt a collector to keep a run green.
- Add a state without hand labels.
