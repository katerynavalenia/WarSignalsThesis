# AGENTS.md

This repository supports a Master 2 thesis project:

**War Signals and Defense Equity Risk: Physical Air-Attack Intensity versus Multilingual News Narratives**

Use this file as the quick-start guide for AI coding agents. The authoritative project source is
`Master_Thesis_Research_Completion_Plan.md`; read it before substantive research or modeling work.

## Essential Reading Order

1. `Master_Thesis_Research_Completion_Plan.md` - research design and phase plan.
2. `instructions.md` - operational rules for agents.
3. `docs/project_status.md` - current phase, completed deliverables, next action.
4. `decision_log.md` - methodological decisions already made.
5. `docs/professor_thesis_guidelines.md` - required thesis-writing structure and style.
6. Relevant audit docs in `docs/` before touching a phase-specific pipeline.

## Current State

- Phase 0 project setup is complete.
- Phase 1 financial-data audit is complete.
- Phase 2 physical attack dataset is complete.
- Phase 3 GDELT extraction and source classification is in progress.
- Immediate next action: run or continue the Phase 3 Colab workflow described in
  `docs/colab_03_setup.md` and `notebooks/colab_03_gdelt_extraction.ipynb`.

## Research Guardrails

- The study is predictive, not causal. Use language such as "predicts", "improves forecast accuracy",
  or "contains incremental predictive information".
- Do not claim causality unless a separate identification strategy is designed and documented.
- Null results are acceptable if the forecasting experiment is well designed.
- Do not silently change the research question or core scope.
- Follow `docs/professor_thesis_guidelines.md` for thesis structure, literature placement, table/figure design,
  reference practice, and paragraph-level writing rules.

## Leakage And Timing Rules

- No look-ahead bias: information available through day `t` predicts market outcomes on trading day `t+1`.
- Do not use random train/test splits. Use expanding-window or rolling-origin validation.
- Fit scalers, imputers, surprise models, narrative-gap models, and feature selection only inside training folds.
- Compare models only on identical forecast dates.
- Keep `attack_start_date`, `official_report_timestamp`, and `market_information_date` distinct.
- Do not create artificial weekend financial observations.

## Data Rules

- Never edit raw data in `data/raw/`.
- Every processed artifact must be reproducible from code.
- Use Parquet for large analytical tables.
- Mark unaudited sources, fields, and results as planned or unverified.
- Do not invent Bloomberg fields, credentials, coverage, sources, or empirical results.
- Do not modify `thesis_old_try/`; it is archived except for reference.

## Compute Boundaries

- Run Phases 1, 2, 5, and 8 locally.
- Use Google Colab for Phase 3 article extraction/deduplication and Phase 4 transformer inference.
- Optional heavy Phase 6-7 runs may use Colab if local execution is too slow.
- Colab notebooks live in `notebooks/` with a `colab_` prefix.
- Google Drive is the shared data bridge; see `docs/data_sharing.md`.

## Testing And Verification

- Run focused tests for changed code, usually with `pytest`.
- Setup can be checked with:

```powershell
python scripts/verify_setup.py
```

- Existing focused test files include:
  - `tests/test_financial.py`
  - `tests/test_attacks.py`
  - `tests/test_gdelt.py`
  - `tests/test_classifier_enhanced.py`

## Task Completion Protocol

For each substantive task, report or document:

1. Objective.
2. Inputs used.
3. Actions performed.
4. Outputs created.
5. Quality checks.
6. Decisions made.
7. Unresolved issues.
8. Recommended next action.

Record important methodological decisions in `decision_log.md` using the project template.
