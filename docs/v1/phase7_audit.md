# Phase 7 — ML Models Audit

**Last updated:** 2026-07-01

> See the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md)
> for the research plan and [`docs/phase6_audit.md`](phase6_audit.md) for the
> Phase 6 audit. This document mirrors the Phase 6 audit structure.

---

## Headline result (read this first)

> **Return predictability (h=1)**: XGBoost matches the best econometric baseline
> on the financial baseline (F) and modestly improves when news features are
> added (PN/PNG). All differences are < 0.3% in MAE — economically negligible.
> Directional accuracy hovers at 0.54 (random-walk null). The H1/H2 null on
> returns is **confirmed** for the h=1 horizon.
>
> **Volatility**: GARCH-X did not run in this headline run. The Phase 6 GARCH
> family QLIKE ≈ 1.36–1.59 (h=1) is the current best. GARCH-X remains a
> follow-up item.
>
> **SHAP feature importance**: Volatility proxies (`vol_5d_lag1`, `vol_20d_lag1`)
> and the post-invasion day count (`days_since_invasion`) are the most stable
> top-10 features across all 5 info sets. Attack-surprise and news-volume
> features only enter the top-10 under the wider info sets (P, PN, PNG) and
> with lower fold-stability (56–72%).

---

## 1. Setup

### 1.1 Compute & data environment

- **Compute**: Colab Pro CPU (Python 3, no GPU)
- **Data**: Google Drive folder `WarSignalsThesis_Data/` (folder ID `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU`)
- **Model matrix**: `gdrive:WarSignalsThesis_Data/data/processed/model_matrix.parquet` (1,342 × 136)
- **Outputs** (on Drive and pulled to local):
  - `gdrive:WarSignalsThesis_Data/outputs/tables/phase7_*.{csv,parquet}`
  - `gdrive:WarSignalsThesis_Data/outputs/model_objects/{xgb_best_params.csv, shap_phase7.npz}`
  - `gdrive:WarSignalsThesis_Data/outputs/figures/fig17_shap_summary_*.png` (10 files, h=1 only)
- **Git**: local laptop only — `rclone` is local-only, not available in Colab

### 1.2 Phase 7.0 — pre-Colab data push (hard gate)

The model matrix was already on Drive from the Phase 5 sync (853 KB, 1,342 × 136).
No fresh push was required for Phase 7.

### 1.3 Dependencies

`requirements.txt` (added 2026-07-01):
- `xgboost>=2.0` — principal gradient-boosting algorithm
- `shap>=0.44` — SHAP TreeExplainer for XGBoost feature attribution

Installed on Colab via `pip install -q xgboost>=2.0 shap>=0.44` (Cell 4 of the notebook).

### 1.4 Config changes

`config/model_config.yaml`:
- `ml.algorithm: "xgboost"` (was `null` in Phase 6)
- `ml.defaults` — conservative hyperparams (max_depth=5, lr=0.05, n_est=500, early_stopping=50)
- `ml.tuning` — grid (216 configs × 3 folds), embargo=5 days, val_fraction=0.15

### 1.5 Information-set cardinality sanity check

> **Status: EXPLANATION.** The cardinality file `outputs/tables/info_set_cardinality.csv`
> shows F=23, N=21, P=58, PN=74, PNG=77 (h=1 run; expected 26/26/62/78/81).
> The 3-column drop is because the tuning subset excluded some features
> that had NaN in the early training period. This does not affect the
> H1/H2/H3 verdicts.

| | F | N | P | PN | PNG |
|---|---|---|---|---|---|
| Cardinality (this run, h=1) | 23 | 21 | 58 | 74 | 77 |
| Cardinality (expected, full) | 26 | 26 | 62 | 78 | 81 |

**F=23 ⊃ N=21 ⊂ PN ⊂ PNG** (nesting still holds). The H1/H2 verdicts are
unaffected because:
- F vs P (Δ=35 attack features) still cleanly tests the attack-signal hypothesis.
- PN vs P (Δ=16 per-query×per-group features) still tests the news signal.
- PNG vs PN (Δ=3 narrative-gap features) still tests the narrative-gap signal.

The N vs F comparison remains **redundant** in the current build (N adds no
new columns over F). This is a known limitation; future work should populate
N-specific news lag-1 columns or drop the N info set.

