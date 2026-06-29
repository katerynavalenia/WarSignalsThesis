# Project Status

**Last updated:** 2026-06-29

> See the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md) for the full research plan and phase definitions.

---

## Current phase

**Phase 0 — Project setup** ✅ Complete

**Pre-Phase 1 — thesis_old_try audit** ✅ Complete (see [`docs/thesis_old_try_audit.md`](thesis_old_try_audit.md))

**Phase 1 — Financial-data audit** ✅ Complete (see [`docs/phase1_financial_audit.md`](phase1_financial_audit.md))

**Phase 2 — Physical attack dataset** ✅ Complete (see [`docs/phase2_attack_audit.md`](phase2_attack_audit.md))

**Phase 3 — GDELT extraction and source classification** ⏳ In progress
- Extraction: ✅ Complete (5.1 GB, 12M articles, 46 months, 12 columns incl. TONE, COUNTRIES)
- Infrastructure: ✅ Complete (Google Drive + rclone, Colab notebook ready)
- Pipeline: ⏳ Running on Google Colab (chunked for memory safety)
- See [`docs/phase3_gdelt_audit.md`](phase3_gdelt_audit.md), [`docs/phase3_classification_audit.md`](phase3_classification_audit.md), [`docs/data_sharing.md`](data_sharing.md)

---

## Data sharing infrastructure (2026-06-29)

- **Code**: GitHub `katerynavalenia/WarSignalsThesis` (version-controlled)
- **Data**: Google Drive `WarSignalsThesis_Data/` (5.1 GB, folder ID `1i1kkelDYszQ5Bi5Hv94NGT6wjCHkbIWU`)
- **Tooling**: rclone v1.60.1 with `tps_limit=10` (API-polite)
- **Compute**: Local (30 GB RAM) or Colab (12.7 GB free, 35 GB Pro+)
- **Setup verification**: `python scripts/verify_setup.py`
- Full docs: [`docs/data_sharing.md`](data_sharing.md)

---

## Phase 0 — Project setup

| Task | Status | Notes |
|---|---|---|
| Create repository structure | ✅ Done | Directories per research plan Section 6.2 |
| Create `instructions.md` | ✅ Done | Single AI-agent instruction file |
| Update `README.md` | ✅ Done | Links to research plan |
| Create `decision_log.md` | ✅ Done | Initial decisions from plan Section 19 |
| Create `docs/project_status.md` | ✅ Done | This file |
| Create `docs/data_dictionary.md` | ✅ Done | Template with planned variables |
| Create `docs/source_inventory.md` | ✅ Done | Template with planned sources |
| Create `.gitignore` | ✅ Done | Preserves source and docs |
| Create `requirements.txt` | ✅ Done | Minimal dependencies |
| Create config templates | ✅ Done | `paths.yaml.example`, `source_groups.yaml`, `gdelt_queries.yaml`, `model_config.yaml` |
| Add `__init__.py` and `.gitkeep` | ✅ Done | Python packages and empty dirs |

---

## Phase 1 — Financial-data audit ✅ Complete (2026-06-28, revised with ITA)

Full report: [`docs/phase1_financial_audit.md`](phase1_financial_audit.md).

### Key findings (revised)

