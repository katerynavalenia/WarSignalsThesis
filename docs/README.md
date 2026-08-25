# Research documentation

Everything here belongs to the final study. There is one version; earlier
iterations are in [`../archive/`](../archive/).

> ## ⚠ Read [`findings_status.md`](findings_status.md) first
>
> Five plausible positives were produced and retracted during this work, plus one
> narrower claim. The documents that reported them are kept **unedited**, because
> the sequence of retractions is the thesis's methodological contribution — which
> means several files below state, in their own voice, results that no longer
> hold. `findings_status.md` is the authority on which results are live. Nothing
> here should be cited without checking it.

## Start here

| file | what it is |
|---|---|
| [`findings_status.md`](findings_status.md) | live vs retracted, with what killed each |
| [`reproduce.md`](reproduce.md) | run order, BigQuery costs, what each script writes |
| [`research_plan.md`](research_plan.md) | the plan the work executed |
| [`supervisor_response_matrix.md`](supervisor_response_matrix.md) | the five review comments, verbatim, each answered |
| [`supervisor_note.md`](supervisor_note.md) | draft note to send with the thesis |

## The measurement

| file | what it is |
|---|---|
| [`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md) | why the previous indicators measured article *topic* rather than publisher perspective — the finding that drove the rebuild |
| [`data_sources.md`](data_sources.md) | what is reachable without credentials, and what is not |
| [`equity_validation.md`](equity_validation.md) | the free-basket test, pre-registered, and its result |

## The gates

Each pre-registration was committed **before** the data to test it existed, so
the order is verifiable in git history.

| pre-registration | result |
|---|---|
| — (criteria fixed in `equity_validation.md`) | [`gate1_gate2_results.md`](gate1_gate2_results.md) |
| [`gate3_preregistration.md`](gate3_preregistration.md) | [`gate3_results.md`](gate3_results.md) — FAIL |
| [`gate4_preregistration.md`](gate4_preregistration.md) | [`gate4_results.md`](gate4_results.md) — FAIL |
| [`gate5_preregistration.md`](gate5_preregistration.md) | [`gate5_results.md`](gate5_results.md) — FAIL |

## Retracted, kept deliberately

[`gpr_regime_preview.md`](gpr_regime_preview.md) reports a result that is wrong.
It opens with a retraction banner giving the correct number and the mechanism.
It is here because Chapter 8 documents the retraction, and a retraction whose
subject has been deleted cannot be checked.

## Operational

| file | what it is |
|---|---|
| [`environment_setup.md`](environment_setup.md) | BigQuery service account, credentials, what an agent session can and cannot do |
| [`decision_log.md`](decision_log.md) | decisions, with reasons and revisit conditions |
| [`finding_the_submitted_draft.md`](finding_the_submitted_draft.md) | which version the supervisor reviewed, and how to tell |
