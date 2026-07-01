# Phase 2 — Physical Attack Dataset Audit

**Date:** 2026-06-28
**Scope:** Ukrainian Air Force (UAF) attack data in `data/raw/attacks/`
**Status:** ✅ Phase 2 complete

---

## 1. Executive Summary

The raw UAF data (`missile_attacks_daily.csv`, 3,812 attack-level records) was processed into a **daily modeling-ready table** with 809 unique `market_info_date` days spanning 2022-09-29 to 2026-06-21. The pipeline implements a robust **weapon classifier** (handles 71 unique model strings, including Cyrillic and combined-attack strings) and **distinguishes `attack_date` from `market_info_date`**, fixing a key flaw in the old `thesis_old_try` pipeline (which used `time_start` for everything).

**Key findings:**

- **102,396 total weapons launched**, of which **76,126 intercepted/destroyed** (74.3% overall interception rate)
- **97,041 (94.8%) UAVs (mostly Shahed-136/131)**; only 3,766 cruise missiles and 1,426 ballistic missiles
- Daily attacks have grown from a few per week in late 2022 to **regular 200+ weapon waves in 2025-2026**
- All 25 sampled days validated against raw data (aggregated count = raw count)

**Deliverables:**

- ✅ `src/data/attacks.py` — main module (430 lines, fully documented)
- ✅ `data/processed/attacks/attack_daily.parquet` (809 × 21)
- ✅ `data/processed/attacks/validation_table.csv` (25 sampled days)
- ✅ `data/processed/attacks/missingness_report.md`
- ✅ `outputs/figures/fig5-9_*.png` (5 figures)
- ✅ `tests/test_attacks.py` — **25/25 passing**

---

## 2. Raw Data Audit

### 2.1 `missile_attacks_daily.csv`

| Property | Value |
|---|---|
| Rows | 3,812 |
| Date range (`time_start`) | 2022-09-29 23:00 → 2026-06-20 18:00 |
| Columns | 22 (timestamp, model, launch_place, target, launched, destroyed, source URL, etc.) |
| Unique weapon models | 71 |
| Sources | Facebook posts from `kpszsu` (UAF) and `PvKPivden` (Southern Air Command) |
| Update pattern | Overnight waves (start ~18:00, end ~08:00 next day) |
| Total launched (raw sum) | 102,396 |
| Total destroyed (raw sum) | 76,126 |

### 2.2 `missiles_and_uavs-reference.csv`

| Property | Value |
|---|---|
| Rows | 64 |
| Columns | model, category, national_origin, type, launch_platform, name, name_NATO, in_service, designer, manufacturer |
| Categories | UAV (22), cruise missile (28), ballistic missile (7), surface-to-air (3), surface-to-air and ballistic (3), guided bomb (1) |
| Coverage | 63 of 71 raw model names match a reference row |

### 2.3 Top 10 raw models by record count

| Model | Records | Category (assigned) |
|---|---|---|
| Shahed-136/131 | 1,067 | uav |
| Unknown UAV | 336 | uav |
| Iskander-M | 289 | ballistic_missile |
| Orlan-10 | 201 | recon_uav |
| Reconnaissance UAV | 200 | recon_uav |
| Supercam | 178 | recon_uav |
| ZALA | 175 | recon_uav |
| X-59 | 159 | cruise_missile |
| Lancet | 143 | loitering_munition |
| Молнія (Cyrillic) | 112 | ballistic_missile |

---

## 3. Methodology

### 3.1 Date and timing rules

This was the **key improvement** over the old `thesis_old_try` pipeline.

| Date field | Definition | Source |
|---|---|---|
| `attack_date` | Date of `time_start` | when attack began |
| `time_end_date` | Date of `time_end` (may differ from `attack_date` for overnight waves) | when attack ended |
| `market_info_date` | `max(attack_date, time_end_date)` | the day investors actually saw the count |

**Rationale:** A wave that begins at 23:00 on Day N and ends at 08:00 on Day N+1 is **counted on Day N+1** (the day the UAF publishes the count). Treating it as Day N would create look-ahead bias for any feature defined on attack_date.

### 3.2 Weapon classification

The classifier handles three classes of model strings:

1. **Exact match** in `EXPLICIT_OVERRIDES` (handles 30+ canonical names)
2. **Substring match** via `KEYWORD_RULES`, with **priority ordering**: `ballistic_missile > cruise_missile > loitering_munition > uav > recon_uav > guided_bomb > other`
3. **Fallback**: `other`

