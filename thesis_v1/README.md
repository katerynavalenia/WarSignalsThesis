> ## ⚠️ ARCHIVED DRAFT — superseded by `thesis_v2/`
>
> This is v1 of the project, kept as a historical record and as a source of
> reusable data/code. Its forecasting question was tested rigorously and
> found null (see [`../docs/v1/supervisor_audit.md`](../docs/v1/supervisor_audit.md)).
> The active research is now in [`../thesis_v2/`](../thesis_v2/README.md),
> with its plan at [`../docs/v2/research_plan.md`](../docs/v2/research_plan.md).
> **Do not build new work on this version's question.** If you need v1's
> data or code (financial/attack/GDELT pipelines are reused, unchanged, in
> v2), see [`../docs/v1/README.md`](../docs/v1/README.md) for exactly what
> to take and from where.

---

# War Signals and Defense Equity Risk

**Physical Air-Attack Intensity versus Multilingual News Narratives**

Master 2 Financial Technology Development thesis project. This study tests whether unexpected Russian air-attack intensity, weapon composition, interception outcomes, and multilingual news narratives improve out-of-sample forecasts of defense-equity returns and volatility.

---

## Key documents

| Document | Purpose |
|---|---|
| [`docs/v1/phase7_audit.md`](../docs/v1/phase7_audit.md) | **Latest results and hypothesis verdicts.** Read this first. |
| [`docs/source_inventory.md`](../docs/v1/source_inventory.md) | Data source inventory and audit status. |
| [`docs/data_sharing.md`](../docs/v1/data_sharing.md) | **Data sharing architecture** (Google Drive + rclone setup, multi-machine sync). |
| [`docs/phase1_financial_audit.md`](../docs/v1/phase1_financial_audit.md) | Phase 1 financial data audit. |
| [`docs/phase2_attack_audit.md`](../docs/v1/phase2_attack_audit.md) | Phase 2 attack data audit. |
| [`docs/phase3_gdelt_audit.md`](../docs/v1/phase3_gdelt_audit.md) | Phase 3 GDELT extraction audit. |
| [`docs/phase3_classification_audit.md`](../docs/v1/phase3_classification_audit.md) | Phase 3 hybrid classifier methodology and validation. |

## Data outputs (Phases 1-3)

| File | Shape | Description |
|---|---|---|
| `data/processed/financial/financial_daily.parquet` | 1,610 × 15 | Daily financial panel (ITA primary, BSHIELDT robustness, market controls). `date` is the index. |
| `data/processed/attacks/attack_daily.parquet` | 809 × 21 | Daily UAF physical-attack table (7 weapon categories, IR, diversity, intensity). `date` is the index. |
| `data/processed/news/news_daily_enriched.parquet` | 1,342 × 17 | Daily news aggregate (counts, tone, narrative gaps, sample sizes). `date` is the first column. |
| `data/processed/news/news_query_group_pivot.parquet` | 1,342 × 17 | Daily article counts by `query × source_group` (16 combos). `date` is the first column. |
| `data/processed/news/auto_precision_report.md` | markdown | Automated classifier validation (replaces manual audit). |
| `data/processed/news/sensitivity_report.md` | markdown | 5-strategy comparison on the full 11.4M articles. |

> ⚠️ **Schema convention (2026-06-30):** `date` is the first regular column in all Phase 5+ outputs (per decision log 2026-06-30). The financial and attack tables originally used `date` as the index; `build_daily_master` resets them. Regenerate the data dictionary with `python scripts/phase5_data_dictionary.py` to see the convention applied per column.

## Phase 5 outputs (model-ready)

