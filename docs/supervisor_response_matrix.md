# Supervisor Response Matrix

**Review received from:** Thomas (supervisor), on the v1 paper
**Date of this response plan:** 2026-08-17
**Companion documents:** [`research_plan.md`](research_plan.md),
[`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md)

Each comment is reproduced verbatim, then answered with: what it implies, what we
will do, where it lands in the paper, and what it costs.

> **Delivery status, 2026-08-26.** This is a plan written before the work; what
> follows is what became of each commitment.
>
> | commitment | status |
> |---|---|
> | #1 sample start, 2015 not 2022 | **done** — 4,027 days, 2,837 trading days |
> | #2 descriptive chapter before forecasting | **done** — Chapter 5 |
> | #3 publisher-based classifier, country before language | **done** — §4.3 |
> | #3(a) hand-labelled precision audit | **substituted** — automated against Wikidata, §4.6; article-level reading still not done |
> | #3(b) external check against published GPR | **done** — §4.5, WEST 0.866 in levels |
> | #3(c) face validity on known events | **done** — §4.5 |
> | #3(d) sensitivity across classification rules | **done** — §4.5, five rules, one scan |
> | #4 R²_OS, Clark–West, MCS, multiple-testing control | **done** — Chapter 7, plus combination and economic value |
> | #4 HAR-RV-X volatility arm | **done** — volatility restored; GARCH/GJR/EGARCH benchmarks with HAR-RV-X under QLIKE (`run_volatility_race.py`). Nothing improves on the benchmark; eight of 48 augmented specifications are significantly worse |
> | #5 cite Bondarenko et al. (2024) | **done** — the methodological anchor throughout |
>
> The physical air-attack layer, dropped in the v3 rebuild, is also restored —
> the approved title is *Physical Air-Attack Intensity versus Multilingual News
> Narratives*, and without it the work had stopped answering half its own
> question. The five-set horse race (F/P/N/PN/PNG) runs again, now against the
> corrected publisher classifier rather than v1's country-mentioned one.
>
> Two items in the design that this plan did not list were also closed: the
> firm-level exposure gradient (SQ5), recovered from public SIPRI data in §8.7
> after being recorded as untestable; and the merge defect that had been
> silently discarding re-ingested data, which is why the anticipation gate had
> been running on a superseded outlet register.

---

## Comment 1 — sample start

> "Why does the GDELT indicator start only in September 2022? This is a major
> limitation of the current version of the paper. If this is driven by the air
> attack dataset, I think you should estimate a model using only the GDELT
> indicator over a longer sample period."

**Diagnosis of the cause.** Yes — the start date was set by the Ukrainian
air-attack dataset. `thesis_v1/gkg_bulk_download.py` hardcodes
`START = date(2022, 9, 29)`, and `config/gdelt_queries.yaml` states the range
"matches attack data". There is no GDELT-side reason for it.

**What this cost us.** The window sits entirely inside the attrition phase of the
war. Every war indicator is close to a slow war-regime trend that VIX and
`days_since_invasion` already capture, which is exactly why the incremental
out-of-sample tests came out negative (`docs/v1/supervisor_audit.md` §1.5). The
February-2022 re-rating — the largest defence-equity repricing in decades, and
the event with the most identifying power — is entirely outside the sample.

**What we will do.**
- Rebuild the GDELT indicators over **2015-02-18 → 2026-06-30**. That start date
  is a hard constraint: it is when the GDELT 2.0 Translingual archive begins
  (verified: first file `20150218224500.translation.gkg.csv.zip`).
- Observations rise from ~920 to **~2,850 trading days (≈3.1×)**; the sample
  gains a pre-war baseline, the 2021 build-up, the invasion, and the attrition
  phase.
- **All primary specifications are GDELT-only over the long sample.** The
  air-attack data moves to a dedicated short-sample chapter that asks whether
  physically realized intensity adds anything beyond perceived intensity — which
  is a better use for it than as a binding sample constraint.
- Regimes are modelled explicitly (pre-war / build-up / invasion / attrition),
  with the 2021-11 → 2022-02-23 build-up window treated as a near-ideal
  "threat without acts" setting.

**Where it lands.** §4.1 of the plan; Chapters 4, 6, 10.
**Cost.** The main data-engineering task of the project (see plan §7); ~2 weeks.

---

## Comment 2 — descriptive analysis before forecasting

> "Before turning to the forecasting analysis, I would recommend plotting all
> indicators over the full sample period and reporting their correlations. It
> would also be interesting to highlight what happens around February 2022, at
> the onset of the war."

**Accepted without reservation.** The v1 paper had no such section, which made
every later result harder to trust.

**What we will do — a new "Stylized Facts" chapter.**
- Full-sample time-series plots of every indicator, with the four regimes shaded
  and events annotated (2022-02-24 first among them).
- Correlation matrices — levels and first differences, full sample and per
  regime — across perception indices × GPR/GPR_THREAT/GPR_ACT × VIX × defence
  returns and realized volatility × attack intensity.
- **Rolling 90-day correlations**, which is the headline visual: does the
  Ukraine–West perception gap widen or collapse at the invasion, and does the
  perception–returns correlation change sign across regimes?
- **Formal break analysis** rather than eyeballing: Chow tests at 2022-02-24 and
  Bai–Perron tests for unknown break dates, applied both to each index and to the
  index→return relationship.
- Descriptive statistics, stationarity and persistence diagnostics — these also
  settle the levels-vs-changes choice used throughout the rest of the paper.

**Where it lands.** Plan §6 Block A; Chapter 6, placed *before* any forecasting.
**Cost.** Days, not weeks — but it depends on Comments 1 and 3 being done first,
since it must plot the *corrected* indicators over the *long* sample.

---

## Comment 3 — sentiment identification methodology

> "You should provide a much more detailed description of the methodology used
> to identify Western, Ukrainian, and Russian sentiment in the GDELT data."

**This is the most consequential comment, and the honest answer is that the
current method does not do what the paper says it does.** Investigating it
produced the finding written up in
[`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md):