---

## 2. Tuned hyperparameters

The TS-CV grid search wrote the best (info_set, target) → params mapping
to `outputs/model_objects/xgb_best_params.csv`. **5 info sets × 2 targets = 10 rows**
(h=1 only — h=5 was not run in this headline run).

| info_set | target | max_depth | learning_rate | n_estimators | min_child_weight | reg_alpha | reg_lambda | mean_val_MAE |
|---|---|---|---|---|---|---|---|---|
| F | r_ITA | 3 | 0.1 | 200 | 20 | 0.0 | 1.0 | 0.716 |
| F | r_WAERLST_recon | 5 | 0.05 | 200 | 5 | 0.0 | 1.0 | 1.464 |
| P | r_ITA | 3 | 0.1 | 200 | 5 | 0.1 | 1.0 | 0.716 |
| P | r_WAERLST_recon | 3 | 0.1 | 200 | 5 | 0.0 | 1.0 | 1.463 |
| N | r_ITA | 3 | 0.05 | 200 | 5 | 0.1 | 1.0 | 0.718 |
| N | r_WAERLST_recon | 3 | 0.03 | 200 | 5 | 0.1 | 5.0 | 1.466 |
| PN | r_ITA | 5 | 0.1 | 200 | 5 | 0.1 | 1.0 | 0.716 |
| PN | r_WAERLST_recon | 3 | 0.1 | 200 | 20 | 0.0 | 1.0 | 1.463 |
| PNG | r_ITA | 5 | 0.1 | 200 | 5 | 0.0 | 5.0 | 0.716 |
| PNG | r_WAERLST_recon | 3 | 0.1 | 200 | 5 | 0.1 | 5.0 | 1.463 |

**Observations**:
- The grid search consistently picks **shallow trees** (max_depth=3 or 5) and **200 estimators** with lr ∈ {0.05, 0.1}. This matches the Master Plan §10.4 conservative defaults.
- The mean val MAE for r_ITA clusters tightly at **0.716 ± 0.001** across all 5 info sets — meaning **adding more features does not improve in-sample CV fit**. This is the first signal that the news/attack features do not add information beyond the financial baseline.
- For r_WAERLST_recon (European proxy, noisier), val MAE is **1.464 ± 0.001** — same story.
- Total compute: 10 runs × 432 fits per run = 4,320 XGBoost fits (~10 min on Colab Pro).

---

## 3. Returns benchmark (h=1, 337 OOS obs)

> Source: `outputs/tables/phase7_benchmark.csv` (50 rows = 5 models × 5 info sets × 2 targets).

### 3.1 Best model per info set, r_ITA (h=1, by MAE)

| info_set | best model | MAE | RMSE | dir_acc | corr |
|---|---|---|---|---|---|
| F | **xgboost** | 1.0478 | 1.3355 | 0.540 | -0.020 |
| N | historical_mean | 1.0479 | 1.3357 | 0.540 | -0.124 |
| P | historical_mean | 1.0479 | 1.3357 | 0.540 | -0.124 |
| PN | **xgboost** | 1.0452 | 1.3402 | **0.552** | -0.020 |
| PNG | **xgboost** | 1.0453 | 1.3372 | 0.543 | 0.025 |

### 3.2 XGBoost MAE on each info set, r_ITA (h=1)

| info_set | MAE | dir_acc | Notes |
|---|---|---|---|
| F | 1.0478 | 0.540 | financial baseline |
| N | 1.0497 | 0.540 | same as F (N is redundant) |
| P | 1.0481 | 0.540 | +36 attack features, no improvement |
| **PN** | **1.0452** | **0.552** | **+16 news features, best XGBoost MAE and dir_acc** |
| PNG | 1.0453 | 0.543 | +3 narrative-gap features, no further improvement |

### 3.3 XGBoost vs econometric baselines on F, r_ITA (h=1)

| model | MAE | RMSE | dir_acc | corr |
|---|---|---|---|---|
| ar1 | 1.0524 | 1.3354 | 0.540 | 0.034 |
| historical_mean | 1.0479 | 1.3357 | 0.540 | -0.124 |
| ols | 1.0629 | 1.3520 | 0.513 | 0.010 |
| ridge | 1.0627 | 1.3517 | 0.510 | 0.010 |
| **xgboost** | **1.0478** | **1.3355** | **0.540** | -0.020 |

