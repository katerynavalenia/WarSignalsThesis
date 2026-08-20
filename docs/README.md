# Documentation Index

This `docs/` folder is shared context for all research iterations. It sits
alongside `thesis_v1/` (archived draft) and `thesis_v2/` (active code) at the
project root, so either version's code can reference the same history.

```text
WarSignalsThesis/
├── docs/
│   ├── v1/   ← historical record of the reviewed draft (read-only)
│   ├── v2/   ← the contemporaneous-response pivot (superseded, kept for its evidence)
│   └── v3/   ← ACTIVE plan, after the supervisor review (edit here)
├── thesis_v1/  ← archived code, data, outputs (draft) — still reused wholesale
└── thesis_v2/  ← code skeleton; new v3 work goes here
```

## Start here

- **Working on the thesis now?** Read [`v3/README.md`](v3/README.md), then
  [`v3/gdelt_measurement_diagnosis.md`](v3/gdelt_measurement_diagnosis.md),
  [`v3/research_plan_v3.md`](v3/research_plan_v3.md), and
  [`v3/supervisor_response_matrix.md`](v3/supervisor_response_matrix.md).
- **Need v1 history or data to reuse?** See [`v1/README.md`](v1/README.md) and
  [`v1/supervisor_audit.md`](v1/supervisor_audit.md).
- **Want v2's preliminary regression evidence?** It is real and still useful —
  see [`v2/research_plan.md`](v2/research_plan.md) §6.
- **Setting up, or working without the laptop?**
  [`cloud_sessions.md`](cloud_sessions.md) covers GitHub connection and what is
  possible from a dataless checkout; [`v3/environment_setup.md`](v3/environment_setup.md)
  covers the BigQuery route that makes the GDELT rebuild possible from a cloud
  session.

## Why there are three versions

**v1 (reviewed by the supervisor).** Asked whether physical attack intensity and
multilingual news narratives *forecast* defence-equity returns and volatility
out-of-sample, on 2022-09 → 2026-06. Both arms came out null. See
[`v1/supervisor_audit.md`](v1/supervisor_audit.md).

**v2 (superseded).** Reframed from forecasting to contemporaneous *response*, at
the firm-panel level, adding GPR and SIPRI. Its intended centrepiece — that the
response scales with a firm's defence-revenue exposure — was falsified on the
attrition-only sample. Its surviving evidence (defence volatility loads on
GPR_THREAT more than GPR_ACT, especially in Europe) is folded into v3.

**v3 (active).** After the supervisor's five-point review. Keeps the topic and
every pipeline, and fixes the three things that actually caused the nulls: the
sample was too short and contained no regime variation; the national sentiment
indicators measured article *topic* rather than publisher *perspective*; and
forecast accuracy was judged on metrics too blunt to detect the effect sizes this
literature deals in. New question: **whose perception of geopolitical risk is
priced in defence equities?** See [`v3/README.md`](v3/README.md).

## Phase numbers do not carry across versions

Each iteration numbered its phases independently, so a bare "Phase 5" is
ambiguous — and v1's numbers are still live in filenames (`phase5_build_master.py`,
`test_phase6_baselines.py`) while v3's exist only in prose.

| # | v1 — *in filenames* | v2 | v3 — *in the plan* |
|---|---|---|---|
| 1 | Financial-data audit | Data assembly | Long-sample data spine |
| 2 | Physical attack dataset | Panel construction | **Perception indices — the gate** |
| 3 | GDELT extraction & classification | Main response analysis | Stylized facts |
| 4 | GDELT tone | Heterogeneity | Dynamic response |
| 5 | Merge & feature engineering | Predictability check | Forecasting repair |
| 6 | Econometric baselines | Robustness | Cross-section & events |
| 7 | Machine-learning models | Writing | Robustness |
| 8 | — | Final validation | Writing |
| 9 | — | — | Final validation |

**Conventions, to stop this recurring:**

- **Always qualify in prose**: "v3 Phase 5", never a bare "Phase 5".
- **Never put a phase number in a new filename.** The numbering has been
  rewritten twice in two months; files outlive it. Name by content instead —
  `build_spine.py`, `gpr_regime_preview.py`, `gpr_race_returns_bshieldt.csv`.
- **v1's phase-numbered filenames are frozen**, not a precedent. Roughly 78
  references across `docs/v1/` cite them, and that trail is the point of keeping
  v1 at all.

## Rules

- Do not edit `docs/v1/*` or `docs/v2/*` — they are the historical record of what
  was tried and found.
- All new planning, status, and decision documents go in `docs/v3/`.