- v1 downloaded from the **GKG 1.0 daily stream**, which is effectively
  English-language only. Measured directly: on 2025-03-01 that stream contained
  **7 `.ru` and 21 `.ua` articles out of 60,690**.
- National groups were assigned, for 88.6% of articles, by the **most-mentioned
  country in the article's `LOCATIONS` field** — i.e. by *what the article is
  about*, not *who wrote it*.
- So "Russian sentiment" is the tone of English-language articles about Russia,
  and "Ukrainian sentiment" the tone of English-language articles about Ukraine.
  The three series are near-duplicates drawn from one media population, and the
  "narrative gap" is a difference between two topic proxies.
- The v1 audit itself recorded the symptom — per-group "precision" of 0.365 (UA)
  and 0.318 (RU) — but attributed it to the validation proxy rather than to the
  classifier.

**What we will do.**
- Rebuild from the **GDELT 2.0 Translingual** archive, which carries a
  `srclc` source-language code and real Russian and Ukrainian outlets (verified:
  `tass.ru`, `ria.ru`, `mk.ru`, `pravda.ru`, `unian.ua`, `pravda.com.ua`,
  `tsn.ua`, `nv.ua`, …) at roughly three orders of magnitude higher volume.
- Assign ecosystems by **publisher**, using four ordered tiers: a hand-curated
  register of the ~300 highest-volume outlets (country, language, and
  state-controlled vs independent ownership), then ccTLD, then source language
  *conditioned on* country, then GDELT's domain-country lookup.
- Enforce the rule that **language ≠ country**: many Ukrainian outlets publish in
  Russian, so language is used to split *within* a country, never to assign one.
- Split Russian media into **state-controlled** and **independent/exile** — the
  same control for press freedom that Bondarenko et al. (2024) apply, and a new
  "censorship wedge" indicator in its own right.
