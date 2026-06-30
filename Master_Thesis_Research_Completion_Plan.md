# Master Thesis Research Completion Plan

**Project:** Master 2 Financial Technology Development  
**Working title:** *War Signals and Defense Equity Risk: Physical Air-Attack Intensity versus Multilingual News Narratives*  
**Last updated:** 28 June 2026  
**Purpose of this file:** Provide a self-contained execution plan and decision record that can be given to any AI agent, supervisor, research assistant, or collaborator without requiring access to earlier conversations.

---

## 1. Executive summary

This thesis studies whether daily information about Russian missile and drone attacks on Ukraine improves forecasts of defense-equity returns and volatility.

It compares two information layers:

1. **Physical attack signals:** what was launched, intercepted, and geographically experienced.
2. **News narrative signals:** how Ukrainian, Russian, and Western media reported and interpreted those attacks.

The main empirical question is not whether war is merely correlated with defense-stock prices. It is whether physical attacks, multilingual narratives, or their combination contain **incremental out-of-sample predictive information** beyond standard financial-market variables.

The main financial outcome is the Bloomberg `WAERLST` aerospace-and-defense index. A European aerospace-and-defense index will be used as the principal robustness outcome, and `BSHIELDT` as an additional defense-specific robustness check. Historical constituent-level analysis is desirable but remains an extension unless the core index-level study is complete.

The minimum viable thesis uses daily returns and daily volatility measures. Long historical intraday data are not assumed to be available. HAR-RV is therefore optional, not required.

---

## 2. Final research scope

### 2.1 Main research question

> **Do unexpected changes in the scale, composition, and interception of Russian air attacks on Ukraine provide incremental out-of-sample predictive information for defense-equity returns and volatility beyond multilingual news narratives?**

### 2.2 Focused subquestions

1. Does the physical attack signal improve forecasts beyond standard financial controls?
2. Does multilingual news improve forecasts beyond the physical attack itself?
3. Does a media “narrative gap” carry more predictive content than raw article volume?
4. Does weapon composition contain more information than the aggregate number of weapons launched?
5. Is information absorbed differently over one-day and five-day forecast horizons?
6. Are findings robust across a global defense index and European defense indices?

### 2.3 Research type

This is primarily a **predictive forecasting study**, not a causal identification study.

Permitted language:

- “predicts”
- “contains incremental predictive information”
- “improves out-of-sample forecast accuracy”
- “is associated with subsequent returns or volatility”

Avoid unless a separate credible identification strategy is developed:

- “causes”
- “leads to”
- “has a causal effect on”

---

## 3. Core contribution

The intended contribution is a direct forecasting comparison between:

1. standard financial information;
2. observed military attack intensity;
3. multilingual media attention and framing;
4. the combination of physical and narrative information.

The novelty should be framed around the following elements:

- continuous daily signals rather than only a small number of event dates;
- weapon composition and interception success rather than a generic war dummy;
- multilingual and geographically distinct media environments;
- separation of physical severity from media amplification;
- strict out-of-sample forecasting rather than only in-sample regressions;
- comparison of econometric baselines with explainable machine-learning models.

---

## 4. Scope control

### 4.1 Minimum viable thesis

The thesis is complete and defensible if it contains:

- daily data from 24 February 2022 onward;
- `WAERLST` as the main financial outcome;
- at least one European defense-index robustness outcome;
- daily physical attack variables;
- daily GDELT news-volume variables for Ukrainian, Russian, and Western source groups;
- at least one multilingual text-derived narrative or sentiment measure;
- daily returns;
- a defensible daily volatility target;
- econometric benchmark models;
- one gradient-boosting model;
- time-series out-of-sample evaluation;
- ablation tests showing the incremental value of attacks and news;
- a careful discussion of leakage, data quality, and limitations.

### 4.2 Optional extensions

Only begin these after the minimum viable thesis is working:

- firm-level constituent panel;
- defense-revenue exposure interactions;
- firm specialization by radar, air defense, missiles, drones, or electronics;
- intraday realized volatility and HAR-RV;
- procurement announcements;
- sanctions;
- arms-delivery announcements;
- trading-strategy implementation;
- complex deep-learning forecasting architectures;
- causal identification.

### 4.3 Explicitly excluded from the core thesis

Do not make these additional full research pillars:

- ground-war intensity;
- all geopolitical events globally;
- sanctions and procurement as equal primary questions;
- social-media sentiment as another separate dataset;
- event studies as the main method;
- more than one principal boosting algorithm;
- multiple transformer architectures selected only for novelty.

---

## 5. Current project status and decisions

### 5.1 Confirmed decisions

- Main topic and research question are selected.
- Main frequency is daily.
- `WAERLST` is the primary index.
- A European aerospace-and-defense index is required for robustness.
- `BSHIELDT` is an additional thematic robustness check.
- The analysis will compare physical attacks with multilingual news.
- Forecast evaluation must be genuinely out of sample.
- ML interpretation will use SHAP or a similarly transparent feature-attribution method.
- The study is predictive rather than causal.

### 5.2 Financial-data feasibility status

The researcher has received Bloomberg corporate data for the selected indices beginning in 2020.

This resolves the basic availability problem for:

