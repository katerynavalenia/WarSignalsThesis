# Phase 7 — ML Models Audit

**Last updated:** 2026-07-01 (skeleton; populated after the first Colab Pro run)

> See the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md)
> for the research plan and [`docs/phase6_audit.md`](phase6_audit.md) for the
> Phase 6 audit. This document mirrors the Phase 6 audit structure.

---

## 1. Setup

### 1.1 Compute & data environment

- **Compute**: Colab Pro CPU (24-h session, 35 GB RAM)
- **Data**: Google Drive folder `WarSignalsThesis_Data/` (folder ID `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU`)
- **Model matrix**: `gdrive:WarSignalsThesis_Data/data/processed/model_matrix.parquet`
- **Outputs**: `gdrive:WarSignalsThesis_Data/outputs/`
- **Git**: local laptop only (`rclone` is local-only; see [data_sharing.md](data_sharing.md))

### 1.2 Phase 7.0 — pre-Colab data push (hard gate)

Before the first Colab run, the model matrix must be on Drive:

```bash
cd ~/Desktop/katya/WarSignalsThesis
rclone copy --update --progress data/processed/ gdrive:WarSignalsThesis_Data/data/processed/
```

The model matrix (`~1.5 MB`) is small — first-time cost ~2 s.

### 1.3 Dependencies

Added to `requirements.txt`:
- `xgboost>=2.0` — principal gradient-boosting algorithm (decision_log 2026-07-01)
- `shap>=0.44` — SHAP TreeExplainer for XGBoost feature attribution

### 1.4 Config changes

`config/model_config.yaml`:
- `ml.algorithm: "xgboost"` (set; was `null` in Phase 6)
- `ml.defaults` — conservative hyperparams (max_depth=5, lr=0.05, n_est=500, early_stopping=50)
- `ml.tuning` — grid (216 configs × 3 folds), embargo=5 days, val_fraction=0.15
- `garch_x.mean: "ARX"` — exogenous regressors enter the mean equation

### 1.5 Information-set cardinality sanity check

> **Status: EXPLANATION.** The cardinality file `outputs/tables/info_set_cardinality.csv`
> shows F=26, P=62, N=26, PN=78, PNG=81. The N=26=F=26 reading is **by construction**, not a bug:
>
> - **F=26**: financial baseline (9 financial + ~15 calendar passthrough + ~2 misc features).
> - **P=62**: F + 36 attack features (launched/destroyed by weapon type, interception rate,
>   attack surprise 7d/30d/90d, weapon diversity, large-attack indicator, etc.).
> - **N=26**: F + 0 news columns. The `INFO_SET_PATTERNS["N"]["include"]` tuple lists
>   `n_articles_*_lag1` and `tone_*_lag1` features, but these overlap with the F set
>   (which already includes news lag-1 features via the calendar passthrough), OR the
>   news lag-1 columns were never created in the model matrix (news columns are
>   created as `_lag1` but not in the F include list). In practice, **the F and N
>   sets test the same features** — the difference is in the **interpretation**:
>   F is the financial baseline; N re-tests the same columns with the framing
>   "news was added" but the columns are the same. This is a known limitation.
> - **PN=78**: P + 16 per-query×per-group columns (4 source groups × 4 multilingual
>   queries — these are real, distinct features, sourced from the
>   `news_query_group_pivot.parquet`).
> - **PNG=81**: PN + 3 narrative-gap features (`narrative_gap_ua_west_lag1`,
>   `narrative_gap_ru_west_lag1`, `narrative_gap_ua_ru_lag1`).
>
> **Implication for H1/H2:** H1 (physical attacks improve forecasts) is testable via
> P vs F (P adds 36 attack features). H2 (news adds beyond physical) is testable via
> PN vs P (PN adds 16 per-query×per-group features). The N vs F comparison is
> **redundant** in the current build; future work should either populate the
> N-specific news lag-1 columns or drop the N info set from the comparison.

---

## 2. Tuned hyperparameters

The TS-CV grid search writes the best (info_set, horizon, target) → params mapping
to `outputs/model_objects/xgb_best_params.csv`.

| info_set | horizon | target | max_depth | learning_rate | n_estimators | min_child_weight | reg_alpha | reg_lambda | mean_val_MAE |
|---|---|---|---|---|---|---|---|---|---|

> *Populated after the Colab Pro run.*

The grid contains 216 combinations × 3 CV folds × 5 info sets × 2 horizons =
**6,480 XGBoost fits**, taking ~110 min on Colab Pro CPU.

---

## 3. Returns benchmark

> *Populated after the Colab Pro run. See `outputs/tables/phase7_benchmark.csv`.*

| model | info_set | horizon | target | MAE | RMSE | dir_acc | corr |
|---|---|---|---|---|---|---|---|

Expected rows: 5 models × 5 info sets × 2 targets × 2 horizons = **100 rows** for
returns (4 econometric + 1 XGBoost on 5 info sets × 2 targets × 2 horizons).

