# Chapter 9 — Conclusion

## 9.1 The question and the answer

This thesis asked whose perception of geopolitical risk is priced in Western
defence equities. Two candidate answers were available. The first is that the
information which moves these assets originates where the war is fought, in
Ukrainian and Russian media, and reaches Western prices with the delay that
translation and attention impose. The second is that Western markets price the
Western narrative, and that local coverage — however much earlier, more
voluminous or better informed it may be — adds nothing once the Western signal
is in the regression.

The answer is the second, with one qualification that turns out to carry the
argument rather than weaken it.

Conditional on Western and native-English perception, the local ecosystems add no
explanatory power to defence-equity returns **at the horizon a trader could have
used** — in attention or in tone, at daily or weekly frequency, and in both gates
that tested it. Gate 2's primary specification leaves one Benjamini–Hochberg
survivor of thirty-one, in a 2017–19 window predating the war; Gate 3's leaves
two, both resting on 58 observations and both failing the target and sign
conditions of its pre-registered pass rule.

The qualification is that the same-day specification is not empty. Credit the
news to the day it was published rather than the day after, and seven of
thirty-one cells survive correction, including the two largest in the grid. That
gap is the thesis's central observation. Local coverage and defence returns move
together within the session; one trading day of lag removes almost all of it.
Since GDELT days are full UTC days and the lag removes only what was published
after the market closed, an effect that was genuinely informational should have
survived. What survives instead is the pattern efficiency predicts.

Extending the same design to a second asset class and then to a non-financial
outcome does not change it: local perception is not priced in European gas, where
all four pre-registered conditions fail, and it does not anticipate realized
escalation out of sample, where the pre-registered test returns p = 0.21 at one
day and p = 0.23 at five. Out-of-sample return predictability is likewise absent:
across fifty specifications there are zero Clark–West rejections, against roughly
two and a half expected by chance alone.

A null is only a finding if the test could have found otherwise, and here it
could. The best out-of-sample Campbell–Thompson R²_OS observed anywhere in the
grid is 0.10%. Simulation on the 1,855 out-of-sample days shows the design detects
a true R²_OS of 0.5% with 82% power and 0.2% with 43% power, at a size of 0.02
under the null. Predictability across most of the range this literature reports
is therefore ruled out for these assets and this information set. At the lower
end it is not, and the thesis says so.

The positive controls carry the same weight as the nulls, and are reported with
the same discipline. In the pre-registered Gate-3 grid the Western block survives
correction in two of thirty-one cells, at a minimum p of 0.00016; the equivalent
control fires in the gas window at p = 0.00005 and in the escalation test. In
Gate 2 it does not survive correction at all, and §6.1 says so — there the
demonstration that the apparatus is not blind comes from the local block itself,
which survives correction in seven cells when the news is aligned same-day and in
one when it is lagged by a day. The apparatus sees what is there. What it does
not see is local perception carrying information the market had not already
priced.

## 9.2 The mirror of Bondarenko et al.

The design is a deliberate mirror. Bondarenko, Lewis, Rottner and Schüler (2024,
*Journal of International Economics* 152:104005) construct Russian-language
geopolitical risk indices and find that they move the Russian economy while
English-language risk measures do not. Their asymmetry is a statement about
whose information matters to a domestic market: the local narrative dominates,
and the foreign one is redundant once it is included.

Running the same contrast on the counterparty's assets produces the reverse
asymmetry. For Western defence equities the local narrative is the redundant
one. Neither result generalises into "local media matter" or "local media do
not"; taken together they say something more specific and more useful. Each
market prices the information ecosystem it inhabits. The Russian economy responds
to Russian-language risk perception; Western assets respond to Western risk
perception, and the eleven-year record of what Ukrainian and Russian outlets
published about their own war contributes nothing measurable on top. The two
studies are consistent, and their consistency is the point.

That is not a claim that geopolitical risk is unpriced. Threat is priced
market-wide in Europe: the STOXX 600 itself loads on the threat component at
+0.474 with p < 0.0001 across the build-up and invasion, though not outside it. What fails is the narrower proposition that defence
equities respond differentially, and the narrower proposition still that they
respond to *local* perception of the risk.

## 9.3 What the thesis contributes

Three things survive.

