# Decision Log

This file records all important methodological decisions for the thesis project.
Any AI agent or researcher must append new decisions here using the template below.

**Template** (from Section 19 of the research plan):

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

---

## 2026-06-28 — Delegate GPU and heavy-compute tasks to Google Colab

**Decision:**  
Use Google Colab (Pro subscription) for GPU-intensive and high-RAM tasks: GDELT article-level extraction (Phase 3), near-duplicate deduplication (Phase 3), multilingual transformer inference (Phase 4), and optional GARCH refitting / hyperparameter search (Phases 6–7). Google Drive serves as the shared storage bridge between Colab and local.

**Reason:**  
Phase 3 requires hundreds of GDELT API calls (hours of wall-clock time) and MinHash/LSH deduplication on 500K–2M articles (high RAM). Phase 4 requires scoring 500K–2M articles with a multilingual transformer (GPU needed — hours on CPU, minutes on T4). These tasks exceed typical laptop resources. Colab Pro provides T4/A100 GPUs, 32 GB RAM, and stable network.

**Alternatives considered:**  
- Run everything locally (rejected: transformer inference on CPU would take days; deduplication may OOM).
- Use a dedicated cloud VM (rejected: Colab Pro is simpler and already available).
- Use Kaggle GPUs (rejected: Colab Pro has better GDrive integration and longer sessions).

**Consequences:**  
- Colab notebooks with `colab_` prefix are stored in `notebooks/`.
- Colab-specific dependencies (transformers, torch, datasketch) are separated in `requirements.txt`.
- Intermediate outputs are saved to Google Drive as Parquet, then downloaded to local `data/interim/`.
- Phases 1, 2, 5, and 8 run locally only.
- All Colab runs must record runtime type, Python version, and package versions for reproducibility.

**Revisit condition:**  
If a local GPU becomes available or if Colab session limits become prohibitive.

---

## 2026-06-30 — Phase 4 two-tier approach: GDELT tone now, transformer after milestone

**Decision:**  
Split Phase 4 into two tiers. Tier 1 uses GDELT tone fields (already available from Phase 3) as the core multilingual sentiment/threat measure — no further work needed. Tier 2 (transformer enhancement) is deferred until after the first analytical milestone (§25: after Phase 6 produces the common out-of-sample forecast table). Manual article labeling (500+ articles across Ukrainian/Russian/English) starts now in parallel.

**Reason:**  
The GKG bulk data has no article text — only metadata and pre-computed tone fields. Transformer scoring requires fetching titles via DOC API (separate sample) and is not on the critical path. GDELT tone fields satisfy the minimum viable thesis requirement (§4.2). Per §25, transformer features should only be added after the first milestone. Per §18 priority order, NLP features are priority #8 — after baselines (#6) and ablation forecasts (#7).

**Alternatives considered:**  
- Zero-shot classification on all 11.4M GKG articles (rejected: no text available; zero-shot with English labels on non-English text is methodologically weak).
- Re-extract all articles via DOC API with titles (rejected: ~9 hours API time; creates inconsistent parallel dataset; not on critical path).
- Skip transformer entirely (rejected: §8.6 requires transformer evaluation; Tier 2 will address this after milestone).

**Consequences:**  
- Phase 5 and Phase 6 proceed using GDELT tone fields as the NLP measure.
- First milestone is reached without transformer features.
- After milestone: fine-tune `xlm-roberta-base` on labeled sample → score ~67K articles → re-run forecasts with enhanced N features.
- Manual labeling starts now (parallel human work, ~1–2 days).

**Revisit condition:**  
If GDELT tone fields prove insufficient for the thesis committee, escalate Tier 2 priority.

---

## 2026-06-28 — WAERLST as main financial outcome

**Decision:**  
Use Bloomberg `WAERLST` (global aerospace & defense index) as the primary financial outcome.

**Reason:**  
`WAERLST` provides broad global coverage of aerospace and defense firms and is available via Bloomberg. It is the most directly relevant equity index for studying defense-sector risk pricing.

**Alternatives considered:**  
- A single firm-level portfolio (rejected: index-level is the core study).
- A European-only defense index as primary (rejected: reserved for robustness).
- `BSHIELDT` as primary (rejected: reserved as additional robustness check).

**Consequences:**  
All primary return and volatility forecasts use `WAERLST`. Robustness uses a European index and `BSHIELDT`.

**Revisit condition:**  
If `WAERLST` is found to have severe data quality issues or insufficient history after the Bloomberg audit.

---

## 2026-06-28 — Daily frequency as main frequency

**Decision:**  
Use daily frequency as the main modeling frequency.

