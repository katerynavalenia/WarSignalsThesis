# Chapter 5 — Stylized facts

This chapter describes the perception series before any of them is asked to
explain an asset price. It exists because the supervisor's review asked for it,
and because the previous version of this project moved directly to forecasting
without ever showing what its indicators looked like — which made every later
result harder to trust than it needed to be.

The review asked for three specific things, and this chapter is organised around
them: every indicator plotted over the full sample period (Figures 1 and 2,
Section 5.1); their correlations reported (Section 5.6); and what happens around
February 2022 highlighted (Sections 5.1–5.4, which add formal break tests, and the marked invasion date in
both figures). Two further things are established along the way. One ecosystem
barely reacted to the invasion at all, and periods of anticipation without
realization can be identified from published data alone — which is what sets up
the research design of Chapter 6.

## 5.1 The indicators over the full sample

Figure 1 plots each ecosystem's conflict-attention share and Figure 2 its mean
conflict tone, both as thirty-day means, across the whole **4,027-day** coverage
window from 18 February 2015 to 20 May 2026. The war regimes of Section 3.6 are
shaded and 24 February 2022 is marked with a dashed line.

![Conflict attention by media ecosystem, 30-day mean, full
sample](../outputs/figures/fig1_attention_full_sample.png)

*Figure 1. Conflict coverage as a share of each ecosystem's own daily output,
2015-02-18 to 2026-05-20, thirty-day moving average. Shading marks the build-up,
invasion and attrition regimes; the dashed line is 24 February 2022.*

![Conflict tone by media ecosystem, 30-day mean, full
sample](../outputs/figures/fig2_tone_full_sample.png)

*Figure 2. Mean GDELT tone of each ecosystem's conflict articles, same window and
smoothing. More negative is more negative coverage.*

Three features of Figure 1 do most of the descriptive work. The ecosystems occupy
two entirely separate bands for the whole eleven years: the Ukrainian and Russian
series sit between roughly 55% and 95% throughout, while the Western and
native-English series stay below 10% until 2022. The invasion is visible in only
one of those bands — the Western and native-English lines spike sharply, while the
local lines barely can, because they were already near their ceiling. And the
spike is temporary where the shift is not: Western and native-English attention
decays back toward its pre-war level within about two years, while Russian state
coverage settles above the band it occupied before the war and stays there. This
is the sense in which the two media environments are covering different worlds
rather than the same war at different intensities.

Figure 2 carries the result Section 5.3 quantifies. Before 2022 the five tone
series interleave with no stable ordering. After 24 February 2022 the Ukrainian
line separates downward and stays separated for the rest of the sample, while the
Russian state line does not move out of the band it occupied before the war.

## 5.2 Attention around the invasion

Conflict coverage as a share of each ecosystem's own daily output rises sharply
on 24 February 2022 for the ecosystems that had room to rise. Western media go
from 18.8% on the 23rd to 40.7% on the 24th, and peak near 47% by the 27th.
Native-English media roughly double, 11.8% to 23.8%. Ukrainian and Russian
outlets were already saturated — above 84% before the invasion — and move to
between 91% and 96%.

The asymmetry in *levels* is itself descriptive. Across the sample, conflict
coverage accounts for 79.2% of Ukrainian outlets' output and 6.6% of Western
outlets'. The two media environments are not covering the same war at different
intensities; they are covering different worlds, one of which is almost entirely
this conflict.

## 5.3 The tone response, and the ecosystem that did not have one

Mean tone of conflict coverage, comparing the pre-invasion build-up
(1 November 2021 – 23 February 2022) with the period after
(24 February – 5 June 2022). Tone is GDELT's own scale; more negative is more
negative coverage.

| ecosystem | pre | post | shift |
|---|---|---|---|
| Ukrainian | −1.77 | −3.43 | **−1.66** |
| Native-English | −1.87 | −2.51 | −0.64 |
| Western | −1.88 | −2.25 | −0.38 |
| Russian independent | −2.23 | −2.49 | −0.26 |
| **Russian state** | **−1.81** | **−1.79** | **+0.02** |

**Russian state media's tone did not move when Russia invaded Ukraine.** Every
other ecosystem's did, Ukraine's by more than a point and a half.