| File | Shape | Description |
|---|---|---|
| `data/processed/daily_master.parquet` | 2,358 × 82 | Calendar-day outer-join of financial (incl. real WAERLST/BSHIELDT), attack, news, and news-pivot (2020-01-01 → 2026-06-30). |
| `data/processed/feature_matrix.parquet` | 2,358 × 156 | daily_master + engineered features (Phase 5C: vol, attack surprise, news normalizations, calendar, regime dummies). |
| `data/processed/model_matrix.parquet` | 1,358 × 154 | **Phase 5D — final input to Phase 6/7.** Lagged features (`_lag1` suffix), weekend-rule targets (`target_r_WAERLST_t1`, `target_r_BSHIELDT_t1`, `target_r_ITA_t1`), and information-set column masks in `.attrs["info_sets"]`. |
| `data/processed/data_dictionary.csv` | 154 rows | Per-column metadata (group, dtype, unit, available_at, non-null, description). |
| `outputs/tables/info_set_cardinality.csv` | 5 rows | n_features per information set (F=37, P=73, N=63, PN=115, PNG=118). |
| `outputs/tables/leakage_audit.csv` | 118 rows | Per-feature leakage flags (currently 0 critical, 0 warn). |
| `outputs/tables/descriptive_stats.csv` | 153 rows | Per-column n, mean, std, quantiles, skew, kurtosis. |
| `outputs/figures/fig10_master_coverage.png` | image | Phase 5B missingness heatmap. |
| `outputs/figures/fig11_target_distribution.png` | image | Phase 5E target histogram + log scale. |
| `outputs/figures/fig12_correlation_heatmap.png` | image | Phase 5E top-25 feature correlation heatmap. |
| `outputs/figures/fig13_feature_distributions.png` | image | Phase 5E key feature histograms. |

### Phase 5 information sets (horse race)

| Set | n_features | Description |
|---|---|---|
| F | 37 | Financial baseline (lagged returns for WAERLST/BSHIELDT/ITA, volume/liquidity, vol, VIX, calendar). |
| P | 73 | F + physical attacks (counts, surprise, composition). |
| N | 63 | F + news attention (counts, shares, log, z30, tones) — fixed 2026-07-02 (was erroneously == F). |
| PN | 115 | F + P + N (per-query × per-group counts). |
| PNG | 118 | F + PN + narrative-gap features. |

### Build the model matrix

```bash
source .venv/bin/activate
python scripts/phase5_build_master.py           # build daily_master + feature_matrix
python scripts/phase5_build_model_matrix.py      # build model_matrix
python scripts/phase5_data_dictionary.py        # generate data_dictionary.csv + .md
python scripts/phase5_leakage_audit.py          # run leakage audit
python scripts/phase5_descriptive_stats.py      # run descriptive stats + figures
python scripts/verify_setup.py                  # full smoke check (incl. Phase 5)
```

### Targets (decision_log 2026-07-02)

- **Primary:** `target_r_WAERLST_t1` (real Bloomberg WAERLST index, next-trading-day return)
- **Robustness (European, war-exposed):** `target_r_BSHIELDT_t1` (real Bloomberg BSHIELDT index)
- **Robustness (US):** `target_r_ITA_t1` (iShares U.S. Aerospace & Defense ETF, yfinance proxy)
- **Retired:** `r_WAERLST_recon` (Bloomberg mcap-weighted reconstruction, too noisy — ρ=0.15 vs ITA) is no longer a modeling target; kept as a lagged feature (`r_WAERLST_recon_lag1`) only, now that the real WAERLST/BSHIELDT series are available.

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

- **Primary outcome:** `WAERLST` — real Bloomberg global aerospace & defense index (1,695 daily rows, 2020-01-01 → 2026-06-30, per decision_log 2026-07-02).
- **Robustness outcomes:** `BSHIELDT` — real Bloomberg European defense index (most exposed to the Russia-Ukraine war; H6 comparison); `ITA` — iShares U.S. Aerospace & Defense ETF (yfinance proxy, ρ=0.86 with SPX per Phase 1 audit).
- **Retired:** `r_WAERLST_recon` (mcap-weighted reconstruction, ρ=0.15 vs ITA — too noisy) — kept as an archival lagged feature only.
- **Physical attack signal:** UAF daily reports (809 days, 7 weapon categories).
- **News narrative signal:** GDELT GKG (11.4M articles, 4 queries × 4 source groups, 1,342 days).
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
- See [`docs/data_sharing.md`](../docs/v1/data_sharing.md) for full setup
- Drive folder: `WarSignalsThesis_Data/` (5.1 GB raw data + pipeline outputs)
- rclone configured with `tps_limit=10` to respect Drive API limits
- On Colab: mount Drive, clone repo, run pipeline (no local storage needed)
- **For rclone re-auth and sync commands** (remote is `gdrive:`), see [`docs/data_sharing.md`](../docs/v1/data_sharing.md) — it covers `rclone authorize drive` and the `rclone copy --update` invocations