**Reason:**  
Attack data and news data are available at daily resolution. Daily financial data are confirmed from Bloomberg. Intraday data are not assumed to be available.

**Alternatives considered:**  
- Weekly frequency (rejected: loses too much daily variation in attacks and news).
- Intraday frequency (rejected: not confirmed to be available; reserved as optional extension).

**Consequences:**  
All core models, features, and evaluation operate at daily frequency. Intraday and HAR-RV are optional extensions.

**Revisit condition:**  
If genuine intraday data become available and the core thesis is already complete.

---

## 2026-06-28 — Predictive rather than causal framing

**Decision:**  
Frame the study as a predictive forecasting study, not a causal identification study.

**Reason:**  
The research question is about incremental out-of-sample predictive information, not causal effects. A credible causal identification strategy is not available given the data and design.

**Alternatives considered:**  
- Causal framing with event-study design (rejected: event studies are not the main method).
- Causal framing with instrumental variables (rejected: no credible instruments).

**Consequences:**  
Use predictive language only. Avoid "causes", "leads to", "has a causal effect on" unless a separate identification strategy is developed.

**Revisit condition:**  
If a credible causal identification strategy is developed and documented.

---

## 2026-06-28 — HAR-RV is optional

**Decision:**  
Treat HAR-RV (Heterogeneous Autoregressive Realized Volatility) as an optional extension, not a requirement.

**Reason:**  
Long historical intraday data are not assumed to be available. HAR-RV requires realized volatility from intraday bars. The thesis must be defensible without it.

**Alternatives considered:**  
- Require HAR-RV (rejected: would block thesis if intraday data unavailable).
- Use HAR-RV as the main volatility model (rejected: same reason).

**Consequences:**  
Volatility target follows a hierarchy: intraday → realized volatility; OHLC → range-based; close-only → absolute/squared returns + GARCH. HAR-RV is only pursued if intraday data exist and the core thesis is complete.

**Revisit condition:**  
If genuine intraday data are confirmed available during the Bloomberg audit.

---

## 2026-06-28 — One principal gradient-boosting model

**Decision:**  
Use one principal gradient-boosting algorithm (LightGBM or XGBoost), not both as equal main models.

**Reason:**  
The daily sample is relatively small. Using multiple algorithms as equal main models increases complexity and the risk of false positives from multiple comparisons.

**Alternatives considered:**  
- Both LightGBM and XGBoost as equal main models (rejected: unnecessary complexity).
- Random forest as main model (rejected: gradient boosting generally better for tabular data).
- Deep learning as main model (rejected: reserved as optional extension).

**Consequences:**  
Select either LightGBM or XGBoost after initial benchmarking. The other may be used for robustness only.

**Revisit condition:**  
If both algorithms give materially different results and a reviewer requests both.

---

## 2026-06-28 — Source groups based on geography and language

**Decision:**  
Classify GDELT news sources into Ukrainian, Russian, and Western information environments using both source geography and original language.

**Reason:**  
Language alone does not determine political viewpoint. A Russian-language Ukrainian source should not be automatically placed in the Russian information environment.

**Alternatives considered:**  
- Language-only classification (rejected: conflates language with viewpoint).
- Geography-only classification (rejected: misses important language-based framing differences).

**Consequences:**  
Source classification uses both dimensions. A Russian-language Ukrainian source is classified by geography first, with language as a secondary attribute.

**Revisit condition:**  
If a more nuanced classification scheme is needed and validated.

---

## 2026-06-28 — Index-level core; firm-level extension

**Decision:**  
Keep the index-level study as the core. Treat firm-level constituent analysis as an optional extension.

**Reason:**  
Firm-level analysis requires point-in-time constituents, membership dates, weights, and defense-revenue data — all of which introduce survivorship and look-ahead bias risks. The index-level study is feasible and defensible on its own.

**Alternatives considered:**  
- Firm-level as core (rejected: too many data requirements and bias risks).
- Both as equal pillars (rejected: firm-level should not block the core).

**Consequences:**  
Firm-level work begins only after the index-level thesis is complete and requires point-in-time constituents.

**Revisit condition:**  
If point-in-time constituent data are readily available and the core thesis is complete.

---

## 2026-06-28 — No event study as main design

**Decision:**  
Do not use event studies as the main research design. Use out-of-sample forecasting.

**Reason:**  
Event studies focus on a small number of event dates and cannot test incremental predictive information continuously. The thesis contribution relies on daily signals and strict out-of-sample evaluation.

**Alternatives considered:**  
- Event study as main design (rejected: loses the continuous daily signal contribution).
- Event study as complement (acceptable but not required).

**Consequences:**  
The main design is expanding-window out-of-sample forecasting. Event studies may be mentioned as context but are not the core method.

