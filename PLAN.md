# PLAN

The contract this repository already follows.

This document was missing for the whole of the project's first year while 76 files told
their reader to consult it, 67 of them pointing at §7 before editing anything. Nothing here
is new policy. It is a reconstruction of the rules the code already enforces, written down
so that the next person can find them where the code says they are. Where this document and
the code disagree, the code is right and this file is the bug.

---

## §1 — Statements about the record, never about the scheme

Everything here is about *the data about* schemes. "No end date published" is a fact about
a database field. It is not a judgment on the scheme, and it is not a hint that money went
missing.

Every flag, column and sentence must survive being **screenshotted without its caption**.
That is the test, and it is why there is no letter grade anywhere in this register, only a
count of checks passed: a grade invites a reader to rank schemes, and this register has no
evidence about whether a scheme works.

The same rule governs the CAG pages. This register records **that** an audit exists, on
what, when, and where to read it. What an audit *concluded* is the CAG's to publish, and
paraphrasing a conclusion here would be this project doing the one thing it tells every
source not to do.

---

## §2 — The shape of the pipeline

```
collect/   FROZEN. Raw bytes to archive/. Never parses, never adapts.
verify/    Deterministic assertions over the archive. Writes status.json. Exits non-zero.
parse/     Replayable. archive/ to data/. An agent may fix this half.
enrich/    Secondary sources, kept strictly apart from the record.
site/      Static build to site/_out/, deployed to Cloudflare Pages.
```

`run.sh` is the pipeline and the only supported way to run it. It records each failing step,
keeps going, publishes what succeeded, and exits non-zero. A broken source costs that source
and not the month.

**Git is the archive.** One file per scheme, overwritten each month, so
`git log -p data/myscheme/schemes/pm-kisan.json` is that scheme's history. There is no diff
engine to maintain. `archive/` holds the raw bytes every claim was derived from, which is
what makes a correction traceable to the fetch that produced it.

---

## §3 — The sources

### §3.1 myScheme
The citizen-facing portal, and the only source written for citizens rather than accountants.
Its API key is public by construction, read from the JS bundle served to every visitor.

### §3.2 DBT Bharat
Per-state scheme counts and the central DBT list. It publishes a **count** per state and no
state scheme list, which is why a state's DBT figure can be compared and not itemised.

### §3.3 Union Budget, Statements 4A and 4B
Per-scheme allocations. Two assertions must both pass before these are publishable as a
census: the extracted money reconciles against the printed Grand Total, **and** the row
numbering is contiguous against the numbers the document itself prints.

Both are needed because they fail independently. `pdftotext` drops rows silently, and the
surviving rows can still sum to the printed total exactly when the lost rows carry a nil
allocation. Money reconciling is not evidence that the scheme count is right.

### §3.4 Outcome Budget
Output and outcome targets. It carries what a scheme promised and no achieved-versus-promised
column, so this register can say what was promised and never whether it was delivered.

### §3.5 State budgets
Surveyed one at a time, recorded in `docs/state-sources.md`, and there is **no generic state
parser**. Each state gets its own collector, parser and classifier because each publishes a
different document. A state that cannot be read is recorded as a refusal with the measurement
that decided it, and refusals are published beside the states that yielded.

### §3.6 The CAG audit catalogue
A catalogue and never a finding. See §1.

---

## §4 — What a scheme is, and the two bars

**The definition, which is the same in every state:**

> A **scheme** is where the money buys an identifiable benefit received by a person or
> household: cash, a kit, food, a scholarship, a stipend, a fee waiver, a pension,
> insurance, a subsidy that lowers what that household pays, a loan or an interest
> subvention on its own borrowing, free travel, free power, a house, a named treatment
> entitlement, or training in which the trainee is himself the beneficiary class.
>
> It is **not a scheme** where the money runs, builds, staffs or maintains an organisation
> or an asset, devolves general purpose funds to another tier of government, pays for the
> capacity of the delivery system rather than the benefit, discharges the state's obligation
> to its own serving or retired staff, services the state's own debt, or is an accounting or
> adjustment head.

That last clause is the one that does the work, and the one this register got wrong: seven
states were labelled against this wording and eight later ones against a looser sentence
admitting "a service". Sixty-nine published rows were re-read and fifty-six changed side.

**THE TWO BARS ARE DIFFERENT CLAIMS AND MUST NEVER SHARE A THRESHOLD.**

| bar | claim | tuned for |
|---|---|---|
| `listing_threshold` | "this state's budget names this as a scheme" | F1 optimum |
| `publish_threshold` | "this is funded and no portal lists it" | precision; recall is sacrificed |

Listing a budget head is an annoyance. Naming one as hidden is a false accusation. Using one
threshold for both inflated every absence claim here until it was caught.

Every row at or above the publishing bar carries a hand label, so precision is a **count**
and the errors are **named** in `known_errors`. Recall is measured on the **stratified sample
alone**: the audit census is selected on the classifier's own output, so counting it there
raises the number with the size of the audit rather than the quality of the classifier.
`parse/ratios.py` asserts all of this and fails the run if any published ratio divides two
counts of different populations.

---

## §5 — Tiers of checks

**Tier 1 ships first and alone.** These need no network and therefore have no false-positive
rate: either a field is there or it is not. `parse/checks.py`.

**Tier 2, link reachability**, and **Tier 3, cross-source joins**, carry real error bars and
belong behind a methodology page. Tier 2 is still not shipped. Tier 3 ships only where the
join is validated by hand and the rejected rules are published with the measurement that
rejected them — see `parse/cag_join.py`.

Never HEAD a government URL. Measured across 186 real scheme URLs, HEAD misclassifies 18% of
live pages as dead.

