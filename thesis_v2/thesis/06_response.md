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

The null is only worth reporting because the same design carries a **positive
control**. The Western block enters in exactly the same functional form, in
exactly the same cells, and is detected in **6 of 31** cells in each of Gates 2
and 3, with a minimum p-value of **0.0028** in the pre-registered Gate-3 grid and
0.0005 in Gate 2.
In several cells the two verdicts sit side by side: weekly European defence
returns load on the Western block at p = 0.011 while the local block returns
p = 0.320. The instrument finds Western media where Western media matter. When it
reports nothing for local media, that is a measurement rather than a failure to
measure.

## 6.2 Gate 2 — attention and tone

The first test uses the indices in their simplest form: each ecosystem's
conflict-attention share and its mean conflict tone, both in daily changes.

| specification | specs | nominal 5% | survive BH |
|---|---|---|---|
| same-day alignment | 31 | 8 | 2 |
| **news lagged one day (primary)** | **31** | **6** | **0** |

Eight nominal rejections against 1.6 expected by chance looks, at first glance,
like something. It is not. Both BH survivors fall in the *same* window at the
*same* frequency — the 2025–26 episode, weekly, sixty observations supporting
thirteen parameters — and dropping tone to halve the parameter count leaves one.
A result that lives in one thin corner of a grid, and thins further when the
corner is de-crowded, is a result about the corner.

The timing convention settles it. GDELT days are full UTC days while European
markets close around 16:30 UTC, so a same-day regression credits the market with
news published after it shut. Lagging the news one day is the defensible
alignment and is reported as primary. It roughly doubles the raw correlations —
European defence moves from −0.013 to +0.094 — and it changes *which* cells look
significant: the Russia-window cells improve markedly, the ITA proxy from 0.090
to 0.014 and the global A&D index from 0.324 to 0.042, while the 2025–26
survivors fade. Under correction, **nothing survives at all.** That the nominally
significant cells relocate when an innocuous convention changes is itself the
diagnosis: they are noise with a p-value attached.

The window the thesis is about is the emptiest of all. In the Russian build-up
and invasion — a European land war, covered first, closest and most intensively
by Ukrainian and Russian outlets, where any local-information advantage should be
at its maximum — the same-day local-block p-values run from 0.090 to 0.619 across
the five targets. Nothing is close to correction on any of them.

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
five blocks as Gate 2, in the same conditional form. Run on **1,605 days spanning
April 2017 to May 2026**, it fails under both timing conventions:

| specification | specs | nominal 5% | survive BH | verdict |
|---|---|---|---|---|
| primary (news lagged one day) | 31 | 9 | 2 | **FAIL** |
| secondary (same-day) | 31 | 6 | 0 | **FAIL** |

Applied strictly, neither pre-registered arm clears. Arm 1 required a survivor in
the Russia window on a Bloomberg target or the ITA proxy; the only Russia-window
survivor is a hand-built basket, which the pre-registration explicitly excludes
from that arm. Arm 2 required survivors in two independent episode windows with
the *same sign*; two windows do carry survivors, and the Russia daily cell has
the opposite sign to all six weekly cells on every local term. In the build-up
and invasion the primary local-block p-values run from 0.012 to 0.597, with
nothing surviving correction. The positive control passes here as it does in Gate
2 — the Western block in 6 of 31 cells, minimum p = 0.0028.

One pattern inside those cells deserves reporting precisely because it is
seductive. Among the weekly survivors the coefficient signs were strikingly
coherent: realized-conflict coverage in Russian independent media carried the
same sign in 7 of 7 cells, and Ukrainian realized, Ukrainian anticipatory and
Russian state realized coverage in 6 of 7 each. Read literally, that is *buy the
rumour, sell the fact* in Ukrainian media — a shift toward anticipation raises
defence returns, a shift toward realization lowers them. It is exactly the
mechanism this project set out to find. Those four signs were written down and
tested on the 2017–19 window, which had not been ingested when the hypothesis was
formed: **8 of 12 signs match, binomial p = 0.194.** Indistinguishable from coin
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

On **651 held-out days** the local block returns **p = 0.16** at one day and
**p = 0.30** at five. It does not survive twelve lags of the outcome's own
dynamics (0.143 and 0.566). The shuffle placebo passes cleanly (0.557, 0.799),
confirming the design is not manufacturing significance, and the Western block is
still detected in two cells, at p = 0.006 and p = 0.041. The exploratory evidence
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

The weight of that statement rests on the positive control appearing in every one
of the tests. The design detects the Western block at p = 0.0028 in the equity
grid, at p = 0.001 in the gas window, and at p = 0.006 in the escalation test, in
the same cells where the local block is flat. Chapter 7 supplies the
complementary bound from the other direction: an out-of-sample R²_OS of 1.0% is
detectable at 80% power and 0.5% at 56%, against a best observed value of 0.45%.
These are nulls with the reach to have been positives.

Their direction is worth stating rather than apologising for. Bondarenko et al.
(2024) find that local-language geopolitical risk moves the Russian economy while
English-language risk does not. Run on the counterparty's assets, the same
instrument gives the mirror-image asymmetry: the Western narrative is what is
priced, and local perception adds nothing in volume, in tone, or in anticipation
structure. Chapter 8 takes up why several plausible versions of the opposite
conclusion appeared along the way, and what killed each of them.
