# Instructions for AI Agents

> **Read [`Master_Thesis_Research_Completion_Plan.md`](Master_Thesis_Research_Completion_Plan.md) first.**
> It is the authoritative research plan and source of truth for this project.
> This file covers only operational coding and repository rules.

---

## Project identity

**Title:** War Signals and Defense Equity Risk: Physical Air-Attack Intensity versus Multilingual News Narratives

**Type:** Master 2 thesis — predictive forecasting study (not causal).

**Primary outcome:** `WAERLST` (Bloomberg global aerospace & defense index).

**Robustness outcomes:** one European aerospace & defense index (to be selected after data audit); `BSHIELDT`.

**Core frequency:** daily. **Core level:** index-level.

---

## Operational rules

### Research framing

- Use **predictive** language: "predicts", "improves forecast accuracy", "contains incremental predictive information".
- **Never** use causal language ("causes", "leads to", "has a causal effect") unless a separate identification strategy is developed and documented.
- A **null result is valid** if the forecasting experiment is well designed.

### Data integrity

- **Preserve raw data unchanged.** Never edit raw files in `data/raw/`.
- Every processed file must be reproducible from code.
- Log removed observations and the reason for removal.
- Save extraction dates and source URLs where permitted.
- Use Parquet for large analytical tables.
- Mark unaudited data, fields, and sources as **planned** or **unverified**.
- Do not invent Bloomberg fields, coverage, credentials, sources, or results.

### Leakage prevention

- **No look-ahead bias.** Information available through day `t` predicts outcomes on trading day `t+1`.
- **No random train/test splits.** Use time-series validation (expanding window or rolling-origin).
- **Training-only preprocessing.** Fit scalers, imputers, surprise models, and narrative-gap models within training folds only. Apply fitted transformations to validation/test data without re-estimating.
- **No full-sample normalization.** Never use the full-sample mean or std for scaling.
- **No full-sample feature selection.** Select features only within training data.
- **Point-in-time constituents.** For any historical firm-level analysis, use point-in-time membership — never apply current constituents retrospectively.
- Every feature must have an explicit **"available at" timestamp**.

### Model comparison

- Compare all models on **identical forecast dates**.
- Report common evaluation metrics across all information sets.
- Do not claim model superiority without common test dates.
- Use deterministic random seeds. Record every parameter and seed.

### Scope discipline

- **Index-level study is the core.** Firm-level, intraday, procurement, sanctions, and deep-learning work are **optional extensions** — begin only after the core is complete.
- **HAR-RV is optional** and must never block thesis completion.
- Volatility target depends on audited data: intraday → realized volatility; OHLC → range-based; close-only → absolute/squared returns + GARCH.
- Do not add heavy ML or NLP dependencies until the core data pipeline is functional.
- Never prioritize an optional extension over a broken core data pipeline.

### Weekend and timing rules

- Weekend attack/news information is accumulated per a pre-defined rule (e.g., Friday close → Monday pre-market information predicts Monday).
- Do not create artificial Saturday/Sunday financial observations.
- Maintain `attack_start_date`, `official_report_timestamp`, and `market_information_date` separately. Use `market_information_date` for predictive models.

### Phase 3 gap-closure workflow (2026-06-30)

Phase 3 produces a daily news aggregate and a per-query × group pivot via a single automated orchestrator:

```bash
source .venv/bin/activate
python scripts/phase3_close_gaps.py            # full run (~15 s, < 1 GB RAM)
python scripts/phase3_close_gaps.py --dry-run  # plan only, no writes
python -m pytest tests/test_phase3_close_gaps.py -v   # 13 unit + 1 e2e test
```

Steps:
1. **Date-index fix + narrative gap** — `date` becomes a regular column; adds 3 gap cols + 4 `n_tone_*` cols.
2. **Per-query × group pivot** — `news_query_group_pivot.parquet` (1,342 × 17).
3. **Automated precision check** — replaces the 400-article manual audit. Outputs `auto_precision_report.md`.
4. **Sensitivity refresh** — re-runs the 5-strategy comparison on the full 11.4M-article frame. Outputs `sensitivity_report.md`.

Library: `src/data/gdelt_postprocess.py` (7 functions). The user memory file `/memories/repo/pandas_categorical_dtypes.md` documents a known pitfall with `load_articles_columns()` and `.str.split` on categorical data — **always cast to `str` before splitting** a categorical column.

---

## Colab delegation

