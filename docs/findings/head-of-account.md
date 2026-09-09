# The number we were not reading: the head of account

**Status: adopted in four states on 2026-09-09, per state, at a weight each state's own
audit census supports.** Kerala, Karnataka, Tamil Nadu and West Bengal. Not adopted in
Odisha, Andhra Pradesh or Maharashtra, and the reasons are in "Where it was not adopted"
below. What changed and where each number came from is in "What was actually adopted".

---

## The question

Every classifier in this register reads the scheme's **name**. Sixteen states, sixteen sets
of regexes, each derived separately because each state writes differently. Median recall at
the publishing bar is **41%**, and the worst are Kerala 12%, West Bengal 21%, Odisha 25%.

The question that prompted this: are the schemes carrying an identifying number we are not
looking at?

They are, and it is not a scheme code. Scheme codes exist in most state books and are
**state-internal**: Odisha's 4-digit code means nothing in Maharashtra's 10-digit one. The
useful number is the **head of account**, whose first four digits are a *nationally
standardised* function code. 2235 is Social Security and Welfare in every state's book and
in the Union Budget. It is the only vocabulary all these documents share.

---

## What it measures

On the **stratified sample only** — never the audit census, which is selected on the
classifier's own output:

| state | base rate | head | P(scheme) | over |
|---|---|---|---|---|
| Kerala | 0.159 | 2225 Welfare of SC/ST/OBC | **0.632** | 19 |
| Kerala | 0.159 | 2230 Labour and Employment | 0.500 | 10 |
| West Bengal | 0.084 | 2235 Social Security and Welfare | **0.385** | 26 |
| West Bengal | 0.084 | 2049 Interest Payments | **0.000** | 21 |
| Odisha | 0.103 | 2235 Social Security and Welfare | 0.333 | 27 |
| Odisha | 0.103 | 3451 Secretariat, Economic Services | **0.000** | 14 |

**The same heads behave the same way in different states.** 2235 and 2225 lift everywhere;
2049 and 6003, interest and internal debt, are zero everywhere. No name-based signal in this
register has ever been portable — Karnataka's purpose line is worth 0.947 and Haryana's is
worth 0.008. This one is, because the code is a national standard rather than a local habit.

## And it recovers exactly what the names miss

Of the labelled schemes in each stratified sample that the current classifier does **not**
catch:

- **Kerala** misses 43, clustering in 2225 (7), 2401 (6), 2501 (6), 2230 (5), 2235 (4)
- **West Bengal** misses 30, clustering in 2235 (7)
- **Odisha** misses 30, clustering in 2235 (6)

2235 is the top miss in two of the three. The classifiers are missing welfare schemes filed
under the welfare head, because they only ever read the name.

## Held out

The eight heads above were chosen by looking at Kerala, West Bengal and Odisha, so they are
fitted to those three. On states not used to choose them:

| state | inside the heads | outside | lift |
|---|---|---|---|
| Karnataka | 0.662 over 71 | 0.222 over 144 | **3.0x** |
| Tamil Nadu | 0.409 over 93 | 0.075 over 306 | **5.4x** |
| Andhra Pradesh | 0.458 over 59 | 0.403 over 144 | 1.1x |

Two of three hold strongly. **Andhra does not**, and that is in the table rather than left
out: whatever this signal is measuring, it is not measuring it there.

---

## What adopting it would cost

Simulated as a flat bonus on the existing score, with precision counted on rows that already
carry a hand label:

| state | now | +2 for a welfare head |
|---|---|---|
| **Kerala** | 38 rows, precision 0.974 | **99 rows, precision 0.909** |
| West Bengal | 134 rows, 0.925 | 222 rows, 0.901 |
| Odisha | 31 rows, 0.903 | 64 rows, **0.688** |

**Kerala is a clear win**: 2.6 times the schemes at a precision still above the register's
floor, which is Odisha's 0.903. **Odisha is a clear loss.** West Bengal is on the line.

Two things make Kerala unusually cheap: **no newly unlabelled rows**, because its audit
census already labelled down to score 4 and the bar is 9, so the precision above is a COUNT
and not an estimate. The work is already paid for.

---

---

## What was actually adopted

Not a new signal and not a new head list. **The weight on a signal all four classifiers
already had.** Every one of them was scoring the welfare head at 2 or 3 points, a number
picked by hand when the classifier was written and never measured against anything.

Membership was left exactly as committed, and that was tested rather than assumed. Three
variants were measured at the adopted weight: each state's shipped hand-picked set, a set
fitted to that state's own development half, and one national set read off the List of Major
and Minor Heads of Account.

| state | shipped | fitted to its own dev half | national list |
|---|---|---|---|
| Kerala | **99 @ 0.909** | 114 @ 0.886, under the floor | 114 @ 0.886, under the floor |
| Karnataka | **112 @ 0.938** | 110, 4 rows unlabelled | 134, 9 rows unlabelled |
| Tamil Nadu | **419 @ 0.912** | 431, 12 rows unlabelled | 437, 18 rows unlabelled |
| West Bengal | **219 @ 0.904** | identical set | 266 @ 0.865, under the floor |

**The shipped set is the only one publishable in all four**, and the two alternatives fail
in different ways: the wider sets buy rows the audit census never labelled, and where they
do stay inside the labelled region they buy them at a precision under the floor. Widening
membership and raising the weight are the same move made twice, and the weight is the one
that can be measured per state against a census that already exists.

