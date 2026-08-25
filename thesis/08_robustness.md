# Chapter 8 — Robustness, and five results that did not survive it

Five times in this project a plausible positive appeared, was significant at
conventional levels, had a mechanism that could be stated in a sentence, and
survived at least one robustness check. None of them is in this thesis as a
finding. Each was retracted; the six retracted claims that follow come from those
five episodes, the first of which kills two claims at once.

This chapter is not an appendix. The thesis's central result is a null, and a
null is worth reporting only if the reader can be shown that the search was
serious. Each section below states what was found, why it was believed, and what
killed it.

## 8.1 The market control: a threat channel that was an omitted market factor

**What was found.** Daily defence-equity returns regressed on standardised
Caldara–Iacoviello threat and act shocks, interacted with regime dummies, with a
market return and lagged VIX as controls and HAC(5) standard errors, gave a sharp
result in the pre-invasion build-up: threat shocks moved European defence returns
at **p = 0.0001**, and were indistinguishable from zero in the pre-war, invasion
and attrition regimes. The previous version of this project had reported a
related headline on the volatility side — European defence volatility loading on
threat at p < 0.001 — and it falls to the same missing control.

**Why it was believed.** It was not a lone coefficient. It strengthened
monotonically as the build-up window was tightened, survived dropping the
controls entirely in the pooled regime-interaction specification (BSHIELDT
+0.342, p = 0.004), survived removing the ten largest absolute return days, and
was null in a placebo run on the same calendar window one year earlier. It also
explained something: the previous version of this project had found nothing, and
its sample covered only the attrition regime — the one regime in which this
effect was absent.

**What killed it.** The market control was the S&P 500, because that was the
series reachable without a vendor key. European defence equities need a European
benchmark. Re-running the identical window with the STOXX 600 instead reverses
the result on every target:

| target | control = SPX | control = **SXXP** | no control |
|---|---|---|---|
| European defence index | 0.018 | **0.843** | 0.228 |
| European defence basket | 0.004 | **0.460** | 0.049 |
| Global A&D index | 0.002 | **0.865** | 0.295 |
| US defence basket | 0.009 | **0.360** | 0.229 |

Read the first column with care. The re-run estimates the build-up window on its
own rather than through the pooled regime interaction that produced the original
p = 0.0001, so its S&P 500 column is 0.018 rather than 0.0001. The two
specifications are not the same regression and their SPX p-values are not
expected to coincide. What is common to both, and what the retraction rests on,
is the column beside it: under the correct regional control the effect is gone on
every target.

The mechanism is measurable rather than conjectural. Over that window the
correlation between daily S&P 500 and STOXX 600 returns is only **0.409**, so an
S&P 500 control leaves nearly all European market variation in the residual — and
that residual correlates **0.26** with the threat shock. The threat variable was
standing in for the omitted European market factor. On this tightened window the
no-control column is null too, so on the re-run the result exists only under the
*wrong* control — this failure mode's signature rather than the sign of a fragile
true effect. That column disagrees with the earlier no-control check quoted
above, which was run on the pooled regime-interaction specification rather than
on this window; both are reported as they stand, because nothing in the record
adjudicates why they differ.

**What survives is better than what was lost.** Regressing the European market
index itself on the two channels, with no market control, threat loads at
**+0.474 (p < 0.0001)**, while the same regression on the US market gives
nothing. Geopolitical threat *is* priced — market-wide in Europe, not
differentially in defence. That is why controlling for the STOXX 600 removes the
defence-specific coefficient: the effect is in the control. The retraction turns
a fragile claim about one sector into a robust claim about a market.

## 8.2 The truncated sample: a pre-registered pass that was not one

**What was found.** Gate 3 tested whether the threat/act structure of local-media
coverage explains defence returns conditional on Western coverage, across a
pre-registered grid of 31 specifications with Benjamini–Hochberg correction. On
the data then in hand — a partial ingest of **694 days** — the primary
specification returned **7 BH survivors and a verdict of PASS**.

**Why it was believed.** The protocol had been written down before the test was
built: grid, statistic, correction and pass rule all fixed in advance.
Pre-registration is the discipline that is supposed to make a positive
trustworthy, and by the letter of the document this was a pre-registered pass.

