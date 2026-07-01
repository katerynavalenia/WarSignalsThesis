# Project Status — v2

**Last updated:** 2026-07-01

> See [`research_plan.md`](research_plan.md) for the full plan and
> [`decision_log.md`](decision_log.md) for why v2 exists.

## Current phase

**Phase 0 — Setup** 🟡 In progress
- [x] Restructured repo into `thesis_v1/` (archived) + `thesis_v2/` (active) + shared `docs/`
- [x] `thesis_v2/` skeleton created (`config/`, `data/{raw,interim,processed,external}/`, `notebooks/`, `outputs/{figures,tables,model_objects,logs}/`, `scripts/`, `src/{data,features,models,utils}/`, `tests/`)
- [x] Config templates copied from v1 (`gdelt_queries.yaml`, `source_groups.yaml`, `country_groups.yaml`, `paths.yaml.example`, `requirements.txt`)
- [x] `docs/v2/research_plan.md` written (question, hypotheses, preliminary evidence, data, methodology, phases)
- [x] `docs/v2/decision_log.md` started
- [x] GPR and SIPRI source files located and verified in `thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/`
- [ ] `thesis_v2/README.md` — pending
- [ ] `config/paths.yaml` (local, gitignored) — copy from `paths.yaml.example` and adjust
- [ ] `python -m venv` / install deps for `thesis_v2/` (or confirm shared `.venv` at project root covers it)

## Not yet started

- **Phase 1 — Data assembly**: copy/reference v1 processed tables; parse GPR daily; parse & ticker-match SIPRI.
- **Phase 2 — Panel construction**.
- **Phase 3 — Main response analysis** (H1–H3).
- **Phase 4 — Heterogeneity** (H4–H5).
- **Phase 5 — Predictability/efficiency check** (H7): requires fixing 48 currently-failing tests in `thesis_v1/tests/test_phase6_baselines.py` (broken by the mid-v1-session data changes — stale target names/fixtures after the switch to real WAERLST/BSHIELDT) and closing v1's open C7 (h=5) / C8 (GARCH-X) items.
- **Phase 6 — Robustness & multiple-testing correction**.
- **Phase 7 — Writing**.
- **Phase 8 — Final validation**.

## Known blockers / carry-overs from v1

1. **48 failing tests** in `thesis_v1/tests/test_phase6_baselines.py` — need fixing before Phase 5 (efficiency check) can run cleanly. Not yet investigated in v2.
2. **SIPRI company-name → Bloomberg-ticker matching** is manual and not yet started (~50 relevant firms across WAERLST/BSHIELDT).
3. **N info set** (if the v1 F/P/N/PN/PNG nested-info-set framework is reused for Phase 5): was degenerate in v1 (N ⊆ F). Decision made: populate it properly with genuine news-only lag columns if/when Phase 5 code is touched.

## Immediate next action

Start Phase 1: write a small script in `thesis_v2/scripts/` (or `src/data/`)
to (a) parse `data_gpr_daily_recent.xls` into a clean daily
`date, GPRD, GPRD_ACT, GPRD_THREAT` table, and (b) parse the SIPRI workbook
into a long `year, company, country, arms_pct_of_total` table, saved to
`thesis_v2/data/interim/`.
