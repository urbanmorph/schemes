# The number we were not reading: the head of account

**Status: measured, validated on held-out states, not adopted.** Adopting it is a decision
about what the register publishes, not a mechanical change, and the note below has the
numbers that decision needs.

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

## Why it is not adopted here

Three reasons, and none of them is that the signal is bad.

1. **A positive on an accusation bar lowers precision.** The publishing bar is
   high-precision on purpose (`PLAN.md` §4) and 0.974 to 0.909 is a real cost paid in false
   accusations. That is a decision about the register's standards.
2. **The right weight is per state, as every signal here is.** A flat +2 helps Kerala,
   breaks Odisha, and does almost nothing in Andhra. Each state has to measure it against
   its own labels and re-read its own census at the new bar.
3. **The heads above are a first cut.** A state adopting this should measure the heads *its*
   book actually uses rather than inheriting this list, and publish that measurement in its
   `signals_rejected` the way every other signal here does.

## If you are picking this up

Start with **Kerala**: worst recall in the register, biggest measured gain, labels already
deep enough that precision stays a count. Measure its own heads against its own stratified
sample, set the weight from that, re-read the census at the new bar, and put the numbers in
the classifier's docstring.

Do not roll one head list across sixteen states. That is the mistake this register already
made once with a shared definition, and it took 56 rows changing side to find it.