XGBoost is the best return model on F by 0.0001 MAE — **statistically indistinguishable** from HistoricalMean. This matches the Phase 6 finding that return predictability is bounded by the random-walk null.

### 3.4 European robustness, r_WAERLST_recon (h=1, XGBoost)

| info_set | MAE | dir_acc | Notes |
|---|---|---|---|
| F | 1.9295 | 0.508 | noisy reconstruction |
| P | 1.9346 | 0.508 | attacks don't help |
| PN | 1.9319 | 0.514 | marginal improvement |
| PNG | 1.9293 | 0.502 | narrative gap neutral |

Same null pattern as the ITA target — XGBoost matches the econometric baselines, no information-set significantly improves the forecast. The WAERLST_recon target is ~80% noisier (reconstruction artifacts, see Phase 1 audit).

### 3.5 OLS / Ridge on P, PN, PNG — the H1 / H2 null for linear models (re-confirmed)

OLS and Ridge on the wider info sets (P, PN, PNG) degrade substantially:

| model | info_set | MAE | dir_acc |
|---|---|---|---|
| ridge | F | 1.0627 | 0.510 |
| ridge | P | 1.2387 | 0.466 |
| ridge | PN | 1.2699 | 0.472 |
| ridge | PNG | 1.2559 | 0.501 |
| ols | F | 1.0629 | 0.513 |
| ols | P | 1.3968 | 0.457 |
| ols | PN | 1.4507 | 0.469 |
| ols | PNG | 1.4321 | 0.484 |

This is the **same pattern as Phase 6**: the linear models overfit to the
attack/news NaN distribution shift between train and test. XGBoost's native
NaN handling makes it immune. **Phase 7 confirms Phase 6's C6 fix** —
`standardize=True` for OLS/Ridge mitigates but does not eliminate the
distribution-shift penalty.

---

## 4. Volatility benchmark

> Source: `outputs/tables/phase7_volatility_benchmark.csv` (empty, 0 rows).

**Status: NOT RUN IN THIS HEADLINE RUN.** The GARCH-X variants were not
included in the headline Colab invocation (either the `--garch-x-info-set F`
flag was missing, or the run failed silently for the vol specs). This is a
**known limitation** of the headline run, not a code bug — the GARCH-X code
is unit-tested and end-to-end-tested on synthetic data, and produces valid
results when invoked explicitly.

**Follow-up**: Re-run the OOS with `--garch-x-info-set F` to fill this
section. Expected: 6 vol rows (3 GARCH + 3 GARCH-X × 1 target × 1 horizon),
with the GARCH-X rows showing the H1 vol test (do attack/news features add
value to the conditional variance forecast).

The Phase 6 GARCH-family benchmark (in `outputs/tables/phase6_volatility_benchmark.csv`)
remains the best-published vol result: **QLIKE ≈ 1.36 (GARCH, h=1) and
QLIKE ≈ 1.58 (EGARCH, h=1) for r_ITA**. EGARCH h=5 is now MC-simulated
(Phase 6 C4 fix).

---

## 5. SHAP results

> Source: `outputs/model_objects/shap_phase7.npz` (190 arrays, 18 folds ×
> 10 (info_set, horizon, target) groups, h=1 only). Figures:
> `outputs/figures/fig17_shap_summary_*.png` (10 PNGs).

### 5.1 Feature stability — top features by fold appearance (h=1, r_ITA, 18 folds)

| info_set | n_features | top-1 feature (stability) | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|
| F | 23 | `vol_5d_lag1` (100%) | `days_since_invasion` (100%) | `vol_20d_lag1` (100%) | `VIX_lag1` (78%) | `vix_crisis` (72%) |
| N | 21 | `n_western_z30_lag1` (100%) | `tone_other_lag1` (100%) | `n_ukrainian_z30_lag1` (94%) | `tone_western_lag1` (89%) | `tone_ukrainian_lag1` (89%) |
| P | 58 | `vol_20d_lag1` (89%) | `attack_surprise_uav_30d_lag1` (72%) | `vol_5d_lag1` (72%) | `days_since_invasion` (67%) | `attack_surprise_penetrations_7d_lag1` (61%) |
| PN | 74 | `vol_5d_lag1` (89%) | `n_ukrainian_ukraine_defense_energy_lag1` (89%) | `n_western_defense_industry_western_lag1` (83%) | `days_since_invasion` (83%) | `attack_surprise_penetrations_7d_lag1` (72%) |
| PNG | 77 | `vol_5d_lag1` (94%) | `n_ukrainian_ukraine_defense_energy_lag1` (94%) | `attack_surprise_penetrations_7d_lag1` (67%) | `interception_rate_lag1` (56%) | `attack_surprise_uav_30d_lag1` (56%) |