- daily index returns;
- warm-up estimation before February 2022;
- daily GARCH-family models;
- daily machine-learning models.

It does **not automatically confirm** the availability of:

- open, high, low, and close fields;
- intraday bars;
- full-sample realized volatility;
- HAR-RV.

Until the actual fields are inspected, assume:

- daily close or total-return index data are available;
- OHLC fields are possible but unconfirmed;
- long intraday history is unavailable.

### 5.3 Volatility-model decision rule

Use this hierarchy:

1. **If full historical intraday bars exist:** construct realized volatility and consider HAR-RV.
2. **If daily OHLC exists:** use range-based volatility as the main observed volatility target and GARCH-family forecasts as benchmarks.
3. **If only daily closes exist:** use absolute or squared returns as observed volatility proxies and GARCH conditional variance as a model-based forecast target.

HAR-RV is an extension and must never block thesis completion.

### 5.4 Items still unresolved

- Exact Bloomberg fields and index identifiers.
- Choice of the principal European robustness index.
- Availability of historical constituent membership.
- Quality and completeness of launched-versus-intercepted attack data.
- Access to article full text for transformer analysis.
- Final multilingual transformer model.
- Final date cutoff shared by all data sources.

---

## 6. Data architecture

### 6.1 Target master dataset

The central modeling table should contain one row per financial trading day and index.

Suggested key:

```text
date × index_id
```

Core columns:

```text
date
index_id
index_name
index_region
close_or_total_return_level
daily_return
market_adjusted_return
volatility_target
broad_market_return
market_volatility_control
brent_return
eurusd_return
interest_rate_change
attack_total
attack_uav
attack_cruise
attack_ballistic
attack_other
neutralised_total
penetrations_estimated
interception_rate
weapon_diversity
oblasts_affected
alert_duration
attack_surprise
ua_news_volume
ru_news_volume
west_news_volume
ua_sentiment
ru_sentiment
west_sentiment
ua_narrative_gap
ru_narrative_gap
west_narrative_gap
weekday
holiday_flags
forecast_origin
```

### 6.2 Recommended folder structure

```text
master_thesis/
├── README.md
├── research_plan.md
├── environment.yml
├── requirements.txt
├── config/
│   ├── paths.yaml
│   ├── source_groups.yaml
│   ├── gdelt_queries.yaml
│   └── model_config.yaml
├── data/
│   ├── raw/
│   │   ├── bloomberg/
│   │   ├── attacks/
│   │   ├── air_alerts/
│   │   ├── gdelt/
│   │   └── controls/
│   ├── interim/
│   │   ├── financial/
│   │   ├── attacks/
│   │   └── news/
│   ├── processed/
│   │   ├── daily_master.parquet
│   │   ├── model_matrix.parquet
│   │   └── data_dictionary.csv
│   └── external/
├── notebooks/
│   ├── 01_financial_data_audit.ipynb
│   ├── 02_attack_data_audit.ipynb
│   ├── 03_gdelt_extraction_audit.ipynb
│   ├── 04_feature_engineering.ipynb
│   ├── 05_exploratory_analysis.ipynb
│   ├── 06_baseline_models.ipynb
│   ├── 07_ml_models.ipynb
│   └── 08_robustness.ipynb
├── src/
│   ├── data/
│   │   ├── financial.py
│   │   ├── attacks.py
│   │   ├── gdelt.py
│   │   └── merge.py
│   ├── features/
│   │   ├── returns.py
│   │   ├── volatility.py
│   │   ├── attack_surprise.py
│   │   ├── narratives.py
│   │   └── lags.py
│   ├── models/
│   │   ├── baselines.py
│   │   ├── garch.py
│   │   ├── boosting.py
│   │   └── evaluation.py
│   └── utils/
├── outputs/
│   ├── figures/
│   ├── tables/
│   ├── model_objects/
│   └── logs/
├── thesis/
│   ├── chapters/
│   ├── references.bib
│   └── main_document
└── decision_log.md
```

### 6.3 Reproducibility rules

- Never manually edit processed datasets.
- Preserve raw files unchanged.
- Every processed file must be reproducible from code.
- Save exact extraction dates.
- Save source URLs or source identifiers where permitted.
- Use deterministic random seeds.
- Store model parameters in configuration files.
- Log removed observations and reasons.
- Use Parquet for large analytical tables.
- Maintain a data dictionary with units, frequency, timing, and transformations.

---

## 7. Dataset requirements

## 7.1 Bloomberg financial data

### Required fields

At minimum:

- date;
- Bloomberg identifier;
- index name;
- index level or total-return index level;
- currency.

Strongly preferred:

- open;
- high;
- low;
- close;
- trading volume where meaningful;
- price-return and total-return versions;
- index constituents;
- constituent weights;
- membership start and end dates.

### Main financial series

- `WAERLST`: primary global aerospace-and-defense outcome.
- Principal European aerospace-and-defense index: choose after field/history comparison.
- `BSHIELDT`: additional defense-specific robustness outcome.
- Broad global and European equity-market benchmarks.
- Market volatility index.
- Brent crude oil.
- EUR/USD.
- Relevant interest-rate or bond-yield control.

### Audit tasks

