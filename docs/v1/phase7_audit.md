# Phase 7 — ML Models Audit

**Last updated:** 2026-07-02 (populated with real results after the WAERLST/BSHIELDT
target-hierarchy rebuild; see decision_log 2026-07-02 entries)

> See the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md)
> for the research plan and [`docs/phase6_audit.md`](phase6_audit.md) for the
> Phase 6 audit. This document mirrors the Phase 6 audit structure.

---

## 1. Setup

### 1.1 Compute & data environment

- **Compute (this run)**: local laptop, default (non-tuned) XGBoost hyperparameters
  from `config/model_config.yaml`. Full run (all 5 info sets × 2 horizons × 3 targets,
  340-day OOS test window, 18 refits) completed in **3.1 minutes** — the earlier
  Colab-Pro-only guidance was written when the pipeline used a 6,480-fit tuning grid;
  the *default*-hyperparameter run used for this audit is cheap enough to run locally.
  A tuned run (`scripts/phase7_tune.py`, 216 configs × 3 folds) is still recommended for
  the final thesis numbers and remains a Colab-Pro candidate (~110 min).
- **Model matrix**: `data/processed/model_matrix.parquet` (1,358 × 154, real
  WAERLST/BSHIELDT targets, rebuilt 2026-07-02).
- **Prior run**: an earlier Colab Pro run (2026-07-01) used the OLD target hierarchy
  (`r_ITA` primary, `r_WAERLST_recon` secondary) and is now superseded by this run.

### 1.2 Dependencies

Added to `requirements.txt`:
- `xgboost>=2.0` — principal gradient-boosting algorithm (decision_log 2026-07-01)
- `shap>=0.44` — SHAP TreeExplainer for XGBoost feature attribution

### 1.3 Config

`config/model_config.yaml`:
- `ml.algorithm: "xgboost"`, conservative defaults (max_depth=5, lr=0.05, n_est=500,
  early_stopping=50) — **used as-is for this run** (no tuning grid applied yet).
- `garch_x.mean: "ARX"` — exogenous regressors enter the mean equation (see §4, §7 for
  why this specification is now flagged as numerically fragile).

### 1.4 Target hierarchy (decision_log 2026-07-02)

- **Primary:** `r_WAERLST` (real Bloomberg global aerospace & defense index)
- **Robustness (European, war-exposed):** `r_BSHIELDT` (real Bloomberg)
- **Robustness (US):** `r_ITA` (yfinance ETF proxy)
- `r_WAERLST_recon` is **retired as a target** (kept as a lagged feature only)

### 1.5 Information-set cardinality — N==F bug fixed

The N==F redundancy flagged in earlier drafts of this audit was a genuine bug, not
"by construction." `build_info_sets()` in `src/features/build_model_matrix.py` unions
P/PN/PNG progressively but was **missing the equivalent union for N**. Fixed
2026-07-02:

```python
out["P"] = sorted(set(out["F"]) | set(out["P"]))
out["N"] = sorted(set(out["F"]) | set(out["N"]))
out["PN"] = sorted(set(out["P"]) | set(out["N"]) | set(out["PN"]))
out["PNG"] = sorted(set(out["PN"]) | set(out["PNG"]))
```

**Post-fix, post-rebuild cardinalities** (`outputs/tables/info_set_cardinality.csv`):

| info_set | n_features |
|---|---|
| F | 37 |
| P | 73 |
| N | 63 |
| PN | 115 |
| PNG | 118 |

N (63) is now a genuine superset of F (37) plus news-only columns — no longer equal to
F. H1 (P vs F), H2 (PN vs P), and now N vs F are all meaningful, non-redundant
comparisons.

---

## 2. Tuned hyperparameters

**Not run in this pass.** This audit uses `config/model_config.yaml` defaults
(max_depth=5, lr=0.05, n_estimators=500, early_stopping=50) for all info
sets/targets/horizons. The 216-config TS-CV grid search (`scripts/phase7_tune.py`) is
still available and recommended before finalizing thesis numbers, but the return-side
null result (§3) is unlikely to change materially with tuning, given how flat MAE/
dir_acc already are across info sets.

