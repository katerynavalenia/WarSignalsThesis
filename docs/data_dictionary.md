# Data Dictionary

**Status:** Phases 1, 2, and 3 all verified and complete (2026-06-30).
- Financial: `data/processed/financial/financial_daily.parquet` (1,610 × 15) — verified 2026-06-28
- Attacks: `data/processed/attacks/attack_daily.parquet` (809 × 21) — verified 2026-06-28
- News: `data/processed/news/news_daily_enriched.parquet` (1,342 × 17) — verified 2026-06-30
- News pivot: `data/processed/news/news_query_group_pivot.parquet` (1,342 × 17) — verified 2026-06-30

This dictionary follows the target master dataset schema from Section 6.1 of the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md).

## ⚠️ Schema convention (2026-06-30)

All Phase 1-3 daily tables currently use **different conventions** for the `date` key:

| Table | `date` is… |
|---|---|
| `financial_daily.parquet` | **index** (datetime64[ms]) |
| `attack_daily.parquet` | **index** (datetime64[ms]) |
| `news_daily_enriched.parquet` | **column** (datetime64, first position) |
| `news_query_group_pivot.parquet` | **column** (datetime64, first position) |

**Phase 5 will standardise all tables to `date` as the first regular column** (drop-in for the news schema). Until then, downstream code should use the `fix_date_index()` helper in `src/data/gdelt_postprocess.py` or call `df.reset_index()` explicitly.

## ⚠️ Return-unit convention (2026-06-30)

All `r_*` columns in `financial_daily.parquet` are expressed in **percent (%), not decimal**.  For example:

- `r_ITA` daily std = 1.67 → annualised = 1.67 × √252 ≈ 26.5 %
- `r_SPX` daily std = 1.28 → annualised ≈ 20.3 %

