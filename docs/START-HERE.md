# Start here

You have just been given access to this repository and know nothing about it. This page is
the hour it takes to become useful. Read it in order; every step ends with something you
can check.

---

## 1. What this is, in one paragraph

Four national government sources publish lists of Indian welfare schemes, and none of them
agrees with the others about how many exist. Sixteen state governments publish their own
budgets, which name schemes no national portal lists at all. This repository collects all of
it once a month, keeps the raw bytes forever, and publishes a register that says what each
source claims and what it leaves out. It is at
<https://india-schemes.pages.dev>.

The register makes **statements about records**, never about schemes. "No end date
published" is a fact about a database field. Whether a scheme works is not a question this
project has any evidence about, and every sentence on the site is written so that stays true
when the sentence is screenshotted without its caption.

---

## 2. Get it running (about ten minutes, no network)

```bash
git clone --filter=blob:none git@github.com:urbanmorph/schemes.git
cd schemes
brew install poppler        # or: apt-get install poppler-utils
./check.sh
```

`--filter=blob:none` matters: `archive/` is 0.69 GB of government PDFs and you do not need
its history to work on the code. Git fetches blobs on demand.

`./check.sh` runs every check that needs no network — syntax, the self-tests, the ratio
guard, the site build, and every internal link. It should end with **all checks passed**.
That is your baseline; run it before every push.

Then:

```bash
./run.sh --skip-collect     # replay the whole pipeline from the archive. No network.
./serve.sh                  # look at what you built, at 127.0.0.1:8788
```

`--skip-collect` is the command you will use ninety per cent of the time. It rebuilds
everything from bytes already on disk and touches no government server.

**Do not run bare `./run.sh` casually.** It collects: about 4,800 paced requests taking an
hour and a half against public infrastructure, some of it visibly fragile.

---

## 3. The one rule

**`collect/` is frozen. Everything else can be fixed.**

The value here is a *comparable* time series. A collector that breaks leaves a hole you can
see and date. A collector that quietly adapts leaves a seam you cannot: month 7 gathered
under different semantics than month 6, looking perfectly continuous. Parsing replays against
the archive; collection does not.

So when a government site changes shape, the collector is **allowed to fail** and the month
is **allowed to have a hole**. Do not make it adapt to keep a run green. Changing a collector
is a deliberate, reviewed act.

Every file says which half it is in, in its first three lines. `PLAN.md` §7 is the argument
in full, and 67 files point at it.

---

## 4. Read the code in this order

The codebase is roughly 36,000 lines, and most of it is per-state parsing you can ignore
until you need it. Four files carry the ideas:

| file | why |
|---|---|
| `PLAN.md` | the contract. Sections 1, 4, 7 and 8 are the ones that matter. |
| `run.sh` | the pipeline, top to bottom. Every stage in order, with its reasoning. |
| `parse/classify_common.py` | how a budget line becomes a claim, and the two bars. |
| `parse/ratios.py` | what this project treats as a bug, which tells you a lot. |

Then one state end to end — `collect/tripura.py`, `parse/tripura.py`,
`parse/classify_tripura.py` — because Tripura is the smallest and the whole shape fits in
your head.

---

## 5. The idea you have to have

Two claims, two thresholds, and confusing them was the project's worst bug.

- **"This state's budget names this as a scheme."** Weak claim. Being wrong is an
  annoyance. Tuned to the F1 optimum.
- **"This is funded and no portal lists it."** An accusation about a government portal.
  Being wrong is a false accusation. Tuned for precision; recall is deliberately sacrificed.

Every row at or above the second bar carries a **hand label**, so the precision printed on
the site is a *count*, not an estimate, and the errors are *named* rather than described.
That is why adding a state means writing a few hundred hand labels, and why a state cannot
be added without them.

The corollary, which `parse/ratios.py` enforces: **a number and its denominator must come
from the same population.** Three separate bugs here were that shape.

---

## 6. How work reaches the site

```
you push  ->  Checks (check.sh)  ->  if main and green: Deploy  ->  india-schemes.pages.dev
                                  \
3rd of the month: Collect  ->  commit archive/ + data/  ->  Deploy
```

Nobody holds a Cloudflare token. A pull request never deploys; a failing check never
deploys. If you need to publish without a commit: **Actions → Deploy → Run workflow**.

---

## 7. Working alongside somebody else

- **Do not commit `data/`.** 73 files regenerated wholesale by every run, so two branches
  that both ran the pipeline conflict on all of them, meaninglessly. Take either side and
  re-run `./run.sh --skip-collect`.
- **`site/build.py` is 3,716 lines** and is the likeliest collision. Say which page you are in.
- **`archive/` is append-only** and never conflicts.

---

## 8. Pick something up

`docs/CONTRIBUTING.md` has the open threads with enough context to start cold. The two
easiest first tasks, if you want something bounded:

- **Re-check a refusal.** Six states publish budgets no machine can read, each recorded with
  the measurement that decided it and the one change that would undo it. Two of them are
  waiting on nothing but a new cycle. One has already changed reason once, and the survey said
  the wrong thing until somebody looked again.
- **Split `site/build.py`.** Nobody has needed to badly enough, and everybody who works in it
  wishes somebody had.

The hardest thing on the list is decoding **Chanakya**, the legacy font Chhattisgarh sets
2,562 scheme names in. It has a parallel corpus to check against, an unfinished derivation,
and a record of the four wrong models that came before the right one. It has already fooled a
greedy optimiser into scoring better while rendering अकादमी as अृादमी, which is the whole
reason it is not shipped.

---

## 9. What this project will not do

- Say whether a scheme works, or characterise what an audit found.
- Publish a name it cannot read, or a number it cannot reproduce.
- Adapt a collector to keep a run green.
- Add a state without hand labels.
- Translate. Decoding a font recovers the characters on the page and is a reading.
  Rendering Hindi into English is a claim about meaning, and this register does not make one.

Those are not style preferences. Each is there because the opposite was tried and published
something wrong.