- Check date range.
- Check missing trading days.
- Check duplicate rows.
- Check whether values are price or total-return levels.
- Check currency and timezone.
- Identify index launch dates and whether earlier values are back-tested.
- Compare returns against Bloomberg charts for selected dates.
- Confirm whether OHLC fields are truly available.
- Record all Bloomberg field codes.

### Acceptance criterion

A clean financial table must cover the full modeling period with no unexplained duplicate dates and with documented treatment of holidays, missing data, currency, and return definition.

---

## 7.2 Physical attack data

### Preferred daily variables

- total airborne weapons launched;
- UAVs or Shahed-type drones;
- cruise missiles;
- ballistic or aeroballistic missiles;
- other guided missiles;
- total neutralised or intercepted;
- estimated penetrations;
- interception rate;
- number of weapon categories used;
- number of affected oblasts;
- total or average air-alert duration;
- share of oblasts under alert.

### Source hierarchy

1. Official Ukrainian Air Force or Ministry of Defence reports.
2. Structured datasets that preserve links to official reports.
3. Air-alert datasets based on official alert channels.
4. Reliable external structured trackers for validation only.

### Data challenges to document

- changes in terminology over time;
- weapons described differently across reports;
- launch counts revised later;
- “destroyed,” “suppressed,” “lost,” and “neutralised” may not be equivalent;
- some reports cover overnight attacks spanning two calendar dates;
- attacks may begin before midnight and be reported the next morning;
- air-alert intensity is not identical to weapon-launch intensity.

### Required audit

For a manually selected sample of at least 20 days:

- compare structured counts with original official reports;
- verify date assignment;
- verify category mapping;
- note revisions and ambiguous categories;
- calculate disagreement rates.

### Acceptance criterion

The attack dataset must have a documented category dictionary, transparent source hierarchy, date-assignment rule, and acceptable agreement with original reports.

---

## 7.3 GDELT multilingual news data

### Unit of collection

One article-level record before aggregation.

### Required raw fields

Where available:

- article timestamp;
- URL;
- domain;
- title;
- source country;
- original language;
- translated language indicator;
- themes or event codes;
- tone fields;
- article text or recoverable text;
- extraction timestamp.

### Source groups

Do not equate language with political viewpoint.

Create groups using both source geography and original language:

1. **Ukrainian information environment**
2. **Russian information environment**
3. **Western information environment**

A Russian-language Ukrainian source should not automatically be placed in the Russian information environment.

### Query design

The GDELT query must focus on Russian missile and drone attacks on Ukraine and avoid collecting all Ukraine-war news.

The query dictionary should include multilingual terms for:

- missile;
- ballistic missile;
- cruise missile;
- drone;
- Shahed;
- air attack;
- air defense;
- interception;
- bombardment;
- strike;
- Ukrainian cities and oblasts.

### Deduplication

Apply at least:

- exact URL deduplication;
- canonical-domain cleanup;
- title normalization;
- near-duplicate title or text similarity;
- syndicated-content detection where feasible.

### Daily news features

For each source group:

- article count;
- normalized article count;
- average sentiment or threat score;
- sentiment dispersion;
- escalation probability;
- topic proportions;
- share of articles mentioning interception;
- share mentioning civilian damage;
- share mentioning air-defense shortages;
- share mentioning Western military support.

### Acceptance criterion

A manually reviewed multilingual sample must demonstrate acceptable relevance and source-group classification. Record precision estimates for the query and classification rules.

---

## 8. Feature engineering

## 8.1 Returns

Primary return:

\[
r_t = 100\left[\ln(P_t)-\ln(P_{t-1})\right]
\]

Prefer total-return levels when available.

Also calculate:

- raw return;
- excess or market-adjusted return;
- one-day forward return;
- cumulative five-day forward return.

Do not model price levels as the primary dependent variable.

---

## 8.2 Volatility

### Case A: daily OHLC available

Construct multiple range-based estimators:

- Parkinson;
- Garman–Klass;
- Rogers–Satchell;
- Yang–Zhang, if previous close and opening gaps can be handled correctly.

Select one primary target based on data quality and use others for robustness.

### Case B: only close prices available

Use:

- absolute return;
- squared return;
- GARCH conditional variance.

Explain the measurement limitation.

### Case C: intraday data available

Construct realized variance using a fixed sampling interval and investigate microstructure noise. HAR-RV may then be included.

---

## 8.3 Attack composition

Create:

```text
attack_total
attack_uav_share
attack_cruise_share
attack_ballistic_share
interception_rate
penetrations_estimated
weapon_diversity
large_attack_indicator
```

Possible weapon-diversity measure:

\[
Diversity_t = 1 - \sum_k s_{k,t}^2
\]

where \(s_{k,t}\) is the share of weapon category \(k\) on day \(t\).

---

## 8.4 Attack surprise

The attack-surprise feature must use only past information.

General form:

\[
AttackSurprise_t = ActualAttack_t-\widehat{E}(Attack_t \mid \mathcal{F}_{t-1})
\]

Candidate expectation models:

- rolling mean or median;
- autoregressive count model;
- Poisson or negative-binomial model;
- gradient-boosting count model as a robustness exercise.