**What killed it.** The ingest was still running. Adding the held-out 2017–19
window — same grid, same statistic, same correction, nothing changed but the
number of days available — took seven survivors to **two** and PASS to **FAIL**.
Had the ingest stopped at the BigQuery free-tier guard, this thesis would have
reported a positive headline resting on a correctly pre-registered test.

The lesson is narrow and it is the most useful methodological observation the
project produced: **a pre-registered test run on a truncated sample is not a
pre-registered test.** Pre-registration fixes the analysis and does nothing about
the data-collection boundary; when collection is incremental, that boundary is a
researcher degree of freedom like any other.

## 8.3 The register error: `dw.com` in the Russian independent ecosystem

**What was found.** Contrasting Russian state media against Russian independent
media across the invasion produced a wedge that widened materially, the
independent sector's tone falling while the state sector's did not move. It was
the project's strongest descriptive result at the time, and the cleanest version
of the press-freedom control Bondarenko et al. (2024) apply: same corpus, same
tone dictionary, same days, the two groups separated only by ownership.

**Why it was believed.** The classifier had passed every check Chapter 4
describes — distinct populations, Western indices tracking published GPR at 0.87
in levels, correct behaviour on 24 February 2022 — and nothing downstream flagged
anything.

**What killed it.** `dw.com` — Deutsche Welle, the German public broadcaster,
which runs a Russian-language service — sat in the hand-curated register as a
Russian *independent* outlet. It was that ecosystem's largest contributor by
volume and carried its largest negative tone shift, **−0.73**. By the criterion
this project exists to apply, publisher rather than language, it is a Western
outlet, and it had been in the register from the first ingest.

Two features matter. The error was found by a fixed-outlet-panel robustness run,
**not** by validation: the hand-labelled precision audit that would have caught
it was never carried out, so a classification error surfaced through an analysis
whose purpose was something else. And it compounded a separate problem of the
same sign — as Chapter 5 sets out, the independent ecosystem is thin and its
membership changes across the very event being measured, so on a fixed panel only
four independent outlets qualify and the difference in shifts is not significant
(Welch test, p = 0.561).

Re-running the panel as the register was corrected is itself instructive, because
it moved twice in the same direction. With Deutsche Welle counted as
Russian-independent the comparison gave six outlets, a −0.31 shift and p = 0.151;
removing Deutsche Welle left five outlets, −0.22 and p = 0.323; removing Radio
Free Europe/Radio Liberty's two services as well leaves **four outlets, −0.17 and
p = 0.561**. Every outlet the register was wrong about had been supplying that
ecosystem's largest negative shifts, so each correction moves the contrast
further from significance. The retraction was correct, and each pass at the
register makes it more so.

**What survives.** Russian state media's tone genuinely did not move when Russia
invaded Ukraine: **+0.02** in aggregate, and **−0.05** on a fixed panel of 24
state outlets present on both sides with at least 200 conflict articles each.
Against Ukrainian media's **−1.66** that contrast is an order of magnitude larger
than the retracted one and robust to the panel restriction. The
state-versus-Ukraine contrast is the claim this thesis makes; the
state-versus-independent wedge is directional and underpowered.

## 8.4 The small sample: local perception and European gas

**What was found.** European natural gas is the asset through which this conflict
physically transmitted to Europe, and Russian state media the channel through
which supply intent was signalled — a better testbed than defence equities, where
the link from Russian reporting to a US contractor runs entirely through Western
investors. On 81 days of the build-up window the local block explained TTF
returns conditional on the Western block at **p = 0.0005**.

**Why it was believed.** Unlike 8.1 and 8.2 it *strengthened* under better
controls rather than dissolving: adding Brent and EUR/USD on top of the STOXX
600 and VIX controls moved the p-value from 0.0056 to 0.0005. The placebo that
discriminates the mechanism was clean — US Henry Hub gas, carrying no Russian supply, gave p = 0.588, with
Brent, wheat and an unexposed consumer staple all null. A supply-signalling
channel visible in European gas and not American gas is a mechanism, not a
correlation.