**The dataset.** An eleven-year, publisher-classified, multilingual perception
series covering 18 February 2015 to 20 May 2026 — 4,027 days, 98% of the
calendar — with six media ecosystems separated by the nationality and ownership
of the outlet rather than by the topic of the article. The ecosystems are
genuinely distinct: the largest pairwise correlation of daily attention changes
is 0.602, between two series that overlap by construction, while Ukrainian
against native-English is 0.02. They track an external benchmark when they
should and not when they should not, correlating 0.866 (Western) and 0.884
(native-English) with published GPR in the Ukraine-driven window and 0.083 and
0.048 in 2017–2019, when that index is driven by Korea and Iran.

**The bounded null.** Not "no effect was found", but no effect across three
outcome classes — defence equities, European gas, realized escalation — with
positive controls that fire in each and an explicit power curve attached to the
forecasting result.

**The methodological sequence.** Five plausible positives were produced and
retracted in the course of this work, and they cost six claims — the first
episode kills two at once.

| # | the claim, as it first appeared | what dissolved it | reported in |
|---|---|---|---|
| 1 | a threat channel in European defence volatility | the correct regional market control | §8.1 |
| 2 | threat shocks moving defence returns in the build-up | the same control, S&P 500 replaced by STOXX 600 | §8.1 |
| 3 | the threat/act structure of local media being priced | adding the held-out window to a truncated sample | §8.2 |
| 4 | the state-versus-independent censorship wedge | a fixed outlet panel, and a register error | §8.3 |
| 5 | local perception priced in European gas | pre-registered replication on continuous data | §8.4 |
| 6 | local media anticipating realized escalation | a pre-registered held-out sample | §8.5 |

The numbering here is of *claims*; Chapter 8 numbers the five *episodes* that
produced them, which is why the first two rows share a section.

The failure modes are five distinct kinds, no two episodes sharing one: an
omitted variable, which cost two claims at once, a truncated sample, a small
sample, an in-sample split that did not generalise, and a change of composition
across the very event being measured. Each was
significant at conventional levels when found and each had a mechanism a reader
would accept. That sequence is reported rather than hidden because it is the
reason the null should be believed: it was not obtained by failing to look.

## 9.4 What the thesis does not establish

The precision of the ecosystem classification is unverified. The hand-labelled
audit specified in the design was not run, and the one register error that was
found — a German public broadcaster sitting in the Russian-independent
ecosystem — was caught by a robustness run rather than by validation. Chapter 4's
classification is therefore provisional, and the correct reading is that the
distinctness and external-validity checks are consistent with a good classifier
without demonstrating one.

Nothing here speaks to intraday timing. The news series are built from a
fifteen-minute feed and then aggregated to daily observations matched to daily
equity data. If local coverage leads Western coverage by hours, this design
cannot see it, and the null is silent about that horizon.

The firm cross-section is spoken to, but weakly. Section 8.7 recovers the
exposure-gradient question from public SIPRI revenue shares and finds no gradient
in any war window: the two nominally significant cells are the pre-war period and
a full sample dominated by it, and neither survives correction. The qualification
is that the build-up and invasion windows carry 79 and 149 trading days, thin
enough that a moderate gradient could hide in them. What can be said is that the
one war window with enough data to speak confidently — the attrition phase, 931
days — does not show one.

## 9.5 Where this goes next

Three extensions follow directly. The first is the hand-labelled precision
audit, which would convert a provisional classification into a validated one and
is the prerequisite for reusing these indices. The second is an intraday
lead-lag test, matching the fifteen-minute GDELT stream against intraday prices,
which is the one place a local-information advantage could still be hiding. The
third is a fresh test set — a different conflict, or a different asset class —
because every held-out window inside this dataset has now been spent: the
2017–2019 period by Gate 3, and the last remaining coverage gaps by Gate 5. A
hypothesis tested against data it has already seen is not tested at all. That
constraint is the honest cost of the sequence in §9.3, and it should be stated
rather than quietly ignored by the next study.

## 9.6 The finding a reader will remember

Set the price results aside and one number remains. Between the build-up and the
months after the invasion, Ukrainian media's mean conflict tone fell by 1.66
points. Over the same weeks, Russian state media's moved by +0.02 — and on a
fixed panel of twenty-four state outlets present on both sides of the event, by
−0.05. The largest interstate war in Europe since 1945 began, and the tone of
the invading state's own press did not register it. Several of those outlets
became more positive.

That is what a controlled information ecosystem looks like when it is measured
rather than asserted. It is also the most economical account of why one half of
local perception could never have been priced: a perception series carries
information about the world only to the extent that the outlets producing it are
responding to the world, and one of the two local ecosystems here was not.