**Revisit condition:**  
Not applicable — this is a fundamental design choice.

---

## 2026-06-28 — Salvage assessment of thesis_old_try before Phase 1

**Decision:**  
Audit `thesis_old_try/` to identify reusable raw data, code patterns, and reference material before deleting the folder. Defer deletion until salvage is complete.

**Reason:**  
The `thesis_old_try/` folder contains Bloomberg raw data (WAERLST, BSHIELDT), UAF attack data, GPR index, GDELT topic counts, ACLED data, SIPRI exposure data, and 15 processing scripts. These may contain reusable raw data and code patterns. However, the old attempt was a causal firm-level panel regression study, which is fundamentally different from the new predictive index-level forecasting design. Raw data may be reusable; old methodology and results are not.

**Alternatives considered:**  
- Delete `thesis_old_try/` immediately (rejected: would lose potentially valuable raw data).
- Keep `thesis_old_try/` indefinitely without audit (rejected: creates confusion and clutter).
- Copy everything to new structure without assessment (rejected: would import incompatible processed data and methodology).

**Consequences:**  
A new agent session will audit the folder and produce a salvage plan in `docs/thesis_old_try_audit.md`. Only after salvage is executed will the folder be deleted.

**Revisit condition:**  
After salvage is complete, verify nothing needed was lost before deletion.

---

## 2026-06-28 — Conservative timing: day t information predicts t+1

**Decision:**  
Use the conservative timing rule: information available through the end of day `t` predicts the market outcome on trading day `t+1`.

**Reason:**  
Ukrainian overnight attacks and morning reports may overlap with European trading hours. The conservative rule reduces ambiguity around publication times and overnight attacks.

**Alternatives considered:**  
- Same-day prediction with pre-market cutoff (rejected as primary: timing ambiguity; reserved as secondary).
- t+2 or longer (rejected: loses the main one-day-ahead forecast horizon).

**Consequences:**  
All features must have an "available at" timestamp ≤ end of day `t`. The primary forecast horizon is one trading day ahead.

**Revisit condition:**  
If precise timestamps allow a reliable pre-market cutoff for a secondary design.

---

## 2026-06-28 — Return units: percent, not decimal

**Decision:**  
All `r_*` columns in `data/processed/financial/financial_daily.parquet` are stored in **percent (%)**, not decimal.  For example, `r_ITA` daily std ≈ 1.67 means 1.67 %, not 0.0167.

**Reason:**  
Matches Bloomberg's terminal display convention and makes the columns human-readable without a multiplier.  The data dictionary and all downstream code must be aware of this convention to avoid unit-mismatch bugs (e.g., Sharpe ratios inflated by 100×).

**Alternatives considered:**  
- Store as decimal (rejected: easy to misread on screen, easy to forget to scale up in plots).
- Store both percent and decimal columns (rejected: doubles column count for negligible benefit).

**Consequences:**  
- All Phase 5-7 code that consumes `r_*` columns must treat them as percent.
- Any standardised decimal-return library (e.g. `empyrical`, `quantstats`) must divide by 100 first.
- Plots and tables should label axes as "Return (%)".

**Revisit condition:**  
If a downstream model absolutely requires decimal input and the conversion overhead becomes a recurring friction.

---

## 2026-06-28 — GKG country codes: dual mapping (ISO + GKG aliases)

**Decision:**  
`config/country_groups.yaml` maps **both** ISO 3166-1 alpha-2 codes (e.g. `UA`, `RU`, `DE`) **and** GKG-specific aliases (e.g. `UP`, `RS`, `GM`, `UK`, `EI`, `IS`, `JA`, `KS`) to the same source group.

**Reason:**  
GDELT GKG uses non-ISO codes in its `LOCATIONS` field for several countries (Ukraine = `UP` not `UA`, Russia = `RS` not `RU`, etc.).  A single-code mapping would miss every Ukrainian and Russian article.

**Alternatives considered:**  
- Normalise GKG codes to ISO before classification (rejected: adds a translation step and risks lossy mapping for codes with no ISO equivalent).
- Reject articles with non-ISO codes (rejected: would discard 100 % of Ukrainian and Russian coverage).

**Consequences:**  
- The hybrid classifier in `src/data/gdelt.py::classify_source_enhanced` handles both codes transparently.
- The country lookup is done in upper-case after `.str.strip()`.

**Revisit condition:**  
If GDELT changes its country-code scheme in a future GKG version.

---

## 2026-06-30 — Standardize `date` as the first regular column across all daily tables

