# Chapter 7 — Out-of-sample predictability and market efficiency

The supervisor's fourth comment asked for a formal test of forecast accuracy —
"such as a Diebold–Mariano test" — against the benchmark, on the grounds that the
previous version reported differences without saying whether any of them was
significant. The comment is accepted, and it turns out to matter more than it
first appears. The previous version judged forecasts on mean absolute error and
directional accuracy. Those statistics cannot resolve the effect sizes this
literature deals in: an out-of-sample R² of half a percent is publishable and
economically meaningful, and is invisible in MAE. Under this thesis's final
framing the point sharpens further. Once the answer is that local perception is
not priced, the evaluation apparatus is not an accessory to the result — it *is*
the result, because a null claim rests entirely on being able to say how large an
effect would have been found had one existed.

This chapter therefore does two things. It reports the forecasting exercise, and
it reports the power of that exercise. The second half is the contribution.

## 7.1 Design

The forecasting design is deliberately plain, because the interest lies in the
evaluation rather than in the model. Forecasts are one day ahead, made on an
expanding window and re-estimated at every step, with a minimum training window
of 250 observations — roughly one trading year — before the first forecast is
issued. The benchmark is the historical mean of the target return, the standard
and famously hard-to-beat hurdle in the return-predictability literature. The
competing model is that same benchmark plus one perception predictor, entering as
a lagged daily change so that only information available strictly before the
forecast date is used.

The grid has five targets and ten predictors, giving **50 specifications**. The
targets are the two Bloomberg defence indices — the global aggregate and the
European, war-exposed index — together with the three freely available
alternatives whose validation is reported in Chapter 3: the ITA exchange-traded
fund and the two hand-built baskets. The predictors are the attention and tone
series of the five ecosystems: Ukrainian, Russian state, Russian independent,
Western, and native-English. Every ecosystem therefore gets
ten chances to forecast, and each target is asked about by every ecosystem in
both of the dimensions the indices measure.

A single-predictor linear forecast is the weakest form the exercise could take,
and that is a genuine limitation. It is also the exact structure the power
simulation of Section 7.4 implants, so the bound reported there applies to
precisely this class of forecast and is not being borrowed from a stronger one.

## 7.2 Why Clark–West and not Diebold–Mariano

The supervisor named Diebold–Mariano, and the module implements it — but it is
not the test that arbitrates the headline grid, and the reason is not a matter of
taste.

Diebold–Mariano tests the null that two forecasts have equal expected loss, using
the sample mean of the loss differential standardised by its long-run variance.
The statistic is asymptotically normal when the two models are **non-nested**.
Here they are not. Setting the perception coefficient to zero returns the
benchmark exactly, so the benchmark is nested inside the model. Under the null
that the predictor has no content, the population loss differential is not merely
zero on average — it is degenerate, and the DM statistic has no standard normal
limit. Worse, the direction of the resulting distortion is systematic rather than
random. The larger model must estimate a parameter that is truly zero, and that
estimation noise enters its mean squared error and nothing else. A nested
alternative is therefore set up to lose even when its predictor carries genuine
information. That is, uncomfortably, close to a description of how the previous
version's information-set horse race was arranged: richer information sets were
penalised for the cost of using their extra variables, and the penalty was read
as evidence that the variables were empty.

Clark and West (2007) correct exactly this. The adjusted loss differential adds
back the squared difference between the two forecasts, which removes the
estimation-noise term the nested model is otherwise charged for. The test is
one-sided by construction — the alternative is that the larger model forecasts
better — and its variance is computed with a Bartlett-kernel long-run estimator,
which at the one-day horizon requires no lags. Campbell–Thompson out-of-sample R²
is the accompanying descriptive statistic: one minus the ratio of the model's sum
of squared errors to the benchmark's, reported as a fraction, where negative
values mean the model forecasts worse than the mean and are the ordinary case.

Diebold–Mariano is retained for the comparisons where it is valid — two different
predictors set against each other, neither nesting the other — with the
Harvey–Leybourne–Newbold small-sample correction applied by default, which
matters at the out-of-sample lengths available here. The distinction is enforced
in the code by providing two separate functions rather than one function with a
flag, so that the nested case cannot be reached by accident.

Both tests, the Campbell–Thompson statistic, the Benjamini–Hochberg and
Romano–Wolf corrections and the power simulation live in
`src/models/evaluation.py` and are covered by **24 unit tests**,
including one that asserts the Clark–West statistic is more favourable to the
nested model than Diebold–Mariano on the same data. The two Clark–West figures
quoted in the previous version's audit were computed in a session and never
committed; nothing testable survived them. This time the tests are the artefact.

## 7.3 Results

Nothing forecasts.

