# Chapter 5 — Stylized facts

This chapter describes the perception series before any of them is asked to
explain an asset price. It exists because the supervisor's review asked for it,
and because the previous version of this project moved directly to forecasting
without ever showing what its indicators looked like — which made every later
result harder to trust than it needed to be.

Three things are established here. The ecosystems behave differently around the
invasion; one of them barely reacted at all; and periods of anticipation without
realization can be identified from published data alone, which sets up the
research design of Chapter 6.

## 5.1 Attention around the invasion

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

## 5.2 The tone response, and the ecosystem that did not have one

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
et al. (2024) apply. Directionally it holds: independent outlets shift −0.31
against the state sector's −0.05. But on the fixed panel only six independent
outlets survive, and the difference in shifts is not statistically significant
(Welch test, p = 0.151). The independent ecosystem is thin precisely because of
what is being measured — `meduza.io`, `tvrain.ru`, `zona.media` and
`themoscowtimes.com` drop out of the panel entirely, and `echo.msk.ru` falls from
13,951 conflict articles before the invasion to 1,043 after its liquidation in
March 2022.

That attrition is substantively interesting and statistically disabling at the
same time. The claim this thesis makes is therefore the state-versus-Ukraine
contrast, which is an order of magnitude larger and robust to the panel
restriction; the state-versus-independent wedge is reported as directional and
underpowered.

## 5.3 Anticipation episodes

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

## 5.4 Correlations

Across ecosystems, daily attention changes are close to independent: the largest
pairwise correlation is 0.673, between Western and native-English media, which
overlap by construction. Ukrainian against native-English is 0.05.

Against the published GPR index, the perception series correlate at 0.87 in
levels during the Ukraine-driven window and near zero in daily changes. The gap
between those two numbers is the central measurement fact of this thesis: the
series agree about *where* the conflict sits in the news over months, and agree
about almost nothing day to day. Chapter 6 tests both frequencies for that
reason, and Chapter 8 returns to what it implies.