**Decision:**  
All Phase 1-3 daily tables use a consistent schema: **`date` is the first regular column** (not the index).  `news_daily_enriched.parquet` already follows this convention after the Phase 3 gap-closure (`scripts/phase3_close_gaps.py`).  `financial_daily.parquet` and `attack_daily.parquet` still use `date` as the index and **will be re-written by Phase 5**.

**Reason:**  
Mixed index-vs-column conventions cause silent bugs in `merge()` and `join()` operations.  Standardising now (before any merge code is written) prevents a class of subtle errors that would be hard to debug later.

**Alternatives considered:**  
- Keep the index convention for all three (rejected: less pandas-idiomatic; harder to read CSV exports).
- Use a multi-index (`date`, `index_id`) (rejected: only one asset per row at the moment, multi-index would be overkill).

**Consequences:**  
Phase 5 (`src/data/merge.py`) will include a `standardize_date_column()` helper that does `df.reset_index()` if `date` is the index, then asserts `date` is the first column.

**Revisit condition:**  
Never — this is a permanent schema convention.

---

## 2026-06-30 — Automated precision check replaces manual audit

**Decision:**  
Replace the planned 400-article manual labelling audit (`data/processed/news/manual_precision_audit_enriched.csv`) with an **automated agreement check** against the high-confidence domain→country mapping.  The manual CSV is retained in the repo as a reference but is **not blocking** the thesis.

**Reason:**  
- The manual audit would label only 400 articles, providing weak statistical power.
- An automated check on 11 M+ articles with a high-confidence subset (6,480 domains, 31 % of total) provides more reliable precision estimates and runs in <1 min.
- The audit dataset's `title` column is empty (GKG bulk has no title), making manual labelling by URL alone significantly harder.

**Alternatives considered:**  
- Manual labelling of 400 articles (rejected: 2-4 h of human work, lower statistical power).
- Skip precision estimation entirely (rejected: needed to defend the classifier choice in the thesis).
- Hybrid: automated + spot-check 50 per group (~2 h) (deferred: can be added in Phase 8 robustness if needed).

**Consequences:**  
- `data/processed/news/auto_precision_report.md` is generated by `scripts/phase3_close_gaps.py` step 4.
- Per-method and per-group precision is reported (overall 85.4 %).
- The thesis documents the caveat that the precision is agreement with a data-driven proxy, not a hand-labelled ground truth.

**Revisit condition:**  
If a true labelled dataset (e.g., 50 articles per group hand-classified) becomes available, replace the proxy with the true estimate and report both for transparency.

## 2026-07-01 — XGBoost as principal ML algorithm

**Decision:** Use XGBoost (not LightGBM) as the principal gradient-boosting algorithm for Phase 7 return forecasts.

**Reason:** XGBoost has a deterministic early-stopping API, first-class SHAP TreeExplainer support, and a mature codebase for tabular financial data. Decision log 2026-06-28 requires one principal algorithm; LightGBM is a documented robustness alternative but is not implemented.

**Alternatives considered:**
- **LightGBM** — slightly faster training, comparable accuracy on small financial datasets. Rejected as the principal algorithm because SHAP integration is less mature.
- **Both as co-equal** — explicitly forbidden by the 2026-06-28 decision.

**Consequences:** `src/models/ml.py` implements `XGBoostForecaster`; `requirements.txt` adds `xgboost>=2.0`. The thesis Methodology chapter must justify the choice and acknowledge LightGBM as the robustness alternative.

**Revisit condition:** If XGBoost MAE on F-set is > 1.3× Ridge MAE in the first run, swap to LightGBM and re-run. Document the swap in the audit doc.

## 2026-07-01 — Time-series CV grid search for hyperparameter tuning

**Decision:** Use a pure-Python grid search (216 combinations × 3 expanding-window folds with 5-day embargo) for XGBoost hyperparameter tuning, run once before the OOS engine and saved to `outputs/model_objects/xgb_best_params.csv`.

**Reason:** Reproducible (no random sampling, no Optuna study to log), defensible in thesis text ("exhaustive grid over 6 hyperparameters"), and the total cost is bounded (~6,480 XGBoost fits × ~1s = ~110 min on Colab Pro CPU). Decision log 2026-06-28 permits TS-CV tuning as a Phase 7 extension; this is that extension.

**Alternatives considered:**
- **Fixed defaults from YAML** — fastest, but wastes the Master's plan §11.2 call for CV tuning.
- **Optuna Bayesian search** — better for high-dim grids, but adds dependency, reproducibility concerns (study must be logged), and is not strictly necessary for a 6-dim grid.

**Consequences:** `src/models/ml_tuning.py` implements `time_series_cv_splits`, `grid_search_xgb`, and `tune_per_info_set`. The CLI is `python scripts/phase7_tune.py`. The OOS run uses the cached best params via `--tuned-params`.