- Validate with (a) a genuine **hand-labelled** precision audit with a confusion
  matrix per tier, (b) an external check that the Western index correlates with
  the published Caldara–Iacoviello GPR series over the full sample, (c) face
  validity against known events, and (d) a sensitivity analysis across
  classification rules.

**Where it lands.** Plan §5; Chapter 5 becomes a full methodology chapter with
its own validation section and appendix tables.
**Cost.** Bundled with Comment 1's rebuild — same ingestion, better classifier.

---

## Comment 4 — statistical testing of forecast accuracy

> "For the out-of-sample return forecasting exercise, you could report a
> statistical test comparing forecast accuracy (such as a Diebold–Mariano test)
> to show whether the differences relative to the benchmark are statistically
> significant."

**Accepted, and taken further** — because the deeper issue is that v1 evaluated
forecasts on MAE and directional accuracy, which are not sensitive enough to
detect the effect sizes this literature deals in. There is currently **no
Diebold–Mariano, Clark–West or MCS code anywhere in the repository**; the two
Clark–West figures quoted in the v1 audit were computed ad hoc in a session and
never committed.

**What we will do.**
- Build a tested `evaluation/tests.py` module: **Diebold–Mariano** (with the
  Harvey–Leybourne–Newbold small-sample correction) for non-nested comparisons,
  **Clark–West** for nested ones, and the **Model Confidence Set**.
- Report **Campbell–Thompson out-of-sample R²** as the headline metric instead of
  MAE. This is the field standard, and values of 0.3–1% are both publishable and
  economically meaningful — the range MAE cannot resolve.
- Apply **Benjamini–Hochberg** and **Romano–Wolf** corrections across the whole
  grid of predictor × target × horizon × model, so no single lucky cell can be
  presented as a finding.
- Add **forecast combination** (equal-weighted across single-predictor forecasts)
  and shrinkage toward the benchmark — the standard remedies when individual
  predictors are weak — plus Campbell–Thompson economic sign constraints.
- Report **economic value**: certainty-equivalent gain and Sharpe ratio for a
  mean–variance investor timing on the signal, net of transaction costs.
- Include an explicit **power statement**: given the out-of-sample length, the
  smallest R²_OS detectable at the 5% level. This turns a null into a *powered*
  null.
- On the volatility side, replace the `GARCH-X`-in-mean specification — which was
  100% numerically degenerate for BSHIELDT (`docs/v1/phase7_audit.md` §4.2) —
  with **HAR-RV-X** (a stable OLS regression) as the primary model, keeping the
  GARCH family as robustness with exogenous terms in the variance equation.

**Where it lands.** Plan §6 Block C; Chapter 8.
**Cost.** Around a week, mostly writing and testing the statistics module; the
expanding-window machinery already exists and is reused.

---

## Comment 5 — required citation

> "You should read and cite the following paper, which is closely related to your
> work: Bondarenko, Y., Lewis, V., Rottner, M., & Schüler, Y. (2024).
> Geopolitical Risk Perceptions. Journal of International Economics, 152, 104005."

**Read, and promoted from "a citation" to the thesis's primary methodological
anchor.** Their abstract:

> "Geopolitical risk cannot be measured in a universal way. We develop new
> geopolitical risk indicators relying on local newspaper coverage to account for
> different perceptions. Using Russia as a case study, we demonstrate that
> geopolitical risk shocks identified from local news sources have significant
> adverse effects on the Russian economy, whereas geopolitical risk shocks
> identified from English-language news sources do not. We control for restricted
> press freedom by analyzing state-controlled and independent media separately.
> Employing a novel Russian sanctions index, we illustrate that geopolitical risk
> shocks propagate beyond the sanctions channel. Still, sanctions worsen the
> inflationary impact of geopolitical risk shocks substantially."

