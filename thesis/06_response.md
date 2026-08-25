# Chapter 6 — Whose perception moves prices?

This is the chapter the thesis was built for. Chapters 4 and 5 established that
the six media ecosystems are distinct populations and that they behaved very
differently around the invasion. The question now is whether any of that
difference reaches an asset price: does Ukrainian, Russian state or Russian
independent coverage of the conflict carry information about defence-equity
returns *over and above* what Western media were already saying?

Four tests answer it, three of them pre-registered, run in sequence as each null
closed off the obvious objection to the one before. All four fail to reject. The
purpose of this chapter is to show that they fail with the power to have found
otherwise.

## 6.1 The test, and what makes its failure informative

The specification is the same throughout. Daily — or weekly — returns of a
defence target are regressed on the attention and tone shocks of the five
ecosystems that enter the tests — Ukrainian, Russian state, Russian independent,
Western and native-English — plus a regional market control and the VIX, with HAC(5)
standard errors. The object of interest is a **joint F-test on the three local
blocks — Ukrainian, Russian state, Russian independent — conditional on the
Western and native-English blocks already being in the regression.** The local
block is therefore never asked whether it correlates with returns; it is asked
whether it adds anything once Western coverage is controlled for. That is the
question the literature actually poses, and it is the only version of it that
mirrors the test Bondarenko et al. (2024) run on the other side of the conflict.

The grid runs across frequency, window — the six anticipation episodes of
Chapter 5 plus the full sample — and target, the two Bloomberg indices, the ITA
proxy and the two hand-built baskets. Benjamini–Hochberg correction is applied
across the whole grid rather than within any slice of it. Thirty-one cells
survive the minimum-observation rule.

The null is only worth reporting if the design is capable of detecting a media
block at all, and the chapter is built so that a reader can check this rather
than take it on trust. The **Western block** enters in exactly the same
functional form, in exactly the same cells, and is available as a positive
control throughout.

That control gives a split verdict, and the split is reported rather than
averaged away.

In **Gate 3** it passes. The Western block survives Benjamini–Hochberg in 2 of
31 cells, at adjusted p = 0.005 and 0.016 (nominal 0.00016 and 0.0011). The
instrument detects a media block in this data, with the same correction applied
to it that kills the local one.

In **Gate 2** it does not. The Western block is nominally significant in 7 of 31
cells under the primary alignment and 2 of 31 same-day, and **none of them
survives correction** — the smallest adjusted p is 0.082. A reader entitled to
demand consistency should note this: on attention and tone, the design does not
demonstrate sensitivity to Western media either, and any claim that it *reliably*
finds Western media where it fails to find local media would overstate what these
tables support.

What carries Gate 2's sensitivity instead is the local block's own behaviour.
Under the same-day alignment it survives correction in 7 of 31 cells — including
the deepest cell in the entire grid, 2,104 daily observations, at adjusted
p = 0.014. Whatever else is true, the instrument is not blind to local media: it
detects them, strongly and in the cells with the most data. Section 6.2 is about
what happens when that same signal is shifted by one day into an alignment a
trader could actually have used.

One further qualification belongs here, because it limits the control rather than
supporting it. Gate 3's two surviving Western cells are both **weekly cells in
the 2025–26 window, resting on 58 observations** — the same thin corner of the
grid in which the local survivors sit, and which §6.3 argues is the reason not to
believe them. The control therefore establishes that a block *can* be detected
here, but in precisely the region where this chapter is least willing to trust a
detection. It is a real check and a weak one, and the quantitative version of the
argument — how large an effect would have had to be to show up — is Chapter 7's
power curve, not this control.

## 6.2 Gate 2 — attention and tone

The first test uses the indices in their simplest form: each ecosystem's
conflict-attention share and its mean conflict tone, both in daily changes.

| specification | specs | nominal 5% | survive BH |
|---|---|---|---|
| same-day alignment | 31 | 13 | 7 |
| **news lagged one day (primary)** | **31** | **7** | **1** |

**The gap between those two rows is the result of this section.** Seven
survivors under one alignment and one under the other, from the same data, the
same grid and the same correction, differing only in whether the news is credited
to the day it was published or the day after.

The alignment is not a matter of taste. GDELT days are full UTC days; European
markets close around 16:30 UTC and US markets at 21:00. A same-day regression
therefore credits the market with news published **after it shut** — information
no trader could have acted on. Lagging one day is the only alignment in which the
regressor is genuinely available, and it is reported as primary throughout.

An effect that is real information should survive that correction, or strengthen
under it, since lagging removes only the impossible part. Instead it collapses by
a factor of seven. The natural reading is that the same-day cells are picking up
*contemporaneous* co-movement — coverage and prices both responding to the same
events within the day, and coverage responding to the day's market news as much
as the reverse — rather than information the market later used. That is
reporting, not prediction, and it is what an efficiently priced market should
look like from this angle.

