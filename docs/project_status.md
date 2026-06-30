# Project Status

**Last updated:** 2026-06-30

> See the [`Master_Thesis_Research_Completion_Plan.md`](../Master_Thesis_Research_Completion_Plan.md) for the full research plan and phase definitions.

---

## Current phase

**Phase 0 — Project setup** ✅ Complete

**Pre-Phase 1 — thesis_old_try audit** ✅ Complete (see [`docs/thesis_old_try_audit.md`](thesis_old_try_audit.md))

**Phase 1 — Financial-data audit** ✅ Complete (see [`docs/phase1_financial_audit.md`](phase1_financial_audit.md))

**Phase 2 — Physical attack dataset** ✅ Complete (see [`docs/phase2_attack_audit.md`](phase2_attack_audit.md))

**Phase 3 — GDELT extraction and source classification** ✅ Complete (2026-06-30)
- Extraction: ✅ Complete (5.1 GB raw, 12M articles, 46 months, 12 enriched columns)
- Post-processing: ✅ Complete (URL dedup → 11.4M articles, hybrid classification, daily aggregation)
- Gap-closure: ✅ Complete (date-index fix, narrative-gap columns, query × group pivot, automated precision check, refreshed sensitivity report)
- See [`docs/phase3_gdelt_audit.md`](phase3_gdelt_audit.md), [`docs/phase3_classification_audit.md`](phase3_classification_audit.md), [`docs/data_sharing.md`](data_sharing.md)

### Phase 3 final deliverables (2026-06-30)

- [x] 11,433,653 articles URL-deduplicated from 12,108,464 raw (≈5.6% cross-month dedup)
- [x] Date range 2022-09-29 → 2026-06-21 (1,342 days)
- [x] 4 multilingual queries × 4 source groups (UA / RU / Western / Other)
- [x] Classifier coverage: 88.6% country + 4.5% domain + 0.3% TLD + 6.9% fallback
- [x] Daily aggregate: `news_daily_enriched.parquet` (1,342 × 16 — counts, tone, narrative gaps, per-group sample sizes)
- [x] Query × group pivot: `news_query_group_pivot.parquet` (1,342 × 17) for composition analysis
- [x] Automated precision check (`auto_precision_report.md`) — 6,480 high-confidence domains, overall 85.4% agreement (replaces the manual 400-article audit)
- [x] Sensitivity report refreshed on the full 46-month data (`sensitivity_report.md`)
- [x] Audit documents: [`phase3_gdelt_audit.md`](phase3_gdelt_audit.md), [`phase3_classification_audit.md`](phase3_classification_audit.md)
- [x] Gap-closure code: `src/data/gdelt_postprocess.py` + `scripts/phase3_close_gaps.py` + 13 passing tests in `tests/test_phase3_close_gaps.py`

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
| 2 | Physical attack dataset | ✅ Complete | LOW | Local |
| 3 | GDELT extraction and source classification | ✅ Complete | HIGH | Colab |
| 4 | NLP features (Tier 1 = GDELT tone ✅, Tier 2 = transformer deferred) | Tier 1 ✅ / Tier 2 after milestone | HIGH | Colab (GPU) |
| 5 | Merge and feature engineering | ⏳ **Next — critical path** | MEDIUM | Local |
| 6 | Econometric baselines | 🔲 After Phase 5 | MEDIUM | Local (Colab optional) |
| 7 | Machine-learning models | 🔲 After Phase 6 | MEDIUM | Local (Colab optional) |
| 8 | Statistical comparison and robustness | 🔲 After Phase 7 | LOW | Local |
| 9 | Writing | 🔲 After Phase 8 | LOW | Local |
| 10 | Final validation | 🔲 After Phase 9 | LOW | Local |

---

## Current delegation plan (2026-06-30)

Three parallel tracks to start now:

| Track | What | Agent prompt | Model | Colab? | Blocks milestone? |
|---|---|---|---|---|---|
| **A (critical)** | Phase 5 — Merge & feature engineering | [`agent_prompt_phase5_merge.md`](agent_prompt_phase5_merge.md) | Claude Sonnet 4 | No | **YES** |
| **B (parallel)** | Phase 6 prep — Eval & baseline code (write code only, no data) | [`agent_prompt_phase6_prep.md`](agent_prompt_phase6_prep.md) | Claude Sonnet 4 | No | No |
| **C (parallel)** | Manual labeling — Export 500-article sample for human labeling | (small script, any agent) | Any | No | No (needed for Phase 4 Tier 2 later) |

After Phase 5 completes → Phase 6 executes baselines → 🎯 **First milestone** (common OOS forecast table).

After milestone → Phase 4 Tier 2 (transformer, Colab GPU) → Phase 7 (ML) → Phase 8 (comparison) → Phase 9 (writing) → Phase 10 (validation).

### Colab delegation summary

Phases 3 and 4 require Google Colab (Pro). See [`instructions.md`](../instructions.md) § "Colab delegation" for full rules. Key points:

- **Phase 3 (GDELT):** Article-level extraction via API (hundreds of calls, 2–6 hours) + MinHash/LSH dedup on 500K–2M articles (high RAM). Run on Colab CPU with Google Drive storage.
- **Phase 4 (NLP Tier 2):** Transformer enhancement **deferred until after first milestone** (§25). GDELT tone fields from Phase 3 serve as the core NLP measure for now. When ready: fine-tune `xlm-roberta-base` on 500+ manually labeled articles, score ~67K articles on Colab T4/A100 GPU. Manual labeling can start now in parallel.
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
8. **GDELT access** — ✅ resolved in Phase 3. 11.4M articles extracted, classified into 4 source groups, daily aggregates in `news_daily_enriched.parquet`. See [`phase3_gdelt_audit.md`](phase3_gdelt_audit.md) and [`phase3_classification_audit.md`](phase3_classification_audit.md).
9. **Phase 4 NLP** — Tier 1 (GDELT tone) complete from Phase 3. Tier 2 (transformer) deferred until after first milestone. Manual labeling (500+ articles) can start now in parallel. See [`agent_prompt_phase4_nlp.md`](agent_prompt_phase4_nlp.md).

---

## Immediate next action

**Start three parallel agents now:**

1. **Phase 5 agent** (critical path) — Merge financial, attack, and news data into a leakage-safe daily master table. Prompt: [`agent_prompt_phase5_merge.md`](agent_prompt_phase5_merge.md)
2. **Phase 6 prep agent** (parallel) — Write evaluation framework and baseline model code (no data needed yet). Prompt: [`agent_prompt_phase6_prep.md`](agent_prompt_phase6_prep.md)
3. **Manual labeling export** (parallel) — Export a stratified 500-article sample across Ukrainian/Russian/English for human labeling. Needed later for Phase 4 Tier 2.

After Phase 5 completes → run Phase 6 baselines → reach first milestone → then Phase 4 Tier 2 (Colab GPU) → Phase 7 → Phase 8.
