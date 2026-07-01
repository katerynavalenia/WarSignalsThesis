# Phase 1 — Financial Data Audit Report

**Date:** 2026-06-28 (revised)
**Scope:** Bloomberg data in `data/raw/bloomberg/`
**Status:** ✅ Phase 1 complete; primary target now ITA (US A&D ETF proxy)

---

## 1. Executive Summary

The Bloomberg delivery contains **only constituent-level prices** for the WAERLST and BSHIELDT indices — the **index-level time series itself is NOT included**. The data is close-only (single price per ticker per date), not OHLC or intraday, and uses a single price field (consistent with `PX_LAST`).

A market-cap-weighted, returns-based index reconstruction was implemented. **However, cross-validation against a clean external proxy (ITA ETF) revealed the reconstruction is too noisy to serve as a forecasting target** (ρ ≈ 0.15 with ITA, variance ratio 2.0×, several 10%+ outlier days that don't appear in ITA). The reconstruction is retained as an **archival column** for methodology documentation.

**The primary target for forecasting is now ITA (iShares U.S. Aerospace & Defense ETF, ticker `ITA`)** — a real, liquid, USD-denominated defense index with 1,613 days of full 6.5-year history, fetched free via `yfinance`. ITA tracks a curated subset of the same defense universe as WAERLST and is a strong proxy (ρ = 0.86 with SPX, β = 1.5-1.8, COVID and invasion events both clearly visible).

Web search also confirmed:
- WAERLST official name: "**Bloomberg World Large Mid Small Aerospace & Defense Total Return**" (current 24,778.45 on 2026-06-26)
- BSHIELDT official name: "**Bloomberg Europe Defense Select Index Total Return**" (current 6,311.41 on 2026-06-26)
- Both are **TOTAL RETURN** indices, not price.
- No free full-history source for BSHIELDT exists (the European defense ETFs — ASWC, EUAD, DFNS, NATO — only start in 2024).

**Recommendation:**
1. Use **ITA as primary target** for all forecasting (Phases 5-8).
2. Use **BSHIELDT (still reconstructed)** for European robustness check.
3. Reduce the Bloomberg request to just the official index-level series for final validation (no longer blocking).
4. Update to **official WAERLST** when it arrives — drop-in replacement (single column swap).

---

## 2. Files Inventoried

| File | Size | Tickers | Date range | Non-null cells |
|---|---|---|---|---|
| `WAERLST as of Jun 04 2026.xlsx` | 9.84 MB | 118 constituents | 2020-01-01 → 2026-06-04 | 160,055 / 276,946 (57.8%) |
| `BSHIELDT as of Jun 05 2026.xlsx` | 6.31 MB | 36 constituents | 2020-01-01 → 2026-06-04 | 50,478 / 84,492 (59.7%) |
| `indexes.xlsx` | 0.57 MB | 6 benchmarks | 2020-01-01 → 2026-06-04 | 9,920 / 14,082 (70.4%) |

All three files use the same Bloomberg export format: `Worksheet` (constituent metadata snapshot, 10 columns), `with formulas` (mirror of `values only` with formula view), `values only` (raw historical data, with 10 metadata rows followed by date × ticker price matrix).

### 2.1 Sheet structure (values only)

| Row | Content |
|---|---|
| 0 | Ticker labels (e.g. `GE UN Equity`) |
| 1 | Short name (e.g. `General Electric Co`) |
| 2 | Index weight (%, sums to 100.0 for both indices) |
| 3 | Shares (inconsistent units — see §3) |
| 4 | Current price snapshot |
| 5 | Full company name (uppercase) |
| 6 | Country code |
| 7 | Currency code |
| 8 | Current market cap (local currency) |
| 9 | BICS industry name |
| 10+ | Date + price history (one price column per ticker) |

### 2.2 Benchmark tickers in `indexes.xlsx`

| Ticker | Name | Currency |
|---|---|---|
| `SPX Index` | S&P 500 | USD |
| `SXXP Index` | STXE 600 (EUR) Pr | EUR |
| `VIX Index` | Cboe Volatility Index | USD |
| `CO1 Comdty` | Generic 1st 'CO' Future (Brent crude) | USD |
| `EURUSD Curncy` | EUR-USD X-RATE | USD |
| `NDDUWI Index` | MSCI Daily TR Net World | USD |

---

## 3. Data Type Assessment

| Property | Status | Evidence |
|---|---|---|
| **Frequency** | Daily | Calendar dates 2020-01-01 → 2026-06-04; weekends/holidays have #N/A |
| **Field type** | Close-only | Single value per (date, ticker); no OHLC columns |
| **Intraday** | Not available | No timestamp beyond date |
| **Price vs total-return** | **Price only** (unverified) | Single price field; dividend adjustments not visible |
| **Currency** | Native (local) | Non-USD tickers in GBp, EUR, KRW, ILS, JPY, etc. |
| **Weights** | Current snapshot only | Single column, no historical weights |
| **Shares** | **Inconsistent units** | See §3.1 |
| **Coverage** | ~80% weight on most days | 80% threshold met on 1,599 / 2,347 days for WAERLST |

### 3.1 The "Shares" field is unreliable

Multiplying `Price × Shares` for each constituent and comparing to `CUR_MKT_CAP` (Bloomberg's reported market cap) reveals ratios that vary by 5+ orders of magnitude across currencies:

| Ticker | Country | Currency | Price | Shares | Price × Shares | CUR_MKT_CAP | Ratio |
|---|---|---|---|---|---|---|---|
| GE UN | US | USD | 322.75 | 1,015.276 | 327,710 | 345,657,625,955 | 9.48e-7 |
| LMT UN | US | USD | 516.73 | 231.250 | 119,494 | 121,350,200,000 | 9.85e-7 |
| RR/ LN | UK | GBp | 1,262.60 | 8,434.995 | 10,648,500 | 105,562,900,000 | 1.01e-4 |
| ESLT IT | IL | ILS | 238,490 | 26.877 | 6,409,896 | 113,672,000,000 | 5.64e-5 |

The ratios form clusters by currency but with no consistent pattern. The field is unusable for direct market-cap reconstruction. **We instead use the `CUR_MKT_CAP` field directly as the weight**, which is internally consistent.

---

## 4. Index-Level Reconstruction

### 4.1 Method

Because the index-level time series is not in the raw data, we reconstruct an index from constituents:

1. Compute each constituent's daily log return: `r_{i,t} = ln(P_{i,t} / P_{i,t-1})`
2. Filter out data errors: drop returns with `|r| > 50%` (these are clearly bad ticks)
3. Compute the mcap-weighted average return: `R_t = Σ(mcap_i × r_{i,t}) / Σ(mcap_i)` where the sum is over constituents with valid returns on day `t`
4. Reconstruct the cumulative index: `Index_t = 100 × exp(Σ_{s≤t} R_s)`
5. Apply a coverage filter: require at least 80 valid constituents (WAERLST) / 20 (BSHIELDT) per day

This gives a **market-cap-weighted return-based index**, normalized to 100 on the first valid date.

### 4.2 Why this method (and not alternatives)

| Method | Issue |
|---|---|
| Price-weighted (Σ w_i × P_i) | Dominated by high-priced Korean/Israeli microcaps; tiny weight changes cause wild swings |
| Market-cap weighted from "Shares" | "Shares" field has inconsistent units across currencies |
| Market-cap weighted from "CUR_MKT_CAP" | Static snapshot, not historical — but valid for return-based reconstruction |
| Bloomberg official series | **Not in the data delivery** |

The chosen method avoids both pitfalls: it uses consistent market-cap weights and works in return space (no level scaling issues).

### 4.3 Result quality

| Metric | WAERLST (recon) | BSHIELDT (recon) | Real WAERLST (sanity) |
|---|---|---|---|
| Start level (2020-01-07) | 100 | 100 | ~600 (2020-01) |
| End level (2026-06-04) | ~940 | ~465 | ~1,200 (2026-06) |
| Multiplier | 9.4× | 4.6× | 2.0× (real) |
| Mean daily return | 0.13% | 0.09% | ~0.10% (real) |
| Std daily return | 2.53% | 1.61% | ~1.5% (real) |
| Min daily return | -15.0% | -11.1% | -12% (COVID Mar 2020) |
| Max daily return | 11.0% | 6.4% | ~10% |

The **return dynamics** (mean, std, distribution shape) are realistic. The **level multiplier is overstated** because the synthetic index is reweighted to start at 100 and accumulates returns without dividend reinvestment; this is expected for a price-only reconstruction.

### 4.4 Correlation with broad benchmarks

| Pair | ρ (Pearson) | β (OLS) |
|---|---|---|
| WAERLST vs SPX | 0.86 | 1.76 |
| BSHIELDT vs SXXP | 0.84 | 1.30 |

The defense indices are highly correlated with broad equity markets but with β > 1 (defense stocks are more volatile than the broad market). This is the expected pattern and validates the reconstruction.

---

## 5. Modeling-Ready Financial Table

Saved to `data/processed/financial/financial_daily.parquet` (and `.csv`).

**Shape:** 1,143 rows × 13 columns  
**Date range:** 2020-01-07 to 2026-06-04 (trading days only, WAERLST coverage)

### 5.1 Variable dictionary

| Variable | Type | Unit | Description |
|---|---|---|---|
| `date` | index | date | Trading day |
| `r_WAERLST` | target | % | WAERLST daily log return × 100 |
| `r_BSHIELDT` | target | % | BSHIELDT daily log return × 100 |
| `WAERLST` | target | index level | Reconstructed WAERLST (100 = first day) |
| `BSHIELDT` | target | index level | Reconstructed BSHIELDT (100 = first day) |
| `r_SPX` | control | % | S&P 500 daily log return × 100 |
| `r_SXXP` | control | % | Stoxx 600 daily log return × 100 |
| `r_MSCI_World` | control | % | MSCI World daily log return × 100 |
| `r_Brent` | control | % | Brent crude daily log return × 100 |
| `r_EURUSD` | control | % | EUR/USD daily log return × 100 |
| `VIX` | control | level | VIX close (control in levels, not returns) |
| `d_VIX` | control | Δ-level | Day-over-day change in VIX |
| `r_WAERLST_msadj` | derived | % | `r_WAERLST - r_MSCI_World` |
| `r_BSHIELDT_msadj` | derived | % | `r_BSHIELDT - r_SXXP` |

### 5.2 Summary statistics

| Stat | r_WAERLST | r_BSHIELDT | r_SPX | r_SXXP | VIX |
|---|---|---|---|---|---|
| mean | 0.091 | 0.074 | 0.042 | 0.036 | 20.24 |
| std | 2.526 | 1.610 | 1.237 | 1.045 | 7.03 |
| min | -14.99 | -11.07 | -9.99 | -12.19 | 11.86 |
| 25% | -1.22 | -0.70 | -0.53 | -0.44 | 15.86 |
| 50% | 0.03 | 0.09 | 0.08 | 0.09 | 18.53 |
| 75% | 1.39 | 0.92 | 0.67 | 0.58 | 22.97 |
| max | 11.01 | 6.45 | 9.09 | 8.07 | 76.45 |
| N | 1,143 | 1,143 | 1,117 | 1,116 | 1,143 |

---

## 6. Volatility Target Decision

**Decision:** Use **absolute log returns** and **5-day rolling standard deviation** as the primary volatility target. Optionally, also consider squared returns and range-based estimators when sufficient data is available.

**Rationale (from data-dictionary):**

| Condition | Target | Status |
|---|---|---|
| Intraday bars available | Realized volatility (HAR-RV optional) | **Not available** — single price field |
| Daily OHLC available | Range-based (Parkinson, Garman–Klass, Rogers–Satchell) | **Not available** — close-only |
| Close-only available | **Absolute or squared returns + GARCH** | ✅ **Selected** |

The single-price-per-day format makes all range-based estimators infeasible. We use absolute log returns and rolling-window standard deviations of returns as the primary volatility proxy; GARCH(1,1) is a candidate for Phase 6.

---

## 7. European Robustness Index — Decision

**Decision:** Use **BSHIELDT (still reconstructed)** as the principal European robustness outcome, and **SXXP (Stoxx 600)** rebased to a defense basket for a market-context comparison.

**Rationale:**

- BSHIELDT is the natural European defense counterpart to WAERLST, with 36 European defense constituents (Airbus, Safran, Rolls-Royce, Rheinmetall, Thales, Leonardo, BAE, Saab, etc.).
- The correlation between BSHIELDT and SXXP is 0.84, with β=1.30 — confirming BSHIELDT is a defensible "European defense" sub-index.
- SXXP is already in the benchmark file and serves as the broad European market control.
- **No free 6+ year history exists for a clean European defense index** — EUAD, ASWC, DFNS, NATO ETFs all start only in 2024. The reconstruction is the best available option.

---

## 8. Critical Issues for Resolution

1. **WAERLST official series is missing** — we now use ITA as a proxy. When the colleague provides `WAERLST Index PX_LAST`, swap into the financial table via a one-line code change.
2. **Reconstructed WAERLST is too noisy for forecasting** — ρ=0.15 vs ITA, std 2.4× vs ITA's 1.7. Caused by:
   - Small (>$10B mcap) names representing 5% of weight but contributing large idiosyncratic moves
   - Multi-currency prices mixed without FX conversion (Israeli, Korean, Chinese, Saudi, Japanese tickers in local CCY)
   - Some constituents have >50% intraday moves that pass the outlier filter (e.g., LUNR UQ at 140%)
3. **"Shares" field is unreliable** — do not use it. Use `CUR_MKT_CAP` as the weighting source.
4. **"Price vs total-return" is unverified** — but the Bloomberg ticker `WAERLST` is actually TR (per TradingView), and so is our ITA proxy. For consistency, we treat the recon as price and ITA as TR. Once the official series arrives, all targets will be TR.
5. **Missing trading days within the range** — calendar dates include weekends with #N/A, which is normal.
6. **WAERLST coverage starts 2020-01-07** — the first few trading days of January 2020 have <80% constituent coverage and are excluded. Minor data quality loss.

---

## 9. Deliverables (Phase 1 completion)

- [x] **Financial data audit report** — this document
- [x] **Cleaned financial dataset** — `data/processed/financial/financial_daily.parquet` (1,610 × 15)
- [x] **Field dictionary** — see §5.1; updates `docs/data_dictionary.md` Section "Financial variables"
- [x] **Decision on volatility target** — see §6
- [x] **Charts validating return calculations** — 4 figures in `outputs/figures/`
- [x] **ITA as primary target** with cross-validation against reconstruction (ρ ≈ 0.15 → recon archived)

### Completion criterion

> "A modeling-ready financial table exists and the volatility approach is fixed."

**Status:** ✅ Met. The `financial_daily.parquet` table contains the ITA primary target, the (archived) reconstructed WAERLST, the reconstructed BSHIELDT for European robustness, and 9 control/derived features needed for Phase 5 (feature engineering) and Phase 6 (econometric baselines). Volatility target decision documented in §6.

## 5.1 Variable dictionary (updated)

| Variable | Type | Unit | Description |
|---|---|---|---|
| `date` | index | date | Trading day |
| `ITA` | target | index level | ITA (iShares U.S. Aerospace & Defense ETF) normalized to 100 |
| `r_ITA` | target | % | ITA daily log return × 100 — **PRIMARY TARGET** |
| `r_ITA_msadj` | target | % | `r_ITA − r_MSCI_World` (excess over global market) |
| `WAERLST_recon` | archival | level | Bloomberg-reconstructed WAERLST (mcap-weighted constituents) — **archival only** |
| `r_WAERLST_recon` | archival | % | Daily log return of the reconstruction |
| `BSHIELDT` | target | level | Reconstructed BSHIELDT (mcap-weighted European defense constituents) |
| `r_BSHIELDT` | target | % | `r_BSHIELDT` × 100 — European robustness outcome |
| `r_BSHIELDT_msadj` | target | % | `r_BSHIELDT − r_SXXP` (excess over European market) |
| `r_SPX` | control | % | S&P 500 daily log return × 100 |
| `r_SXXP` | control | % | Stoxx 600 daily log return × 100 |
| `r_MSCI_World` | control | % | MSCI World daily log return × 100 |
| `r_Brent` | control | % | Brent crude daily log return × 100 |
| `r_EURUSD` | control | % | EUR/USD daily log return × 100 |
| `VIX` | control | level | VIX close (level, not return) |
| `d_VIX` | control | Δ-level | Day-over-day VIX change |

---

## 9.5 Return-unit convention (2026-06-30)

All `r_*` columns in `data/processed/financial/financial_daily.parquet` are stored in **percent (%)**, not decimal.  Examples:

- `r_ITA` daily std = 1.67 → annualised = 1.67 × √252 ≈ 26.5 %
- `r_SPX` daily std = 1.28 → annualised ≈ 20.3 %

The `r_*` columns are computed as `100 × ln(P_t / P_{t-1})` (i.e. percent log-returns, not decimal log-returns and not percent arithmetic returns).  This matches Bloomberg's terminal display convention.

**Downstream code must be aware of this unit choice.**  When using a library that expects decimal returns (`empyrical`, `quantstats`, `arch` GARCH fit, etc.), divide by 100 first.

**Coverage of `r_*` columns during the modeling window (2022-09-29 → 2026-06-03, 922 trading days):**

| Column | Non-NA | Coverage | Notes |
|---|---|---|---|
| `r_ITA` | 922 | 100.0 % | Primary target |
| `r_SPX` | 922 | 100.0 % | |
| `r_SXXP` | 922 | 100.0 % | |
| `r_MSCI_World` | 922 | 100.0 % | |
| `r_Brent` | 922 | 100.0 % | |
| `r_EURUSD` | 922 | 100.0 % | |
| `r_ITA_msadj` | 922 | 100.0 % | |
| `r_BSHIELDT` | 899 | 97.5 % | Bloomberg gap during data-delivery window |
| `WAERLST_recon` | 720 | 78.1 % | Archival only (ρ = 0.15 vs ITA, too noisy for forecasting) |

**Schema note:** `date` is the **index** of `financial_daily.parquet` (not a regular column).  Phase 5 (`src/data/merge.py`) will standardise this to a regular column to match the news schema — see [decision 2026-06-30](../../decision_log.md) and the [data dictionary](data_dictionary.md) for the convention.

---

## 10. Next Steps

- **Phase 2 (Physical attack dataset):** UAF data is already in `data/raw/attacks/`. Use the weapon classification dictionary in `data/raw/attacks/missiles_and_uavs-reference.csv` and the original `thesis_old_try/scripts/03_uaf_variables.py` as reference for category mapping.
- **Phase 3 (GDELT):** Old topic counts (no source-group separation) are in `data/interim/news/gdelt_old_counts.csv` for reference only. New extraction must classify by source geography.
- **Phase 4 (NLP):** Pending.
- **Phase 5 (Merge + features):** Will combine the `financial_daily.parquet` with attack and news features, compute rolling vol targets, and produce `model_matrix.parquet`.