The same-day result is worth stating positively rather than only as a foil,
because it is the strongest thing in this chapter. Local conflict coverage
co-moves with defence-equity returns robustly enough to survive correction across
seven cells, including the two deepest in the grid. The claim this thesis
declines to make is the next one — that the co-movement is *exploitable*, or that
local media know something Western media do not yet know. One day of lag is
enough to remove it.

**One cell does survive correction under the defensible alignment**, and it is
reported rather than rounded away: weekly ITA returns in the 2017–19 episode
window, p = 0.0009, BH-adjusted 0.028, on 129 observations. It is one of
thirty-one tests, which is roughly what a false-discovery-rate procedure is
designed to tolerate, and it sits where the hypothesised mechanism does not
apply — a window predating the escalation, on a US-focused aerospace ETF, driven
by Ukrainian and Russian coverage during a frozen conflict. A local-information
advantage that shows up there and nowhere in the Russian build-up is not the
mechanism the thesis set out to test.

These figures changed twice late in the project, and the reason is instructive
rather than incidental. Correcting the outlet register — first Deutsche Welle,
then Radio Free Europe/Radio Liberty's two Russian-language services, all three
removed from the Russian-independent block — moved just over 200,000 articles and
took the same-day survivor count from three to seven. Section 8.3 sets out why a
measurement error of that kind can move a result in either direction, and why
validating the register mattered more than any single robustness check.

The window the thesis is about remains the emptiest. In the Russian build-up and
invasion — a European land war, covered first, closest and most intensively by
Ukrainian and Russian outlets, where any local-information advantage should be at
its maximum — the local-block p-values under the primary alignment are 0.012,
0.124, 0.361, 0.414 and 0.506 across the five targets. The smallest is 0.082
after correction. Nothing clears on any of them.

## 6.3 Gate 3 — the anticipation structure

Gate 2 tests volume and sentiment. The obvious objection is that neither is the
right functional form: what should be priced is not how *much* local media cover
the conflict but whether they cover it as something coming or something that has
happened. Chapter 4 describes the split of each ecosystem's conflict share into
anticipatory and realized components using GDELT's theme taxonomy. Gate 3 puts
those series through the identical grid, and it was pre-registered — the verdict
rule, the two arms, the excluded targets and the sign condition were fixed in
writing before the test was built.

The threat/act series are built for all six ecosystems, including the residual
Russian group that is reported but never tested; the joint F-test uses the same
five blocks as Gate 2, in the same conditional form. Run on the full **4,027 days
from February 2015 to May 2026**, it fails under both timing conventions:

| specification | specs | nominal 5% | survive BH | verdict |
|---|---|---|---|---|
| primary (news lagged one day) | 31 | 8 | 2 | **FAIL** |
| secondary (same-day) | 31 | 4 | 0 | **FAIL** |

The two surviving cells are worth locating precisely, because where they sit is
the argument. Both are weekly, both fall in the 2025–26 episode, and both rest on
**58 observations supporting thirteen parameters**. The cell with the most data
in the entire grid — pooled daily, **2,754 observations** — returns p = 0.082.
A local-information effect that appears only in the thinnest corner of a grid and
vanishes where the data is deepest is the signature of noise, not of a small
effect that needs more power to see.

Applied strictly, neither pre-registered arm clears. Arm 1 required a survivor in
the Russia window on a Bloomberg target or the ITA proxy; the only Russia-window
survivor is a hand-built basket, which the pre-registration explicitly excludes
from that arm. Arm 2 required survivors in two independent episode windows with
the *same sign*; two windows do carry survivors, and the Russia daily cell has
the opposite sign to all six weekly cells on every local term. In the build-up
and invasion the primary local-block p-values run from 0.018 to 0.720, the
smallest of them 0.127 after correction, with nothing surviving.

This is the gate in which the positive control passes, and it is the only one.
The Western block survives Benjamini–Hochberg in 2 of 31 cells, at nominal
p = 0.00016 and 0.0011 (adjusted 0.005 and 0.016), so the same F-test with the
same correction does detect a media block in this data. The qualification from
§6.1 applies with full force here: both of those cells are the weekly 2025–26
cells resting on 58 observations, which is the thin corner this section has just
finished arguing not to trust. The control shows the instrument can fire; it does
not show that a detection in that corner should be believed, and the thesis does
not treat the local survivors there as believable either. Applying one standard
to both is the point.

One pattern inside those cells deserves reporting precisely because it is
seductive. Across the two surviving cells the coefficient signs were
strikingly coherent: **five of the six local terms carry the same sign in both**,
and the exception (Russian state anticipatory coverage) is the smallest of them.
Ukrainian realized-conflict coverage enters negative in both (mean −0.43),
Ukrainian anticipatory coverage positive in both (+0.27), Russian state realized
coverage negative in both (−1.35) and Russian independent realized coverage
positive in both (+1.00). Read literally, that is *buy the rumour, sell the fact*
in Ukrainian media — a shift toward anticipation raises
defence returns, a shift toward realization lowers them. It is exactly the
mechanism this project set out to find. Those four signs were written down and
tested on the 2017–19 window, which had not been ingested when the hypothesis was
formed: **7 of 12 signs match, binomial p = 0.387.** Indistinguishable from coin
flips. The US-facing targets replicate and the European target inverts, which is
the signature of a pattern that is not structural. Chapter 8 returns to an
earlier, truncated version of this same test, and to what it reported before the
held-out window was added.

