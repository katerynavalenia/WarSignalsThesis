# Source Inventory

**Status:** Template — all sources are **planned** or **unverified** until the corresponding audit phase is complete.

---

## Financial data

| Source | Data | Coverage | Frequency | Status | Audit phase | Notes |
|---|---|---|---|---|---|---|
| **ITA ETF (primary)** | iShares U.S. Aerospace & Defense ETF | 2020-01 → present | daily | **verified** | Phase 1 | **PRIMARY target** — WAERLST proxy, fetched free via yfinance |
| yfinance → ITA | constituents of ITA | implicit in NAV | daily | **verified** | Phase 1 | Public, reproducible |
| Bloomberg (archival) | `WAERLST` constituents | 2020-01-01 → 2026-06-04 | daily | **verified (noisy)** | Phase 1 | Reconstructed; ρ=0.15 vs ITA — kept for archival only |
| Bloomberg (reconstructed) | `BSHIELDT` constituents | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | European robustness; no free full-history proxy available |
| Bloomberg (delivered) | `SXXP` Index | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | Stoxx 600 European market control |
| Bloomberg (delivered) | `SPX` Index | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | S&P 500 broad-market control |
| Bloomberg (delivered) | `NDDUWI` Index | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | MSCI World global control |
| Bloomberg (delivered) | `CO1` Comdty | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | Brent crude oil |
| Bloomberg (delivered) | `EURUSD` Curncy | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | EUR/USD FX |
| Bloomberg (delivered) | `VIX` Index | 2020-01-01 → 2026-06-04 | daily | **verified** | Phase 1 | Cboe volatility index |
| Bloomberg (pending) | `WAERLST` Index | TBD | daily | **pending** | Phase 1 | Official series (optional, for final validation only) |
| Bloomberg (pending) | `USGG10YR` Index | TBD | daily | **pending** | Phase 1 | Interest-rate control (optional) |

### Bloomberg audit checklist (Phase 1) — completed

- [x] Inventory all delivered files.
- [x] Record exact field codes (PX_LAST).
- [x] Confirm date range and coverage.
- [x] Check missing trading days.
- [x] Check duplicate rows.
- [x] Confirm price vs total-return — **TR for WAERLST/BSHIELDT** (per TradingView/Bloomberg).
- [x] Confirm currency and timezone.
- [x] Identify index launch dates and back-tested history.
- [x] Confirm OHLC availability — **Not available** (close-only).
- [x] Confirm intraday availability — **Not available**.
- [x] Compare returns against Bloomberg charts for selected dates.

---

## Physical attack data

| Source | Data | Coverage | Frequency | Status | Audit phase | Notes |
|---|---|---|---|---|---|---|
| Ukrainian Air Force (UAF) | Daily attack reports | 2022-09-29 → 2026-06-20 | daily | **verified** | Phase 2 | Primary source — 3,812 records, 100% with source URL |
| Weapon reference table | Model → category mapping | 64 weapons | static | **verified** | Phase 2 | From UAF reference data, supplemented by keyword rules |
| Ukrainian Ministry of Defence | Attack announcements | TBD | daily | **deferred** | Phase 2 | UAF data is sufficient for the thesis |
| Air-alert datasets | Alert duration and oblast coverage | TBD | daily | **deferred** | Phase 2 | `oblasts_affected`, `alert_duration` deferred; not blocking |
| External structured trackers | Validation counts | TBD | daily | **deferred** | Phase 2 | Source URLs in raw data allow manual validation |

### Attack data audit checklist (Phase 2) — completed

- [x] Select source hierarchy (UAF as primary)
- [x] Download or compile official daily reports (3,812 records)
- [x] Standardize weapon categories (7 categories: uav, cruise_missile, ballistic_missile, recon_uav, loitering_munition, guided_bomb, other)
- [x] Resolve date and timestamp rules (`market_info_date = max(attack_date, time_end_date)`)
- [x] Create launched, destroyed, interception rate, weapon diversity, per-category counts
- [x] Validate against original reports (25 random days sampled, all match)
- [x] Document category dictionary (in audit §3.2)
- [x] Document missingness and revisions (`data/processed/attacks/missingness_report.md`)