**What killed it.** A pre-registered replication, written down in full — asset,
controls, windows, statistic, correction, placebos and a four-condition pass rule
— *before* the continuous 2021–2023 coverage was collected. On **222 days** of
continuous coverage of the same period, same asset and same specification, the
p-value is **0.100**, and all four conditions fail:

| condition | result |
|---|---|
| BH survivor in both non-overlapping windows | **FAIL** — none in either |
| all placebos p > 0.10 | **FAIL** — Brent 0.041, Unilever 0.084, US gas 0.095 |
| survives dropping the ten largest TTF moves | **FAIL** — 0.100 → 0.322 |
| RU_STATE leads the local block | **FAIL** — RU_INDEP leads in two of four cells |

Nothing changed but the amount of data. The placebo pattern is the second tell:
in the later window the local block "explains" an unexposed consumer-staples
equity about as readily as European gas, which is what a common factor looks
like, not a supply channel. The Western block is detected at p = 0.00005 in the
build-up window, so the positive control passes and this is a null with power.

The retraction broadens the thesis rather than narrowing it: local-language
perception is not priced in Western defence equities, and not in the asset
through which the war actually reached Europe.

## 8.5 The in-sample split: anticipating escalation

**What was found.** Escalation is not a traded asset, so no arbitrage force
requires media coverage to be uninformative about it. Testing whether local
ecosystems' attention and tone predict changes in realised geopolitical acts,
conditional on the Western ecosystems and on six lags of the outcome's own level
and first difference, the local block was significant **in both halves of the
in-sample period independently**: p = 0.039 and 0.024 at one- and five-day
horizons in 2017–2021, and p = 0.0001 and 0.0000 in 2022–2026.

**Why it was believed.** By this project's standards the evidence was unusually
strong: two halves four years apart agreeing, survival under twelve lags of own
dynamics rather than six, and a time-shuffle placebo at p = 0.616. In the earlier
half the Western block was null while the local block was not — the asymmetry
Bondarenko et al. (2024) report for Russian macroeconomic aggregates, appearing
here on conflict escalation. A pass would have turned the thesis from an absence
into a mechanism: the information exists and markets do not use it.

**What killed it.** A pre-registered test on roughly 950 days that had never been
ingested, collected only after the hypothesis was fixed. On the 651 usable days
the hypothesis had never seen:

| condition | result |
|---|---|
| local block survives BH at both horizons | **FAIL** — p = 0.159 (h = 1), 0.301 (h = 5) |
| shuffle placebo p > 0.20 | PASS — 0.557, 0.799 |
| survives twelve own-dynamics lags | **FAIL** — 0.143, 0.566 |

The design was sound on the held-out data — the placebo confirms it and the
Western block is still detected in two cells — so the effect is simply not there.

The lesson is the most transferable in this chapter: **split-half replication
inside a sample is not out-of-sample replication.** The halves were not
independent evidence. They shared the same eleven-year construction, outlet
register, GDELT coverage regime and persistent-levels specification. Whatever
produced significance in one produced it in the other for the same reason, and
neither carried to fresh data. Splitting a sample and finding agreement
establishes that the artefact, if there is one, is stable — not that there is
none.

## 8.6 Five failure modes, and why the sequence is reported

The five episodes are five distinct ways for a media-and-markets study to produce
a convincing artefact:

| # | claim | how it looked | what killed it | failure mode |
|---|---|---|---|---|
| 1 | Threat moves defence returns and volatility | p = 0.0001 | SPX → SXXP | omitted variable |
| 2 | Local threat/act structure is priced | 7 BH survivors, PASS | held-out window added | truncated sample |
| 3 | State-versus-independent censorship wedge | large, clean contrast | fixed panel, plus `dw.com` | classification and composition |
| 4 | Local perception priced in European gas | p = 0.0005, clean placebos | replication, n 81 → 222 | small sample |
| 5 | Local media anticipate escalation | both halves significant | held-out sample, p = 0.16 | non-generalising split |