| quantity | value |
|---|---|
| specifications | 50 |
| positive R²_OS | 3 |
| best R²_OS | **+0.0011** |
| Clark–West p < 0.05 | **0** (2.5 expected by chance) |
| surviving Benjamini–Hochberg at 5% FDR | **0** |

Three features of that table are worth stating explicitly. The best out-of-sample
R² across the whole grid is **0.11%**, and it is not significant. Only three of
fifty specifications improve on the historical mean at all; the other forty-seven
forecast worse than a constant, which is the expected consequence of adding a
noisy regressor to an already hard-to-beat benchmark. And the count of nominal
Clark–West rejections is not merely small — it is **zero, against the 2.5 that
chance alone would deliver across fifty tests at the 5% level**. The
multiple-testing correction is applied for completeness and has nothing to
correct; with no nominal rejections, the stricter Romano–Wolf familywise
procedure could not change the verdict either.

## 7.4 The power statement

A null result is only a finding if the test that produced it could have found
something. Analytic power expressions for the Clark–West test require assumptions
about the predictor's variance ratio that are not worth defending, so power is
established by simulation on the actual return series instead. A predictor is
implanted that explains a known fraction of return variance; returns are
regenerated from it; the identical expanding-window machinery is run; and
rejections at the 5% level are counted. The exercise uses the longest target,
**1,855 out-of-sample days**.

| true R²_OS | 0.0% | 0.2% | 0.5% | 1.0% | 2.0% | 4.0% |
|---|---|---|---|---|---|---|
| rejection rate | 0.02 | 0.43 | **0.82** | 0.98 | 1.00 | 1.00 |

Read the first column first. At a true effect of exactly zero the test rejects 2%
of the time against a nominal 5%, so it is conservative rather than liberal — the
zero rejections in Section 7.3 are not the artefact of a test that manufactures
significance. Reading across: an effect of **0.5% is detectable at 82% power**, an
effect of **0.2% at 43%**, and anything at 2% or above is found essentially every
time.

That converts the null from an observation into a bound. The range of
out-of-sample R² this literature reports and treats as economically meaningful
runs from roughly half a percent to one percent. **That range is ruled out.** Had
local perception forecast defence returns as strongly as the better published
predictors forecast equity returns, this design would have found it between four
and five times in five, and it found it zero times in fifty.

**What is not ruled out is the region below the literature's range.** At a true
effect of 0.2% the test succeeds a little over two times in five, so an effect of
a couple of tenths of a percent remains consistent with everything reported here.
The best observed value, 0.11%, sits below even that and is not significant.

The distinction matters and it moved with the sample. On the shorter corpus this
project first analysed, the 80%-power threshold sat at 1.0% and only the top of
the literature's range could be excluded. Extending the out-of-sample window to
1,855 days moved the threshold to 0.5% and brought most of the range inside it.
More data did not rescue the result; it sharpened the statement of what the
result rules out, which is the more useful thing for a null to do.

Stating both halves is the point. The claim the thesis makes is bounded rather
than absolute, and the bound is quantified rather than gestured at.

Two further scope conditions belong with it. The bound is a bound on *linear,
single-predictor, one-day-ahead* forecasts of the level of index returns; it says
nothing about nonlinear structure, about conditioning on regime, or about lower
frequencies. And it is a bound on predictability, not on pricing. Chapter 6's
contemporaneous tests are the ones that ask whether perception is impounded in
prices at all, and they too return a null for the local ecosystems while the
positive control — the Western block, detected in 6 of 31 cells with a minimum p
of 0.0028 — passes.

## 7.5 What it means for efficiency

The narrow reading is the defensible one. Publicly available multilingual news
perception, measured at daily frequency, does not forecast next-day returns on
defence indices, and the exercise had the power to detect any effect at the upper
end of what the literature reports. That is a statement about semi-strong-form
efficiency with respect to one specific and unusually rich public information
set — one that had not previously been constructed, and which the previous
version of this project could not have tested at all, because its indicators
contained almost no non-English media.

What the exercise cannot do alone is separate "the information is worthless" from
"the information is already in the price". A forecasting null is consistent with
both, which is the joint-hypothesis problem in its ordinary form. The
contemporaneous evidence is what breaks the tie, and it points the same way:
local perception is not detected in defence returns on the day either, while
European market-wide threat pricing is — the STOXX 600 itself loads on threat at
**+0.474 (p < 0.0001)**, reported in Chapter 8. Information that is priced in
this sample is priced immediately and broadly, not with a day's delay in one
sector.

Chapter 4's measurement result supplies the mechanism that makes this
unsurprising rather than puzzling. The perception series agree with the published
geopolitical-risk index at 0.87 in levels and at close to nothing in daily
changes. The co-movement over months is real; the daily increments are dominated
by noise. A daily forecasting exercise has to extract signal from precisely those
increments, and the power curve above says how much signal would have had to be
there for it to succeed.
