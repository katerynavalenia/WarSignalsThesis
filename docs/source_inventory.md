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
| GDELT GKG | Article-level records (12 cols incl. TONE, COUNTRIES) | 2022-09-29 → 2026-06-21 | daily | **extracted** | Phase 3 | 5.1 GB raw, 12M articles; stored locally + Google Drive |
| GDELT GKG | Source classification (hybrid) | 2022-09-29 → 2026-06-21 | daily | **classified** | Phase 3 | 88.5% coverage via domain+country+TLD hybrid |
| GDELT GKG | Tone per source group | 2022-09-29 → 2026-06-21 | daily | **pending pipeline run** | Phase 3 | Daily aggregate output ready |

### GDELT audit checklist (Phase 3)

> **✅ Extraction complete.** Bulk download via GKG raw files (no rate limit, no quota). 184 enriched parquets (12 columns: date, domain, url, tone_*, countries, persons, orgs, themes, query_name). Stored in `data/news_colab_sim/war_signals_phase3/raw_enriched/` and `WarSignalsThesis_Data/data/raw_enriched/` on Google Drive.

- [x] Define multilingual keyword dictionary → `config/gdelt_queries.yaml` (4 queries, 6 languages: EN, RU, UA, DE, FR, PL)
- [x] Build reproducible extraction → `gkg_bulk_download.py` (resumable monthly batches, memory-bounded)
- [x] Separate source geography from language → `config/source_groups.yaml` (4 groups: Ukrainian / Russian / Western / Other) + `config/country_groups.yaml` (49 country codes including GKG-specific)
- [x] Classify sources via hybrid method → `classify_source_enhanced()` in `src/data/gdelt.py` (domain → country → TLD → fallback)
- [x] Deduplicate by URL → 11M articles after dedup (GKG bulk has no title field; URL is the only viable approach)
- [x] 42 unit tests for classifier → `tests/test_classifier_enhanced.py` (all passing)
- [x] Data sharing infrastructure → rclone + Google Drive + Colab notebook (see `docs/data_sharing.md`)
- [ ] Run post-processing pipeline → `scripts/phase3_post_process_enriched.py --chunk-size 1000000` (chunked for memory safety)
- [ ] Run sensitivity analysis → `scripts/phase3_sensitivity_analysis.py` (compares 5 strategies)
- [ ] Manually assess classification precision → 400 articles in `manual_precision_audit_enriched.csv` to label
- [x] Record extraction dates → in metadata

### Infrastructure notes

- **Local**: Data in `data/news_colab_sim/war_signals_phase3/raw_enriched/` (5.1 GB, 184 files)
- **Google Drive**: `WarSignalsThesis_Data/data/raw_enriched/` (mirrored, 5.095 GiB)
- **Colab**: `notebooks/colab_03b_phase3_pipeline.ipynb` — mounts Drive, clones repo, runs pipeline
- **Multi-machine**: rclone + refresh token (see `docs/data_sharing.md` for setup)
- **Cost**: $0 (within Google Drive free tier 15 GB)

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
