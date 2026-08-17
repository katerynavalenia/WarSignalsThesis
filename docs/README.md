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

## Rules

- Do not edit `docs/v1/*` or `docs/v2/*` — they are the historical record of what
  was tried and found.
- All new planning, status, and decision documents go in `docs/v3/`.
