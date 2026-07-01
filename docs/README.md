# Documentation Index

This `docs/` folder is shared context for both research iterations. It sits
alongside `thesis_v1/` (archived draft) and `thesis_v2/` (active research) at
the project root, so either version's code can reference the same history.

```text
WarSignalsThesis/
├── docs/
│   ├── v1/   ← historical record of the draft (read-only, do not edit)
│   └── v2/   ← active research plan, decision log, status (edit here)
├── thesis_v1/  ← archived code, data, outputs (draft)
└── thesis_v2/  ← active code, data, outputs (current)
```

## Start here

- **Working on the active thesis?** Read [`v2/research_plan.md`](v2/research_plan.md)
  first — it is the authoritative plan. Then [`v2/decision_log.md`](v2/decision_log.md)
  and [`v2/project_status.md`](v2/project_status.md).
- **Need v1 history or data to reuse?** See [`v1/README.md`](v1/README.md)
  (index of the draft) and [`v1/supervisor_audit.md`](v1/supervisor_audit.md)
  (why the pivot happened).

## Why there are two versions

**v1 (draft, archived)** asked whether physical attack intensity and
multilingual news narratives *forecast* defense-equity returns/volatility
out-of-sample. A supervisor audit found both arms fail a properly specified
out-of-sample test — a rigorous, defensible null, but not a differentiated
contribution. See [`v1/supervisor_audit.md`](v1/supervisor_audit.md).

**v2 (active)** reframes the question from *forecasting* to *response*:
**"Do defence and defence-related stocks respond more strongly to realized
conflict intensity or to media-driven geopolitical expectations? Evidence
from the Russia–Ukraine war."** This moves the unit of analysis to
firm-level panels, the design from prediction to contemporaneous response,
and adds GPR and SIPRI as new data sources — while reusing v1's financial,
attack, and GDELT pipelines. See [`v2/research_plan.md`](v2/research_plan.md).

## Rules

- Do not edit `docs/v1/*` — it is the historical record of what was tried
  and found. If v1 code/data needs revisiting, do it in `thesis_v1/` and
  document the change in `docs/v2/decision_log.md`, not by rewriting v1 docs.
- All new planning, status, and decision documents go in `docs/v2/`.
