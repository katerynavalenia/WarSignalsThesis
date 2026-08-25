# Chapter 1 — Introduction

## 1.1 The question

Geopolitical risk is not observed. It is read. Every empirical measure of it in
current use — the Caldara–Iacoviello index most of all — is a count of what
newspapers wrote, and the newspapers in question are almost always
Anglo-American. When a defence-equity investor is said to be pricing
geopolitical risk, what is being asserted is that a price responds to a quantity
constructed from one particular editorial vantage point.

That is a substantive assumption, and there is now published evidence against
it. Bondarenko, Lewis, Rottner and Schüler (2024) construct geopolitical-risk
indicators from Russian-language sources and from English-language sources
separately, and find that the two behave differently in the Russian economy:
local-language risk shocks move output, inflation and the exchange rate, while
English-language shocks do not. Whose newspapers you read changes the measured
macroeconomic effect of the same underlying event.

This thesis runs the mirror of that test. Their setting is the economy the risk
is *about*; the setting here is the counterparties who arm one side of the war
and trade the other — Western and global defence equities, an asset class that
re-rated sharply in February 2022 and whose entire investment case is a claim
about how a conflict will develop. If the local-versus-English asymmetry is a
general property of geopolitical-risk measurement, it should appear here too,
and the perception that matters should be the one closest to the fighting. The
research question is therefore: **whose perception of geopolitical risk is
priced in defence equities?**

The question is decomposed into three parts. Do local-language media —
Ukrainian, Russian state, Russian independent — carry information about defence
returns beyond what Western media already carry? Does the distinction between
*anticipated* and *realized* conflict, which the media of a country at war
record very differently from the media of a country watching one, change the
answer? And is any of it usable out of sample, or is it a
contemporaneous association only?

## 1.2 Why the question could not previously be asked

An earlier version of this project believed it had already measured national
sentiment. It had not. Its indicators were built from GDELT's version 1.0 Global
Knowledge Graph, a stream that is effectively English-only — on 1 March 2025 it
carries **7 articles from `.ru` domains and 21 from `.ua` domains out of
60,690** — and, worse, it assigned nationality by the country an article
*mentioned* rather than the country that published it, for **88.6%** of
articles. The series labelled Ukrainian and Russian sentiment were, in fact, the
tone of English-language writing about Ukraine and about Russia — a single
editorial perspective sorted by topic and then relabelled as three perspectives.
Their mutual collinearity, and the emptiness of their differences, follow from
that construction rather than from anything about the world.

Chapter 4 documents this in full, because the diagnosis is what makes the
present measurement necessary rather than decorative. The replacement is built
from GDELT's Translingual archive, which machine-translates material from dozens
of source languages and applies one annotation pipeline to the result, and it
classifies every article by **the outlet that published it**.

## 1.3 The answer

The Western narrative's perception is what is priced. Local-language perception
adds nothing — not in volume of attention, not in tone, and not in the
threat-versus-act structure that separates anticipation from realization.

The null is established three times, through a sequence of tests referred to
throughout as Gates 1–5 — pre-registered from Gate 3 onward, and run against
criteria fixed in advance before that — on outcomes chosen so that a common
cause would have to work through three different channels to produce it.

| test | outcome | result |
|---|---|---|
| Gates 2 and 3 | defence-equity returns | not priced ahead of the market: one surviving specification of 31 in Gate 2's lagged primary, two in Gate 3's, none in Gate 3's same-day arm |
| Gate 4 | European natural gas (TTF) | all four pre-registered conditions fail |
| Gate 5 | realized geopolitical escalation itself | p = 0.21 at h = 1, p = 0.23 at h = 5 |

In the equity tests, 31 specifications are run per grid. The pre-registered
Gate-3 grid yields two Benjamini–Hochberg survivors under its primary alignment
and zero same-day; Gate 2 yields one survivor lagged, in a window predating the
war, against seven when the news is credited to the day it was published — a day
no trader could have traded on.

What makes these nulls readable is that the design is demonstrably capable of
detecting a media block, and the evidence for that is reported with its limits
rather than asserted. In the pre-registered Gate-3 grid the **Western control
survives correction** in 2 of 31 cells, at a minimum p of 0.00016; in the gas test
it is detected in the build-up window where the local block is not; in the
escalation test it is detected while the local block fails. In **Gate 2 the
Western control does not survive correction anywhere**, which is stated here
rather than buried: what demonstrates sensitivity in that gate is the local block
itself, which survives in seven cells same-day — including the two largest in the
grid — and loses all but one of them to a single day of lag. The design can see
what is there. What it cannot find is local media telling the market something
Western media had not already told it.

Something is priced, and it is worth being precise about what. The STOXX 600
itself loads on the threat component of geopolitical risk at **+0.474
(p < 0.0001)** across the build-up and invasion. Threat is priced by the European
market, not differentially in defence. The result is windowed and §8.1 says so:
over the full sample the same coefficient is +0.028 and insignificant.