Some phases require computational resources (GPU, high RAM, stable network) that exceed a typical laptop. **Google Colab** (Pro subscription) is available and should be used for the following tasks:

| Phase | Task | Why Colab | Resource |
|---|---|---|---|
| 3 | GDELT article-level extraction | Hundreds of API calls; stable network needed; article storage on Google Drive | Colab CPU + GDrive |
| 3 | Near-duplicate deduplication (MinHash/LSH) on 500K–2M articles | High RAM for similarity matrices | Colab Pro RAM (32 GB) |
| 4 | Multilingual transformer inference (Tier 2, **after milestone**) | GPU required for batch scoring | Colab T4 or A100 GPU |
| 4 | Transformer fine-tuning (if needed) | GPU training | Colab T4 or A100 GPU |
| 6 | GARCH expanding-window refitting (optional) | ~2,400 model fits; CPU-bound | Colab CPU (optional) |
| 7 | LightGBM hyperparameter search (optional) | Parallel search across folds | Colab CPU (optional) |

### Colab workflow rules

- **Google Drive is the shared storage bridge.** Mount GDrive in Colab; save intermediate outputs as Parquet to GDrive; download to local `data/interim/` or `data/processed/` after.
- **Colab notebooks live in `notebooks/`** with a `colab_` prefix (e.g., `notebooks/colab_03_gdelt_extraction.ipynb`).
- **Colab-specific dependencies** (transformers, torch, datasketch) are listed in `requirements.txt` under a separate section. Do not install them locally unless needed.
- **Reproducibility:** Colab notebooks must record the Colab runtime type (CPU/GPU), Python version, and package versions used.
- **Data flow:** Raw data → Colab (extraction/scoring) → GDrive → local `data/interim/` → local pipeline (Phases 5–8).
- **Do not** run Phases 1, 2, 5, or 8 on Colab — they are lightweight and should run locally.

### Phase-by-phase compute guidance

| Phase | Compute risk | Run where | Estimated time |
|---|---|---|---|
| 1 — Financial audit | LOW | Local | Minutes |
| 2 — Attack data | LOW | Local | Minutes |
| **3 — GDELT extraction** | **HIGH** | **Colab** | 2–6 hours (API-limited) |
| **4 — NLP features (Tier 2)** | **HIGH** | **Colab (GPU)** — **deferred until after first milestone** | 1–4 hours (GPU) |
| 5 — Merge & features | MEDIUM | Local | Minutes |
| 6 — Baselines | MEDIUM | Local (Colab optional) | 1–3 hours |
| 7 — ML models | MEDIUM | Local (Colab optional) | 30–60 min |
| 8 — Comparison | LOW | Local | Minutes |

---

## Repository structure

```
config/           Configuration templates (YAML)
data/raw/         Immutable raw data (never edit)
data/interim/     Intermediate processing outputs
data/processed/   Final analytical tables (Parquet)
data/external/    External reference data
docs/             Documentation (status, data dictionary, source inventory)
notebooks/        Jupyter notebooks for audits and exploration
src/data/         Data loading and cleaning modules
src/features/     Feature engineering modules
src/models/       Forecasting model modules
src/utils/        Shared utilities
tests/            Unit tests
outputs/          Figures, tables, model objects, logs
thesis/           Thesis document and chapters
```

The `thesis_old_try/` directory contains a previous attempt and is **not** part of the active codebase. Do not modify it.

---

## Task completion protocol

After every task, document in the work output or `decision_log.md`:

1. **Objective** — what was requested.
2. **Inputs used** — files, tables, fields, date ranges.
3. **Actions performed** — main transformations or steps.
4. **Outputs created** — exact file paths.
5. **Quality checks** — tests, comparisons, validation.
6. **Decisions made** — any new methodological choices.
7. **Unresolved issues** — what remains uncertain.
8. **Recommended next action** — one concrete next step.

Record all important methodological decisions in [`decision_log.md`](decision_log.md) using the template in Section 19 of the research plan.

---

## Prohibited actions

- Do not silently change the research question.
- Do not add new datasets without explaining their contribution and cost.
- Do not use future information in features.
- Do not assume daily data are intraday data.
- Do not describe predictive results as causal.
- Do not apply current index constituents retrospectively.
- Do not overwrite raw data.
- Do not report model superiority without common test dates.
- Do not use random train/test splits.
- Do not fit scalers or residual models on the full sample.
- Do not download external data, query GDELT, scrape reports, or build models until the corresponding phase is authorized.
- Do not commit or push changes unless explicitly asked.