Start with a simple, interpretable model. Do not over-engineer this stage.

Construct surprises separately for:

- total attacks;
- UAVs;
- cruise missiles;
- ballistic missiles;
- estimated penetrations.

Standardized surprise may be used:

\[
StandardizedSurprise_t =
\frac{ActualAttack_t-\widehat{Attack}_t}
{\widehat{\sigma}_{t}}
\]

All parameters must be estimated recursively or within training folds.

---

## 8.5 News attention normalization

Raw volume can rise because GDELT’s general coverage changes.

Possible normalized measure:

\[
NormalizedNews_{g,t}
=
\frac{RelevantArticles_{g,t}}
{AllMonitoredArticles_{g,t}}
\]

Alternative:

- z-score within each source group;
- rolling percentile;
- log transformation: \(\log(1+count)\).

Use raw and normalized measures in robustness checks.

---

## 8.6 Multilingual narrative measures

Use one multilingual transformer that can consistently score Ukrainian, Russian, and major Western languages.

Preferred tasks:

- threat or escalation score;
- negative sentiment;
- narrative-topic probabilities;
- possibly stance toward Russian military capability or Ukrainian air-defense effectiveness.

Requirements:

- manually labeled validation subset;
- transparent label definitions;
- class-balance reporting;
- model performance reported by language group;
- no fine-tuning on future test-period articles.

A generic positive/negative sentiment score is insufficient on its own because reports of intercepted missiles may sound negative while conveying successful defense. Threat and escalation measures are therefore more economically meaningful.

---

## 8.7 Narrative gap

For source group \(g\):

\[
NarrativeGap_{g,t}
=
ObservedNews_{g,t}
-
\widehat{E}(News_{g,t}\mid PhysicalAttack_t)
\]

Estimate expected news using only training-period observations.

The physical predictors may include:

- total attack count;
- weapon composition;
- penetrations;
- interception rate;
- oblast breadth;
- alert duration.

Construct gaps for:

- volume;
- escalation score;
- air-defense-shortage narrative;
- civilian-damage narrative.

The gap represents unusual media amplification, under-reporting, or framing relative to physical attack severity. It is not automatically causal media bias.

---

## 8.8 Lags and timing

Candidate lags:

- \(t\);
- \(t-1\);
- 3-day rolling mean;
- 7-day rolling mean;
- 30-day rolling mean for financial variables.

Avoid creating too many highly correlated features.

All features must have an explicit “available at” timestamp.

---

## 9. Timing and leakage policy

This is one of the most important sections of the project.

### 9.1 Primary forecast design

Use:

\[
Information\ available\ by\ the\ end\ of\ day\ t
\rightarrow
Market\ outcome\ on\ trading\ day\ t+1
\]

This conservative design reduces ambiguity around overnight attacks and report publication times.

### 9.2 Secondary pre-market design

Only if precise timestamps are available:

\[
Information\ available\ before\ a\ fixed\ European\ market\ opening\ cutoff
\rightarrow
Same-day\ European\ market\ outcome
\]

This must be secondary because Ukrainian overnight attacks and morning reports may overlap with European trading hours.

### 9.3 Weekend rule

Weekend attack and news information must be accumulated or assigned according to a pre-defined rule, for example:

- Friday close to Monday pre-market information predicts Monday;
- Monday outcome uses the complete weekend information set;
- do not create artificial Saturday and Sunday financial observations.

### 9.4 Publication-time rule

The date an attack occurred is not always the date investors learned the verified counts.

Maintain both when possible:

```text
attack_start_date
official_report_timestamp
market_information_date
```

Use `market_information_date` for predictive models.

### 9.5 Leakage checklist

Before accepting any model:

- Are future articles used in same-day features?
- Was the full-sample mean used for normalization?
- Was the attack-surprise model fitted on the test period?
- Was the narrative-gap model fitted on the test period?
- Was feature selection performed using the full sample?
- Were test observations used in transformer fine-tuning?
- Were current index constituents imposed retrospectively?
- Were revisions incorporated as if known in real time?

Any “yes” invalidates the claimed out-of-sample result unless explicitly corrected.

---

## 10. Modeling strategy

## 10.1 Forecast horizons

Primary:

- one trading day ahead.

Secondary:

- five trading days ahead.

Optional:

- 20 trading days ahead for volatility only.

---

## 10.2 Information-set horse race

Estimate the same model family with five feature sets:

### Model set F: financial baseline

- lagged returns;
- lagged volatility;
- broad market return;
- market volatility control;
- oil;
- FX;
- rates;
- calendar effects.

### Model set P: financial + physical attacks

Add:

- total attacks;
- weapon composition;
- interceptions;
- penetrations;
- attack surprise;
- alert variables.

### Model set N: financial + news

Add:

- multilingual volume;
- normalized attention;
- sentiment or escalation;
- narrative-topic shares.

### Model set PN: financial + physical + news

Combine P and N.

### Model set PNG: financial + physical + news + narrative gaps

Add narrative-gap features.

This structure is essential because it directly tests incremental predictive value.

---

## 10.3 Econometric benchmarks

### Returns

- historical mean;
- autoregressive model;
- linear regression with financial controls;
- regularized linear model as a robustness benchmark.

