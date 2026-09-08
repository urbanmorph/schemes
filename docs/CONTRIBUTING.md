# Working on this

For someone writing new code here, not just keeping it running. `PLAN.md` is the contract;
`docs/MAINTAINING.md` is the month-to-month operation; this is how to make a change that
fits, and where the open work is.

---

## Before you push

```bash
./check.sh
```

Syntax across every file, the self-tests, the ratio guard, the site build, and every
internal link. No network, a few seconds. **There is no CI beyond the monthly collection
job**, and that job is the wrong place to discover you broke something: it runs once a month
and its failure costs a snapshot.

---

## Three things about working in parallel

**Do not commit `data/` from a feature branch.** It is 73 JSON files regenerated wholesale
by every run, so two branches that both ran the pipeline conflict on all of them and the
conflict is meaningless — the content is derived. Work on code, let `data/` regenerate on
`main`, and if a merge conflicts there take either side and re-run `./run.sh --skip-collect`.

**`site/build.py` is 3,716 lines and is the likeliest collision.** If we are both in it, say
which page. It is one file because the site is one build; splitting it is reasonable work
that nobody has done.

**`archive/` is append-only and never conflicts.** It is also 0.69 GB, so a fresh clone is
slow. `git clone --filter=blob:none` if you only want the code.

---

## The house style, which is not decoration

Read a few classifiers before writing one. The conventions carry the argument:

**A signal must be published with the number that earned it.** Every classifier has a
docstring listing what each signal measured over the hand labels, and a `signals_rejected`
block naming what was tried and the measurement that killed it. A signal added without a
measurement is an opinion, and a signal removed without one is worse.

**Comments say why, with the number that decided it.** Not "sort for determinism" but "sorted
because `Counter.most_common` tie-breaks on insertion order, insertion order comes from
iterating a set, and the registry said `iccr / ipiccr` one month and `iccr / iccr` the next on
identical bytes". If you cannot name the failure, the comment is not finished.

**Errors stay named rather than patched away.** When the audit census finds a row the
classifier got wrong and the evidence in that state cannot support a weight to fix it, it goes
in `known_errors` and stays there. Patching a weight to remove a single row you just found is
fitting the classifier to its own audit.

**Refuse rather than guess.** A name this register cannot read is a name it does not publish.
A ratio it cannot reproduce fails the run. A state whose budget cannot be parsed is recorded
as a refusal with the measurement, not approximated.

**Commit messages say what was learned.** They are the project's real notebook and several
have been the only record of a subtle finding. Long is fine.

---

## Adding anything that publishes a number

Three rules, each of which was learned by getting it wrong:

1. **The numerator and the denominator come from the same population.** `parse/ratios.py`
   asserts this and it exists because three separate bugs were this shape.
2. **Say what the number is measured on**, in the sentence that shows it. "Recall is 34%,
   measured on the stratified sample alone" rather than "recall is 34%".
3. **Compute it, never type it.** A figure written into prose drifts from the figure in the
   file. `/divergence` said 37% for Andhra for two commits after the data said 36%.

---

## Where the open work is

Rough order of value, and each is genuinely unstarted or genuinely stuck rather than merely
unpolished.

### Chanakya — 2,562 Chhattisgarh scheme names behind a font
`parse/chanakya_derive.py`, `data/chhattisgarh/chanakya_corpus.json`. The encoding is
understood, the corpus to check any table against exists, and the derivation reaches 10 of
187 pairs exactly. What is left: use the full 235 pairs rather than the filtered 187,
separate corpus noise from table error before tuning anything, and hold out a split, because
a greedy override loop already "improved" the score by making अकादमी decode as अृादमी. The
bar before it ships is every pair exact **and** a sample from outside the corpus read by
somebody who reads Hindi. This is the hardest thing on the list and the most likely to
resist.

### Tier 2, link reachability
Never shipped, deliberately. Every stored URL in the register could be checked for whether it
resolves, which is a real finding about a portal, and it carries a real error rate: **never
HEAD a government URL**, and even GET misclassifies. It belongs behind a methodology page
that does not exist. See `PLAN.md` §5.

### The remaining five refusals
Each is published with the single change that would undo it. Two are worth re-checking rather
than working on: **Madhya Pradesh** needs only its 2026-27 cycle to appear, and the decoder
for it already works; **Assam** needs a current-cycle scheme list. Gujarat and Rajasthan are
genuine parsing problems and Rajasthan's is probably unsolvable honestly, because it prints no
totals to check a reconstruction against. Bihar publishes drawings.

### The archive decision
0.69 GB, growing about 790 MB a year. Nothing is restructured yet and the reasoning is in
`docs/MAINTAINING.md`. Somebody will have to decide between git-lfs and a split repository,
and the second costs the property that makes this auditable.

### Splitting `site/build.py`
3,716 lines, one file, and the reason it has not been split is that nobody has needed to
badly enough. If you are going to live in it, this is worth doing first.

---

## What not to do

- **Do not touch `collect/`** to make a run go green. `PLAN.md` §7 is the whole argument and
  it is the one rule with no exceptions.
- **Do not add a state without hand labels.** The precision claims are counts because every
  row at the publishing bar carries one. A state added without them publishes an estimate
  dressed as a count.
- **Do not translate.** Decoding a font encoding recovers the characters on the page and is a
  reading. Rendering Hindi into English is a claim about meaning this register does not make.
- **Do not characterise an audit's findings.** `PLAN.md` §1.