Because ecosystem membership can change — outlets are founded, exiled, or shut
down — the comparison is repeated on a fixed panel: outlets present on both sides
of the invasion with at least 200 conflict articles in each period. Twenty-four
state outlets qualify, and their mean shift is **−0.05**. The result is not an
artefact of composition.

The per-outlet detail is worth reporting, because it shows the aggregate is not
hiding dispersion in one direction. Several state outlets became *more positive*
across the invasion: `regnum.ru` +0.23, `gazeta.ru` +0.48, `ren.tv` +0.43,
`mskagency.ru` +0.40, `life.ru` +0.24. The clearest exception in the other
direction is `1tv.ru` at −1.04.

**A narrower claim that does not survive.** The natural next step is to contrast
state media against Russian *independent* media, isolating ownership while
holding language and country fixed — the press-freedom control that Bondarenko
et al. (2024) apply. Directionally it holds: independent outlets shift −0.22
against the state sector's −0.05. But on the fixed panel only **five**
independent outlets survive, and the difference in shifts is not statistically
significant (Welch test, **p = 0.323**). The independent ecosystem is thin because of
what is being measured — `meduza.io`, `tvrain.ru`, `zona.media` and
`themoscowtimes.com` drop out of the panel entirely, and `echo.msk.ru` falls from
13,951 conflict articles before the invasion to 1,043 after its liquidation in
March 2022.

That attrition is substantively interesting and statistically disabling at the
same time. The claim this thesis makes is therefore the state-versus-Ukraine
contrast, which is an order of magnitude larger and robust to the panel
restriction; the state-versus-independent wedge is reported as directional and
underpowered.

## 5.4 Formal break tests

Sections 5.2 and 5.3 describe what happens at the invasion. The review asked for
that description; a reader is entitled to a test as well, and two are reported
here. They ask different questions and the second is much the stronger.

**Is there a break on 24 February 2022?** A Chow test, with the date fixed by the
event rather than chosen from the data. Every one of the ten series rejects at
p < 0.001. That is expected and, on its own, not very informative: a test at a
date the analyst supplies can only confirm what the plots already show.

**Where is the largest break if nobody says?** A supremum-Wald scan over every
candidate date in the interior 70% of the sample, with the p-value bootstrapped
under the null of no break. This is the test that can embarrass the narrative,
because nothing points it at February 2022.

| series | largest break | days from the invasion |
|---|---|---|
| **tone_UA** | **2022-02-24** | **0** |
| att_WEST | 2022-02-11 | 13 |
| att_RU_STATE | 2022-01-26 | 29 |
| att_EN_GLOBAL | 2022-01-20 | 35 |
| tone_EN_GLOBAL | 2022-01-06 | 49 |
| tone_WEST | 2022-01-05 | 50 |
| tone_RU_STATE | 2023-03-24 | 393 |
| att_UA | 2023-10-07 | 590 |
| tone_RU_INDEP | 2018-06-07 | 1,358 |
| att_RU_INDEP | 2017-04-23 | 1,768 |

**Six of ten series locate their largest break within sixty days of the invasion
without being told the date**, and Ukrainian conflict tone locates it on the day
itself. The Western and native-English attention series break a fortnight to five
weeks *before* the invasion, which is the build-up becoming newsworthy rather
than the invasion itself — the same anticipation window Section 5.5 identifies
from an entirely separate index (Section 5.5).

The two rows that matter most are the ones that do *not* break at the invasion.

**`tone_RU_STATE` places its largest break 393 days later.** Russian state media's
conflict tone did not shift when Russia invaded Ukraine; its biggest single
change comes more than a year afterwards. That is the formal counterpart of the
+0.02 in Section 5.3, arrived at by a procedure that was free to choose any date
in eleven years and did not choose this one. Set against `tone_UA` breaking on
24 February exactly, the contrast is as sharp as the descriptive table suggests
and does not depend on the pre/post window being drawn where it was.

**`att_UA` places its largest break in October 2023**, which is the ceiling effect
of Section 5.2 showing up in a test: Ukrainian outlets were already devoting more
than 80% of their output to the conflict before the invasion, so their attention
series had almost no room to break upward and its largest movement happens
elsewhere. The two Russian-independent series break early in the sample, where
that ecosystem is thinnest and its composition least stable — the same fragility
that Section 5.3 reports for the state-versus-independent contrast.

## 5.5 Anticipation episodes