### Volatility

Depending on available data:

- GARCH(1,1);
- GJR-GARCH or EGARCH;
- autoregressive model for range-based volatility;
- HAR-RV only if genuine realized volatility exists.

Add attack/news features as exogenous variables only after the baseline is functioning.

---

## 10.4 Machine-learning model

Use one principal algorithm:

- LightGBM **or**
- XGBoost.

Do not use both as equal main models unless required for robustness.

Recommended constraints:

- shallow trees;
- limited feature count;
- early stopping;
- conservative learning rate;
- time-series cross-validation;
- class or target transformations where necessary.

The daily sample is relatively small, so model complexity must remain limited.

---

## 10.5 Explainability

Use SHAP on held-out predictions to report:

- global feature importance;
- feature effects;
- interaction patterns only where stable;
- differences across forecast horizons;
- differences across indices.

Do not interpret SHAP as causal attribution.

Validate that important features are not merely proxies for calendar effects or market-wide volatility.

---

## 11. Out-of-sample design

### 11.1 Primary split

Use an expanding-window forecasting exercise.

Suggested structure:

- initial training period beginning in 2020 for financial variables;
- attack/news modeling begins when those variables become available;
- reserve the final 25–30% of the common sample for strict out-of-sample testing.

Alternative if the sample is too short:

- rolling-origin evaluation with multiple forecast folds;
- report average performance across folds.

### 11.2 Hyperparameter tuning

- Tune only within training data.
- Use time-series cross-validation.
- Never shuffle observations.
- Refit at fixed intervals.
- Record every parameter and seed.

### 11.3 Preprocessing

Within each training fold:

- fit scalers;
- fit text-model calibration where needed;
- fit attack-surprise models;
- fit narrative-gap models;
- select features;
- determine missing-value imputation.

Apply fitted transformations to validation/test data without re-estimating on future observations.

---

## 12. Evaluation framework

## 12.1 Return forecasts

Report:

- MAE;
- RMSE;
- directional accuracy;
- balanced accuracy where sign imbalance exists;
- correlation between forecast and realized return;
- optional economic value after conservative transaction costs.

Return predictability is difficult. Null return results are acceptable if volatility results are informative.

## 12.2 Volatility forecasts

Report:

- QLIKE;
- MAE;
- MSE or RMSE;
- forecast bias;
- calibration plots.

Use QLIKE as a principal metric where the target is positive and volatility-like.

## 12.3 Statistical comparison

Use where applicable:

- Diebold–Mariano tests for non-nested comparisons;
- Clark–West tests for nested forecasting models;
- Model Confidence Set as a robustness procedure;
- block bootstrap confidence intervals if dependence is material.

Correct or discuss multiple comparisons.

## 12.4 Economic significance

Report forecast improvement relative to baseline:

\[
Improvement =
100 \times
\frac{Loss_{baseline}-Loss_{model}}
{Loss_{baseline}}
\]

Do not rely only on p-values.

---

## 13. Hypotheses

### H1: Physical attack information

Unexpected physical attack intensity improves defense-equity volatility forecasts beyond standard financial predictors.

### H2: News information

Multilingual news features improve forecasts beyond physical attack information.

### H3: Narrative gap

Unusual news amplification relative to physical severity has greater predictive content than raw article volume alone.

### H4: Weapon composition

Weapon composition and interception outcomes contain more predictive information than total attack counts alone.

### H5: Information diffusion

Physical and narrative information have different predictive horizons, with effects potentially differing between one-day and five-day forecasts.

### H6: Geographic robustness

Results differ in magnitude between the global defense index and European defense indices but retain the same qualitative information hierarchy.

### Optional H7: Firm exposure

If the firm-level extension is completed, predictive effects are stronger for firms with higher military-revenue exposure.

---

## 14. Exploratory analysis requirements

Before forecasting, produce:

- time plots of all financial outcomes;
- attack counts by category;
- interception rate over time;
- news volume by source group;
- narrative scores by source group;
- correlation heatmap using training data;
- missingness map;
- distribution plots;
- extreme-day table;
- weekend versus weekday summaries;
- lead-lag correlations presented as exploratory only.

Also manually inspect:

- top 20 attack-surprise days;
- top 20 narrative-gap days;
- days when physical and narrative signals strongly disagree.

Do not use exploratory findings to tune the final test set.

---

## 15. Robustness tests

Prioritize:

1. alternative volatility measures;
2. raw versus normalized news volume;
3. alternative attack date assignments;
4. one-day versus five-day horizons;
5. global versus European indices;
6. alternative definitions of Russian, Ukrainian, and Western source groups;
7. excluding the largest extreme attack days;
8. excluding the invasion’s first months;
9. controlling for broad geopolitical-risk measures if accessible;
10. using only official attack reports;
11. alternative attack-surprise models;
12. alternative text aggregation rules.

Optional:

- placebo outcomes such as civilian-heavy aerospace indices or broad industrial indices;
- placebo timing using deliberately shifted attack features;
- firm-level defense-exposure analysis.

---

## 16. Firm-level extension

Begin only after the index-level thesis is complete.

### Required data