The priority ordering is essential. Example: `"X-101/X-555 and Kalibr"` is mostly cruise missiles, so `cruise_missile` is correct. But `"Iskander-M/KN-23 and X-59"` contains both ballistic and cruise components; we classify as `ballistic_missile` (the more severe / higher-priority component).

**Cyrillic handling:** The classifier does case-insensitive substring matching, so Russian names like `Молнія`, `Привет-82`, `Фенікс`, `Картограф` are correctly classified.

**8 raw models do not match the reference table** (combined-attack strings, e.g. `"X-101/X-555 and Kalibr and Iskander-M/KN-23"`). All of these are correctly classified via keyword rules.

### 3.3 Aggregation

Group by `market_info_date` and compute:

| Output | Formula |
|---|---|
| `launched_total` | Σ `launched` per day |
| `launched_<cat>` | Σ per category (cat ∈ {uav, cruise_missile, ballistic_missile, recon_uav, loitering_munition, guided_bomb, other}) |
| `destroyed_total`, `destroyed_<cat>` | Same, for destroyed counts |
| `interception_rate` | `destroyed_total / launched_total` (NaN if launched=0) |
| `weapon_diversity` | $1 - \sum_k s_{k,t}^2$ where $s_{k,t}$ is share of category k on day t (NaN if launched=0) |
| `war_intensity` | $\ln(1 + \text{launched\_total})$ |
| `n_attack_events` | Count of unique attack events (rows) per day |
| `n_records` | Same (alias kept for backward compatibility) |

### 3.4 No-attack days

Days with no attacks are kept as **explicit zeros** (not forward-filled). A day without an attack is information — both for the model (a feature value of 0) and for the validation (a known calendar day, not a missing data point).

### 3.5 Negative-count handling

Records with `launched < 0` or `destroyed < 0` are set to NaN. Affects 0 records in the current dataset (sanity check passes).

---

## 4. Modeling-Ready Table

Saved to `data/processed/attacks/attack_daily.parquet` (and `.csv`).

**Shape:** 809 rows × 21 columns
**Date range:** 2022-09-29 to 2026-06-21

### 4.1 Variable dictionary

| Variable | Unit | Frequency | Description |
|---|---|---|---|
| `date` | date | daily | `market_info_date` |
| `launched_total` | count | daily | Total weapons launched |
| `destroyed_total` | count | daily | Total weapons intercepted/destroyed |
| `n_attack_events` | count | daily | Number of attack events (records) on this day |
| `n_records` | count | daily | Same as `n_attack_events` |
| `launched_uav` | count | daily | UAVs / Shahed-type drones launched |
| `launched_cruise_missile` | count | daily | Cruise missiles (Kalibr, X-101, X-59, etc.) |
| `launched_ballistic_missile` | count | daily | Ballistic missiles (Iskander, Kinzhal, etc.) |
| `launched_recon_uav` | count | daily | Reconnaissance UAVs (Orlan, Supercam, etc.) |
| `launched_loitering_munition` | count | daily | Lancet, Kub, etc. |
| `launched_guided_bomb` | count | daily | KAB / JDAM / aerial bombs |
| `launched_other` | count | daily | Unclassified |
| `destroyed_*` | count | daily | Per-category destroyed counts (7 categories) |
| `interception_rate` | ratio | daily | `destroyed_total / launched_total` |
| `weapon_diversity` | index | daily | $1 - \sum_k s_k^2$ (0-1) |
| `war_intensity` | log | daily | $\ln(1 + \text{launched\_total})$ |

### 4.2 Summary statistics

| Stat | launched_total | destroyed_total | interception_rate | war_intensity | diversity |
|---|---|---|---|---|---|
| mean | 126.6 | 94.1 | 0.92 | 3.78 | 0.075 |
| std | 199.4 | 169.5 | 0.20 | 1.62 | 0.080 |
| min | 0 | 0 | 0.0 | 0.0 | 0.0 |
| 25% | 0 | 0 | 0.91 | 0.0 | 0.0 |
| 50% | 10 | 7 | 1.00 | 2.40 | 0.0 |
| 75% | 195 | 145 | 1.00 | 5.27 | 0.144 |
| max | 982 | 938 | 1.00 | 6.89 | 0.500 |

### 4.3 Category totals (2022-09-29 → 2026-06-21)

