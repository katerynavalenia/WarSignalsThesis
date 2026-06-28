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

| Phase | Task | Resource | Est. time |
|---|---|---|---|
| 3 | GDELT article extraction + dedup | Colab CPU + GDrive | 2–6 hours |
| 4 | Transformer inference on 500K–2M articles | Colab T4/A100 GPU | 1–4 hours |
| 6–7 | GARCH refits / hyperparameter search (optional) | Colab CPU | 1–3 hours |

Phases 1, 2, 5, and 8 run locally. See [`instructions.md`](instructions.md) § "Colab delegation" for full rules.

---

## Current phase

**Phase 0 — Project setup** is complete. The next phase is:

**Phase 1 — Financial-data audit:** Audit the Bloomberg delivery and determine the available fields, date coverage, series type, index identifiers, and feasible volatility target.

See [`docs/project_status.md`](docs/project_status.md) for detailed status.

---

## License

This repository contains academic research code for a Master's thesis. Data files are subject to their respective source licenses and are not redistributed.