- historical point-in-time constituents;
- membership dates;
- weights;
- firm daily returns;
- country and currency;
- market capitalization;
- arms or military revenue;
- total revenue;
- defense specialization.

### Exposure measure

\[
DefenseExposure_{i,y}
=
\frac{MilitaryRevenue_{i,y}}
{TotalRevenue_{i,y}}
\]

### Main question

Do firms with greater defense exposure respond more strongly to attack surprises and news narratives?

### Major risks

- survivorship bias;
- look-ahead bias;
- current constituent lists applied retrospectively;
- inconsistent defense-revenue definitions;
- missing private-company competitors;
- mixed civilian and military business lines.

---

## 17. Research phases and deliverables

## Phase 0 — Project setup

### Tasks

- Create repository and folder structure.
- Freeze the research question.
- Create environment and dependency files.
- Add this plan and a decision log.
- Define naming conventions.
- Create master bibliography.

### Deliverables

- reproducible repository;
- `README.md`;
- `decision_log.md`;
- environment file;
- source inventory.

### Completion criterion

A new agent can clone/open the project and understand how to run it.

---

## Phase 1 — Financial-data audit

### Tasks

- Inventory all Bloomberg files.
- Identify exact fields and tickers.
- Confirm whether data are close-only, OHLC, or intraday.
- Identify price versus total-return series.
- Check coverage from 2020.
- Select the principal European robustness index.
- Create returns and preliminary volatility targets.

### Deliverables

- financial data audit report;
- cleaned financial dataset;
- field dictionary;
- decision on volatility target;
- charts validating return calculations.

### Completion criterion

A modeling-ready financial table exists and the volatility approach is fixed.

---

## Phase 2 — Physical attack dataset

### Tasks

- Select source hierarchy.
- Download or compile official daily reports.
- Standardize weapon categories.
- Resolve date and timestamp rules.
- Create launched, neutralised, penetrations, composition, and alert variables.
- Validate against original reports.

### Deliverables

- cleaned daily attack table;
- weapon-category dictionary;
- source-validation table;
- missingness and revision report.

### Completion criterion

At least 95% of retained observations have a traceable source or documented derivation.

---

## Phase 3 — GDELT extraction and source classification

**Status:** ✅ **Complete (2026-06-30).**  See [`docs/phase3_gdelt_audit.md`](../docs/phase3_gdelt_audit.md) and [`docs/phase3_classification_audit.md`](../docs/phase3_classification_audit.md) for full audit + gap-closure reports.

### Tasks

- [x] Define multilingual keyword dictionary.
- [x] Build reproducible extraction.
- [x] Separate source geography from language.
- [x] Classify sources into Ukrainian, Russian, and Western groups.
- [x] Deduplicate.
- ~~Manually assess query precision.~~  **Replaced with automated agreement check** on 11 M+ articles (see decision log 2026-06-30).

### Deliverables

- [x] article-level dataset (11,433,653 URL-deduped articles, 4.7 GB parquet);
- [x] source-classification table (88.6 % country-mapped);
- [x] query dictionary (`config/gdelt_queries.yaml`, 4 queries × 6 languages);
- [x] automated precision report (`data/processed/news/auto_precision_report.md`);
- [x] daily attention measures (`news_daily_enriched.parquet`, 1,342 × 17);
- [x] per-query × group pivot (`news_query_group_pivot.parquet`, 1,342 × 17);
- [x] narrative-gap features (`narrative_gap_ua_west`, `_ru_west`, `_ua_ru`);
- [x] sensitivity analysis (`sensitivity_report.md`, refreshed on full 46-month data).

### Completion criterion

**Met.**  Tone divergence is strong and stable across the 46-month window (UA −3.51, RU −3.63, Western −1.87, Other −0.17) and the automated precision check reports 85.4 % overall agreement with the high-confidence country map (per-method: country 85.8 %, domain 96.0 %, tld 97.5 %, fallback 73.0 %).

---

## Phase 4 — NLP features

### Tasks

- Define economically meaningful labels.
- Sample and manually label multilingual articles.
- Select one multilingual transformer.
- Evaluate by language group.
- Score recoverable articles.
- Aggregate to daily source-group features.

### Deliverables

- annotation guide;
- labeled validation sample;
- model card;
- performance table by language;
- daily narrative features.

### Completion criterion

The chosen text model performs sufficiently and consistently across language groups, or its limitations are explicitly bounded.

---

## Phase 5 — Merge and feature engineering

### Tasks

- Align calendars and timestamps.
- Construct returns and volatility.
- Construct attack surprises recursively.
- Construct narrative gaps recursively.
- Create controls and lags.
- Handle weekends.
- Produce final model matrix.
- Run leakage checks.

### Deliverables

- `daily_master.parquet`;
- `model_matrix.parquet`;
- data dictionary;
- leakage audit;
- descriptive-statistics table.

### Completion criterion

Every model feature has a documented unit, timing, source, transformation, and missing-value rule.

---

## Phase 6 — Econometric baselines

### Tasks

- Estimate historical-mean/AR return models.
- Estimate GARCH-family or range-volatility baselines.
- Add physical features.
- Add news features.
- Run initial expanding-window forecasts.

### Deliverables