An earlier draft of this note claimed the three variants were worth almost nothing against
each other. That was measured at a weight none of them could publish at, and it was wrong.

### The sweep

Every weight from 1 to 8, scored over every row in the state, read at that state's
publishing bar, counting errors against hand labels rather than estimating them:

| state | bar | weight was | published | precision | weight now | published | precision | what stopped it |
|---|---|---|---|---|---|---|---|---|
| Kerala | 9 | 2 | 38 | 0.974 | **4** | **99** | **0.909** | weight 5 is 0.872, under the floor |
| Karnataka | 7 | 2 | 74 | 0.973 | **4** | **112** | **0.938** | weight 5 leaves 37 rows unlabelled |
| Tamil Nadu | 10 | 2 | 326 | 0.963 | **4** | **419** | **0.912** | weight 5 leaves 94 rows unlabelled |
| West Bengal | 10 | 3 | 134 | 0.925 | **5** | **219** | **0.904** | weight 6 is 0.826, under the floor |

**+277 schemes**, every one of them a row the state's own budget funds and names.

Each state landed on the same increment, +2, and that is a coincidence of four separate
measurements rather than a rule. The stopping conditions differ: Kerala and West Bengal run
out of precision, Karnataka and Tamil Nadu run out of labels.

### The two limits, and why the second one is the interesting one

**The floor.** The register's precision floor is 0.903, which is Odisha's, and nothing
publishes below it.

**The count.** Precision here is a COUNT: every row at or above the bar carries a hand
label and every error is named in `known_errors` (`PLAN.md` §4). Raising a weight pushes
rows up across the bar, and rows nobody ever labelled come up with them. Karnataka at
weight 5 reads 0.948, *better* than the 0.938 it publishes at — but 37 of those 154 rows
have no label, so 0.948 is an estimate over the labelled subset while 0.938 is a count of
the whole list. Tamil Nadu at weight 5 reads 0.927 against the 0.912 it publishes, for the
same reason. **Both were rejected for reading too well.**

### What it cost

Precision fell in all four: Kerala 0.974 → 0.909, Karnataka 0.973 → 0.938, Tamil Nadu
0.963 → 0.912, West Bengal 0.925 → 0.904. Those are real false accusations, from 25 named
errors across the four states to 74. The trade was taken deliberately: 49 more errors buys
277 more funded schemes named as absent, and every error is printed rather than averaged
away.

**West Bengal at 0.904 is one error above the floor.** That is the thinnest margin in the
register and it should be rechecked whenever its labels change.

## Where it was not adopted

- **Odisha.** It sets the floor at 0.903 and the simulation had it falling to 0.688. Its
  bar has no room.
- **Andhra Pradesh.** The signal does not separate there — 0.458 inside the heads against
  0.403 outside, a lift of 1.1x where the others are 3x to 5x. Weighting noise is not a
  gain.
- **Maharashtra and the other ten.** Not measured. Each needs its own sweep against its own
  census; none should inherit these numbers.

## Reproducing this

`parse/classify_<state>.py` carries the state's own sweep table in a comment beside the
weight, which is where the numbers above come from. To re-derive one: score every row at
each candidate weight, take the rows at or above the publishing bar, and count how many
carry a `label` of anything but `scheme` — and, before believing any of it, count how many
carry no label at all. A sweep that does not report that second number will recommend a
weight that cannot be published.

---

## Why it was not adopted when this was written

Kept as written. Three reasons were given, and reading them against what happened is the
useful part: reason 1 was accepted and paid, reason 2 was right and is what the sweep above
does, and reason 3 turned out not to matter at all.

1. **A positive on an accusation bar lowers precision.** The publishing bar is
   high-precision on purpose (`PLAN.md` §4) and 0.974 to 0.909 is a real cost paid in false
   accusations. That is a decision about the register's standards.
2. **The right weight is per state, as every signal here is.** A flat +2 helps Kerala,
   breaks Odisha, and does almost nothing in Andhra. Each state has to measure it against
   its own labels and re-read its own census at the new bar.
3. **The heads above are a first cut.** A state adopting this should measure the heads *its*
   book actually uses rather than inheriting this list, and publish that measurement in its
   `signals_rejected` the way every other signal here does.

That advice was followed: Kerala went first, then Karnataka, Tamil Nadu and West Bengal,
each measured against its own census.

**Reason 3 held, in the opposite direction to the one intended.** It predicted a state would
need to measure the heads *its* book uses rather than inherit a list. A set fitted to each
state's own labels was measured, and it is worse than the shipped one in three states of
four — it reaches rows the census never labelled, or drops precision under the floor. The
head codes are a national standard, which is the whole finding, so a set fitted on 10-row
per-head samples is fitting noise on top of a signal that was already there. What genuinely
differs per state is how much the signal is worth, and that is the weight.

## If you are picking this up

Twelve states have not been measured. Take one, run the sweep in "Reproducing this" against
its own audit census, and stop at the largest weight that clears 0.903 **with no unlabelled
row at the bar**. Report both numbers. If the weight that helps needs labels that do not
exist yet, the answer is to label rows, not to lower the standard.

Do not roll one weight across sixteen states. That is the mistake this register already
made once with a shared definition, and it took 56 rows changing side to find it.