Each was significant at conventional levels. Each had a plausible mechanism. Each
survived at least one robustness check. **None survived the check designed to
kill it.** That is not one mistake repeated five times: no two rows of that table
share a failure mode. The only defect that struck twice is the missing regional
control of Section 8.1, and it did so within a single episode — retracting a
volatility claim and a returns claim estimated in different specifications, which
is why five episodes cost six claims.

Reporting the sequence rather than burying it does two things. It is the more
useful result for anyone building this kind of dataset, because the four checks
that did the killing — the regional control, the sample boundary, the fixed
outlet panel, the genuinely unseen window — are cheap and were not obviously
necessary in advance. And it is why the thesis's null should be believed: it was
not obtained by failing to look — with one qualification stated in §6.1 rather
than smoothed over: the Western control survives correction in Gate 3, the gas
test and the escalation test, but not in Gate 2, where sensitivity is shown by
the local block's own same-day detections instead. Chapter 7's
power calculation bounds what could have been missed. An out-of-sample R² of 0.5%
would have been detected with 82% probability and 0.2% with 43%; the best figure
observed anywhere in the fifty forecasting specifications is 0.11%. Predictability
across most of the range this literature reports is ruled out; only the region below it
is not, and this chapter is why that distinction is drawn carefully.

## 8.7 The firm cross-section, recovered

Section 3.7 records two datasets as lost and draws a consequence from the loss:
that the exposure-gradient question — whether firms with larger arms-revenue
shares respond more strongly to geopolitical risk — is untestable here. **That
consequence was wrong, and this section is the correction.**

What was lost was a particular *copy* of the data, not the data. SIPRI publishes
the Top-100 arms-producing companies annually, with arms revenue and total
revenue for each, and has done so continuously across this sample. Arms revenue
over total revenue is the exposure measure the question needs, and it is a public
figure. Prices for the listed producers come from the same free endpoint the
equity spine already uses. Neither input required the file that went missing. The
question was recoverable for the cost of writing the matching code, and the
inference in Section 3.7 — from *our copy is gone* to *this cannot be tested* —
did not hold.

The matching is deliberately hand-curated rather than fuzzy-matched on company
names. Fuzzy matching is exactly where a silent error of the kind Section 8.3
documents would enter: "General Dynamics" and "General Electric" are close in
string distance and nothing alike in exposure, and a mismatch would attach the
wrong exposure to the wrong returns without failing any test. Thirty-one listed
firms match, spanning arms shares from 0.033 (General Electric) to 0.943 (BAE
Systems), which is the full range the question needs. State-owned and unlisted
producers are absent by construction: they have no returns to explain.

The estimating equation is dictated by the design. Day fixed effects absorb every
day-level shock, so a conflict variable cannot be identified from its own
coefficient — every firm sees the same shock on the same day. The identification
is therefore the **interaction**: does the response to a geopolitical-threat shock
scale with the firm's arms-revenue share? Firm fixed effects absorb the level
differences between producers, standard errors are clustered by date, and each
firm's return is measured against the benchmark of the market it trades in
(Section 8.1 is what that precaution is for).

| window | firm-days | days | interaction β | p |
|---|---|---|---|---|
| full sample | 85,065 | 2,836 | +0.068 | 0.047 |
| pre-war (2015-02→2021-10) | 49,779 | 1,677 | +0.079 | 0.021 |
| build-up (2021-11→2022-02) | 2,405 | 79 | −0.037 | 0.728 |
| invasion (2022-02→2022-09) | 4,529 | 149 | −0.055 | 0.828 |
| attrition (2022-09→2026-06) | 28,352 | 931 | +0.090 | 0.136 |

Two nominal hits, and **neither survives** Benjamini–Hochberg across the ten
tests the specification defines — five windows in signed returns and the same
five in absolute returns, smallest adjusted p = 0.211. The absolute-return arm is
null everywhere, nominally included.

Where the hits sit is the finding rather than the fact that there are two. Both
are the **pre-war** window and the full sample, and the full sample is 59%
pre-war observations, so they are one result reported twice. In the three windows
where the hypothesis actually predicts a gradient the coefficient is
insignificant, and in the build-up and the invasion it carries the wrong sign. A
gradient that is visible in peacetime and absent once the war begins is not
measuring war exposure; the most likely reading is that high-arms-share firms
differ from diversified industrials in some stable way — government-dominated
revenue, low cyclicality — that shows up in their loading on a risk index during
quiet periods and is swamped once a real conflict repricing arrives.

