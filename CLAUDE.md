# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A Master-2 thesis research codebase (Python, empirical finance) on how defense
equities relate to the Russia–Ukraine war. It holds **two research iterations
side by side**:

- `thesis_v1/` — **archived draft.** Index-level out-of-sample *forecasting*
  horse race. Complete through Phase 7; its result is a rigorous **null**.
  Read-only in spirit: reuse its data and code, do not build new work on its
  question.
- `thesis_v2/` — **active research.** Reframed from forecasting to
  *contemporaneous response*: "Do defence and defence-related stocks respond
  more strongly to realized conflict intensity or to media-driven geopolitical
  expectations?" Currently a **skeleton** — `src/` holds only empty
  `__init__.py` files, `scripts/` and `tests/` are empty. Phase 0 (setup), work
  starts at Phase 1.
- `docs/` — shared history. `docs/v1/` is the historical record (**do not
  edit**); `docs/v2/` is where all new planning, status, and decisions go.

**Read before doing anything substantive in v2:** `docs/v2/research_plan.md`
(authoritative plan, hypotheses, phase list), then `docs/v2/decision_log.md`
and `docs/v2/project_status.md`. `docs/v1/README.md` lists exactly which v1
artifacts v2 reuses.

### Findings that constrain new work

These are established results, not open questions — proposing work that
assumes the opposite is a mistake:

- **Forecasting is null** (v1, multi-angle: OLS, Ridge, Clark–West, ITA and
  real WAERLST/BSHIELDT). It survives in v2 only as the "efficiency" leg (H7).
- **H4 is falsified**: firm response does *not* scale with SIPRI
  defense-revenue exposure (two-way FE interaction p=0.82–0.99). Do not make
  firm-level exposure heterogeneity the centerpiece.
- **Media attention (GDELT volume) → volatility is null/negative.**
- What survives as the headline candidate: `GPRD_THREAT` (expectations)
  ≥ `GPRD_ACT` (realized) for **volatility**, strongest for European defense
  (BSHIELDT), nothing on returns. See `research_plan.md` §2, §6.
- Attack + GDELT coverage starts **Sep 2022**, so the Feb–Sep 2022 invasion
  re-rating is out of sample. Structural, not fixable.

## Commands

One shared virtualenv at the project root (`.venv`, Python 3.14). **Working
directory matters**: scripts, tests, and config loading resolve
`config/paths.yaml`, `data/`, and `outputs/` *relative to the current
directory*, and `sys.path` is anchored at the version root. Always `cd` into
`thesis_v1/` or `thesis_v2/` first.

```bash
source .venv/bin/activate
pip install -r thesis_v2/requirements.txt      # v1 and v2 requirements are identical
cp thesis_v2/config/paths.yaml.example thesis_v2/config/paths.yaml   # v2 has none yet; v1's exists
```

Tests (v1 has 463 collected; v2 has none yet):

```bash
cd thesis_v1
python -m pytest -q                                     # full suite
python -m pytest tests/test_phase5_merge.py -v           # one file
python -m pytest tests/test_phase6_baselines.py::TestAR1Forecaster -v   # one class/test
python scripts/verify_setup.py                           # end-to-end smoke check incl. Phase 5
```

Baseline as of 2026-08-16: **437 passed, 2 failed, 23 skipped, 1 xfailed.**
The two failures are `test_phase5_merge.py::TestLoaders::{test_load_financial,
test_load_attack}` and are **missing-data, not code** — they read
`data/processed/{financial,attacks}/*.parquet`, which are absent from this
checkout (see "Data availability" below). Note the v2 docs still list "48
failing tests in `test_phase6_baselines.py`" as a blocker; that is **stale** —
that file passes 96/96.