To convert to decimal, divide by 100 (`r_ITA_dec = r_ITA / 100`).  Any model that takes returns in decimal must apply this conversion explicitly.  The convention is **documented in each row of the financial table below** (Unit column = "%") and is intentional (matches Bloomberg's standard display).

Coverage of `r_*` columns during the modeling window (2022-09-29 → 2026-06-03, 922 trading days):

| Column | Non-NA | Coverage |
|---|---|---|
| `r_ITA` | 922 | 100.0 % |
| `r_BSHIELDT` | 899 | 97.5 % |
| `r_SPX` | 922 | 100.0 % |
| `r_SXXP` | 922 | 100.0 % |
| `r_MSCI_World` | 922 | 100.0 % |
| `r_Brent` | 922 | 100.0 % |
| `r_EURUSD` | 922 | 100.0 % |
| `r_ITA_msadj` | 922 | 100.0 % |
| `WAERLST_recon` | 720 | 78.1 % — too noisy for primary use |
| `r_WAERLST_recon` | 720 | 78.1 % — archival only |

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

**Phase 3 complete (2026-06-30).** See [`phase3_gdelt_audit.md`](phase3_gdelt_audit.md) for the extraction audit + §8 gap-closure report.

### Article-level variables (raw, before daily aggregation)

**Source:** GDELT GKG 2.0 bulk download (5.1 GB, 12M articles, 46 months)

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `date` | string | per article | article date | GKG field 0 | **verified** | `YYYYMMDD` or `YYYYMMDDTHHMMSSZ` format |
| `domain` | string | per article | — | GKG field 9 (RESOURCES) | **verified** | Source domain, e.g. `kyivpost.com` |
| `url` | string | per article | — | GKG field 10 (SOURCEURLS) | **verified** | Full article URL, used for dedup |
| `tone_avg` | float | per article | article date | GKG field 8 (TONE) | **verified** | Sentiment score (-100 to +100, typical range -10 to +10) |
| `tone_positive` | float | per article | article date | GKG | **verified** | Positive sentiment score |
| `tone_negative` | float | per article | article date | GKG | **verified** | Negative sentiment score |
| `tone_polarity` | float | per article | article date | GKG | **verified** | Polarity (pos vs neg balance) |
| `tone_activity` | float | per article | article date | GKG | **verified** | Activity density |
| `countries` | string | per article | — | GKG field 4 (LOCATIONS) | **verified** | Semicolon-separated ISO codes (GKG uses UP/RS/UK/EI/GM/IS/JA/KS aliases) |
| `persons` | string | per article | — | GKG field 5 | **verified** | Named persons mentioned |
| `orgs` | string | per article | — | GKG field 6 | **verified** | Named organizations mentioned |
| `themes` | string | per article | — | GKG field 3 | **verified** | GKG theme codes |
| `query_name` | string | per article | — | derived | **verified** | Which of 4 queries matched: `russian_attack_direct`, `ukraine_defense_energy`, `defense_industry_western`, `energy_war` |
| `source_group` | category | per article | — | hybrid classifier | **verified** | `ukrainian`, `russian`, `western`, `other` |
| `classification_method` | category | per article | — | derived | **verified** | `domain` (manual), `country` (GKG), `tld` (heuristic), `fallback` |

### Daily-level variables (after aggregation)

**Source:** `scripts/phase3_post_process_enriched.py` + gap closure in `scripts/phase3_close_gaps.py`, output `data/processed/news/news_daily_enriched.parquet`

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `date` | date | daily | — | derived | **verified** | First regular column (post-gap-closure, was index) |
| `n_articles_ukrainian` | count | daily | article date | derived | **verified** | Articles in Ukrainian source group |
| `n_articles_russian` | count | daily | article date | derived | **verified** | Articles in Russian source group |
| `n_articles_western` | count | daily | article date | derived | **verified** | Articles in Western source group |
| `n_articles_other` | count | daily | article date | derived | **verified** | Articles in "other" source group |
| `n_articles_total` | count | daily | article date | derived | **verified** | Total articles (sum of groups) |
| `tone_ukrainian` | score | daily | article date | derived | **verified** | Mean `tone_avg` of Ukrainian articles that day |
| `tone_russian` | score | daily | article date | derived | **verified** | Mean `tone_avg` of Russian articles that day |
| `tone_western` | score | daily | article date | derived | **verified** | Mean `tone_avg` of Western articles that day |
| `tone_other` | score | daily | article date | derived | **verified** | Mean `tone_avg` of "other" articles that day |
| `narrative_gap_ua_west` | score diff | daily | article date | derived | **verified** | `tone_ukrainian - tone_western` (the "narrative gap" the thesis hypothesises) |
| `narrative_gap_ru_west` | score diff | daily | article date | derived | **verified** | `tone_russian - tone_western` |
| `narrative_gap_ua_ru` | score diff | daily | article date | derived | **verified** | `tone_ukrainian - tone_russian` (intra-conflict gap) |
| `n_tone_ukrainian` | count | daily | article date | derived | **verified** | Sample size used for `tone_ukrainian` (= `n_articles_ukrainian`); filter low-confidence days |
| `n_tone_russian` | count | daily | article date | derived | **verified** | Sample size for `tone_russian` |
| `n_tone_western` | count | daily | article date | derived | **verified** | Sample size for `tone_western` |
| `n_tone_other` | count | daily | article date | derived | **verified** | Sample size for `tone_other` |

### Per-query × group daily pivot (Phase 3 deliverable)

**Source:** `scripts/phase3_close_gaps.py::build_query_group_pivot`, output `data/processed/news/news_query_group_pivot.parquet`

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `date` | date | daily | — | derived | **verified** | First regular column |
| `n_<group>_<query>` | count | daily | article date | derived | **verified** | 16 columns = 4 groups × 4 queries |

`<group>` ∈ `{ukrainian, russian, western, other}`, `<query>` ∈ `{russian_attack_direct, ukraine_defense_energy, defense_industry_western, energy_war}`.

**Use case:** tests the thesis sub-question *"Does weapon composition contain more information than the aggregate number of weapons launched?"* by joining per-query war-related news counts to the financial target.

### Derived features (for event study, Phase 5+)

| Variable | Unit | Frequency | Timing | Source | Status | Notes |
|---|---|---|---|---|---|---|
| `ua_news_surprise` | residual | daily | article date | derived | **planned** | $ObservedNews - \hat{E}(News \mid Attack)$ |
| `ru_news_surprise` | residual | daily | article date | derived | **planned** | |
| `west_news_surprise` | residual | daily | article date | derived | **planned** | |
| `narrative_gap_ua_west` | score diff | daily | article date | derived | **verified** | $tone\_ukrainian - tone\_western$ — see daily table above |
| `narrative_gap_ru_west` | score diff | daily | article date | derived | **verified** | $tone\_russian - tone\_western$ — see daily table above |
| `narrative_gap_ua_ru` | score diff | daily | article date | derived | **verified** | $tone\_ukrainian - tone\_russian$ — see daily table above |

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