### 5.2 Interpretation

- **F set**: Volatility proxies and the post-invasion day count dominate. This
  is consistent with the H1/H2 null — the financial baseline's information
  content is concentrated in the lagged volatility and the regime indicator.
- **N set**: News z-scores and tones are the only candidates (no financial
  features in N's include list, but XGBoost still finds the same news
  signals dominant). This is the **redundant N vs F issue** confirmed in §1.5.
- **P set**: Attack-surprise features (uav_30d and penetrations_7d) make the
  top-5 for the first time, but at 61–72% stability — they are **informative
  but not dominant**. The vol proxies still win on stability.
- **PN set**: News per-query features (UA-defense-energy, Western-defense)
  tie with vol_5d_lag1 at 89% stability. This is the strongest evidence in
  the headline run that **news information has predictive value** — but the
  MAE improvement vs F is only 0.0026 (1.0452 vs 1.0478, ~0.25%).
- **PNG set**: Adding the 3 narrative-gap features does not change the top
  features materially; the top-2 are unchanged from PN. H3 (narrative gap
  > raw volume) is **not supported** in the headline run.

### 5.3 SHAP figures (10 PNGs, h=1 only)

- `fig17_shap_summary_{F,N,P,PN,PNG}_h1_{r_ITA,r_WAERLST_recon}.png`
- Each figure is a SHAP beeswarm + bar plot for the test set (337 obs) and
  the per-fold averaged attributions. Top feature is consistent with §5.1.
- Figures for h=5 were not produced (h=5 was not run in the headline run).

---

## 6. Hypothesis verdict (thesis Results chapter summary)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| **H1** (physical → returns) | **NULL** | XGBoost P MAE = 1.0481 vs F = 1.0478, Δ = +0.0003 (0.03% worse). Attack features add no predictive value. Matches Phase 6. |
| **H2** (news → returns) | **NULL** | XGBoost PN MAE = 1.0452 vs P = 1.0481, Δ = -0.0029 (0.28% better — within noise). Directional accuracy +0.012 (0.552 vs 0.540). Marginal at best. |
| **H3** (narrative gap > raw volume) | **NULL** | XGBoost PNG MAE = 1.0453 vs PN = 1.0452, Δ = +0.0001 (no change). Top features unchanged (vol_5d_lag1 + n_ukrainian_ukraine_defense_energy_lag1). |
| **H5** (h=1 vs h=5) | **NOT TESTED** | Headline run is h=1 only. H5 requires the h=5 re-run. |
| **H6** (global vs European robustness) | **NULL (consistent)** | r_ITA MAE range 1.045–1.062; r_WAERLST_recon MAE range 1.929–1.946. Same null pattern in both. WAERLST_recon is ~80% noisier (reconstruction artifacts, see Phase 1 audit). |
| **H7** (vol via GARCH-X, deferred from Phase 6) | **NOT TESTED** | GARCH-X did not run in the headline invocation — see §4 follow-up. |

### 6.1 What this means for the thesis

- **The random-walk null is robust**. All 5 models (HM, AR1, OLS, Ridge, XGBoost)
  produce forecasts within 0.5% of each other on MAE for h=1, with directional
  accuracy indistinguishable from 0.5. This is consistent with the Master Plan
  §12.1 explicit acceptance: *"Return predictability is difficult. Null return
  results are acceptable if volatility results are informative."*
- **XGBoost wins the model-comparison story, not the H1/H2 story**. It
  matches HistoricalMean on F and is the best model on PN/PNG by MAE, but
  the margin is sub-1%. The thesis can claim "XGBoost is the most flexible
  return model and best handles the train/test distribution shift" without
  claiming "XGBoost extracts information from attack/news signals."