**Revisit condition:** If the first run shows XGBoost MAE is systematically worse than Ridge on F (e.g., > 1.2× across all info sets), the grid may be missing the optimum — switch to Optuna. Document the swap.

## 2026-07-01 — GARCH-X included in Phase 7 (deferred from Phase 6)

**Decision:** Include GARCH-X variants (3 GARCH-family + exogenous regressors in the ARX mean equation) as a Phase 7 deliverable. The Phase 6 audit §7 listed this as "Phase 7+ extension".

**Reason:** GARCH-X directly tests whether attack/news features add value to the *volatility* forecast — a separate research question from the ML returns story. The `arch` package supports ARX + GARCH-family models via the `x=` parameter; h=1 uses standard forecast, h>1 uses the same analytic-h path (mean exog doesn't affect the variance equation under joint MLE, so the h-step path is unchanged).

**Alternatives considered:**
- **Defer to Phase 8** — delays the vol-feature story by one phase.
- **ML for vol** — explicitly out of scope per decision log 2026-06-28 (one principal boosting algorithm).

**Consequences:** `src/models/garch.py` adds `GARCHXForecaster`. The expanding-window engine's vol-model code path is extended (non-breaking) to pass `X_exog_train` and `X_exog_horizon` if the spec has a `garch_x_info_set` attribute. The CLI flag `--garch-x-info-set` (default "F") controls which info set's columns feed the ARX mean.

**Revisit condition:** If `arch` v6.2 raises on ARX + the chosen vol model, fall back to the two-step approach (fit ARX with GARCH vol, take residuals, fit univariate GARCH on residuals). Document the failure mode in the audit doc.

## 2026-07-01 — Phase 7 runs on Colab Pro with data from Google Drive

**Decision:** Phase 7 compute (tuning, OOS, SHAP) runs on **Colab Pro CPU**. The model matrix is read from and outputs are written directly to Google Drive folder `WarSignalsThesis_Data/`. Local laptop is used only for code editing, git, and `rclone` sync. The `rclone` tool is local-only (not available in Colab).

**Reason:** The TS-CV grid search (6,480 XGBoost fits) is the compute bottleneck; Colab Pro CPU is 3-4× faster than the local laptop, with 35 GB RAM and 24-h sessions (the full Phase 7 run is ~2-2.5 hours). All data already lives in Drive per the Phase 0-6 data-sharing architecture; Colab can read directly from Drive.

**Alternatives considered:**
- **Local execution** — 3-4× slower; would push the tuning step to ~5-6 hours.
- **Colab free tier** — 12.7 GB RAM, may OOM on the full grid with all 6 hyperparameters.

**Consequences:**
- New local pre-Colab step (Phase 7.0): `rclone copy` the model matrix to Drive (one-time, ~2 s).
- New local post-Colab step (Phase 7.7): `rclone copy` the outputs back from Drive, commit, push.
- New Colab notebook: `notebooks/07_ml_models.ipynb` with the strict Colab pattern (mount Drive → clone+pull → sanity check → install → run → verify).
- New memory note: `/memories/repo/phase7_colab_first.md` documents the workflow.
- `docs/data_sharing.md` extends the path-mappings table to include `data/processed/` and `outputs/model_objects/`.

**Revisit condition:** If Colab Pro is unavailable, run locally with the `--quick` flag (4 configs × 2 folds) for the headline run, then expand the grid for the audit-quality run.

## 2026-07-02 — Target hierarchy restructured around real Bloomberg WAERLST/BSHIELDT series

**Decision:**
Real Bloomberg daily series (`WAERLST Index.xlsx`, `BSHIELDT Index.xlsx`; PX_LAST +
PX_VOLUME, 2020-01-01 → 2026-06-29, close-only, no OHLC/TR column) replace the noisy
mcap-weighted reconstruction as the basis for the primary and robustness targets:
- **Primary:** `r_WAERLST` (real Bloomberg global aerospace & defense index).
- **Robustness (European, war-exposed):** `r_BSHIELDT` (real Bloomberg).
- **Optional (US robustness):** `r_ITA` (yfinance ETF proxy) — kept unchanged.
- **Demoted:** `r_WAERLST_recon` — kept as a lagged feature only, no longer a modeling target.

**Reason:**
Phase 1 used `r_ITA` as primary and `r_WAERLST_recon` as secondary because the actual
Bloomberg index-level series were not yet delivered (only constituent-level prices with
weights; the mcap-weighted reconstruction was too noisy for WAERLST, ρ=0.15 vs ITA,
std 2.4×). The real series are now available and verified clean: 1,694 rows each, 0
NaNs, 0 gaps >4 days, std 1.51% (WAERLST) / 1.77% (BSHIELDT), comparable to ITA
(~1.7%). WAERLST is also the literal thesis-title outcome, and BSHIELDT (European
defense) is the index most exposed to the Russia-Ukraine war, making it the most
likely place for the attack/news signal (H1-H3) to appear and the natural H6
(geographic robustness) comparison against WAERLST/ITA.

**Alternatives considered:**
- **Keep ITA primary, add real indices as robustness only** — least disruptive but
  under-uses the real data and keeps a proxy as the headline result against the
  thesis title.
- **Make BSHIELDT primary** — highest chance of finding signal (most war-exposed) but
  departs from the thesis title framing (WAERLST = global aerospace & defense).

**Consequences:**
- `src/data/financial.py`: new `load_bloomberg_index_xlsx()` for the single-index
  sheet layout (distinct from the constituent `load_bloomberg_xlsx()`); real returns
  `r_WAERLST`, `r_BSHIELDT`; volume features (`logvol`, `vol_z30`, `dvol`) with
  zero/holiday-volume guards (`log1p`, masking).
- `src/features/build_model_matrix.py`: `PRIMARY_TARGET = "r_WAERLST"`, robustness
  targets `r_BSHIELDT` and `r_ITA`; `target_r_WAERLST_recon_t1` retired from the
  target set (kept as `r_WAERLST_recon_lag1` feature).
- `src/models/{horse_race,baselines,garch,ml_tuning,ml_explain}.py`: target tuples
  updated from `("r_ITA", "r_WAERLST_recon")` to the new hierarchy.
- Phases 6 and 7 re-run on the new targets, both h=1 and h=5. Close-only data
  (verified — no OHLC/TR fields) confirms the returns-based volatility path
  (abs/squared returns + GARCH) already implemented; no range-based estimator is used.
- `docs/`, `README.md` updated to remove "ITA primary / recon secondary" language.

**Revisit condition:**
If the real WAERLST/BSHIELDT series are later found to be price-return rather than
total-return (contradicting the Phase 1 TR assumption), or if Bloomberg later delivers
genuine index-level OHLC/intraday data, revisit the volatility-target choice.

---

## 2026-07-02 — Code-level rename to the new target hierarchy (step 1 of 2)

**Decision:**
Completed the code-level rename implementing the 2026-07-02 target hierarchy restructure
(`r_WAERLST` primary, `r_BSHIELDT`/`r_ITA` robustness, `r_WAERLST_recon` demoted to
feature). No data files were rebuilt — `data/processed/model_matrix.parquet` on disk
still has the old column names until a second agent runs the Phase 5 rebuild.

**Reason:**
Every hardcoded reference to the old primary/secondary (`r_ITA`/`r_WAERLST_recon`)
pattern needed updating to the new 3-target hierarchy before the rebuild can produce a
matrix consumers expect. A known info-set bug (N never unioned with F) was also fixed
per the real_index_integration_plan §5 gate.

**Alternatives considered:**
- Keep a strict 2-target (primary/secondary) API and bolt BSHIELDT on separately —
  rejected; the other Phase 6/7 modules (`horse_race.py`, `ml_tuning.py`, etc.) already
  used an arbitrary-length `targets` tuple, so generalizing `build_model_matrix.py` to
  match was the minimal, consistent change.

**Consequences:**
- `src/features/build_model_matrix.py`: `PRIMARY_TARGET = "r_WAERLST"`;
  `ROBUSTNESS_TARGETS = ("r_BSHIELDT", "r_ITA")`; `TARGET_COLS` tuple added.
  `build_targets()`/`build_model_matrix()` signatures changed from
  `primary_target`/`secondary_target` to `primary_target`/`robustness_targets`
  (breaking change for any caller passing `secondary_target=`).
  `lag_features()`'s special-case re-lag logic for the demoted `r_WAERLST_recon`
  source now keys off the literal column name instead of `SECONDARY_TARGET`.
  `build_info_sets()`: `r_WAERLST_recon_lag1` removed from `base_excludes` (it is no
  longer a target source, so excluding it was leakage-prevention logic applied to the
  wrong column) and added to F's include list instead. **N-set bug fix:**
  `out["N"] = sorted(set(out["F"]) | set(out["N"]))` added so N = F + news (previously
  N was news-only, coincidentally sized like F). PN's nesting was also extended to
  `P | N | PN_own` so PN = F + P + N as documented (previously PN = P + per-query/group
  news only, missing N's plain news columns) — a deliberate extension beyond the literal
  N-fix ask, flagged here for the rebuild agent.
  F's include list gained `r_WAERLST_lag1/lag2/lag5`, `abs_r_WAERLST_lag1`,
  `r_WAERLST_recon_lag1`, and volume features (`logvol_/vol_z30_/dvol_` ×
  `{WAERLST,BSHIELDT}_lag1`) — declared now (inert until the columns exist), since
  `build_info_sets` filters by existence. Only `r_WAERLST_lag1`/`r_BSHIELDT_lag1`
  materialize for free via the existing raw→lag1 path; `r_WAERLST_lag2/lag5`,
  `abs_r_WAERLST_lag1`, and all volume features require extending
  `src/features/financial_features.py` (out of scope for this rename step — the
  rebuild agent must add them, mirroring the existing `r_ITA_lag2/lag5`/`abs_r_ITA`
  pattern and wiring in `compute_index_returns_and_volume` from `financial.py`).
- `src/models/horse_race.py`, `ml_tuning.py`, `ml_explain.py`, `expanding_window.py`,
  `scripts/{phase6_run_baselines,phase7_run_ml,phase7_tune}.py`: target-tuple/CLI
  defaults changed from `("r_ITA", "r_WAERLST_recon")` to
  `("r_WAERLST", "r_BSHIELDT", "r_ITA")`.
- `scripts/phase5_leakage_audit.py`: `TARGET_COLS` and the headline audit target
  updated to `target_r_WAERLST_t1`.
- `scripts/phase5_data_dictionary.py`, `phase5_descriptive_stats.py`,
  `phase5_build_model_matrix.py`: metadata/labels updated for the new hierarchy;
  `.attrs["secondary_target"]` replaced by `.attrs["robustness_targets"]` (list).
- `config/model_config.yaml`: `targets.secondary` replaced by `targets.robustness`
  (list).
- `docs/phase7_audit.md` §1.5: corrected from "N==F is by construction, not a bug" to
  documenting the actual fix, with a code snippet and a note that exact post-fix
  cardinalities are pending the Phase 5 rebuild.
- `src/features/load_model_matrix.py`: `validate_model_matrix_for_phase6` generalized
  to check all robustness targets, not just one secondary target.
- Test fallout fixed in the same commit (not a separate step): `tests/test_phase5_model_matrix.py`,
  `tests/test_phase6_baselines.py`, `tests/test_phase7_ml.py` updated for the new API
  and new (correct) info-set semantics (`r_WAERLST_recon_lag1` now allowed in F; target
  column count 8→12 per fixture). `TestPhase7RealData::test_real_mm_info_sets` (reads
  the real, still-stale parquet) marked `xfail` with a precise reason: its hardcoded
  cardinalities (F=26, N=26, PN=78) encode the pre-fix bug and will NOT be restored by
  the rebuild — they need to be recomputed from a fresh `info_set_cardinality.csv`,
  not just re-run.
- `src/data/financial.py` and `src/models/garch.py` were NOT touched (owned by parallel
  agents per task scope). No data files were rebuilt; `data/processed/model_matrix.parquet`
  still has old columns until the rebuild step runs.

**Revisit condition:**
None — this is a mechanical rename step. Revisit only if the Phase 5 rebuild agent
finds the new `build_model_matrix()` API awkward to call from `phase5_build_master.py`
or needs a different `robustness_targets=None` convention.

## 2026-07-02 — Real-index model matrix rebuilt; GARCH-X-in-mean found numerically non-viable

**Decision:**
1. `data/processed/{daily_master,feature_matrix,model_matrix}.parquet` rebuilt via
   `scripts/phase5_overlay_real_indices.py` (new) + `scripts/phase5_build_model_matrix.py`,
   overlaying the real WAERLST/BSHIELDT series onto the cached `daily_master.parquet`
   (the original raw Bloomberg constituent files and `indexes.xlsx` market-benchmark
   source are unavailable locally or on Drive — confirmed absent everywhere — so the
   already-computed control columns, SPX/VIX/Brent/EURUSD/MSCI_World, were reused
   rather than re-derived or fabricated). `src/features/financial_features.py` extended
   to compute `r_WAERLST_lag1/2/5`, `abs_r_WAERLST`, and `r_BSHIELDT_msadj` (real,
   mirroring the old reconstruction's msadj convention); `vol_5d`/`vol_20d` switched
   from `r_ITA`-based to `r_WAERLST`-based (the new primary target) per this session's
   target restructure. `config/paths.yaml` created locally from the example (was
   missing) with a `feature_matrix` key added (missing from the example).
2. Phase 5 leakage audit: 0 flags across 118 features (was 98). N info-set cardinality
   fix confirmed working (N=63, was N=F=26 — the redundancy bug is resolved).
3. Phase 6 baselines re-run on the real target hierarchy — clean, expected results
   (r_WAERLST MAE ~0.95 at h=1, comparable to ITA's prior ~1.05; the "features don't
   help returns" null holds as predicted, OLS/Ridge degrade with more features, AR1/
   historical_mean remain best; plain GARCH/GJR/EGARCH numerically sane).
4. **GARCH-X-in-mean (ARX exogenous regressors) found to be numerically non-viable on
   this sample.** Two real bugs were found and fixed in `src/models/expanding_window.py`
   during this session: (a) the GARCH source column itself was included in its own
   exogenous regressor set (perfect self-fit, collapsed `omega`→~0, variance
   forecast→~1e-27); (b) exogenous regressors (VIX levels, days_since_invasion, etc.)
   were passed unscaled to `arch_model` while `y` is internally rescaled, destabilizing
   the ARX-mean optimizer. Both fixed (exclude source column; standardize exog using
   train-block-only mean/std, matching the training-only-preprocessing rule). After the
   fix, GARCH-X variants are genuinely distinct (previously byte-identical due to both
   collapsing to the same degenerate state) — but a residual `arch`-package ARX-mean
   optimizer instability remains, rooted in `src/models/garch.py` (explicitly out of
   scope for this fix). A point-in-time-safe degenerate-fold guard was added in
   `src/models/horse_race.py::_aggregate` (excludes folds whose variance forecast is
   >1000x or <0.001x the plain-GARCH forecast scale for the same target/horizon,
   counted in a new `n_degenerate` column) — deliberately using the plain-GARCH models'
   own contemporaneous forecast as the reference scale, NOT realized (future) variance,
   to avoid outcome-dependent sample selection. Result: **100% of `r_BSHIELDT` folds are
   degenerate for all 3 GARCH-X variants** (0 usable rows); `r_WAERLST`/`r_ITA` retain
   25-55% usable folds with QLIKE 4-6 (vs plain GARCH's 1.4-1.8) — a legitimate null/
   negative finding under `instructions.md`'s "a null result is valid" rule, not a bug
   to keep chasing without touching the off-limits GARCH-X mean-equation design.

**Reason:**
The target restructure (prior 2026-07-02 entry) required a data rebuild since
`financial_daily.parquet` never existed as a separate artifact on Drive (only merged
`daily_master`/`feature_matrix`/`model_matrix` were persisted). The GARCH-X
investigation was triggered by a smoke test showing all 3 GARCH-X variants producing
byte-identical benchmark rows post-target-rename — a red flag before trusting any
volatility results for H1.

**Alternatives considered (GARCH-X):**
- **Keep chasing full numerical stability** — would require editing `garch.py`'s
  ARX/rescale design, explicitly scoped out of this fix to avoid conflicting with the
  parallel target-rename work; the residual instability may be inherent to putting
  correlated financial regressors in an ARX mean equation at this sample size (500-1300
  obs) regardless of implementation.
- **Silently suppress/clip extreme QLIKE values** — rejected; would hide a genuine
  numerical failure rather than reporting it, violating the "no invented results" rule.
- **Use realized (future) variance to filter degenerate folds** — rejected by design;
  an earlier version of the guard did this and was caught as outcome-dependent sample
  selection (leakage-adjacent). The final guard uses only same-fold plain-GARCH output.

**Consequences:**
- `scripts/phase5_overlay_real_indices.py` (new), `src/features/financial_features.py`,
  `config/paths.yaml` (new), `tests/test_features_financial.py` updated (18 tests).
- `src/models/expanding_window.py`, `src/models/horse_race.py` — GARCH-X exog fixes +
  degenerate-fold guard; `tests/test_expanding_window.py` (new, 3 tests).
- `docs/phase7_audit.md` §4 and §7 (known limitations) must be updated to report the
  GARCH-X-in-mean null finding rather than a clean H1 volatility verdict; H1 should be
  assessed primarily via plain GARCH/GJR/EGARCH (all numerically sane) with attack/news
  features noted as testable only through the return-side XGBoost/Ridge horse race
  (P/PN/PNG info sets) for now.
- Full test suite: 437 passed, 2 pre-existing failures (missing
  `financial_daily.parquet`/`attack_daily.parquet` raw sources, confirmed unrelated to
  this session's changes via `git stash`), 1 documented xfail.

**Revisit condition:**
If a future session revisits `garch.py`'s ARX/rescale design specifically to fix the
mean-equation optimizer instability (e.g. switching to variance-equation exog, which
the original Phase 7 audit already flagged as the methodologically more direct test of
H1 but noted as unstable in the `arch` package API), or reduces exog dimensionality to
1-2 aggregate attack/news features instead of the full F info set, re-attempt GARCH-X
and update this finding.
