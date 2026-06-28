# Data Dictionary

**Status:** Financial variables verified after Phase 1 (2026-06-28). Other variables remain **planned** or **unverified** until their respective audit phases.

This dictionary follows the target master dataset schema from Section 6.1 of the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md).

---

## Financial variables

**Phase 1 complete (2026-06-28, revised).** See [`phase1_financial_audit.md`](phase1_financial_audit.md) for the full audit. Modeling-ready table at `data/processed/financial/financial_daily.parquet` (1,610 × 15).

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `date` | date | daily | trading day | derived | **verified** | 2020-01-07 → 2026-06-03 |
| `ITA` | index level | daily | close | yfinance `ITA` | **verified** | **PRIMARY target** (iShares U.S. A&D ETF), normalized to 100 |
| `r_ITA` | % | daily | close-to-close | derived | **verified** | $100 \times \ln(P_t/P_{t-1})$; primary forecasting target |
| `r_ITA_msadj` | % | daily | close-to-close | derived | **verified** | `r_ITA - r_MSCI_World` (excess over global market) |
| `r_BSHIELDT` | % | daily | close-to-close | derived | **verified** | European defense robustness target (still reconstructed) |
| `BSHIELDT` | index level | daily | close | derived | **verified** | Reconstructed, normalized to 100 on 2020-01-07 |
| `r_BSHIELDT_msadj` | % | daily | close-to-close | derived | **verified** | `r_BSHIELDT - r_SXXP` |
| `WAERLST_recon` | index level | daily | close | derived | **archival** | Bloomberg-reconstructed WAERLST (mcap-weighted) — too noisy for forecasting (ρ=0.15 vs ITA) |
| `r_WAERLST_recon` | % | daily | close-to-close | derived | **archival** | Kept for methodology documentation |
| `r_SPX` | % | daily | close-to-close | Bloomberg `SPX Index` | **verified** | S&P 500 broad-market control |
| `r_SXXP` | % | daily | close-to-close | Bloomberg `SXXP Index` | **verified** | Stoxx 600 European market control |
| `r_MSCI_World` | % | daily | close-to-close | Bloomberg `NDDUWI Index` | **verified** | Global broad-market control |
| `r_Brent` | % | daily | close-to-close | Bloomberg `CO1 Comdty` | **verified** | Brent crude oil |
| `r_EURUSD` | % | daily | close-to-close | Bloomberg `EURUSD Curncy` | **verified** | EUR/USD FX |
| `VIX` | level | daily | close | Bloomberg `VIX Index` | **verified** | Cboe volatility index (level) |
| `d_VIX` | Δ-level | daily | close | derived | **verified** | Day-over-day VIX change |
| `volatility_target` | % | daily | close | derived | **decided** | 5-day rolling std of `r_ITA` (close-only data) |
| `interest_rate_change` | bp | daily | close | Bloomberg | **unverified** | Not in current delivery; defer or use GPR control |

### Volatility target hierarchy (decided)

| Condition | Target | Status |
|---|---|---|
| Intraday bars available | Realized volatility (HAR-RV optional) | **Not available** |
| Daily OHLC available | Range-based (Parkinson, Garman–Klass, Rogers–Satchell) | **Not available** — close-only |
| Close-only available | **Absolute or squared returns + GARCH** | ✅ **Selected** |

See [`phase1_financial_audit.md` §6](phase1_financial_audit.md) for the full decision rationale.

---

## Physical attack variables

**Phase 2 complete (2026-06-28).** See [`phase2_attack_audit.md`](phase2_attack_audit.md) for the full audit. Modeling-ready table at `data/processed/attacks/attack_daily.parquet` (809 × 21).

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `date` | date | daily | `market_info_date` | UAF | **verified** | 2022-09-29 → 2026-06-21 |
| `launched_total` | count | daily | info date | UAF | **verified** | total airborne weapons launched |
| `destroyed_total` | count | daily | info date | UAF | **verified** | intercepted / shot down |
| `launched_uav` | count | daily | info date | UAF | **verified** | UAVs / Shahed-type (94.8% of total) |
| `launched_cruise_missile` | count | daily | info date | UAF | **verified** | Kalibr, X-101/X-555, X-59, etc. |
| `launched_ballistic_missile` | count | daily | info date | UAF | **verified** | Iskander, Kinzhal, C-300/C-400 (as ballistic) |
| `launched_recon_uav` | count | daily | info date | UAF | **verified** | Orlan, Supercam, ZALA — observation drones |
| `launched_loitering_munition` | count | daily | info date | UAF | **verified** | Lancet, Kub |
| `launched_guided_bomb` | count | daily | info date | UAF | **verified** | KAB / JDAM / aerial bombs |
| `launched_other` | count | daily | info date | UAF | **verified** | Unclassified weapons |
| `destroyed_*` | count | daily | info date | UAF | **verified** | Same 7 categories |
| `n_attack_events` | count | daily | info date | derived | **verified** | Number of attack events (rows) on this day |
| `n_records` | count | daily | info date | derived | **verified** | Alias of n_attack_events |
| `interception_rate` | ratio | daily | info date | derived | **verified** | `destroyed_total / launched_total` (NaN if launched=0) |
| `weapon_diversity` | index | daily | info date | derived | **verified** | $1 - \sum_k s_{k,t}^2$ (0=monoculture, 1=fully diversified) |
| `war_intensity` | log | daily | info date | derived | **verified** | $\ln(1 + \text{launched\_total})$ |
| `oblasts_affected` | count | daily | attack date | air-alert data | **deferred** | Not in current dataset |
| `alert_duration` | hours | daily | alert date | air-alert data | **deferred** | Not in current dataset |
| `attack_surprise` | standardized | daily | info date | derived | **deferred** | $Actual - \hat{E}(Attack \mid \mathcal{F}_{t-1})$ — to be computed in Phase 5 with recursive expectations |

### Date fields

| Variable | Description | Status |
|---|---|---|
| `attack_date` | When the attack began (date of `time_start`) | **verified** |
| `time_end_date` | When the attack ended (date of `time_end`) | **verified** |
| `market_info_date` | When investors learned verified counts (`max(attack_date, time_end_date)`) | **verified** |
| `attack_surprise` | Recursive surprise feature | deferred to Phase 5 |

---

## News and narrative variables

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `ua_news_volume` | count | daily | article date | GDELT | planned | Ukrainian source group |
| `ru_news_volume` | count | daily | article date | GDELT | planned | Russian source group |
| `west_news_volume` | count | daily | article date | GDELT | planned | Western source group |
| `ua_sentiment` | score | daily | article date | NLP model | planned | |
| `ru_sentiment` | score | daily | article date | NLP model | planned | |
| `west_sentiment` | score | daily | article date | NLP model | planned | |
| `ua_narrative_gap` | residual | daily | article date | derived | planned | $ObservedNews - \hat{E}(News \mid Attack)$ |
| `ru_narrative_gap` | residual | daily | article date | derived | planned | |
| `west_narrative_gap` | residual | daily | article date | derived | planned | |

---

## Calendar variables

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `weekday` | category | daily | — | derived | planned | |
| `holiday_flags` | boolean | daily | — | calendar | planned | |
| `forecast_origin` | date | daily | end of day t | derived | planned | info available date |

---

## Notes

- All variables marked **planned** are defined in the research plan but not yet constructed.
- All variables marked **unverified** depend on the Bloomberg data audit (Phase 1).
- Timing column indicates when the information is available to investors, not when the event occurred.
- Every feature used in forecasting must have an "available at" timestamp ≤ end of day `t` for predicting day `t+1`.
