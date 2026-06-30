# Phase 5 — Merge and Feature Engineering (COMPLETE through 5C)

**Date completed:** 2026-06-30
**Tests:** 255 passed, 1 skipped, 0 failures (up from 182 at start of Phase 5)

## Deliverables

### Code (new files)
- `src/utils/date_utils.py` — `standardize_date_column`, `build_calendar_index`, `is_trading_day`, `shift_to_next_trading_day`, `US_FEDERAL_HOLIDAYS` (set of 60+ dates 2020-2026)
- `src/utils/recursive.py` — `expanding_compute`, `rolling_compute` (leakage-free, past-only)
- `src/features/merge.py` — `build_daily_master()` + 4 `load_*` helpers
- `src/features/financial_features.py` — `add_financial_features()` (vol_5d, vol_20d, abs_r_ITA, lags)
- `src/features/attack_features.py` — `add_attack_features()` (composition, 15 surprise features, lags) + `compute_attack_surprise_ar1()` hook for Phase 6
- `src/features/news_features.py` — `add_news_features()` (3 normalizations × 4 groups, narrative gaps, lags)
- `src/features/calendar_features.py` — `add_calendar_features()` (date components, invasion tenure, VIX regimes)
- `scripts/phase5_build_master.py` — CLI (builds both daily_master AND feature_matrix)
- `tests/test_date_utils.py` (25 tests)
- `tests/test_recursive.py` (12 tests)
- `tests/test_phase5_merge.py` (21 tests)
- `tests/test_features_financial.py` (11 tests)
- `tests/test_features_attack.py` (12 tests)
- `tests/test_features_news.py` (11 tests)
- `tests/test_features_calendar.py` (15 tests)

### Config
- `config/paths.yaml` (gitignored) — includes `daily_master`, `feature_matrix`, `model_matrix`, `data_dictionary` paths
- `requirements.txt` updated: statsmodels, scikit-learn, arch uncommented

### Data outputs
- `data/processed/daily_master.parquet` — 2,358 rows × 72 cols (calendar-day index 2020-01-07 → 2026-06-21)
- `data/processed/feature_matrix.parquet` — 2,358 rows × 141 cols (daily_master + 69 engineered features)
- `outputs/figures/fig10_master_coverage.png` — missingness heatmap

## End-to-end feature matrix (post-5C)

The 4 feature modules expand the panel from **72 → 141 columns**:

| Block | Cols | Examples |
|---|---|---|
| Financial (passthrough + derived) | 16 | `r_ITA`, `VIX`, `vol_5d`, `vol_20d`, `r_ITA_lag{1,2,5}` |
| Attack (raw + composition + surprise) | 31 | `launched_total`, `attack_uav_share`, `attack_surprise_total_{7,30,90}d` (× 5 series = 15) |
| News (raw + 3 normalizations + lags) | 27 | `n_articles_total`, `n_ukrainian_share/log/z30` (× 4 groups = 12), `narrative_gap_*_lag1` |
| News pivot (per-query×group) | 16 | `n_ukrainian_russian_attack_direct` etc. |
| Calendar | 8 | `day_of_week`, `days_since_invasion`, `vix_{low,normal,high,crisis}` |
| Other | 3 | `date`, `waerlst_missing`, `is_weekend`, `is_holiday` |

**Modeling window (2022-09-29 → 2026-06-21):** 1,362 rows × 141 cols
- vol_5d non-null: 1,348 / 1,362 (99.0%) — needs 5 past obs
- vol_20d non-null: 1,362 / 1,362 (100.0%) — needs 20 past obs
- attack_surprise_total_7d non-null: 785 / 1,362 (57.6%) — needs 7 past obs
- attack_surprise_total_30d non-null: 806 / 1,362 (59.2%)
- attack_surprise_total_90d non-null: 808 / 1,362 (59.3%)
- n_ukrainian_z30 non-null: 1,340 / 1,362 (98.4%)
- vix_crisis days: 6
- large_attack_indicator days: 81
- days_since_invasion: 217 → 1,578

## Critical design notes (locked in)

1. **`closed='left'` does NOT exclude the current value in pandas 3.0+ for fixed windows.** All past-only rolling features use `rolling_compute` from `src.utils.recursive` (a small loop) — unambiguous and version-agnostic.
2. **`np.std` / `np.mean` return NaN if any value in the window is NaN.** Critical for financial volatility: `r_ITA` is NaN on weekends/holidays, so a 5/20-day window that includes a weekend day would yield NaN volatility. We use `np.nanstd` / `np.nanmean` everywhere in the rolling features to ignore NaN days — this raised vol_5d coverage from 11.3% → 99.0% and vol_20d from 0% → 100%.
3. **`news_query_group_pivot` date column is `category` of strings** ('20220929'), not int64 as the exploration subagent suggested. `standardize_date_column` handles both via the generic `pd.to_datetime()` path.
4. **Test fixtures must standardize inputs before passing to `build_daily_master`.** The function does not standardize internally (loaders do). The `pvt` fixture in `test_phase5_merge.py` shows the pattern.
5. **Federal holidays on weekends are observed on the adjacent weekday** (e.g. 2022-12-25 Sun → 2022-12-26 Mon; 2023-01-01 Sun → 2023-01-02 Mon). 2024 is a leap year (Feb 29 is month-end; Feb 28 is NOT).
6. **Conservative timing rule (§9):** Financial features are documented "available at end of trading day t-1". The shift to predict t+1 happens at the **target** level in Phase 5D, not at the feature level here.
7. **`rolling_compute` suppresses the empty-slice `RuntimeWarning`** from `np.nanmean`/`np.nanstd` on all-NaN windows. The result is still NaN, but the test output is clean.

## Self-review fixes (2026-06-30)

During the self-review I identified and fixed:

1. **`phase5_build_master.py` now also writes `feature_matrix.parquet`** (was previously only writing `daily_master.parquet`, leaving the engineered features un-persisted).
2. **Critical NaN bug in rolling features**: `np.std`/`np.mean` return NaN if any value in the window is NaN. For `r_ITA` (NaN on weekends), a 5/20-day window that includes a weekend day would yield NaN volatility. Switched to `np.nanstd`/`np.nanmean` in `_past_std` (financial, news) and in the mean calls (attack, news). Result: vol_5d 11.3% → 99.0%, vol_20d 0% → 100%, attack_surprise 26-38% → 57-59% non-null.
3. **Added 11 end-to-end tests** in `tests/test_phase5_e2e.py` that load real data, run the full pipeline, and assert key invariants (date dtype, no duplicates, VIX regime sum-to-1, days_since_invasion ≥ 0, etc.).
4. **Removed unused `Tuple` import** in `src/features/merge.py`.
5. **Updated `paths.yaml`** to include the `feature_matrix` path.
6. **Suppressed `RuntimeWarning: Mean of empty slice`** in `rolling_compute` via a `_safe_call` helper.

## Phase 5D–5F (remaining work)

- **5D** — `build_model_matrix.py`: target construction (`target_r_ITA_t1 = r_ITA.shift(-1)` on next trading day), lag structure, info-set column masks, drop pre-2022-09-29 rows
- **5E** — `data_dictionary.csv`, `leakage_audit.py`, `descriptive_stats.py`, figures 11-13
- **5F** — `load_model_matrix()` helper, `validate_model_matrix_for_phase6()`, README update
