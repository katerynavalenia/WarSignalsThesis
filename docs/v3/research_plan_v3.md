# Research Plan v3 — Whose Geopolitical Risk Is Priced?

**Status:** proposed — awaiting Kateryna's and the supervisor's sign-off
**Date:** 2026-08-17
**Trigger:** supervisor review (Thomas, 5 comments) on the v1 paper
**Relationship to earlier plans:** supersedes `docs/v2/research_plan.md` as the
active plan; retains the v1 question and *all* v1/v2 infrastructure. This is a
**measurement and sample correction, not a topic change.**

---

## 0. One-paragraph summary

The paper stays on its topic: **media-based war signals and defence-equity
pricing during the Russia–Ukraine war**. Three things change. (1) The GDELT
indicators are rebuilt from the **GDELT 2.0 Translingual** archive, so
"Ukrainian", "Russian" and "Western" sentiment measure *who published the
article* rather than *which country the article mentions* — the current
indicators do not measure national perspectives at all (see
[`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md)). (2) The
sample runs **2015-02 → 2026-06** instead of 2022-09 → 2026-06, which triples
the number of observations and puts the February-2022 invasion — the single
largest defence-equity repricing in decades — *inside* the sample. (3) The
econometrics move to the standard toolkit of this literature: local projections
on identified perception shocks, Campbell–Thompson out-of-sample R² with
Clark–West and **Diebold–Mariano** tests, HAR-type volatility models, and
explicit multiple-testing control. The air-attack dataset is retained but
demoted to a **short-sample refinement**, exactly as the supervisor suggests.

---

## 1. Why v1 was insignificant — three root causes

This matters because the plan must fix causes, not symptoms.

### 1.1 The sample contained almost no identifying variation (supervisor #1)

The window 2022-09-29 → 2026-06 is entirely inside the "attrition/drone-war
plateau". Within it, every war indicator is close to a slow-moving war-regime
trend that `days_since_invasion` and VIX already capture — which is precisely
what the v1 audit found (`docs/v1/supervisor_audit.md` §1.5: war signals make the
OOS volatility forecast *worse* once the trend is in both models). With no
regime transition in-sample, there is nothing for a war indicator to explain
that a trend cannot.

Fixing this is the highest-value single change: **n rises from ~920 to ~2,850
trading days (≈3.1×)**, and the sample gains a pre-war baseline (2015–2021), the
2021 build-up, the February-2022 shock, and the attrition phase. Standard errors
fall by ≈45% mechanically, and — more importantly — regime *contrasts* become
estimable.

### 1.2 The news indicators did not measure what they claimed (supervisor #3)

Verified this session: v1 downloaded the **English-only GKG 1.0 daily stream**
and assigned national groups by the article's most-mentioned country. "Russian
sentiment" is the tone of English-language articles *about* Russia. The three
national series are therefore near-duplicates, and the narrative-gap features are
differences between topic proxies. Full evidence and counts:
[`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md).

### 1.3 The evaluation toolkit was not the one this literature uses (supervisor #4)

v1 judged forecasts on MAE and directional accuracy with no formal test. Return
predictability at daily frequency is *always* economically small; the literature
detects it with **Campbell–Thompson out-of-sample R²** (values of 0.3–1% are
publishable), **Clark–West** for nested models, **Diebold–Mariano** for
non-nested ones, forecast combination, and economic-value metrics
(certainty-equivalent gains, Sharpe ratios). Judged on MAE, a real signal of
R²_OS = 0.5% is invisible. Separately, the volatility arm was run through a
`GARCH-X`-in-mean specification that was **100% numerically degenerate** for
BSHIELDT (`docs/v1/phase7_audit.md` §4.2) — an implementation failure that was
reported as a finding.

**None of these three causes is a property of the research question.** All three
are fixable, which is why the recommendation is to fix rather than pivot.

---

## 2. Research question and contribution

### 2.1 Question

> **Whose perception of geopolitical risk is priced in defence equities?**
> Do defence-equity returns and volatility respond to — and can they be
> predicted by — geopolitical-risk perceptions measured in *Russian*,
> *Ukrainian* and *Western* media; does it matter whether the perception
> concerns a **threat** or a **realized act**; and does the answer change
> across the pre-war, invasion, and attrition regimes?

Sub-questions:

- **SQ1 (measurement)** Do national media ecosystems produce measurably distinct
  geopolitical-risk perception series once source-language and source-country are
  correctly identified, and how do they behave around February 2022?
- **SQ2 (response)** What is the dynamic response of defence-equity returns and
  volatility to an identified perception shock from each ecosystem?
- **SQ3 (predictability)** Do perception indices deliver positive out-of-sample
  R² over a financial benchmark, and is the improvement significant
  (Diebold–Mariano / Clark–West), robust to multiple testing, and economically
  valuable?
- **SQ4 (threat vs act)** Does the *anticipatory* component (threat) dominate the
  *realized* component (acts), and does that ranking differ between Western and
  local media?
- **SQ5 (cross-section)** Does the response scale with a firm's defence-revenue
  exposure (SIPRI), and does the answer differ across the February-2022 break —
  where the v2 tests, run only on the post-2022 attrition sample, found no
  gradient?

### 2.2 Contribution, stated so it survives a "so what?"

1. **First source-perspective decomposition of geopolitical risk perception in an
   asset-pricing setting.** Bondarenko, Lewis, Rottner & Schüler (2024, *JIE*)
   establish for *macro* aggregates in *Russia* that local-language geopolitical
   risk shocks matter and English-language ones do not. We test whether the same
   asymmetry holds in *financial markets*, for the *counterparty* to the shock
   (Western defence equities), and we extend the split from two-way
   (local/English) to **three-way — aggressor media, victim media, third-party
   investor-facing media** — plus their state-controlled/independent subdivision.
   This is a direct, citable extension of the paper the supervisor named.
2. **A perception-vs-realization horse race with symmetric measurement.** Threat
   and act components are extracted from *the same corpus with the same
   dictionary in each language*, so the comparison is not contaminated by the
   differential measurement error that plagues "sharp attack counts vs noisy news
   volume" designs.
3. **An 11-year, multilingual, machine-translated conflict-perception dataset**
   for the Russia–Ukraine conflict — reusable, and a genuine artefact.
4. **A clean identification of what markets do and do not price**, spanning three
   regimes, with the invasion shock inside the sample.

Even under the least favourable outcome (no OOS predictability), SQ1, SQ2 and SQ4
deliver a complete paper; the predictability null then becomes a market-efficiency
result *with power*, rather than an underpowered one.

### 2.3 Literature anchors

| Strand | Anchors |
|---|---|
| Geopolitical risk measurement | Caldara & Iacoviello (2022, *AER*) GPR / GPR_ACT / GPR_THREAT; **Bondarenko, Lewis, Rottner & Schüler (2024, *JIE* 152:104005)** — local vs English-language perception (**required by supervisor**) |
| Text-based risk & asset prices | Baker, Bloom & Davis (2016) EPU; Manela & Moreira (2017) NVIX; Hassan et al. (2019) firm-level political risk |
| War / conflict and equity markets | Berkman, Jacobsen & Lee (2011); Brune et al.; the 2022 defence re-rating literature |
| Return predictability methodology | Campbell & Thompson (2008); Clark & West (2007); Diebold & Mariano (1995); Welch & Goyal (2008); Rapach, Strauss & Zhou (2010) forecast combination |
| Volatility | Corsi (2009) HAR-RV; Patton (2011) robust loss functions; Hansen, Lunde & Nason (2011) MCS |
| Local projections | Jordà (2005); Ramey (2016) on shock identification |

---

## 3. Response to the supervisor, point by point

Detailed mapping in [`supervisor_response_matrix.md`](supervisor_response_matrix.md).
Summary:

| # | Comment | Response |
|---|---|---|
| 1 | Why does GDELT start Sep 2022? Estimate a GDELT-only model over a longer sample. | Accepted in full and made the backbone. GDELT 2.0 Translingual is available from **2015-02-18**; the sample becomes 2015-02 → 2026-06. The attack dataset (2022-09 →) is demoted to a short-sample refinement chapter. Primary specifications are GDELT-only over the long sample. |
| 2 | Plot all indicators over the full sample, report correlations, highlight Feb 2022. | Accepted. New **Chapter: Stylized Facts** — full-sample plots, correlation matrix (levels/changes, full sample and by regime), rolling correlations, event annotations, and a formal structural-break analysis (Chow at 2022-02-24, Bai–Perron for unknown breaks). |
| 3 | Much more detailed description of the Western / Ukrainian / Russian sentiment methodology. | Accepted — and the audit found the method was invalid, not merely underdocumented. Indicators are rebuilt on source-country/source-language identification with a curated outlet register, a hand-labelled precision audit, and a sensitivity analysis across classification rules. Written up as a full methodology section. |
| 4 | Report Diebold–Mariano (or similar) for the OOS forecasting exercise. | Accepted, and extended: DM (non-nested), Clark–West (nested), Campbell–Thompson R²_OS, Model Confidence Set, Benjamini–Hochberg and Romano–Wolf corrections across the forecast grid, plus a power statement. None of this code exists yet; it will be a tested module. |
| 5 | Read and cite Bondarenko, Lewis, Rottner & Schüler (2024). | Accepted, and promoted to the thesis's primary methodological anchor — the three-way perception decomposition is framed as an extension of their local-vs-English result from Russian macro aggregates to Western defence equities. |

---

## 4. Data

### 4.1 Target sample

**2015-02-18 → 2026-06-30**, daily. Binding constraint is the GDELT Translingual
start date. Regimes:

| Regime | Window | Role |
|---|---|---|
| R0 pre-war baseline | 2015-02 → 2021-10 | post-Crimea "frozen conflict"; identifies the normal relationship |
| R1 build-up | 2021-11 → 2022-02-23 | intelligence warnings, troop build-up — **pure threat, no act** |
| R2 invasion & re-rating | 2022-02-24 → 2022-09-28 | the defence re-rating; currently *entirely out of sample* |
| R3 attrition | 2022-09-29 → 2026-06 | the v1 sample; the only window with attack data |

R1 is analytically valuable: it is a period of large threat variation with almost
no realized acts, which is close to an ideal setting for SQ4.

### 4.2 Sources

| Data | Status | Coverage | Notes |
|---|---|---|---|
| **GDELT 2.0 Translingual GKG** | **to build** | 2015-02-18 → present | 390,440 files / 4.19 TB compressed; ingestion route in §7 |
| GDELT 2.0 English GKG | to build | 2015-02-18 → present | needed for the explicit "English-only" comparison arm that mirrors Bondarenko et al. |
| Bloomberg WAERLST / BSHIELDT index levels | ✅ have | 2020-01 → 2026-06 | **shorter than the target sample — see §4.3** |
| WAERLST / BSHIELDT constituents (118 + 36 firms) | ✅ have | 2020 → 2026 | same constraint |
| Firm metadata (region, country, mktcap, weight) | ✅ have | — | 154/154 matched |
| SIPRI Top-100 arms-revenue share | ✅ have | 2002–2024 | 87/128 firms matched; used for exposure |
| **GPR daily** (GPRD, GPRD_ACT, GPRD_THREAT) | ✅ have | 1985 → 2026-06 | covers the full sample; benchmark + validation target |
| Market controls (SPX, SXXP, VIX, Brent, EURUSD, MSCI World) | ✅ have | needs back-extension to 2015 | free via yfinance/FRED |
| Ukrainian air-attack daily | ✅ have | 2022-09-29 → 2026-06 | **short sample only** — R3 refinement chapter |
| **Defence equities, long history** | **to build** | 2015 → 2026 | see §4.3 |

### 4.3 The one real new data gap

The Bloomberg index files start **2020-01-01**, not 2015. Options, in order of
preference:

1. **Re-pull WAERLST / BSHIELDT from Bloomberg with a 2015 start.** If terminal
   access is still available this is a 10-minute job and fully solves it.
2. **Build a long-history defence basket from free data** (`yfinance`): US primes
   (LMT, RTX, NOC, GD, BA, LHX), European names (RHM.DE, HO.PA, BA.L, LDO.MI,
   SAABB.ST, HAG.DE, THAL), plus the ITA and EXX5/DFEN ETFs. Equal-weight and
   market-cap-weight variants, in USD and EUR, with a documented mapping to the
   Bloomberg indices over the 2020–2026 overlap (report the correlation — this is
   the validation that v1's *reconstructed* indices failed at ρ=0.15; with real
   listed constituents it should be ≥0.95).
3. Run the long sample on the free basket as primary and use the Bloomberg
   indices for the 2020–2026 robustness check.

**Recommendation: do (1) and (2).** (2) is cheap, independent, and makes the
paper reproducible without a Bloomberg terminal — which is itself worth
something.

---

## 5. Measurement: the perception indices (this is the methodology chapter)

### 5.1 Corpus

GDELT 2.0 Translingual GKG, 2015-02-18 → 2026-06-30, restricted to articles
matching a Russia–Ukraine conflict query. Every record carries a
machine-translated English rendering plus GDELT's tone scores, themes, and the
`srclc` **source-language code**.

### 5.2 Ecosystem assignment — four tiers, applied in order

| Tier | Rule | Expected coverage | Precision |
|---|---|---|---|
| 1 | **Curated outlet register** — the ~300 outlets carrying most volume, hand-verified for country, primary language, and ownership (state-controlled vs independent) | high share of volume | very high, auditable |
| 2 | Domain ccTLD (`.ua`, `.ru`, `.de`, `.pl`, …) | tail | high |
| 3 | `srclc` source language, **conditioned on** tier-1/2 country when known | tail | medium |
| 4 | GDELT `SourceCommonName` → country lookup | remainder | medium |

**Critical rule: language ≠ country.** Many Ukrainian outlets publish in Russian.
`srclc=rus` alone would systematically reclassify Ukrainian media as Russian —
a failure mode that would look like "the two ecosystems agree" and destroy the
result. Country dominates language; language is used to *split within* a country
(e.g. Ukrainian-language vs Russian-language Ukrainian media, which is itself an
interesting cut).

### 5.3 Ecosystems

| Ecosystem | Definition | Rationale |
|---|---|---|
| **RU-state** | Russian outlets under state control (TASS, RIA, RT, Rossiyskaya Gazeta, Channel One …) | the aggressor's official narrative; Bondarenko et al. treat this split explicitly |
| **RU-independent** | Russian-language independent/exile outlets (Meduza, Novaya Gazeta Europe, The Insider, Mediazona …) | Russian-language perception free of state control — the control for censorship |
| **UA** | Ukrainian outlets, both language variants | the victim's perception; closest to ground truth on realized acts |
| **WEST** | Outlets in NATO/EU countries, any language | the investor-facing information set — what the marginal buyer of Rheinmetall reads |
| **EN-global** | English-language articles regardless of country | the **replication of v1's information set**, and the arm that Bondarenko et al. find inert |
| *(optional)* **NEUTRAL** | India, Turkey, Gulf, China, Africa, LatAm | third-party framing; useful robustness |

### 5.4 Index construction (per ecosystem, per day)

For each ecosystem $e$ and day $t$:

- **Volume** $V_{e,t}$ = conflict-matching articles, and **attention share**
  $V_{e,t}/N_{e,t}$ where $N_{e,t}$ is that ecosystem's total daily article
  count. The share is essential: it removes GDELT's well-known secular drift in
  source coverage, which otherwise produces spurious trends (v1's negative
  news→volatility sign is a likely victim of this).
- **Tone** $T_{e,t}$ = volume-weighted mean GKG tone of matching articles.
- **Threat / act split**: a Caldara–Iacoviello-style dictionary applied **in each
  source language** (native terms, not translations, with translated fallback),
  yielding $GPR^{ACT}_{e,t}$ and $GPR^{THREAT}_{e,t}$. Cross-language equivalence
  of the dictionaries is validated by hand on a sample.
- **Escalation intensity**: GKG theme shares (`ARMEDCONFLICT`, `MILITARY`,
  `NUCLEAR`, `SANCTIONS`, `REARMAMENT`-type themes).
- **Perception gaps**: $\Delta_{UA,WEST}$, $\Delta_{RU,WEST}$, $\Delta_{UA,RU}$,
  and $\Delta_{RUstate,RUind}$ — the last is a *censorship wedge* and is new.
- All series: 7-day and 30-day standardization, in levels and log-changes.

### 5.5 Validation (mandatory — v1's validation could not detect its own error)

1. **Hand-labelled precision audit**: stratified sample of 400+ articles
   (100 per ecosystem), labelled by opening the URL, with a confusion matrix and
   per-tier precision. This must be genuine hand-labelling, not agreement with a
   derived proxy.
2. **External validity**: correlate WEST and EN-global indices with the published
   **GPR / GPR_THREAT / GPR_ACT** daily series. A correctly built WEST index
   should correlate strongly with GPR; if it does not, the construction is wrong.
   This is a hard, falsifiable check available for the *entire* sample.
3. **Face validity**: the indices must spike on 2022-02-24, on 2014-style
   escalations, on Prigozhin (2023-06-24), on major strike waves. Plot them.
4. **Sensitivity**: re-estimate every headline result under (a) tier-1 outlets
   only, (b) ccTLD-only, (c) language-only, (d) the full four-tier rule.

---

## 6. Empirical design

Four blocks. Blocks A and B are the new core; C is the supervisor-requested
repair of the v1 forecasting exercise; D is the cross-section.

### Block A — Stylized facts (supervisor #2)

- Full-sample plots of every indicator with the four regimes shaded and key
  events annotated (2022-02-24 in particular).
- Correlation matrices: full sample and by regime, in levels and changes, for
  perception indices × GPR × VIX × defence returns/vol × attack intensity.
- Rolling 90-day correlations — the headline visual: does the West–Ukraine
  perception gap widen or collapse at the invasion?
- Formal breaks: Chow test at 2022-02-24; Bai–Perron unknown-break tests on each
  index and on the index→return relationship.
- Descriptive statistics, stationarity tests, persistence (each index is likely
  highly persistent — this drives the choice of levels vs changes throughout).

**Acceptance:** a self-contained descriptive chapter that answers comment #2 and
establishes that the ecosystems genuinely differ.

### Block B — Dynamic response to perception shocks (the new core)

1. **Shock identification.** Orthogonalize each perception index against its own
   lags, lagged market returns, VIX, oil, and the other ecosystems' lags —
   a small recursive VAR ordered [perception → VIX → defence returns] with the
   market variables ordered last within the day. Report robustness to ordering.
2. **Local projections** (Jordà 2005), horizons $h = 0 \dots 20$ trading days:
   $$ y_{t+h} = \alpha_h + \beta_h\,\text{shock}_{e,t} + \gamma_h' X_t + \varepsilon_{t+h} $$
   with $y$ = cumulative defence-equity return, realized volatility, and
   defence-minus-market excess return; Newey–West/Driscoll–Kraay SEs.
3. **The central comparison:** $\beta_h$ for RU-state vs RU-independent vs UA vs
   WEST vs EN-global. Bondarenko et al.'s prior says local-language shocks carry
   information the English ones do not. **If that holds in equities it is the
   headline result. If it fails, the contrast with a JIE paper is itself
   publishable**, provided the measurement is defensible — which §5.5 ensures.
4. **Threat vs act** (SQ4): the same LPs with $GPR^{THREAT}$ and $GPR^{ACT}$
   entered jointly, per ecosystem.
5. **Regime interaction:** all of the above interacted with regime dummies, and
   estimated separately on R0∪R1 (pre-invasion) vs R2∪R3.

**Why this block is the most likely source of significance:** it uses all ~2,850
observations, tests a dynamic response rather than a one-day-ahead point
forecast, and is the design the cited literature uses. Contemporaneous and
short-horizon responses to geopolitical shocks are well established; the open
question is *whose* shock — which is our question.

### Block C — Out-of-sample forecasting, done properly (supervisor #4)

Retained, repaired, and reframed as the market-efficiency leg.

- **Benchmark:** historical mean (returns) / HAR-RV (volatility), plus a
  financial-controls benchmark including VIX and the war-regime trend.
- **Metrics:** Campbell–Thompson $R^2_{OS}$ (the field standard — report this,
  not MAE), MSFE ratio, QLIKE for volatility.
- **Tests:** **Diebold–Mariano** (non-nested), **Clark–West** (nested),
  **Model Confidence Set**, with **Benjamini–Hochberg** and **Romano–Wolf**
  corrections across the full grid of (predictor × target × horizon × model).
- **Estimation:** expanding window (reuse `ExpandingWindowEngine`), plus
  **forecast combination** (equal-weighted mean across single-predictor
  forecasts — Rapach et al. show this often works where the kitchen-sink model
  fails) and shrinkage toward the benchmark.
- **Economic constraints:** Campbell–Thompson sign/positivity restrictions.
- **Economic value:** certainty-equivalent return and Sharpe ratio of a
  mean–variance investor timing on the signal, net of costs.
- **Power statement:** given $n_{OOS}$, the minimum $R^2_{OS}$ detectable at 5%.
  A null without a power statement is not a scientific null.
- **Volatility:** replace the numerically degenerate `GARCH-X`-in-mean with
  **HAR-RV-X** (Corsi 2009 plus exogenous perception terms — a simple, stable
  OLS) as primary, with GARCH-family models as robustness and the exogenous
  terms in the *variance* equation, not the mean.

**Acceptance:** a table of $R^2_{OS}$ with DM/CW p-values and corrected
significance, for every predictor × target × horizon; plus economic-value
figures; plus a power statement.

### Block D — Cross-section and the invasion event (SQ5)

- Firm panel (154 names, 2020–2026 with Bloomberg data; longer for the free
  basket), two-way fixed effects, date-clustered SEs.
- $\text{shock}_{e,t} \times \text{SIPRI exposure}_i$ — **re-run across the
  February-2022 break.** v2 found this null, but only on the post-2022 attrition
  sample, where there was no repricing to detect. Testing it across the actual
  re-rating is a genuinely different test.
- Event study around 2022-02-24 and the ~20 largest escalations: cumulative
  abnormal returns by exposure decile and by region.
- Regional split (US vs Europe), which the v1 evidence suggests matters
  (attack→vol correlation ITA 0.23 → WAERLST 0.26 → BSHIELDT 0.33).

### Block E — Short-sample refinement (the attack data)

Everything above, re-estimated on R3 only, adding the Ukrainian air-attack
intensity series: does *physically realized* intensity add anything beyond
*perceived* intensity? This is where the attack dataset belongs — as a
validation of the perception measures against ground truth, and as a bounded
robustness exercise — rather than as a binding sample constraint. It is also a
direct, transparent answer to the supervisor's "if this is driven by the air
attack dataset…".

---

## 7. Feasibility: getting 11 years of translingual GDELT

Three routes; **recommendation is Route 1 with Route 2 as fallback.**

### Route 1 — BigQuery (recommended)

`gdelt-bq.gdeltv2.gkg_partitioned` is date-partitioned and columnar, so a query
that selects only `DATE, SourceCommonName, DocumentIdentifier, V2Themes,
V1Locations, V1_5Tone, TranslationInfo` and filters partitions to 2015-2026
scans a small fraction of the table. Aggregation to daily ecosystem-level series
happens **server-side**, so what comes back is a few-MB table, not terabytes.

- Cost: BigQuery's free tier is 1 TB/month; overflow is ~$6.25/TB. Expect a
  handful of dollars for the whole project. **Run `--dry_run` first to price it.**
- Must verify early that translingual records are present in
  `gkg_partitioned` (one query, day one of Phase 1). If they are not, use
  Route 2 for the translingual arm.
- Colab Pro connects to BigQuery natively; results land in Drive.

### Route 2 — Bulk download of the translingual archive (fallback / verification)

390,440 files, 4.19 TB compressed, resumable. The v1 downloader already does the
monthly-batch, filter-on-the-fly, discard-raw pattern and needs only a URL and a
parser change (27-column v2 format instead of 11-column v1). On Colab Pro with a
fast link this is on the order of 1–3 days of wall clock, run in resumable
chunks; only the filtered subset (a few GB) is kept.

### Route 3 — GDELT DOC 2.0 API `timelinetone` / `timelinevolraw` (quick win)

Supports `sourcecountry:` and `sourcelang:` operators and returns daily series
directly — no big-data step at all. Limitations: coverage starts **2017-01-01**
(not 2015), the query language is less expressive, and it is rate-limited to one
request per 5 seconds (it refused requests from this session's proxy IP; run it
from Colab with throttling). **Use it in week 1 to get a provisional 2017–2026
version of the indices and sanity-check the whole design before committing to
Route 1 or 2.**

### Compute

Everything else is light — panel regressions and local projections on ~3k rows
run in seconds. Colab Pro is needed for the GDELT ingestion and the tuning grid,
not for the econometrics.

---

## 8. Phased execution plan

Each phase has an acceptance test. Phases 1–2 are the make-or-break; do not start
Phase 4 before Phase 2 passes.

| Phase | Work | Acceptance |
|---|---|---|
| **0. Sign-off** | Agree the reframing with the supervisor. Send: the measurement diagnosis, the revised question, the sample extension, and the response matrix. | Written go-ahead; confirmation that a three-way perception extension of Bondarenko et al. is the right framing. |
| **1. Long-sample data spine** | Back-extend financial data to 2015 (Bloomberg re-pull and/or free basket); back-extend market controls; assemble GPR over the full sample; build the regime calendar; **provisional indices via Route 3 (2017+)**. | A 2015–2026 daily table of returns, realized vol, controls and GPR; provisional perception indices plotted; free-basket vs Bloomberg correlation ≥0.95 on the overlap. |
| **2. Perception indices (the core build)** | Verify BigQuery translingual coverage; build the outlet register; ingest 2015–2026; construct all indices (§5.4); run the full validation battery (§5.5). | **Gate:** hand-labelled precision reported per ecosystem; WEST index correlates strongly with published GPR; indices visibly spike on known events; the ecosystems are *not* mutually collinear (pairwise |ρ| well below the v1 topic-proxy levels). If this gate fails, stop and reconsider before investing in Blocks B–E. |
| **3. Stylized facts** | Block A in full. | The descriptive chapter, ready to send to the supervisor as the first deliverable answering comments #1–#3. |
| **4. Dynamic response** | Block B: shock identification, local projections, threat-vs-act, regime interactions. | IRF figures + tables with corrected significance; a clear verdict on whose perception is priced. |
| **5. Forecasting repair** | Block C: build the tested `evaluation/tests.py` module (DM, CW, CT-R²_OS, MCS, BH, Romano–Wolf), HAR-RV-X, forecast combination, economic value, power statement. | Every forecasting claim carries a DM or CW p-value and a multiple-testing-corrected verdict. |
| **6. Cross-section & events** | Block D + Block E. | Exposure-gradient result across the break; event-study CARs; short-sample attack refinement. |
| **7. Robustness** | Classification-rule sensitivity, alternative dictionaries, alternative shock orderings, placebo dates, subsample stability, alternative market models. | Robustness matrix; every headline either survives or is explicitly demoted. |
| **8. Writing** | Chapters per §9. | Draft. |
| **9. Final validation** | Re-run end-to-end from raw; verify every number in the text against an output file. | Reproducibility log. |

### Chapter structure (§9)

1. Introduction — whose perception is priced?
2. Related literature (anchored on Caldara–Iacoviello and Bondarenko et al.)
3. Institutional background: the conflict, the media ecosystems, the defence
   sector re-rating
4. Data
5. **Measuring geopolitical risk perceptions** (the methodology chapter that
   answers comment #3)
6. **Stylized facts** (comment #2)
7. Dynamic responses (Block B)
8. Out-of-sample predictability and market efficiency (Block C, comment #4)
9. Cross-section and the invasion event (Block D)
10. Realized intensity: the attack-data refinement (Block E, comment #1)
11. Robustness
12. Conclusion

---

## 9. Honest assessment of the odds

| Result | Probability | Why |
|---|---|---|
| The ecosystems differ measurably and behave differently around Feb 2022 (SQ1) | **very high** | Different corpora, different incentives, a censorship wedge; and unlike v1 these are genuinely different populations. Delivers Chapters 5–6 regardless of everything else. |
| Significant contemporaneous/short-horizon response of defence vol to perception shocks (SQ2) | **high** | Already found at index level even on the weak v1/v2 data (GPR_THREAT → BSHIELDT vol, p<0.001); with 3× the sample and better measurement it should strengthen. |
| Local-language indices carry information English-language ones do not, in equities (the headline) | **moderate** | Strong theoretical prior + a JIE paper finding it for Russian macro. The risk is the opposite: Western investors plausibly *only* read Western media, so EN may dominate — which is itself a clean, interpretable, publishable finding ("markets price the Western narrative, not the local one"). **Either direction is a result**, which is why this is the right headline to bet on. |
| Threat dominates act, and differently by ecosystem (SQ4) | **moderate–high** | Supported by the v2 preliminary GPR evidence and by the R1 build-up period being pure threat. |
| Positive, significant, multiple-testing-robust OOS return predictability (SQ3) | **low–moderate** | Daily return predictability is hard everywhere. But R²_OS + CW + combination + economic value is a far more sensitive toolkit than MAE, and the sample is 3× larger. A modest positive is now plausible where before it was not. |
| Exposure gradient across the Feb-2022 break (SQ5) | **moderate** | Untested — v2's null was measured only in the attrition regime where there was no repricing. |

**Overall:** this design has *at least two* chapters (5–6) that are secured by
construction, a likely-positive response chapter, and a headline question whose
*both* answers are interesting. That is a materially better risk profile than v1
(which staked everything on one forecasting result) and than v2 (whose
centerpiece was already falsified). It also requires no topic change and reuses
every existing pipeline.

---

## 10. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| BigQuery `gkg_partitioned` lacks translingual records | medium | Verify on day 1 of Phase 2; fall back to bulk download (Route 2), which is confirmed available and sized. |
| Ukrainian-language volume is thin pre-2022 | medium-high | Measured: ~18–94 records per 15-min slice. Use **source-country UA (any language)** as primary and language as a within-country split; aggregate weekly for the pre-war regime if daily counts are too noisy; report the count series so thinness is visible, not hidden. |
| Bloomberg indices unavailable before 2020 | high (confirmed) | Free long-history basket (§4.3), validated against Bloomberg on the 2020–2026 overlap. |
| GDELT coverage drift over 11 years contaminates volume series | high | Always use **shares** of each ecosystem's total daily output, never raw counts; include year effects; show the raw counts in the appendix. |
| Machine-translation quality varies by language and over time | medium | Report results on native-language dictionaries as primary; the tone score is GDELT's own and is applied consistently; run a subsample check against hand-read articles. |
| The invasion break dominates everything (a single event drives all identification) | medium | Report with and without R2; report R0∪R1-only estimates; use LPs on *shocks* rather than levels. |
| Scope creep — this is more work than v1 | high | Phase gate at the end of Phase 2. Blocks C–E are all *reuse* of existing v1 code. Blocks A–B are new but small. |

---

## 11. Decisions needed before Phase 1

1. **Sample start:** 2015-02 (Route 1/2, full translingual) vs 2017-01
   (Route 3, DOC API only). *Recommendation: target 2015-02, but produce the
   2017+ version first as a fast proof of concept.*
2. **Bloomberg access:** is a terminal still available to re-pull WAERLST /
   BSHIELDT from 2015? This determines whether the free basket is primary or a
   robustness check.
3. **Headline framing:** "whose perception is priced" (recommended) vs keeping
   the v1 forecasting framing with a longer sample. The former is more novel,
   better anchored in the cited literature, and does not depend on a
   predictability result landing.
4. **v2's contemporaneous-response work:** fold it into Block B/D as a
   short-sample robustness section rather than running it as a separate project.
   *Recommendation: fold in.*
5. **What to send the supervisor now:** recommendation is a short memo containing
   the measurement diagnosis (§1.2), the sample-extension plan (§4.1), and the
   revised question (§2.1), asking for approval before the ~2-week data build.
