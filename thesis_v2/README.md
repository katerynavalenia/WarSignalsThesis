# WarSignalsThesis — v2 (active)

**Question:** Do defence and defence-related stocks respond more strongly to
realized conflict intensity or to media-driven geopolitical expectations?
Evidence from the Russia–Ukraine war.

**Full plan, hypotheses, and status:** see
[`../docs/v2/research_plan.md`](../docs/v2/research_plan.md),
[`../docs/v2/decision_log.md`](../docs/v2/decision_log.md), and
[`../docs/v2/project_status.md`](../docs/v2/project_status.md).

This folder holds v2's code, data, and outputs only. Planning and decision
records live in `docs/v2/` (shared, alongside `docs/v1/` for the archived
prior iteration). See [`../thesis_v1/README.md`](../thesis_v1/README.md)
for the archived draft this project pivoted from, and
[`../docs/v1/README.md`](../docs/v1/README.md) for exactly which v1 data
this version reuses.

## Structure

```text
thesis_v2/
├── config/          # paths.yaml (local, gitignored), gdelt_queries.yaml, source_groups.yaml, ...
├── data/
│   ├── raw/         # bloomberg, attacks, gdelt, gpr, sipri, controls — untouched originals
│   ├── interim/      # cleaned per-source tables (financial, attacks, news, panel)
│   ├── processed/   # analysis-ready tables (financial, attacks, news, panel)
│   └── external/    # reused v1 outputs / third-party reference data
├── notebooks/       # exploratory / Colab notebooks
├── outputs/         # figures, tables, model_objects, logs
├── scripts/         # thin phase entry points
├── src/
│   ├── data/        # loaders/cleaners
│   ├── features/    # panel & feature construction
│   ├── models/      # response regressions, heterogeneity, efficiency check
│   └── utils/       # shared helpers
└── tests/           # test_*.py
```

## Setup

```bash
# from the project root (WarSignalsThesis/)
source .venv/bin/activate   # or create one: python -m venv .venv
pip install -r thesis_v2/requirements.txt
cp thesis_v2/config/paths.yaml.example thesis_v2/config/paths.yaml
```

## Data note

Most inputs are **reused from `thesis_v1/`** (real Bloomberg WAERLST/
BSHIELDT, constituent panels, attack data, GDELT aggregates) rather than
re-extracted. GPR and SIPRI are new; both source files already exist at
`../thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/` and need parsing into
`data/interim/` here (see `docs/v2/project_status.md` → "Immediate next
action"). Do not re-download or re-run the GDELT extraction — it is
unchanged from v1.