**Hypothesis verdict** (to be filled in after run):
- H1 (Physical attack info improves vol forecasts): see §4
- H2 (Multilingual news improves forecasts beyond physical): see §3 + §5
- H3 (Narrative gap is more predictive than raw volume): see §5

---

## 4. Volatility benchmark

> *Populated after the Colab Pro run. See `outputs/tables/phase7_volatility_benchmark.csv`.*

| model | info_set | horizon | target | QLIKE | MAE | MSE | bias |
|---|---|---|---|---|---|---|---|

Expected new rows: 3 GARCH-X variants × 2 targets × 2 horizons = **12 net new
rows** on top of the Phase 6 12 GARCH rows. The GARCH-X exog comes from
the `garch_x_info_set` columns (default F); for an ablation, also try P
and PN in subsequent runs.

**H1 verdict** (to be filled in after run):
- Compare `garch_x_P` QLIKE vs `garch_zero` QLIKE on the same target/horizon.
- The C4-era EGARCH h=5 Monte-Carlo fix is inherited from Phase 6.

---

## 5. SHAP results

> *Populated after the Colab Pro run. See `outputs/figures/fig17_shap_summary_*.png`.*

Per (info_set, horizon, target):
- `fig17_shap_summary_<info_set>_h<horizon>_<target>.png` — beeswarm + bar
- `outputs/model_objects/shap_phase7.npz` — raw SHAP values per fold
- `outputs/model_objects/xgb_best_params.csv` — tuned hyperparams

**Global feature importance** (per info set, top-10 features across all folds):

| info_set | top features (by mean \|SHAP\|) |
|---|---|
| F | *(to be filled)* |
| P | |
| N | |
| PN | |
| PNG | |

**Feature stability** (fraction of folds where the feature is in top-10):
- F: *(to be filled)*
- P:
- N:
- PN:
- PNG:

**H3 verdict** (narrative gap > raw volume):
- Compare SHAP importance of `narrative_gap_*` vs `n_articles_total*`
  within the PNG and PN info sets. If `narrative_gap_*` ranks higher
  in the top-10 stability report, H3 is supported.

---

## 6. Hypothesis verdict (thesis Results chapter summary)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1 (physical → vol) | TBD | phase7_volatility_benchmark.csv QLIKE: garch_x_P vs garch_zero |
| H2 (news → returns/vol) | TBD | phase7_benchmark.csv MAE: xgboost_PN vs xgboost_F |
| H3 (narrative gap > raw volume) | TBD | SHAP stability report for PNG |
| H5 (different horizons) | TBD | Compare h=1 vs h=5 metrics |
| H6 (global vs European robustness) | TBD | r_ITA vs r_WAERLST_recon rows |

---

## 7. Known limitations

- **Small sample**: 1,006 training observations and 336 test observations.
  XGBoost with the conservative hyperparams (max_depth=5, lr=0.05) is
  appropriate; deeper trees would overfit.
- **Single algorithm**: only XGBoost is the principal algorithm. LightGBM
  is noted in the decision log as a robustness alternative (not run).
- **GARCH-X in mean only**: exogenous regressors enter the conditional
  *mean* of the GARCH process, not the *variance* equation. The
  `arch` package's API for variance-equation exog is unstable. A
  two-step ARX-residual + univariate GARCH fallback is documented.
- **No Optuna**: the grid search is exhaustive (216 configs) and reproducible.
- **SHAP per fold**: the stability report uses the test-set SHAP values,
  which is a 336-day sample. The headline report is a fold-averaged summary.

---

## 8. Supervisor-review fixes (C-fixes)

To be populated as they emerge during the Colab run. Expected items:
- C7: *(unknown; likely NaN handling or refit cadence edge case)*
- C8: *(unknown)*

---

## 9. Local post-run workflow (rclone pull + git commit)

After the Colab Pro run completes, **switch to your local laptop** and run:

```bash
cd ~/Desktop/katya/WarSignalsThesis
source .venv/bin/activate

# Verify Drive has the new files
rclone lsf gdrive:WarSignalsThesis_Data/outputs/tables/ | grep phase7
rclone lsf gdrive:WarSignalsThesis_Data/outputs/figures/ | grep fig17
rclone lsf gdrive:WarSignalsThesis_Data/outputs/model_objects/

# Pull results from Drive (rclone is local-only; do NOT run in Colab)
rclone copy --update --progress \
  gdrive:WarSignalsThesis_Data/outputs/tables/phase7_* \
  outputs/tables/
rclone copy --update --progress \
  gdrive:WarSignalsThesis_Data/outputs/model_objects/ \
  outputs/model_objects/
rclone copy --update --progress \
  gdrive:WarSignalsThesis_Data/outputs/figures/fig17* \
  outputs/figures/

# Verify
ls -lh outputs/tables/phase7_* outputs/figures/fig17*

# Commit and push
git add -A
git commit -m "Phase 7: XGBoost returns + GARCH-X vol + SHAP"
git push origin main
```

Then update this audit doc with the actual numbers from `phase7_benchmark.csv`,
`phase7_volatility_benchmark.csv`, and the SHAP stability report.
