# docs/v3 — Post-supervisor-review plan

**Created:** 2026-08-17, in response to the supervisor's five-point review of the
v1 paper.

## Read in this order

1. **[`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md)** — the
   empirical finding that drives everything else: the v1 "Ukrainian / Russian /
   Western sentiment" indicators were built from GDELT's English-only stream and
   classified by *which country the article mentions*, not *who published it*.
   Reproducible via `thesis_v2/scripts/diagnose_gdelt_streams.py`.
2. **[`research_plan_v3.md`](research_plan_v3.md)** — the revised research plan:
   question, contribution, data, measurement, empirical design, phases, risks,
   honest odds, and the decisions needed before starting.
3. **[`supervisor_response_matrix.md`](supervisor_response_matrix.md)** — each of
   the five review comments answered, with a draft reply to send.
4. **[`environment_setup.md`](environment_setup.md)** — what to configure
   (GitHub App, BigQuery service account, Drive, Colab's role) so an agent
   session can execute the plan end to end, and what will always need a human.

## Headline

**Keep the topic; fix the sample, the measurement, and the tests.**

| | v1 (reviewed) | v3 (proposed) |
|---|---|---|
| Sample | 2022-09 → 2026-06 (~920 days) | **2015-02 → 2026-06 (~2,850 days)** |
| Feb-2022 invasion | out of sample | **in sample** |
| GDELT stream | GKG 1.0 daily, English-only | **GKG 2.0 Translingual** (65+ languages) |
| National sentiment | country *mentioned* in the article | **country/language/ownership of the publisher** |
| Attack data | binds the sample start | short-sample refinement chapter |
| Core design | one-day-ahead OOS forecasting | identified perception shocks + local projections, **plus** repaired forecasting |
| Forecast evaluation | MAE, directional accuracy | **Campbell–Thompson R²_OS, Diebold–Mariano, Clark–West, MCS, BH/Romano–Wolf, economic value** |
| Volatility model | GARCH-X-in-mean (100% degenerate for BSHIELDT) | **HAR-RV-X**, GARCH as robustness |
| Anchor paper | — | **Bondarenko, Lewis, Rottner & Schüler (2024, *JIE*)** |
| Question | do war signals forecast defence equities? | **whose perception of geopolitical risk is priced?** |

## Status of the earlier plans

- `docs/v1/` — historical record of the reviewed paper. Do not edit.
- `docs/v2/` — the contemporaneous-response pivot. Its centrepiece (the
  firm-exposure gradient) was falsified on the *attrition-only* sample; v3 folds
  its surviving results into Blocks B and D and re-tests the exposure gradient
  across the February-2022 break, where it was never tested.
- `docs/v3/` — **active**.

## Code

New work goes in `thesis_v2/` (a skeleton, largely unused), reusing
`thesis_v1/src/` modules wholesale — the financial, attack, expanding-window and
horse-race pipelines are sound and are not being rebuilt.