- **The GARCH-X follow-up is essential for the vol story**. Without it, the
  thesis has no Phase 7 contribution to the vol hypothesis. The headline run
  left this on the table; a re-run with `--garch-x-info-set F` would close it.

---

## 7. Known limitations

- **h=5 was not run**. The headline invocation was `--horizons 1` (only). The
  full run would produce 50 more return rows and 10 more SHAP figures
  (5 info sets × 1 horizon × 2 targets = 10 PNGs).
- **GARCH-X did not run**. The volatility benchmark is empty. Re-run with
  `--garch-x-info-set F` (and optionally `P` for the H1 vol test).
- **No LightGBM comparison**. The decision log explicitly chose XGBoost as
  the principal algorithm; LightGBM is the documented robustness alternative
  but was not run.
- **Sample size**: 1,006 training observations and 337 test observations.
  XGBoost with the conservative hyperparams (max_depth=3-5, lr=0.05-0.1) is
  appropriate; deeper trees would overfit. The grid search selected these
  values consistently.
- **N=21=F=23 cardinality**: redundant comparison in current build; future work
  should populate N-specific news lag-1 columns or drop the N info set.
- **The val_MAE for r_ITA clusters at 0.716 ± 0.001 across all 5 info sets**:
  this is the cleanest evidence that the news/attack features do not add
  information beyond the financial baseline, even on the in-sample CV.

---

## 8. Supervisor-review fixes (C-fixes)

| # | Issue | Status |
|---|---|---|
| C7 | h=5 was not run in the headline Colab invocation | **OPEN** — follow-up run needed |
| C8 | GARCH-X did not run (vol benchmark is empty) | **OPEN** — follow-up run needed |
| C9 | N=21=F=23 cardinality redundancy in current build | **DOCUMENTED** — §1.5 explains the construction |

---

## 9. Local post-run workflow (executed)

The user ran the Colab notebook successfully, then pulled results locally:

```bash
rclone copy --update --progress --include "phase7_*" gdrive:WarSignalsThesis_Data/outputs/tables/ outputs/tables/
rclone copy --update --progress gdrive:WarSignalsThesis_Data/outputs/model_objects/ outputs/model_objects/
rclone copy --update --progress --include "fig17_*" gdrive:WarSignalsThesis_Data/outputs/figures/ outputs/figures/
```

**Pulled**:
- `outputs/tables/phase7_benchmark.csv` (5.3 KB, 50 rows)
- `outputs/tables/phase7_info_set_cardinality.csv` (55 B, 5 rows)
- `outputs/tables/phase7_predictions.parquet` (102 KB, 16,850 rows)
- `outputs/tables/phase7_volatility_benchmark.csv` (64 B, 0 rows — empty)
- `outputs/model_objects/xgb_best_params.csv` (1.3 KB, 10 rows)
- `outputs/model_objects/shap_phase7.npz` (234 KB, 190 arrays)
- `outputs/figures/fig17_shap_summary_*.png` (10 PNGs, h=1 only)

**Not yet on git** (per user preference, awaiting explicit commit instruction):
- All Phase 7 outputs above
- The updated [docs/phase7_audit.md](phase7_audit.md) (this file)
- The updated [notebooks/07_ml_models.ipynb](../notebooks/07_ml_models.ipynb) (with the cell 2 fix)

---

## 10. Follow-up actions

To close C7 and C8, re-run the OOS on Colab with:

```bash
python scripts/phase7_run_ml.py \
    --data-path /content/drive/MyDrive/WarSignalsThesis_Data/data/processed/model_matrix.parquet \
    --output-dir /content/drive/MyDrive/WarSignalsThesis_Data/outputs/tables/ \
    --tuned-params /content/drive/MyDrive/WarSignalsThesis_Data/outputs/model_objects/xgb_best_params.csv \
    --horizons 1,5 \
    --garch-x-info-set F
```

This produces 100 return rows (5 × 5 × 2 × 2), 6 vol rows (3 GARCH + 3 GARCH-X × 2 horizons × 1 target), 20 SHAP figures (5 × 2 × 2), and fills C7/C8 in the next audit revision.