**Why it matters so much here.** Their central finding is that *local-language*
geopolitical-risk indicators carry information that *English-language* ones do
not. The v1 indicators are, in their terms, **entirely on the English-language
side** — the side they show to be inert. That is independent confirmation, from a
published *JIE* paper, of the mechanism behind our null.

**How we position relative to them.**

| | Bondarenko et al. (2024) | This thesis |
|---|---|---|
| Outcome | Russian **macro** aggregates (output, inflation, FX) | Western/global **defence-equity** returns and volatility |
| Perspective split | two-way: local Russian vs English | **three-way: aggressor (RU, state vs independent) / victim (UA) / third-party investor-facing (Western)** — plus an English-only arm that replicates their comparison |
| Whose economy | the country the risk is *about* | the counterparties who *arm* one side and *trade* the other |
| Method | SVAR with sign restrictions, Waggoner–Zha sampling | identified perception shocks + Jordà local projections; plus out-of-sample forecasting and a firm cross-section |
| Press-freedom control | state vs independent Russian media | adopted directly, and extended into a **censorship-wedge** indicator |

**The contribution sentence this yields.** *Bondarenko et al. show that whose
newspapers you read changes the measured macroeconomic effect of geopolitical
risk. We ask whether it changes the measured asset-pricing effect — and, because
defence equities are the asset most directly exposed to this particular conflict,
we can ask it with an unusually sharp instrument and a three-way, rather than
two-way, decomposition of perspective.*

**Where it lands.** Chapters 1, 2, 5, 7 — introduction, literature, methodology,
and the interpretation of the central comparison.
**Cost.** Reading and writing time. Also obtain and read the working-paper
version (Bundesbank Discussion Paper 37/2024) for full construction details of
their indicators.

---

## What this implies overall

The five comments are individually reasonable and jointly amount to a rescue
plan rather than a rejection. Comment 1 supplies the statistical power that was
missing; Comment 3, once investigated, supplies the measurement validity that was
missing; Comment 4 supplies the sensitivity that was missing; Comment 5 supplies
the framing that makes the whole thing novel rather than descriptive. Comment 2
is the deliverable that should be sent back first, because it demonstrates that
1 and 3 have been done.

**No change of topic is required, and no existing pipeline is discarded.**

## Suggested reply to send (draft)

> Dear Thomas,
>
> Thank you — the comments were very useful, and acting on the first and third
> together has changed the project substantially.
>
> On the start date: it was set by the air-attack dataset, and there was no
> GDELT-side reason for it. I am rebuilding the news indicators over
> 2015-02-2026-06, which is the full span of GDELT's translingual archive. That
> takes the sample from about 920 to about 2,850 trading days and brings the
> February-2022 period inside it. The air-attack data will be used only in a
> separate short-sample section, asking whether realized intensity adds anything
> beyond perceived intensity.
>
> On the sentiment methodology: writing the detailed description you asked for
> uncovered a real problem. The previous indicators were built from GDELT's
> English-language stream, and national groups were assigned by the country most
> frequently *mentioned* in each article rather than by the country of the
> publisher — so "Russian sentiment" was really the tone of English-language
> coverage about Russia. I am rebuilding them from GDELT's translingual archive,
> classifying by publisher (country, language, and state-controlled versus
> independent ownership), with a hand-labelled precision audit and a validation
> against the Caldara-Iacoviello GPR index.
>
> Bondarenko et al. turned out to be directly relevant: our previous indicators
> were all on the English-language side of exactly the comparison they run. The
> revised paper extends their local-versus-English split into a three-way one -
> Russian, Ukrainian and Western media - and asks whose perception is priced in
> defence equities.
>
> I will also add the descriptive section you suggest (full-sample plots,
> correlations, and the February-2022 break) and report Diebold-Mariano and
> Clark-West tests, with a multiple-testing correction, for the forecasting
> exercise.
>
> May I send you the descriptive section first, once the new indicators are
> built, before I commit to the full set of results?
>
> Best regards,
> Kateryna