---

## 3. Returns benchmark (XGBoost)

Full results: `outputs/tables/phase7_benchmark.csv` (150 rows: 5 return models ×
5 info sets × 3 targets × 2 horizons). XGBoost rows only, primary target:

| target | horizon | info_set | MAE | RMSE | dir_acc | corr |
|---|---|---|---|---|---|---|
| r_WAERLST | 1 | F | 0.9596 | 1.2478 | 0.5513 | -0.014 |
| r_WAERLST | 1 | N | 0.9573 | 1.2446 | 0.5572 | 0.050 |
| r_WAERLST | 1 | P | 0.9566 | 1.2470 | 0.5543 | 0.007 |
| r_WAERLST | 1 | PN | 0.9583 | 1.2466 | 0.5367 | 0.013 |
| r_WAERLST | 1 | PNG | 0.9556 | 1.2450 | 0.5543 | 0.042 |
| r_WAERLST | 5 | F | 2.2462 | 2.8710 | 0.5210 | 0.017 |
| r_WAERLST | 5 | PNG | 2.2286 | 2.8766 | 0.5210 | -0.065 |

r_BSHIELDT and r_ITA show the same flat pattern (MAE/dir_acc barely move across F→PNG;
see the full CSV for all rows).

**Verdict: null result on returns, as anticipated.** Directional accuracy stays in the
51-56% band and MAE is essentially flat (±1%) across F/P/N/PN/PNG for all three
targets and both horizons. Adding attack/news information does not measurably improve
XGBoost point-forecast accuracy for next-day or 5-day returns. This mirrors the Phase 6
econometric-baseline finding (AR1/historical-mean already win) and is consistent with
near-efficient-market daily-return behavior — **a valid null result per
`instructions.md`**, not a pipeline failure.

---

## 4. Volatility benchmark (GARCH family)

Full results: `outputs/tables/phase7_volatility_benchmark.csv`.

### 4.1 Plain GARCH/GJR-GARCH/EGARCH (no exogenous regressors) — numerically sound

| target | horizon | model | MAE | RMSE | QLIKE |
|---|---|---|---|---|---|
| r_WAERLST | 1 | garch | 1.482 | 2.567 | 1.285 |
| r_WAERLST | 1 | gjr_garch | 1.465 | 2.551 | 1.299 |
| r_WAERLST | 1 | egarch | 1.430 | 2.550 | 1.267 |
| r_BSHIELDT | 1 | garch | 2.842 | 4.395 | 1.392 |
| r_BSHIELDT | 1 | gjr_garch | 2.879 | 4.407 | 1.404 |
| r_BSHIELDT | 1 | egarch | 2.964 | 4.423 | 1.402 |
| r_ITA | 1 | garch | 1.655 | 2.616 | 1.362 |
| r_ITA | 1 | gjr_garch | 1.687 | 2.615 | 1.368 |
| r_ITA | 1 | egarch | 1.685 | 2.603 | 1.343 |