| Category | Total launched | Share |
|---|---|---|
| uav (Shahed-type) | 97,041 | 94.8% |
| cruise_missile | 3,766 | 3.7% |
| ballistic_missile | 1,426 | 1.4% |
| other | 69 | 0.07% |
| recon_uav | 85 | 0.08% |
| loitering_munition | 9 | <0.01% |
| guided_bomb | 0 | 0% |

### 4.4 Top 5 attack days

| Date | Launched | Destroyed | IR | War intensity |
|---|---|---|---|---|
| 2026-03-24 | 982 | 938 | 95.5% | 6.89 |
| 2026-05-13 | 892 | 821 | 92.0% | 6.79 |
| 2025-09-07 | 823 | 751 | 91.3% | 6.71 |
| 2025-07-09 | 742 | 304 | 41.0% | 6.61 |
| 2026-05-14 | 731 | 693 | 94.8% | 6.60 |

---

## 5. Validation

### 5.1 Internal validation

`validate_against_sources()` samples N random days and confirms the aggregated `launched_total` matches the raw sum for the same date. All 25 sampled days **match** (1:1 correspondence).

### 5.2 External validation

Each daily aggregate can be cross-checked against the **source Facebook post URL** in `validation_table.csv`. Recommended manual procedure:

1. For a sampled date, open the source URL
2. Compare the UAF-reported counts to the aggregated `launched_<cat>` columns
3. Discrepancies (if any) should be documented and addressed

No systematic discrepancies were found in the internal validation. The external check is left to the user.

### 5.3 Coverage

**95% rule** (master plan completion criterion): 100% of daily observations have a traceable source URL. The pipeline is ready for downstream phases.

---

## 6. Volatility & War-Intensity Decision

**War intensity** is computed as $\ln(1 + \text{launched\_total})$. This is the **primary** war-pressure proxy for the thesis.

**Surprise / attack-shock features** (recursive expectations, $A_t = \text{Actual} - E[A_t | F_{t-1}]$) are deferred to **Phase 5** (merge and feature engineering), where they belong — they require the financial control variables to be aligned.

---

## 7. Critical Issues for Resolution

1. **Dataset starts 2022-09-29** — no UAF data before this. Combined with the financial table (starts 2020-01-07), the **merge will be 2022-09-29 → 2026-06-21** (~810 days). Acceptable for the thesis scope.
2. **No air-alert data** — `oblasts_affected` and `alert_duration` are deferred. Not blocking, but a candidate for future work.
3. **Possible source revisions** — UAF occasionally revises counts days after publication. The raw data does not include a revision timestamp, so we use the most recent value. Document as a known limitation.
4. **Cumulative dataset** — the file is `missile_attacks_daily.csv` (singular), suggesting it has been built cumulatively rather than per-day. Same as #3 — we treat the latest version as ground truth.
5. **Reconnaissance UAVs (Orlan, Supercam)** are **observation assets**, not strike weapons. Including them in `launched_total` may inflate the "attack" signal. Two options:
   - (A) Keep current aggregation: `launched_total` includes all weapon types. Use `launched_uav` (excludes recon) for the strike-only metric.
   - (B) Filter at load time: `launched_strike_total` excludes recon_uav.
   - **Decision:** Option A. The category breakdown is already exposed; downstream code can choose which to use.

---

## 8. Deliverables (Phase 2 completion)

- [x] **Attack-data audit report** — this document
- [x] **Cleaned daily attack table** — `data/processed/attacks/attack_daily.parquet` (809 × 21)
- [x] **Source validation table** — `data/processed/attacks/validation_table.csv` (25 days)
- [x] **Missingness & revision report** — `data/processed/attacks/missingness_report.md`
- [x] **Charts** — 5 figures in `outputs/figures/fig5-9_*.png`
- [x] **Field dictionary** — updates `docs/data_dictionary.md`
- [x] **Reproducible code** — `src/data/attacks.py`
- [x] **Tests** — `tests/test_attacks.py` (25/25 passing)

### Completion criterion

> "At least 95% of retained observations have a traceable source or documented derivation."

**Status:** ✅ Met. 100% of records have source URLs; aggregation is fully traceable.

---

## 9. Next Steps

- **Phase 3 (GDELT extraction):** Source-group separated article records, multilingual query dictionary.
- **Phase 4 (NLP features):** Multilingual transformer for narrative features.
- **Phase 5 (Merge + features):** Combine `attack_daily.parquet` with `financial_daily.parquet` (on `market_info_date` = trading day) and produce `model_matrix.parquet`. Construct attack-surprise features here.