---

## News data

| Source | Data | Coverage | Frequency | Status | Audit phase | Notes |
|---|---|---|---|---|---|---|
| GDELT | Article-level records | 2022-09-29 → 2026-06-21 (planned) | daily | **prep complete** | Phase 3 | Multilingual news — **run on Colab** (API extraction + dedup) |
| GDELT | Tone / themes | TBD | daily | planned | Phase 4 | NLP features (Phase 4) |

### GDELT audit checklist (Phase 3) — prep complete; Colab run pending

> **⚠️ Colab required.** GDELT article-level extraction involves hundreds of API calls (2–6 hours) and near-duplicate deduplication on 500K–2M articles (MinHash/LSH, high RAM). Run on Colab with Google Drive storage. See [`docs/colab_03_setup.md`](../colab_03_setup.md) for step-by-step instructions.

- [x] Define multilingual keyword dictionary → `config/gdelt_queries.yaml` (4 queries, 6 languages: EN, RU, UA, DE, FR, PL)
- [x] Build reproducible extraction → `src/data/gdelt.py` + `notebooks/colab_03_gdelt_extraction.ipynb`
- [x] Separate source geography from language → `config/source_groups.yaml` (4 groups: Ukrainian / Russian / Western / Other)
- [x] Classify sources into Ukrainian, Russian, Western groups → domain-based lookup
- [x] Deduplicate (MinHash + LSH, 5-gram shingles, Jaccard ≥ 0.7) → in notebook Cell 5
- [ ] Manually assess query precision → 100 articles to label (after Colab run)
- [x] Record extraction dates → in metadata

---

## NLP / transformer models

| Source | Data | Coverage | Frequency | Status | Audit phase | Notes |
|---|---|---|---|---|---|---|
| Multilingual transformer | Threat / escalation scores | TBD | daily | planned | Phase 4 | One model; not yet selected — **run on Colab GPU** |
| Manual annotation | Labeled validation sample | TBD | — | planned | Phase 4 | Required for validation — human work, not Colab |

> **⚠️ Colab GPU required for Phase 4.** Transformer inference on 500K–2M articles needs T4 or A100 GPU. Fine-tuning (if needed) also on Colab GPU. See [`instructions.md`](../instructions.md) § "Colab delegation".

---

## Control variables

| Source | Data | Coverage | Frequency | Status | Audit phase | Notes |
|---|---|---|---|---|---|---|
| Bloomberg | Oil, FX, rates, market vol | TBD | daily | unverified | Phase 1 | Financial controls |
| GPR index | Geopolitical risk | TBD | daily | planned | Phase 2 | Optional robustness control |

---

## Archived data (`thesis_old_try/`)

The `thesis_old_try/` directory is a residual archive of a previous attempt. Per the [salvage audit](thesis_old_try_audit.md) completed on 2026-06-28:

- **Active data has been transferred** to the new `data/raw/` structure (see individual source sections above).
- **Reference processed files** moved to `data/interim/` and `data/external/`.
- **Firm-level processed panels, output tables/figures/logs, and obsolete scripts have been deleted.**

The `thesis_old_try/` folder is retained **only** for:

1. **Raw data** (duplicate of `data/raw/`) — kept as a safety copy until the new pipeline produces validated outputs.
2. **Four high-reuse scripts** (`01_bloomberg_parse.py`, `03_uaf_variables.py`, `04_gpr_variables.py`, `08_gdelt_download.py`) — kept for reference while `src/data/` modules are being built.
3. **Reference PDF** (`Master Thesis Coding Context and Requirements.pdf`) — original requirements document, superseded by the research plan.

This directory will be deleted entirely once the new pipeline is validated.

---

## Notes

- Do not download external data, query GDELT, or scrape reports until the corresponding phase is authorized.
- Do not invent Bloomberg fields, confirmed coverage, credentials, sources, or results.
- All sources must have documented: coverage, frequency, licence, download method, and missingness.