Rebuild the v1 data pipeline (order matters — each step consumes the previous
step's parquet):

```bash
cd thesis_v1
python scripts/phase5_build_master.py         # daily_master.parquet + feature_matrix.parquet
python scripts/phase5_build_model_matrix.py   # model_matrix.parquet (the Phase 6/7 input)
python scripts/phase5_data_dictionary.py      # data_dictionary.csv/.md
python scripts/phase5_leakage_audit.py        # outputs/tables/leakage_audit.csv
python scripts/phase5_descriptive_stats.py    # descriptive stats + figures
python scripts/phase6_run_baselines.py        # econometric horse race
python scripts/phase7_run_ml.py               # XGBoost + SHAP
```

Missing packages the v2 plan needs but the env lacks: `linearmodels`
(PanelOLS with entity+time effects) and `rapidfuzz` (SIPRI name→ticker
matching). Install them when Phase 1/4 work begins.

## Architecture (v1 — the reusable engine)

Layered, one direction: `src/data/` (load + clean raw sources) →
`src/features/` (merge, engineer, lag) → `src/models/` (forecast, evaluate).
`scripts/phase*.py` are thin CLI entry points that wire these together and
insert the version root on `sys.path`; they hold no logic worth reusing on
their own.

The pipeline's spine is a chain of parquet artifacts, each a superset of the
last: `daily_master` (calendar-day outer join of financial + attack + news) →
`feature_matrix` (+ engineered vol / surprise / normalization / calendar
features) → `model_matrix` (lagged, targets attached — the only table models
should read, via `src/features/load_model_matrix.py`).

Three conventions are load-bearing and easy to break:

- **`date` is a regular first column**, `datetime64[ns]`, never the index, in
  every Phase 5+ output. `src/utils/date_utils.standardize_date_column`
  normalizes index/int-YYYYMMDD/string inputs; `build_daily_master` resets the
  index of the financial and attack tables, which natively use `date` as index.
- **Leakage discipline.** `build_model_matrix` shifts all informational
  features by one trading day (`_lag1` suffix) and keeps only genuinely
  pre-open-known columns (calendar flags, regime dummies) same-day. The
  **weekend rule**: Friday-close information predicts Monday, so
  Saturday/Sunday rows carry Monday's return as target. `src/utils/recursive.py`
  encodes the asymmetry deliberately — `expanding_compute` at `t` *includes*
  `t`, `rolling_compute` at `t` *excludes* `t` (pandas `closed="left"`). Any
  new feature must go through these, and `phase5_leakage_audit.py` must stay at
  0 critical flags.
- **Information sets** F / P / N / PN / PNG (financial / +physical attacks /
  +news / both / +narrative gaps) are column masks carried on
  `model_matrix.attrs["info_sets"]`, not separate files. They define the
  horse-race grid. Note N was silently equal to F until fixed 2026-07-02 —
  validate cardinalities (`validate_model_matrix_for_phase6`) after touching
  feature construction.

Models share a minimal scikit-learn-style contract (`fit(X, y)` / `predict(X)`,
`y` in percent) defined in `src/models/baselines.py`, so `AR1`,
`HistoricalMean`, OLS/Ridge, GARCH variants, and the XGBoost wrapper
(`src/models/ml.py`) all plug into the same
`src/models/expanding_window.py` engine. That engine enforces the OOS
guarantees (train max date < test min date, refit cadence, minimum training
rows) and emits **long** predictions — one row per
(date, fold, model, info_set, target, horizon) — which `src/models/horse_race.py`
pivots into benchmark tables. Add a model by implementing the contract and
registering a spec, never by writing a new loop.

Targets (decision 2026-07-02): primary `target_r_WAERLST_t1` (real Bloomberg
global A&D index); robustness `target_r_BSHIELDT_t1` (European, war-exposed)
and `target_r_ITA_t1` (US ETF proxy). `r_WAERLST_recon` is retired as a target
and survives only as a lagged feature.

## Data availability in this checkout

The docs describe the data as present; on this machine most of it is **not**.
Verify before planning any pipeline run:

- **Present:** the derived Phase 5 tables (`data/processed/{daily_master,
  feature_matrix,model_matrix}.parquet`, `data_dictionary.csv`), the GDELT news
  outputs under `data/processed/news/`, and all of `thesis_v1/outputs/`.
- **Absent:** every upstream per-source table and raw file — `data/raw/*`
  (bloomberg, attacks, gdelt, controls) is empty, `data/interim/financial/` is
  empty, `data/processed/{financial,attacks}/*.parquet` do not exist, and
  `thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/` — the GPR and SIPRI sources
  v2's Phase 1 depends on — is not in the tree at all.
- Consequence: the Phase 5 rebuild chain and v2's Phase 1 cannot run here until
  data is pulled. It lives on Google Drive via `rclone` (remote `gdrive:`,
  folder `WarSignalsThesis_Data/`); setup and sync commands are in
  `docs/v1/data_sharing.md`. Say this out loud rather than silently
  regenerating or re-downloading from the original sources.

## v2 conventions

Same directory grammar as v1 (`config/`, `data/{raw,interim,processed,external}/`,
`src/{data,features,models,utils}/`, `scripts/`, `tests/`, `outputs/`), but the
design is different: firm-level panels and index-level time series, not an OOS
forecasting engine. Do **not** port `ExpandingWindowEngine` or the F/P/N/PN/PNG
info-set machinery into v2 wholesale — they were built for the forecasting
question and the restructure decision explicitly rejected patching them into
the panel design. Reuse instead: `date_utils`, `recursive`, and the v1
*processed data*.

Analysis conventions established by the preliminary regressions (reproduce
them, do not silently change them): restrict to the **war sample**
(2022-09-29→), use regional market-model abnormal returns (US→SPX,
Europe→SXXP, else MSCI_World), cluster SEs by **date** (the treatment
dimension — firm-clustering was tested and rejected), HAC(5) SEs for
index-level time series, standardize channels so coefficients are comparable,
and apply multiple-testing correction across the horse-race grid (Phase 6).

Do not re-download or re-extract GDELT, financial, or attack data — v2 reuses
v1's processed tables unchanged. GPR and SIPRI are the only new sources; both
raw files already exist under `thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/`.
Compute is light (panel regressions on ~100k rows, seconds locally) — the v1
Colab/Drive delegation architecture is **not** needed for v2's core analysis.

## Data and git

- `data/**` contents are gitignored while directory structure is preserved;
  a few v1 GDELT news outputs are exceptions tracked via **Git LFS** (see
  `.gitignore` / `.gitattributes`).
- `outputs/` (figures, tables) **is** tracked — it is reproducible from
  `scripts/`, and diffs there are the visible evidence of a pipeline change.
- `config/paths.yaml` is local and gitignored; only `paths.yaml.example` is
  committed. Modules raise a pointed error if it is missing.
- New decisions go in `docs/v2/decision_log.md` (Decision / Reason /
  Alternatives considered / Consequences / Revisit condition). Status updates
  go in `docs/v2/project_status.md`. Never rewrite `docs/v1/*` to reflect new
  understanding.
- AI-agent context files and machine-generated docs were stripped on
  2026-08-16; the pre-cleanup tree is tagged `pre-context-cleanup` (flat paths,
  predating the v1/v2 split): `git show pre-context-cleanup:decision_log.md`.
