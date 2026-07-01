# Repository Guidelines

## Project structure

This repository holds two iterations of a Master 2 thesis on defense-equity
markets and the Russia–Ukraine war:

```text
WarSignalsThesis/
├── docs/
│   ├── v1/   ← historical record of the archived draft (read-only)
│   └── v2/   ← active research plan, decision log, status
├── thesis_v1/  ← archived draft: code, data, outputs (do not build on this)
└── thesis_v2/  ← active research: code, data, outputs (work here)
```

**Start every session by reading [`docs/README.md`](docs/README.md)**, then
[`docs/v2/research_plan.md`](docs/v2/research_plan.md) (the authoritative
plan) and [`docs/v2/project_status.md`](docs/v2/project_status.md) (current
state). Consult [`docs/v1/README.md`](docs/v1/README.md) only when you need
to reuse v1 data or understand why the pivot happened.

**v1** asked whether physical attack intensity and multilingual news
narratives *forecast* defense-equity returns/volatility out-of-sample. It
found a rigorous null (`docs/v1/supervisor_audit.md`) and is archived.
**v2** (active) asks whether defense stocks *respond* more strongly to
realized conflict intensity or to media-driven geopolitical expectations —
a firm-level, contemporaneous-response design that reuses most of v1's
data. See `docs/v2/research_plan.md` for full details.

Within `thesis_v2/`: `src/data/` loads and cleans sources, `src/features/`
builds the firm-panel and features, `src/models/` contains the response
regressions and the (supporting) efficiency/forecasting check, `src/utils/`
holds shared helpers. Phase entry points go in `scripts/`. Tests go in
`tests/` as `test_*.py`. Config templates are in `config/`; copy
`config/paths.yaml.example` to `config/paths.yaml` for local paths.

`thesis_v1/` has the same internal layout (plus its own
`Master_Thesis_Research_Completion_Plan.md`, `decision_log.md`,
`instructions.md` — all archived) and remains runnable; treat it as
read-only except when explicitly asked to fix something for v2's
Phase 5 (predictability/efficiency check) reuse.

## Build, test, and development

```bash
python -m venv .venv          # shared at project root
source .venv/bin/activate
pip install -r thesis_v2/requirements.txt   # or thesis_v1/requirements.txt for v1 work
```

Run v2 tests with `python -m pytest thesis_v2/tests`. Run v1 tests with
`python -m pytest thesis_v1/tests` (48 are currently known-failing after the
mid-v1 switch to real WAERLST/BSHIELDT data — see
`docs/v2/project_status.md` "Known blockers").

## Coding style & naming conventions

Standard Python style, 4-space indentation, clear function names, modules in
`snake_case`. Keep phase scripts thin; put reusable logic in `src/`. Preserve
column patterns such as lagged suffixes (`*_lag1`) where relevant. Prefer
deterministic seeds and explicit parameters. No formatter/linter config is
defined — match nearby code.

## Testing guidelines

Tests use `pytest`. Add or update tests when changing transforms, feature
definitions, panel construction, or timing logic. Name files
`tests/test_<area>.py` and functions `test_<behavior>()`. For any
time-ordered or lagged feature, verify no look-ahead bias.

## Commit & pull request guidelines

Git history uses concise, scoped messages: start with the area
(`v2: ...`, `v1: ...`, `docs: ...`), then state the outcome. Pull requests
should include a short objective, key files changed, outputs created, tests
run, and any methodological decisions (which must also be logged in
`docs/v2/decision_log.md`).

## Data integrity & research rules

Never edit raw data (`data/raw/` in either version). Keep generated data
reproducible from code; use Parquet for large tables. Use **associational/
response** language for v2's main claims ("responds to", "is associated
with") — reserve "predicts" for the explicitly predictive Phase 5 check, and
never use causal language ("causes", "leads to") without a documented
identification strategy. Record methodology changes in
`docs/v2/decision_log.md` and consult `docs/v2/research_plan.md` before
changing scope. Do not edit `docs/v1/*` or `thesis_v1/decision_log.md` —
they are the historical record.