- baseline forecast files;
- benchmark tables;
- diagnostic plots;
- residual checks.

### Completion criterion

All baseline models produce reproducible out-of-sample predictions for the same forecast dates.

---

## Phase 7 — Machine-learning models

### Tasks

- Implement the five information sets.
- Tune with time-series cross-validation.
- Generate strictly held-out predictions.
- Calculate SHAP values.
- Check stability across folds.

### Deliverables

- model configurations;
- saved predictions;
- forecast-loss table;
- SHAP plots;
- feature-stability report.

### Completion criterion

The ML comparison is reproducible and uses identical test dates and evaluation metrics across information sets.

---

## Phase 8 — Statistical comparison and robustness

### Tasks

- Compare forecast losses.
- Run Diebold–Mariano or appropriate tests.
- Calculate relative improvements.
- Run robustness specifications.
- Investigate disagreement days.
- Document null and unstable findings.

### Deliverables

- final results tables;
- robustness matrix;
- statistical-test table;
- main figures.

### Completion criterion

The thesis can answer which information set adds predictive content, for which outcome, index, and horizon.

---

## Phase 9 — Writing

### Recommended chapter structure

1. Introduction
2. Institutional background and economic mechanism
3. Related literature
4. Data
5. Feature construction and NLP methodology
6. Forecasting methodology
7. Results
8. Robustness and limitations
9. Conclusion

### Writing order

1. Data
2. Methodology
3. Descriptive results
4. Forecasting results
5. Robustness
6. Literature review
7. Introduction
8. Conclusion
9. Abstract

### Completion criterion

All claims in the abstract and conclusion are directly supported by final tables or figures.

---

## Phase 10 — Final validation

### Tasks

- Re-run the full pipeline from raw data.
- Verify table and figure numbers.
- Check all references.
- Check equations and variable names.
- Review leakage risks.
- Verify no current constituents are used retrospectively.
- Proofread.
- Archive code, configuration, and final outputs.

### Deliverables

- final thesis;
- reproducibility appendix;
- code archive;
- final data dictionary;
- final limitations checklist.

---

## 18. Priority order

When time is limited, follow this order:

1. Financial-data audit.
2. Physical attack dataset.
3. GDELT volume extraction.
4. Calendar and timing alignment.
5. Daily returns and volatility target.
6. Financial baselines.
7. Physical-versus-news ablation forecasts.
8. One multilingual NLP feature.
9. Gradient boosting.
10. SHAP.
11. Robustness index.
12. Additional narrative topics.
13. Firm-level extension.
14. Intraday extension.

Never prioritize an optional extension over a broken core data pipeline.

---

## 19. Decision log template

Every important methodological change must be recorded in `decision_log.md`.

```markdown
## YYYY-MM-DD — Decision title

**Decision:**  
State what was chosen.

**Reason:**  
Explain the empirical or practical reason.

**Alternatives considered:**  
List credible alternatives.

**Consequences:**  
State what changes in data, models, or interpretation.

**Revisit condition:**  
State what new evidence would justify reopening the decision.
```

Initial decisions to record:

- `WAERLST` as main outcome.
- Daily frequency.
- Predictive rather than causal framing.
- HAR-RV optional.
- One principal gradient-boosting model.
- Ukrainian/Russian/Western source groups based on geography and language.
- Index-level core; firm-level extension.
- No event study as the main design.

---

## 20. AI-agent handoff protocol

Any AI agent working on this project must begin by reading:

1. this file;
2. `README.md`;
3. `decision_log.md`;
4. the data dictionary;
5. the latest task/status log.

### Required behavior

- Do not silently change the research question.
- Do not add new datasets without explaining their contribution and cost.
- Do not use future information in features.
- Do not assume daily data are intraday data.
- Do not describe predictive results as causal.
- Do not apply current index constituents retrospectively.
- Do not overwrite raw data.
- Do not report model superiority without common test dates.
- Do not use random train/test splits.
- Do not fit scalers or residual models on the full sample.
- State assumptions explicitly.
- Record unresolved questions.
- Return reproducible code rather than isolated manual calculations.

### Required completion report for every task

```markdown
## Task completed

**Objective:**  
What was requested.

**Inputs used:**  
Files, tables, fields, and date ranges.

**Actions performed:**  
Main transformations or modeling steps.

**Outputs created:**  
Exact file paths.

**Quality checks:**  
Tests, comparisons, missingness, and validation.

**Decisions made:**  
Any new methodological choices.

**Unresolved issues:**  
What remains uncertain.

**Recommended next action:**  
One concrete next step.
```

### Agent prompt template

```text
You are working on a Master's thesis project titled
"War Signals and Defense Equity Risk: Physical Air-Attack Intensity
versus Multilingual News Narratives."

Read research_plan.md and decision_log.md before acting.

The project tests whether unexpected Russian air-attack intensity,
weapon composition, interception outcomes, and multilingual news
narratives improve out-of-sample forecasts of defense-equity returns
and volatility.

WAERLST is the main financial outcome. A European defense index is the
principal robustness outcome, and BSHIELDT is an additional check.
The core study is daily and predictive, not causal. Intraday data and
HAR-RV are optional. Do not introduce look-ahead bias, random splits,
or full-sample preprocessing.

Current task:
[INSERT TASK]

Return:
1. assumptions,
2. method,
3. reproducible code or exact steps,
4. validation checks,
5. outputs,
6. unresolved risks,
7. recommended next action.
```