Phases 1, 2, 5, and 8 run locally.

---

## Current phase

**Phase 0 — Project setup** ✅ Complete
**Phase 1 — Financial-data audit** ✅ Complete; superseded 2026-07-02 by real Bloomberg WAERLST/BSHIELDT series (ITA retained as US robustness)
**Phase 2 — Physical attack dataset** ✅ Complete (809 days, 21 columns)
**Phase 3 — GDELT extraction & classification** ✅ Complete (11.4M articles, 1,342 days, 4 queries × 4 source groups)
**Phase 4 Tier 1 — GDELT tone** ✅ Complete (Tier 2 transformer deferred until after first milestone per §25)
**Phase 5 — Merge & feature engineering** ✅ Complete, rebuilt 2026-07-02 with real indices (model matrix 1,358 × 154, F/P/N/PN/PNG info sets, N==F bug fixed, leakage audit 0 flags)
**Phase 6 — Econometric baselines** ✅ Complete, re-run 2026-07-02 on real WAERLST/BSHIELDT/ITA targets (see [`docs/phase6_audit.md`](../docs/v1/phase6_audit.md))
**Phase 7 — Machine-learning models** ✅ Complete (see [`docs/v1/phase7_audit.md`](../docs/v1/phase7_audit.md)) — returns null result (XGBoost, all info sets); GARCH-X-in-mean found numerically non-viable (documented null); SHAP shows attack features dominate BSHIELDT's importance profile but not WAERLST's (H1/H6 partial support)

---

## Regenerating removed context files

The repository was stripped of AI-agent context files and machine-generated
docs on 2026-08-16 so they can be regenerated fresh against current models and
current data. Nothing is lost — the pre-cleanup tree is tagged
`pre-context-cleanup`. That tag predates the `thesis_v1/` restructure, so its
paths are flat: `git show pre-context-cleanup:decision_log.md` to read a file,
`git show pre-context-cleanup:<flat-path> > thesis_v1/<path>` to restore one.

| Removed | How to regenerate |
|---|---|
| `docs/v1/data_dictionary.md` | `python scripts/phase5_data_dictionary.py` |
| `docs/v1/phase5_descriptive_stats.md` | `python scripts/phase5_descriptive_stats.py` |
| `docs/v1/phase5_leakage_audit.md` | `python scripts/phase5_leakage_audit.py` |
| `instructions.md` (agent coding rules) | Regenerate as `CLAUDE.md` / `AGENTS.md` from the current codebase |
| `docs/v1/project_status.md` | Superseded by the **Current phase** section above |
| `Master_Thesis_Research_Completion_Plan.md`, `decision_log.md` | **Not machine-regenerable** — restore from the tag, or use `docs/v2/research_plan.md` and `docs/v2/decision_log.md` on `main` |
| `docs/v1/real_index_integration_plan.md` | Implemented; see `scripts/phase5_overlay_real_indices.py` and `docs/v1/phase7_audit.md` |
| `.github/skills/rclone-drive-sync/` | Procedure documented in [`docs/data_sharing.md`](../docs/v1/data_sharing.md) |

The retained phase audits (`docs/v1/phase1_*` … `docs/v1/phase7_audit.md`) still cite
`decision_log.md` by date; those citations now point at the tagged history
rather than a live file.

---

## License

This repository contains academic research code for a Master's thesis. Data files are subject to their respective source licenses and are not redistributed.