The research design of Chapter 6 rests on distinguishing periods in which
geopolitical risk is *anticipated* from periods in which it is *realized*. Rather
than assert which periods those are, they are identified from the
Caldara–Iacoviello index alone, by standardising its threat and act components on
a trailing three-year window and taking the smoothed difference.

**Episodes are identified without reference to any asset price.** This matters:
had the search used equity data it would have found windows where the effect
exists by construction, and every subsequent test would be circular.

Six episodes emerge over 2015–2026, covering 645 trading days:

| window | days | peak | corresponds to |
|---|---|---|---|
| Jul 2017 – Jan 2018 | 135 | 1.51 | North Korean ICBM crisis |
| Mar 2018 – Mar 2019 | 252 | 2.32 | trade-war and Iran-deal escalations |
| May – Aug 2019 | 60 | 1.63 | Gulf tanker crisis |
| **Nov 2021 – Mar 2022** | **83** | **2.78** | **Russian build-up and invasion** |
| May – Aug 2025 | 53 | 1.84 | — |
| Dec 2025 – Mar 2026 | 62 | 1.68 | — |

The detector recovers events a reader would recognise and ranks the Russian
build-up highest of all, which is the face-validity check it needs to pass.

The build-up is the sharpest case: its threat-to-act ratio is **3.43**, against
1.12 during the attrition phase that followed. Anticipation and realization are
nearly the same variable in the later period and sharply separated in the
earlier one — which is why a sample beginning after September 2022, as the
previous version's did, cannot distinguish them.

## 5.6 Correlations

The supervisor's review asked for the indicators' correlations, and they are
reported here in full rather than summarised, because the pattern they show — high
agreement in levels, almost none in daily changes — governs every specification
choice in Chapters 6 and 7.

**Across ecosystems.** Pairwise correlations of daily attention changes, on the
1,605 ingested days of the Gate 1–3 sample:

| | UA | RU_STATE | RU_INDEP | WEST | EN_GLOBAL |
|---|---|---|---|---|---|
| **Ukrainian** | 1.00 | 0.44 | 0.13 | 0.18 | **0.05** |
| **Russian state** | 0.44 | 1.00 | 0.29 | 0.16 | **0.05** |
| **Russian independent** | 0.13 | 0.29 | 1.00 | 0.34 | 0.22 |
| **Western** | 0.18 | 0.16 | 0.34 | 1.00 | **0.67** |
| **native-English** | 0.05 | 0.05 | 0.22 | 0.67 | 1.00 |

The largest entry is **0.673**, between Western and native-English media, two
series that overlap by construction — a Western outlet publishing in English
enters both. Every other pair is far lower, and the two extremes are the
informative ones: Ukrainian against Russian state at 0.44, the highest genuinely
cross-national pair, reflecting that both cover the same events on the same days;
Ukrainian against native-English at **0.05**, which is the number that says the
rebuilt indices are not the previous version's near-duplicates. The three local
ecosystems are correlated with the two Western ones at between 0.05 and 0.34, so
the joint F-test of Chapter 6 is not asking a collinear block to add explanatory
power to itself.

**Against the published GPR index.** The perception series are checked against
Caldara–Iacoviello's index in levels, split by what that index is driven by:

| window | Western | native-English | Ukrainian | Russian state |
|---|---|---|---|---|
| 2021-09 → 2022-06, GPR driven by Ukraine | **0.866** | **0.884** | 0.718 | 0.791 |
| 2017–2019, GPR driven by Korea and Iran | 0.083 | 0.048 | 0.010 | −0.105 |

That contrast is the external-validity check of Section 4.5 in its correlational
form: the indices track a published measure of geopolitical risk almost perfectly
when that measure is about their subject, and ignore it when it is not.

**The frequency gap.** The same correlations computed on daily *changes* rather
than levels are near zero throughout — about 0.03 against GPR. Two measures of
the same conflict, agreeing at 0.87 over months, share almost nothing day to day.
The gap between those two numbers is the central measurement fact of this thesis:
the series agree about *where* the conflict sits in the news over months, and
agree about almost nothing day to day. It is why Chapter 6 runs weekly as well as
daily specifications, why Chapter 7's forecasting null is unsurprising once the
power curve is read alongside it, and what Chapter 8 returns to in setting out
what the design could and could not have seen.