---

## 21. Quality-assurance checklist

### Data

- [ ] Raw data preserved.
- [ ] Date range documented.
- [ ] Timestamps and timezones documented.
- [ ] Duplicate rules documented.
- [ ] Missingness documented.
- [ ] Units documented.
- [ ] Source traceability preserved.
- [ ] Revisions documented.
- [ ] Financial series type identified.
- [ ] Back-tested index history identified.

### Features

- [ ] Every feature has an availability timestamp.
- [ ] All rolling features use past data only.
- [ ] Normalization is fitted in training windows.
- [ ] Surprise models are recursive.
- [ ] Narrative-gap models are recursive.
- [ ] Weekend treatment is fixed.
- [ ] Source groups are audited.
- [ ] Text-model performance is reported by language.

### Models

- [ ] No shuffled cross-validation.
- [ ] Common forecast dates across models.
- [ ] Baselines implemented first.
- [ ] Hyperparameters tuned only on training data.
- [ ] Forecast horizons clearly defined.
- [ ] Seeds recorded.
- [ ] Model objects or configurations saved.
- [ ] Statistical and economic significance reported.

### Interpretation

- [ ] Predictive language used.
- [ ] SHAP not described as causal.
- [ ] Null findings reported.
- [ ] Limitations are explicit.
- [ ] Results are not generalized beyond the sample.
- [ ] Index composition limitations discussed.
- [ ] Data quality differences across periods discussed.

---

## 22. Key risks and mitigation

| Risk | Consequence | Mitigation |
|---|---|---|
| No full intraday history | Cannot use full-sample HAR-RV | Use OHLC range volatility or GARCH; keep HAR-RV optional |
| Only close prices available | Volatility target is noisy | Use absolute/squared returns and GARCH; acknowledge limitation |
| Inconsistent attack reporting | Measurement error | Preserve official links, create category dictionary, validate sample |
| Attack/report date mismatch | Leakage or wrong alignment | Maintain event and publication timestamps separately |
| GDELT duplicates | Inflated attention measures | Exact and fuzzy deduplication |
| Changing news coverage | Spurious trend | Normalize by total monitored coverage and source-group baselines |
| Missing article text | Weak NLP coverage | Use metadata/tone as core; transformer on recoverable subset |
| Language ≠ viewpoint | Misclassification | Combine source geography and original language |
| Small daily sample | ML overfitting | Shallow models, limited features, expanding windows |
| Back-tested index history | Look-ahead concerns | Disclose methodology; use established index robustness |
| Current constituents used historically | Survivorship bias | Require point-in-time constituents for extension |
| Many tests | False positives | Pre-specify main outcomes and apply comparison discipline |
| Strong common war trend | Spurious relationships | Use returns, stationary transformations, financial controls |
| Attacks cause news | Collinearity | Use narrative gap and ablation models |
| Procurement news omitted | Confounding predictive signal | Mention limitation; add parsimonious controls only if feasible |

---

## 23. Final thesis success criteria

The project is successful if it can answer, with reproducible evidence:

1. Whether physical attack information improves next-day or next-week forecasts.
2. Whether news adds information after physical attacks are known.
3. Whether the narrative gap adds more than raw attention.
4. Which attack components matter most.
5. Whether conclusions survive a European-index robustness test.
6. Whether forecast improvements are statistically and economically meaningful.
7. Whether results remain credible after strict leakage and timing checks.

A null result is still a valid thesis result if the forecasting experiment is well designed and demonstrates that attacks or narratives do not outperform strong financial baselines.

---

## 24. Immediate next actions

### Task 1 — Audit the Bloomberg delivery

Produce a table with:

```text
file_name
ticker
index_name
field_name
frequency
start_date
end_date
row_count
missing_count
currency
price_or_total_return
ohlc_available
intraday_available
```

Then decide the volatility target.

### Task 2 — Freeze the main index set

Select:

- `WAERLST` as primary;
- one principal European robustness index;
- `BSHIELDT` as additional robustness.

Document launch dates and back-tested histories.

### Task 3 — Build a physical-data source inventory

For every candidate source, record:

```text
source
coverage
frequency
weapon_categories
interception_counts
timestamps
official_status
download_method
missingness
licence
```

### Task 4 — Prototype a narrow GDELT query

Retrieve a small multilingual sample for several high-attack and low-attack days, then manually evaluate relevance before scaling extraction.

### Task 5 — Create the decision log

Record all existing decisions from Section 19 and do not reopen them without a documented reason.

---

## 25. Definition of the first complete analytical milestone

The first complete milestone is reached when the project has:

- one clean financial index series;
- one daily attack-intensity series;
- one daily news-volume series for each source group;
- a leakage-safe merged table;
- a next-day return target;
- a daily volatility target;
- a financial baseline;
- financial-plus-attacks model;
- financial-plus-news model;
- a common out-of-sample forecast table.

Only after this milestone should the project add multilingual transformers, narrative gaps, SHAP, and firm-level analysis.