The honest qualification is power, and it cuts unevenly. The build-up and
invasion windows carry 79 and 149 trading days, which is thin enough that a
moderate gradient could hide there; those two nulls are weak evidence. The
attrition window is not thin — 931 days and 28,352 firm-days — and it returns
p = 0.136 with the largest point estimate in the table. The strongest statement
the data supports is that no exposure gradient is detectable at conventional
significance in any war window, and that the one window with enough data to speak
confidently does not show one.

This matters for the reader's confidence in the design more than for the thesis's
conclusions, which are index-level throughout. The earlier firm-level attempt
recorded in the project's v2 phase found no gradient either, but measured it on
the attrition sample alone — the one window in which no repricing happens — and
so could not distinguish "no gradient" from "no event". This test puts the
February-2022 re-rating inside the sample, which was the whole objection to the
earlier one, and the answer does not change.

## 8.8 Limitations

**Volatility was dropped as an outcome.** The design originally specified a
volatility arm with a HAR-RV-X model, on the strength of a result showing
geopolitical threat raising European defence volatility. Section 8.1 retracts
that result: it was an artefact of the market control, and with the correct
European benchmark it disappears. Since the only volatility finding the project
produced was the one that did not survive, and since Gates 2 and 3 test returns
rather than volatility, the volatility arm was not built. This is a genuine
reduction in scope relative to the plan and is recorded here rather than left to
be noticed — the thesis makes no claim about volatility in either direction, and
the HAR-RV-X specification remains unimplemented.

**The precision audit was not run.** The hand-labelled validation specified in
the research design — several hundred articles opened and classified by a reader
in Russian and Ukrainian — was never carried out, so the ecosystem classification
is provisional. Section 8.3 is the concrete argument for completing it: an
audit-class error sat in the register from the first ingest, passed every
downstream check, and was caught by a robustness run. Chapter 4's checks
establish that the ecosystems are distinct populations and that the Western
indices track a published index; only an audit establishes per-outlet precision.

**The committed ecosystem tables predate the `dw.com` fix.** The register is
corrected in the classifier; the aggregated files were not regenerated. This
affects RU_INDEP only, and so does not touch the state-versus-Ukraine contrast
the thesis claims — but any future use of the independent series must regenerate
first.

**The conflict filter is coarse.** An article enters the sample if its version 1
`Locations` field contains Ukraine or Russia, which admits coverage mentioning
either country incidentally. It was chosen over the richer theme field because
BigQuery prices the two very differently — 0.242 TB against 1.853 TB across the
full sample — and the coarser filter kept the entire ingest inside the free tier.
The cost is measurement noise in attention shares, common across ecosystems and
of a sign that cannot be determined.

**No intraday test.** GDELT publishes every fifteen minutes; the equity data are
daily. A lead-lag test of whether Ukrainian or Russian media move before Western
wires — the most direct form of the thesis question — needs intraday prices and
was never in scope. The convention that *is* testable was tested: lagging news one
trading day rather than aligning it same-day relocates which cells look
nominally significant, and neither alignment produces a surviving result. Gate
2's two Benjamini–Hochberg survivors appear under the same-day convention and sit
in the single thin 2025–26 weekly window, while its lagged primary specification
leaves none; Gate 3's two survivors appear under the lagged primary and fail the
target and sign conditions of its pre-registered pass rule, while its same-day
run leaves none. Both gates fail under either alignment, and the fact that the
nominally significant cells move when an innocuous convention changes is itself
evidence they are noise.

**Every held-out window in this dataset has now been used.** The 2017–19 window
was consumed by Gate 3 and the coverage gaps by Gate 5. Coverage runs from
18 February 2015 to 20 May 2026 — 4,027 days, 98% of the calendar — with no
unexamined region left. Any further hypothesis on these data would be tested on
data it has already seen, which is exactly the failure mode Sections 8.2 and 8.5
document. An honest continuation requires a different asset class, a different
conflict, or new data, not a sixth pass over this one.