The efficiency result has the same shape. Across 50 expanding-window
one-day-ahead specifications, the best Campbell–Thompson out-of-sample R² is
**+0.0010**, 3 of 50 are positive at all, and Clark–West rejects at the 5% level
in **zero** cases against 2.5 expected by chance alone. That is a null, and its
value depends entirely on what it can rule out. Simulated on 1,855 out-of-sample
days:

| true R²_OS | 0.0% | 0.2% | 0.5% | 1.0% | 2.0% | 4.0% |
|---|---|---|---|---|---|---|
| rejection rate | 0.02 | 0.43 | **0.82** | 0.98 | 1.00 | 1.00 |

A true out-of-sample R² of **0.5% would be detected 82% of the time and 0.2%
43% of the time**, with size at zero effect of 0.02. Most of the range this
literature reports as economically meaningful is therefore ruled out. The very
bottom of it is not, and this thesis does not claim otherwise.

## 1.4 Contributions

**(i) An eleven-year, publisher-classified, multilingual perception dataset.**
Six media ecosystems — Ukrainian, Russian state, Russian independent, other
Russian, Western, and native-English — each with a daily conflict-attention
share and a daily conflict tone, covering **18 February 2015 to 20 May 2026:
4,027 days, 98% of the calendar, and about three times the span of the version
the supervisor reviewed**. It is built server-side from a 1.83-billion-row,
21.8-terabyte BigQuery table, and its classifier lets country
dominate language at every tier — a rule that is load-bearing rather than
cosmetic, since `24tv.ua` publishes 2,595 Ukrainian-language and 1,865
Russian-language articles, and a language-first rule would file Ukrainian media
as Russian and manufacture agreement between the two ecosystems it is supposed
to separate. The ecosystems are demonstrably distinct — the largest pairwise
correlation of daily attention changes is 0.602, and Ukrainian against
native-English is **0.02** — and the Western series tracks published GPR at
**0.866** in levels when GPR is driven by Ukraine, falling to 0.083 in 2017–2019
when it is driven by Korea and Iran. The dataset also yields facts worth having
independently of any asset price: conflict coverage is 79.2% of Ukrainian
outlets' total output against 6.6% of Western outlets', and Russian state media's
tone did not move when Russia invaded Ukraine — **+0.02** in aggregate and
**−0.05** on a fixed panel of 24 state outlets present on both sides of the
event, against **−1.66** for Ukrainian media.

**(ii) A null with power, replicated across outcomes.** The finding is not that
one specification failed. It is that local-language perception is absent from
two asset classes and from one non-market outcome, with a positive control
passing in each case and an explicit power bound on the forecasting arm. Read
against Bondarenko et al., the result is an asymmetry running the other way: the
local-language advantage they document for the economy the war is fought in does
not transfer to the equities of the countries arming it. The perception that
moves defence prices is the one held by the investors who own them.

**(iii) The sequence of corrections.** Five plausible positives were produced
and retracted over the course of this project, at a cost of six claims — the
first retraction killed two at once. Each was significant at conventional levels
when found, each had a mechanism a reader would accept, and each survived at
least one robustness check. The failure modes are what make the sequence worth reporting rather than
hiding: an omitted variable, which cost two claims at once, a truncated sample, a
small sample, an in-sample split that did not generalise, and a change of
composition across the very event being measured — five different kinds of error,
none of which would have been caught by the checks the others passed. Chapter 8 reports each in full
with what replaced it. The most instructive is the first: a threat effect on
European defence returns significant at p = 0.0001 becomes p = 0.843 when the
market control is the STOXX 600 rather than the S&P 500, two indices that
correlate at only 0.409 in that window. The second is a pre-registered test that
returned a pass on 694 days of a partial ingest and a fail once the held-out
window was added, with nothing else changed. This is the reason the thesis's
null should be believed: it was not obtained by failing to look.

## 1.5 What is not claimed

The hand-labelled precision audit of the ecosystem classifier was not carried
out, so the classification is provisional — a register error was found by a
robustness run rather than by validation, which is the concrete argument for
completing the audit. The conflict filter is coarse, admitting coverage that
mentions Ukraine or Russia incidentally. Equity data are daily against news
timestamped every fifteen minutes, so no intraday lead–lag test is attempted.
No firm-level exposure result is reported. These limitations are set out in
Chapter 8 rather than left for a reader to find.

## 1.6 Structure

Chapter 2 places the thesis in the geopolitical-risk and text-based
asset-pricing literatures. Chapter 3 describes the data: the translingual GDELT
corpus, the equity spine of 19 tickers over 2,837 trading days, and the
free-basket validation reported as it ran. Chapter 4 builds and validates the
perception indices and documents the measurement error they replace. Chapter 5
shows what the series look like before any of them is asked to explain a price:
every indicator plotted over the full eleven years, the correlations among them
and against published geopolitical risk, the invasion tone response, and the six
anticipation episodes identified from published data alone. Chapter 6 asks whether local perception is
priced. Chapter 7 asks whether it forecasts, and states the power behind the
answer. Chapter 8 is the robustness chapter and the retraction record.
Chapter 9 concludes.