## 6.4 Gate 4 — European natural gas

Two nulls on defence equities invite one serious objection, and it is worth
stating in its strongest form. Defence equities may simply be a weak testbed. The
link from a Russian newspaper to a US defence contractor's share price runs
entirely through Western investors reading Western wires, which makes "only
Western media matter" close to definitional rather than empirical.

European natural gas has no such excuse. Russia supplied roughly **40% of EU
gas**; the Dutch TTF benchmark moved from about **€20 to over €300**; and Russian
state media is the channel through which supply intent was signalled. If local
perception carries information anywhere, it carries it here. The test was
pre-registered with four conditions, and the 944 days of continuous gas-crisis
coverage it needed were ingested only *after* the pre-registration was written.

All four conditions fail.

| window | n | p (local block) | p (Western block) |
|---|---|---|---|
| (a) build-up and invasion, 2021-06 → 2022-06 | 222 | 0.100 | **0.001** |
| (b) shutdown and aftermath, 2022-06 → 2023-06 | 231 | 0.573 | 0.197 |
| (c) full crisis, 2021-06 → 2023-12 | 563 | 0.352 | 0.081 |

There is no BH survivor in either required window. The placebos fail in window
(b), where Brent (0.041), an unexposed consumer-staples equity (0.084) and US
natural gas (0.095) all show local-block p-values at or below 0.10 — what is
being picked up there is a common factor, not a supply channel. The build-up
p-value of 0.100 degrades to 0.322
when the ten largest TTF moves are dropped. And the ordering condition inverts:
Russian *independent* media lead the local block in two of four cells, where the
supply-signalling mechanism requires state media to lead. The Western block,
meanwhile, is detected at p = 0.001 in the window that matters. Again a null with
power.

The provenance of that 0.100 is the point of the exercise. The exploratory run
that motivated Gate 4 returned **p = 0.0005 on 81 days** of the build-up window.
The confirmatory run — same asset, same specification, same controls, on **222
days** of continuous coverage of the same period — returns 0.100. Nothing changed
but the quantity of data.

## 6.5 Gate 5 — anticipating escalation, with no price involved

The last objection available is that markets are the wrong outcome: perhaps local
media do carry real information about the war, and equities and gas simply fail
to impound it. Gate 5 removes prices from the test altogether and asks whether
local perception predicts *realized geopolitical escalation* — changes in the
published act component — one and five days ahead. It too was pre-registered, and
the data were ingested afterwards.

On **651 held-out days** the local block returns **p = 0.21** at one day and
**p = 0.23** at five. It does not survive twelve lags of the outcome's own
dynamics (0.208 and 0.580). The shuffle placebo passes cleanly (0.523, 0.801),
confirming the design is not manufacturing significance, and the Western block is
still detected in two cells, at p = 0.006 and p = 0.033. The exploratory evidence
had been unusually strong — significant in both halves of the in-sample period
independently, with the earlier half showing exactly the local-beats-Western
asymmetry Bondarenko et al. report. It did not survive contact with days the
hypothesis had never seen. Split-half replication inside one sample, built on one
outlet register and one coverage regime, is not out-of-sample replication.

## 6.6 What the four gates establish

Three operationalisations of "whose perception is priced" — volume, tone and
anticipation structure — plus one asset class chosen for the strength of its
causal channel and one outcome that is not a price at all, return the same
answer. Local perception is not priced in Western defence equities, is not priced
in European natural gas, and does not anticipate realized escalation out of
sample.

The weight of that statement rests on the design being able to detect a media
block when one is there, and §6.1 sets out exactly where that is demonstrated and
where it is not. The Western block is detected at p = 0.00016 in the
pre-registered equity grid — surviving correction — at p = 0.00005 in the gas
window and at p = 0.006 in the escalation test, in cells where the local block is
flat. In Gate 2 it is not detected at all after correction, and there the
demonstration runs through the local block itself: seven surviving cells when the
news is credited to the day it was published, one when it is lagged into an
alignment a trader could have used.

Chapter 7 supplies the complementary bound from the other direction, and it is
the quantitative backbone of the whole chapter: an out-of-sample R²_OS of 0.5% is
detectable at 82% power and 0.2% at 43%, against a best observed value of 0.10%.
These are nulls with the reach to have been positives.

Their direction is worth stating rather than apologising for. Bondarenko et al.
(2024) find that local-language geopolitical risk moves the Russian economy while
English-language risk does not. Run on the counterparty's assets, the same
instrument gives the mirror-image asymmetry: the Western narrative is what is
priced, and local perception adds nothing in volume, in tone, or in anticipation
structure. Chapter 8 takes up why several plausible versions of the opposite
conclusion appeared along the way, and what killed each of them.