- **Bloomberg "index" data not in delivery** — only constituent-level prices with weights.
- **Data is close-only**, single price field per ticker. Implies volatility target = returns-based (5-day rolling std, GARCH).
- **"Shares" field has inconsistent units** across currencies (USD ~ 1e-6, GBp ~ 1e-4 vs CUR_MKT_CAP). Unusable for direct mcap reconstruction; `CUR_MKT_CAP` is used instead.
- **Reconstruction method:** mcap-weighted return-based index, normalized to 100. Returns pass sanity checks for BSHIELDT but the **WAERLST reconstruction is too noisy** (ρ=0.15 vs ITA ETF proxy, std 2.4× vs ITA's 1.7). Root cause: small-cap and multi-currency constituents.
- **ITA (iShares U.S. Aerospace & Defense ETF) is now the PRIMARY target** — a real, liquid, USD-denominated defense index with 1,613 days of full 6.5-year history, fetched free via yfinance. Strong proxy for WAERLST (same defense universe, narrower geography).
- **European robustness:** BSHIELDT (still reconstructed) — no free full-history European defense index exists (ASWC/EUAD/DFNS/NATO all start in 2024).
- **Both WAERLST and BSHIELDT are TOTAL RETURN** indices (per TradingView / Bloomberg). Our ITA proxy is also TR (it's a traded ETF). BSHIELDT recon approximates price-only.

### Deliverables

- [x] Financial data audit report — `docs/phase1_financial_audit.md`
- [x] Cleaned financial dataset — `data/processed/financial/financial_daily.parquet` (1,610 × 15) with ITA as primary target
- [x] Field dictionary — updated in `docs/data_dictionary.md`
- [x] Decision on volatility target — audit §6
- [x] Validation charts — `outputs/figures/fig1-4_*.png`
- [x] Reproducible code — `src/data/financial.py` with `load_ita_proxy()`, `build_financial_table()`, `cross_validate_ita_vs_recon()`
- [x] Tests — `tests/test_financial.py` (7/7 passing)

---

## Phase 2 — Physical attack dataset ✅ Complete (2026-06-28)

Full report: [`docs/phase2_attack_audit.md`](phase2_attack_audit.md).

### Key findings

- **3,812 raw UAF attack records** aggregated to **809 unique `market_info_date` days** (2022-09-29 → 2026-06-21).
- **102,396 total weapons launched**, of which **76,126 destroyed (74.3% overall IR)**.
- **UAVs (Shahed-type) dominate** at 94.8% of total; cruise missiles 3.7%; ballistic missiles 1.4%.
- **Key fix vs. old pipeline:** `market_info_date = max(attack_date, time_end_date)` — overnight waves count on the report day, not the launch day. Eliminates look-ahead bias.
- **Weapon classifier** handles 71 model strings, including Cyrillic (`Молнія`, `Привет-82`, `Фенікс`, `Картограф`) and combined attacks (`X-101/X-555 and Kalibr`). Priority-ordered to assign `ballistic > cruise > loitering > uav > recon > guided_bomb > other` for mixed strings.
- **Reconnaissance UAVs** (Orlan, Supercam) are observation assets, not strike weapons. Kept as a separate category; users can choose to exclude.
- **25 random days validated** — aggregated count matches raw count for all 25.

### Deliverables

- [x] Attack-data audit report — `docs/phase2_attack_audit.md`
- [x] Cleaned daily attack table — `data/processed/attacks/attack_daily.parquet` (809 × 21)
- [x] Source validation table — `data/processed/attacks/validation_table.csv` (25 days)
- [x] Missingness & revision report — `data/processed/attacks/missingness_report.md`
- [x] Validation charts — `outputs/figures/fig5-9_*.png`
- [x] Reproducible code — `src/data/attacks.py` (430 lines, fully documented)
- [x] Tests — `tests/test_attacks.py` (25/25 passing)
- [x] Field dictionary — updated in `docs/data_dictionary.md`

### Deferred to Phase 5

- `attack_surprise` (recursive expectation feature) — requires financial controls; belongs in feature engineering
- `oblasts_affected`, `alert_duration` — requires air-alert data acquisition (deferred; not in core per master plan)

---

## Phase 3 — GDELT extraction and source classification ⏳ In progress

Prep work complete (2026-06-28). Colab run pending.

### Deliverables (prep)

- [x] Multilingual query dictionary — `config/gdelt_queries.yaml` (4 queries, 6 languages)
- [x] Source group classification — `config/source_groups.yaml` (Ukrainian / Russian / Western / Other)
- [x] Reproducible extraction pipeline — `src/data/gdelt.py` (~430 lines)
- [x] Colab notebook — `notebooks/colab_03_gdelt_extraction.ipynb` (8 cells)
- [x] Colab setup instructions — `docs/colab_03_setup.md`
- [x] Tests — `tests/test_gdelt.py` (21/21 passing, 1 network test skipped)
- [x] Audit report template — `docs/phase3_gdelt_audit.md` (to be filled after Colab run)

### Pipeline architecture

- **Cell 1:** Setup — mount Drive, install deps, clone repo
- **Cell 2:** Load config — read YAMLs, print summary
- **Cell 3:** Smoke test — 1 day, validate pipeline (1-2 min)
- **Cell 4:** Full extraction — 46 monthly windows × 4 queries = ~180 API calls (2-4 hours)
- **Cell 5:** Deduplication — MinHash + LSH on titles (1-2 hours)
- **Cell 6:** Classification — domain → group + langdetect (5-10 min)
- **Cell 7:** Daily aggregation — group by date+source group (1-2 min)
- **Cell 8:** Summary — print coverage stats, save manual audit sample

### Estimated output

- ~500K-2M articles (raw), ~250K-1.5M (after dedup)
- ~1 GB parquet files
- ~1,400 daily aggregate rows
- 100 articles for manual precision audit

### Next action

User runs `notebooks/colab_03_gdelt_extraction.ipynb` in Google Colab (Pro High-RAM recommended). Wall time: 4-6 hours. See `docs/colab_03_setup.md` for step-by-step instructions.

---

## Phase roadmap

| Phase | Description | Status | Compute | Run where |
|---|---|---|---|---|
| 0 | Project setup | ✅ Complete | LOW | Local |
| 1 | Financial-data audit | ✅ Complete | LOW | Local |
| 2 | Physical attack dataset | ⏳ Next | LOW | Local |
| 3 | GDELT extraction and source classification | 🔲 Not started | **HIGH** | **Colab** |
| 4 | NLP features | 🔲 Not started | **HIGH** | **Colab (GPU)** |
| 5 | Merge and feature engineering | 🔲 Not started | MEDIUM | Local |
| 6 | Econometric baselines | 🔲 Not started | MEDIUM | Local (Colab optional) |
| 7 | Machine-learning models | 🔲 Not started | MEDIUM | Local (Colab optional) |
| 8 | Statistical comparison and robustness | 🔲 Not started | LOW | Local |
| 9 | Writing | 🔲 Not started | LOW | Local |
| 10 | Final validation | 🔲 Not started | LOW | Local |

### Colab delegation summary

Phases 3 and 4 require Google Colab (Pro). See [`instructions.md`](../instructions.md) § "Colab delegation" for full rules. Key points:

- **Phase 3 (GDELT):** Article-level extraction via API (hundreds of calls, 2–6 hours) + MinHash/LSH dedup on 500K–2M articles (high RAM). Run on Colab CPU with Google Drive storage.
- **Phase 4 (NLP):** Multilingual transformer inference on 500K–2M articles (GPU required, 1–4 hours). Run on Colab T4/A100 GPU.
- **Phases 6–7 (optional Colab):** GARCH refitting (~2,400 fits) and LightGBM hyperparameter search can be delegated to Colab CPU if local is too slow.
- **Google Drive** is the shared storage bridge: Colab → GDrive → local `data/interim/`.
- Colab notebooks use `colab_` prefix in `notebooks/` (e.g., `colab_03_gdelt_extraction.ipynb`).

---

## Unresolved issues

1. **`Initial-research-specification.txt` and `Brainstorm-session-1-summary.txt`** — referenced in `prompt.md` but not found in the repository. These may need to be located or their absence documented.
2. **`thesis_old_try/` salvage audit** — ✅ Complete on 2026-06-28. Audit results in [`docs/thesis_old_try_audit.md`](thesis_old_try_audit.md). Raw data transferred to new `data/raw/` structure; reference processed files moved to `data/interim/` and `data/external/`. Firm-level processed files, all output tables/figures/logs, and obsolete scripts have been deleted. The `thesis_old_try/` folder is retained only for raw data and 4 high-reuse scripts pending `src/` extraction.
3. **Bloomberg data fields** — ✅ resolved in Phase 1. Close-only, price-level, single field. Full audit in [`phase1_financial_audit.md`](phase1_financial_audit.md). **Outstanding:** official WAERLST index-level series (we have only constituents) and price-vs-total-return verification.
4. **European robustness index** — ✅ resolved in Phase 1: BSHIELDT is the principal robustness outcome.
5. **Volatility target** — ✅ resolved in Phase 1: returns-based (5-day rolling std, GARCH). Close-only data precludes range-based estimators.
6. **Historical constituent membership** — availability unknown; needed only for the optional firm-level extension.
7. **Attack data quality** — ✅ resolved in Phase 2. See [`phase2_attack_audit.md`](phase2_attack_audit.md). Weapon classifier handles 71 model strings including Cyrillic and combined attacks; `market_info_date` correctly distinguished from `attack_date`.
8. **GDELT access** — query design and extraction not yet prototyped. Old GDELT topic counts (no source-group separation) archived at `data/interim/news/gdelt_old_counts.csv` for reference only. (Phase 3)

---

## Immediate next action

**Phase 3 — GDELT extraction and source classification.** Define multilingual keyword dictionary, build reproducible extraction, separate source geography from language, classify into Ukrainian/Russian/Western groups, dedupe. The 3,812 UAF attack records are now in `data/processed/attacks/attack_daily.parquet`; the financial table is `data/processed/financial/financial_daily.parquet` (ITA primary). Phase 3 will produce the third input table that, in Phase 5, gets merged with these.

Recommended approach (per `instructions.md` Colab delegation rules):
- Use Google Colab (Pro) for the API extraction (2-6 hours) and MinHash/LSH dedup (high RAM)
- Save article-level records to Google Drive
- Bring parquet files back to local for downstream processing