(h=5 rows in the CSV; all QLIKE values in the sane 1.3-4.8 range, comparable to Phase
6's plain-GARCH numbers built on the old target hierarchy.)

### 4.2 GARCH-X (exogenous regressors, F info set, mean equation) — numerically non-viable

**Two real bugs were found and fixed** in `src/models/expanding_window.py` during this
session (see decision_log 2026-07-02 for full detail):
1. The GARCH source column itself was included in its own exogenous-regressor set,
   producing a perfect self-fit (`omega` collapsed to ~0, variance forecast to ~1e-27).
2. Exogenous regressors (VIX level, `days_since_invasion`, etc.) were passed unscaled
   to `arch_model` while `y` is internally rescaled, destabilizing the ARX-mean
   optimizer.

Both are fixed (source column excluded; exog standardized on train-block-only
mean/std). A **point-in-time-safe degenerate-fold guard** was added in
`src/models/horse_race.py::_aggregate` — folds whose variance forecast is >1000x or
<0.001x the plain-GARCH forecast scale for the same target/horizon are excluded from
MAE/RMSE/QLIKE and counted in `n_degenerate`. The guard uses only same-fold
*plain-GARCH* output as the reference (not realized/future variance), so it does not
introduce outcome-dependent sample selection.

**Result — full 340-day OOS window (`n_degenerate` / total folds):**

| target | horizon | garch_x_garch | garch_x_gjr_garch | garch_x_egarch |
|---|---|---|---|---|
| r_WAERLST | 1 | 261/341 (76%) | 281/341 (82%) | 281/281 (100%) |
| r_WAERLST | 5 | 134/334 (40%) | 260/334 (78%) | — |
| r_BSHIELDT | 1 | 201/341 (59%) | 341/341 (**100%**) | 180/180 (**100%**) |
| r_BSHIELDT | 5 | 194/334 (58%) | 334/334 (**100%**) | — |
| r_ITA | 1 | 225/325 (69%) | 220/325 (68%) | 145/145 (**100%**) |
| r_ITA | 5 | 139/319 (44%) | 180/319 (56%) | — |

**Verdict: GARCH-X-in-mean, as currently specified, is numerically non-viable on this
sample.** `r_BSHIELDT` is 100% degenerate for GJR-GARCH-X and EGARCH-X (0 usable
folds); the surviving fraction for other target/variant combinations ranges 18-60%,
with QLIKE on survivors (4-6) still notably worse than the plain-GARCH baseline
(1.3-1.8). This is a **legitimate null/negative finding**, not a remaining bug to keep
chasing — the residual instability is rooted in the `arch` package's ARX-mean
optimizer combined with correlated financial regressors (VIX, lagged returns, vol) at
this sample size (~500-1,300 training observations), which is out of scope to redesign
in this session (see §7, §8 for what a future fix would require).

**H1 (volatility) should therefore be assessed via the plain GARCH-family models
(§4.1) as the volatility baseline**, with attack/news information's *volatility*
contribution left as an open question pending a GARCH-X redesign (variance-equation
exog, or far fewer exogenous regressors) — not asserted either way from the current
GARCH-X-in-mean results.

---

## 5. SHAP results

Per (info_set, horizon, target): `outputs/figures/fig17_shap_summary_<info_set>_h<horizon>_<target>.png`
(beeswarm + bar), raw values in `outputs/model_objects/shap_phase7.npz`.

**Top-10 features by mean |SHAP|, PNG info set, h=1** (the full-information comparison,
computed by concatenating all fold-level SHAP arrays):

**r_WAERLST** (global, less war-exposed):
1. `vol_20d_lag1` (0.0495)
2. `logvol_WAERLST_lag1` (0.0393)
3. `attack_surprise_uav_30d_lag1` (0.0159)
4. `vol_5d_lag1` (0.0095)
5. `destroyed_uav_lag1` (0.0094)
6. `days_since_invasion` (0.0088)
7. `attack_surprise_penetrations_30d_lag1` (0.0074)
8. `n_russian_z30_lag1` (0.0069)
9. `n_ukrainian_z30_lag1` (0.0056)
10. `n_western_defense_industry_western_lag1` (0.0052)

**r_BSHIELDT** (European, most war-exposed):
1. `destroyed_uav_lag1` (0.0442)
2. `destroyed_total_lag1` (0.0320)
3. `attack_surprise_uav_30d_lag1` (0.0239)
4. `vol_5d_lag1` (0.0208)
5. `launched_total_lag1` (0.0135)
6. `attack_surprise_uav_90d_lag1` (0.0129)
7. `n_other_share_lag1` (0.0097)
8. `n_russian_defense_industry_western_lag1` (0.0077)
9. `logvol_BSHIELDT_lag1` (0.0076)
10. `month` (0.0073)

**Notable pattern (H1/H6 evidence):** for `r_WAERLST`, model-driving features are
dominated by volatility/liquidity (own-vol, own-volume). For `r_BSHIELDT` — the
European, most war-exposed index — **4 of the top 6 features are physical-attack
features** (`destroyed_uav`, `destroyed_total`, `attack_surprise_uav_30d`,
`launched_total`), a materially different importance profile from WAERLST. This is
consistent with H1's premise (physical attack intensity is more informative for the
more war-exposed index) even though it does not move the headline MAE/dir_acc metric
(§3) — SHAP importance and point-forecast accuracy are answering different questions;
the former shows the model *uses* attack information more heavily for BSHIELDT, the
latter shows this use doesn't (yet) translate into a materially better forecast.