---

## §6 — Cadence

**Monthly**, on the 3rd, via `.github/workflows/collect.yml`. The Budget is annual and
myScheme moves slowly; weekly was never justified by the data's velocity and only multiplied
the request load against visibly fragile state infrastructure.

Annual sources are collected once per cycle and guarded by `have_cycle()`, which reads the
cycle out of each state's manifest. A glob over the archive directory is **not** a
cycle guard: a state collected once would never be collected again.

GitHub disables scheduled workflows after 60 days without repository activity, so the manual
trigger is kept and the warning email must be acted on.

---

## §7 — Frozen and agent-editable

**This is the section every file points at.**

### `collect/` is FROZEN

A repair agent, or a maintainer in a hurry, may fix `parse/`. **Neither may touch
`collect/`.**

The value of this register is a *comparable* time series. A collector that breaks leaves a
hole you can see and date. A collector that quietly adapts leaves a seam you cannot: month 7
gathered under different semantics than month 6, looking perfectly continuous. Parsing is
replayable against the archive; collection is not.

If a source changes shape, the collector is allowed to **fail loudly** and the month is
allowed to have a hole. Changing the collector is a deliberate, human, reviewed act, and the
commit must say what changed about the source.

### `parse/`, `enrich/` and `site/` are AGENT-EDITABLE

They read `archive/` and `data/` and never fetch. Anything they get wrong can be corrected
by re-running them against bytes that have not moved.

Every file in this repository states which half it is in, in its first three lines. A new
file must do the same.

### The repair job may open a PR and may never merge one

`.github/workflows/collect.yml` carries an optional repair job, inert until a key is
configured. It may propose changes to `parse/`. It must never touch `collect/`, and it must
never merge: the value of the archive is that collection semantics do not drift, and a PR is
where a human checks that.

---

## §8 — Completeness is asserted, not assumed

The failure mode is not a missing file. It is a **present file with the wrong bytes**: a 401
body, a WAF interstitial, page 34 of 48. All of those are valid writes. R2 or git give
durability; nothing gives completeness. `verify/verify.py` does.

It re-counts from the archive rather than trusting the collector's own manifest, because a
collector that miscounts would otherwise certify itself.

Assertions, all fail-loud:

1. details in the archive == `summary.total` from the census response
2. list pages written == pages expected
3. no archived body matches a known error shape
4. (annual) parsed budget line items sum to the PDF's printed Grand Total

A failing run is still archived and still committed, marked `INCOMPLETE`, and `parse/` must
refuse to build `/changes` against it. An incomplete snapshot does not merely lose data, it
**manufactures false events**: one dropped page reads as "100 schemes removed this month",
which is a headline-shaped artefact and entirely our own bug.

A `--limit` run is deliberately marked INCOMPLETE so a smoke test can never be mistaken for a
real snapshot.

---

## §9 — A failure has to reach a human

The alarm must arrive without anyone going to look for it. A failed job emails; a dashboard
does not. The workflow's last step keys on `run.sh`'s exit status rather than on verification
alone, because a snapshot can verify while a state parser, the CAG crawl or a classifier did
not run at all.

`status.json` carries the verdict, the standing issues and anything needing attention, and it
is committed every run so the history of the register's own health is in git beside the data.

---

## §10 — Deployment

The site is a static build in `site/_out/`, published to **Cloudflare Pages**, project
`india-schemes`, live at <https://india-schemes.pages.dev>.

**Deployment is automatic and nobody holds the token.** It used to be a `wrangler` command
run by hand, which meant one person had the credential and was therefore the only route to
production. `.github/workflows/deploy.yml` is a callable workflow, invoked from exactly two
places:

- `check.yml`, after checks pass on a push to `main`. A failing check never reaches the
  public site and a pull request never deploys at all.
- `collect.yml`, after the monthly run commits. This call is necessary rather than tidy: a
  push made with `GITHUB_TOKEN` does not trigger other workflows, so without it the month's
  data would land in the repository and never reach the site.

It rebuilds the site rather than carrying an artefact between jobs, because `site/_out` is
not committed and publishing a stale artefact is the failure this is meant to prevent. It
re-checks every internal link before uploading, and confirms the deployed pages answer 200
afterwards.

`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are **repository secrets**. The token is
scoped to Account → Cloudflare Pages → Edit on the urbanmorph account and nothing else. It
must never be pasted into a chat, a log, an issue or a commit. There is no reason for a
developer to hold a copy; if you find yourself wanting one, deploy from
**Actions → Deploy → Run workflow** instead.

`.dev.vars` remains gitignored and is only needed if you are deploying from a laptop, which
you should not need to do.

Two things about the deployed site that have each caused a wrong conclusion:

- **Unknown paths serve `index.html` with HTTP 200** unless `404.html` exists, which is how
  15,108 dead links once stayed invisible. `404.html` is built; keep it.
- **The edge serves stale under `stale-while-revalidate`.** A check immediately after a
  deploy can return the previous build. Use a cache-busting query, which the deploy
  workflow's own confirmation step does.

## §11 — Taking this over

Read in this order: this file, then `README.md`, then `docs/state-sources.md`, then
`docs/MAINTAINING.md` for the month-to-month operation.

The two habits that matter more than any of the code:

**Publish the measurement that rejected a claim.** Every classifier carries a
`signals_rejected` block naming what was tried and the number that killed it. A signal
removed without a measurement is an opinion.

**Never let a number and its denominator come from different populations.** This has been
the shape of every serious bug here: an absence claim counted under a key the site did not
read, a recall divided by a sample plus a census, a join divided by half the register.
`parse/ratios.py` exists to catch the next one.
