# War Signals and Defense Equity Risk

**Physical Air-Attack Intensity versus Multilingual News Narratives**

Master 2 Financial Technology Development thesis project. This study tests whether unexpected Russian air-attack intensity, weapon composition, interception outcomes, and multilingual news narratives improve out-of-sample forecasts of defense-equity returns and volatility.

---

## Key documents

| Document | Purpose |
|---|---|
| [`Master_Thesis_Research_Completion_Plan.md`](Master_Thesis_Research_Completion_Plan.md) | **Authoritative research plan and source of truth.** Read this first. |
| [`instructions.md`](instructions.md) | Operational coding and repository rules for AI agents. |
| [`decision_log.md`](decision_log.md) | Record of all methodological decisions. |
| [`docs/project_status.md`](docs/project_status.md) | Current phase and task status. |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Variable definitions, units, timing, and transformations. |
| [`docs/source_inventory.md`](docs/source_inventory.md) | Data source inventory and audit status. |
| [`docs/data_sharing.md`](docs/data_sharing.md) | **Data sharing architecture** (Google Drive + rclone setup, multi-machine sync). |
| [`docs/phase1_financial_audit.md`](docs/phase1_financial_audit.md) | Phase 1 financial data audit. |
| [`docs/phase2_attack_audit.md`](docs/phase2_attack_audit.md) | Phase 2 attack data audit. |
| [`docs/phase3_gdelt_audit.md`](docs/phase3_gdelt_audit.md) | Phase 3 GDELT extraction audit. |
| [`docs/phase3_classification_audit.md`](docs/phase3_classification_audit.md) | Phase 3 hybrid classifier methodology and validation. |

## Data outputs (Phases 1-3)

| File | Shape | Description |
|---|---|---|
| `data/processed/financial/financial_daily.parquet` | 1,610 × 15 | Daily financial panel (ITA primary, BSHIELDT robustness, market controls). `date` is the index. |
| `data/processed/attacks/attack_daily.parquet` | 809 × 21 | Daily UAF physical-attack table (7 weapon categories, IR, diversity, intensity). `date` is the index. |
| `data/processed/news/news_daily_enriched.parquet` | 1,342 × 17 | Daily news aggregate (counts, tone, narrative gaps, sample sizes). `date` is the first column. |
| `data/processed/news/news_query_group_pivot.parquet` | 1,342 × 17 | Daily article counts by `query × source_group` (16 combos). `date` is the first column. |
| `data/processed/news/auto_precision_report.md` | markdown | Automated classifier validation (replaces manual audit). |
| `data/processed/news/sensitivity_report.md` | markdown | 5-strategy comparison on the full 11.4M articles. |

> ⚠️ **Schema convention (2026-06-30):** `date` is the index in the financial and attack tables, but a column in the news tables. Phase 5 will standardize on `date` as the first regular column. See the [data dictionary](docs/data_dictionary.md) and [decision log](decision_log.md) for the convention.

## Gap-closure workflow (Phase 3)

Re-run the Phase 3 gap-closure steps at any time:

```bash
source .venv/bin/activate
python scripts/phase3_close_gaps.py            # full run
python scripts/phase3_close_gaps.py --dry-run  # plan only
python scripts/phase3_close_gaps.py --skip-sensitivity
python -m pytest tests/test_phase3_close_gaps.py -v   # tests
```

Total wall time: ~15 s.  Peak RAM: < 1 GB.

---

## Research summary

- **Primary outcome:** `WAERLST` — Bloomberg global aerospace & defense index.
- **Robustness outcomes:** one European aerospace & defense index (to be selected after data audit); `BSHIELDT`.
- **Frequency:** daily.
- **Design:** strict out-of-sample forecasting (expanding window).
- **Timing:** information available through day `t` predicts market outcome on trading day `t+1`.
- **Core level:** index-level. Firm-level analysis is an optional extension.
- **Framing:** predictive, not causal.

The volatility target depends on audited data availability:
1. Genuine intraday data → realized volatility (HAR-RV optional).
2. Daily OHLC → range-based volatility (Parkinson, Garman–Klass, etc.).
3. Close-only data → absolute/squared returns and GARCH.

---

## Repository structure

```
config/           Configuration templates (YAML)
data/raw/         Immutable raw data (never edit)
data/interim/     Intermediate processing outputs
data/processed/   Final analytical tables (Parquet)
data/external/    External reference data
docs/             Documentation
notebooks/        Jupyter notebooks for audits and exploration
src/data/         Data loading and cleaning modules
src/features/     Feature engineering modules
src/models/       Forecasting model modules
src/utils/        Shared utilities
tests/            Unit tests
outputs/          Figures, tables, model objects, logs
thesis/           Thesis document and chapters
thesis_old_try/   Previous attempt (archived, not active)
```

---

## Setup

```bash
# Create and activate a Python environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Configuration templates are in `config/`. Copy them and fill in local paths:

```bash
cp config/paths.yaml.example config/paths.yaml
```

---

## Colab delegation

Some phases require GPU or high-RAM resources and are delegated to **Google Colab** (Pro subscription). Google Drive serves as the shared storage bridge.

| Phase | Task | Resource | Notebook |
|---|---|---|---|
| 3 | GDELT post-processing (5.1 GB) | Colab CPU + 12 GB RAM | [`notebooks/colab_03b_phase3_pipeline.ipynb`](notebooks/colab_03b_phase3_pipeline.ipynb) |
| 4 | Transformer inference on 500K–2M articles | Colab T4/A100 GPU | TBD |
| 6–7 | GARCH refits / hyperparameter search (optional) | Colab CPU | TBD |

**Data sharing architecture** (code on GitHub, data on Google Drive via rclone):
- See [`docs/data_sharing.md`](docs/data_sharing.md) for full setup
- Drive folder: `WarSignalsThesis_Data/` (5.1 GB raw data + pipeline outputs)
- rclone configured with `tps_limit=10` to respect Drive API limits
- On Colab: mount Drive, clone repo, run pipeline (no local storage needed)
- **For rclone re-auth or sync operations**, use the [`rclone-drive-sync`](.github/skills/rclone-drive-sync/SKILL.md) skill (just say "sync to drive" in chat, or run `bash .github/skills/rclone-drive-sync/scripts/reauth.sh` when the OAuth token expires)

Phases 1, 2, 5, and 8 run locally. See [`instructions.md`](instructions.md) § "Colab delegation" for full rules.

---

## Current phase

**Phase 0 — Project setup** ✅ Complete
**Phase 1 — Financial-data audit** ✅ Complete (ITA as primary target)
**Phase 2 — Physical attack dataset** ✅ Complete (809 days, 21 columns)
**Phase 3 — GDELT extraction & classification** ⏳ In progress

Phase 3 is processing 5.1 GB of enriched GKG data (12M articles, 46 months) through:
- URL-based deduplication
- Hybrid source-group classification (domain + country + TLD)
- Daily aggregation with tone averages (TONE field from GKG)

The pipeline runs on Colab (12 GB RAM) using chunked classification. See:
- [`docs/phase3_gdelt_audit.md`](docs/phase3_gdelt_audit.md) — extraction methodology
- [`docs/phase3_classification_audit.md`](docs/phase3_classification_audit.md) — classifier validation
- [`docs/data_sharing.md`](docs/data_sharing.md) — data infrastructure

See [`docs/project_status.md`](docs/project_status.md) for detailed status.

---

## License

This repository contains academic research code for a Master's thesis. Data files are subject to their respective source licenses and are not redistributed.