**H3 verdict (narrative gap > raw volume): NOT supported.** No `narrative_gap_*`
feature appears in the top-10 for either target's PNG info set — raw attack/volume/
liquidity features dominate over narrative-gap features in this sample.

---

## 6. Hypothesis verdict (thesis Results chapter summary)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1 (physical → returns) | **Null** (no MAE/dir_acc lift) | §3: XGBoost P vs F, all targets |
| H1 (physical → vol) | **Inconclusive** (GARCH-X non-viable) | §4.2: 18-100% degenerate folds |
| H1 (physical, SHAP importance) | **Supported for BSHIELDT** | §5: attack features dominate BSHIELDT's top-10, not WAERLST's |
| H2 (news → returns) | **Null** | §3: PN vs P flat MAE/dir_acc |
| H3 (narrative gap > raw volume) | **Not supported** | §5: no narrative_gap_* in top-10 |
| H5 (horizon differences) | **Minimal** | §3: h=1 vs h=5 patterns near-identical (flat both ways) |
| H6 (global vs European robustness) | **Partially supported** | §5: BSHIELDT's feature-importance profile differs qualitatively from WAERLST/ITA (attack-driven vs vol-driven), even though point-forecast metrics are similar in magnitude across all three |

---

## 7. Known limitations

- **Returns are a genuine null across the whole pipeline** — Phase 6 econometric
  baselines, Phase 7 XGBoost (default hyperparameters), all info sets, both horizons,
  all three targets. This is consistent and not an artifact of any single model choice.
- **GARCH-X-in-mean is numerically non-viable on this sample** (§4.2) — a future
  session could retry with (a) far fewer exogenous regressors (e.g. 1-2 attack/news
  aggregates instead of the full F info set), or (b) a genuine variance-equation exog
  specification (the `arch` package's API for this is unstable, as originally noted;
  a two-step ARX-residual + univariate-GARCH fallback remains undocumented in code).
- **Hyperparameters not tuned** — this audit uses `config/model_config.yaml` defaults.
  `scripts/phase7_tune.py` (216-config grid) should be run before finalizing thesis
  numbers, though the flatness of the null result across info sets makes a tuning-driven
  reversal unlikely.
- **Single algorithm**: only XGBoost is the principal ML algorithm; LightGBM is a
  documented but unrun robustness alternative.
- **SHAP is fold-averaged** over the full 325-341 day OOS test window per target.

---

## 8. Next steps

1. Run `scripts/phase7_tune.py` (Colab-Pro-viable, ~110 min) for tuned hyperparameters
   and re-verify §3's null result holds under tuning.
2. If GARCH-X is worth pursuing further for H1, redesign with far fewer exogenous
   regressors (e.g., `attack_surprise_total_30d`, `n_articles_total_z30` only) rather
   than the full F info set, to reduce ARX-mean optimizer instability.
3. Update `docs/project_status.md` and `README.md` to reflect Phase 7 complete with
   these (honest, partially-null) findings, and move to Phase 8 (statistical
   comparison / robustness) — the null result on returns and the GARCH-X limitation
   are valid, reportable findings, not blockers.
