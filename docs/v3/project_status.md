# Project Status — v3

**Last updated:** 2026-08-20

> Plan: [`research_plan_v3.md`](research_plan_v3.md).
> Why v3 exists: [`decision_log.md`](decision_log.md).
> Setup: [`environment_setup.md`](environment_setup.md) and
> [`../cloud_sessions.md`](../cloud_sessions.md).
> Phase numbers below are **v3's** and do not correspond to v1's — those survive
> in filenames like `test_phase5_merge.py`. Key: [`../README.md`](../README.md).

## Current phase

**v3 Phase 0 — Notify, then execute** 🟢 Unblocked

- [x] Supervisor review received (5 comments) and answered point by point
      ([`supervisor_response_matrix.md`](supervisor_response_matrix.md))
- [x] Root causes of the v1 nulls diagnosed: short sample, invalid news
      indicators, insensitive forecast evaluation ([`research_plan_v3.md`](research_plan_v3.md) §1)
- [x] GDELT stream audit — v1 used the English-only GKG 1.0 daily stream;
      translingual archive verified available from 2015-02-18
      ([`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md))
- [x] Bondarenko et al. (2024, *JIE*) read and adopted as the methodological anchor
- [x] Established that supervisor approval is **not** required to begin — four of
      the five comments are explicit instructions, and the fifth (methodology)
      can only be complied with by rebuilding. See
      [`research_plan_v3.md`](research_plan_v3.md) §8 "Why v3 Phase 0 does not block".
- [ ] Send the supervisor an informational note (does not block anything)
- [ ] Decide the headline framing — **defer to v3 Phase 3**, when the descriptive
      chapter makes the choice evidential rather than speculative
- [ ] Bloomberg: confirm whether WAERLST/BSHIELDT can be re-pulled from 2015

## Blockers

1. ~~GitHub write access from cloud sessions.~~ **Resolved 2026-08-18** via
   `/web-setup` from a local CLI. A cloud session has pushed to `origin`
   successfully. See [`../cloud_sessions.md`](../cloud_sessions.md) §1.
2. **No BigQuery credentials.** Without them the GDELT rebuild cannot run from a
   cloud session at all. See [`environment_setup.md`](environment_setup.md) §3.2.
3. **Data is on Google Drive, not in git.** A cloud checkout has no parquets.
   Measured baseline on a dataless cloud checkout, 2026-08-18:
   **425 passed, 4 failed, 34 skipped** in 48 s (`cd thesis_v1 && python3 -m pytest -q`).
   All four failures are `test_phase5_merge.py::TestLoaders` — missing data, not
   code. Do not try to fix them in a cloud session. (`cloud_sessions.md` records
   426/4/33; one test has since moved from passed to skipped, which is
   environment drift, not a regression.)

## v3 Phase 1 — partially delivered

- [x] Macro half of the spine ([`data_sources.md`](data_sources.md))
- [x] Free-basket validation pre-registered ([`equity_validation.md`](equity_validation.md))
- [x] **Threat-vs-act estimated on the surviving Bloomberg indices**
      ([`gpr_regime_preview.md`](gpr_regime_preview.md)) — the
      response is in **returns**, in the **build-up regime**, and nowhere else;
      v2's volatility headline does not survive first-differencing; neither
      channel forecasts one day ahead.
- [x] Bloomberg workbooks mirrored to
      `gdrive:WarSignalsThesis_Data/data/raw/bloomberg/` (2026-08-20). They had
      existed only on one laptop, untracked by git and absent from Drive.
- [ ] Equity half of the spine — still needs a Drive sync or a vendor key

Three plan revisions follow from the preview and are **not yet applied** to
[`research_plan_v3.md`](research_plan_v3.md): downgrade §9's "volatility
response — high" prior, commit to changes/shocks rather than levels in Block A,
and reframe the identification claim from sample *length* to the number of
anticipation *episodes*. See the preview's §7.

## Not yet started

v3 Phases 2–9 of [`research_plan_v3.md`](research_plan_v3.md) §8. The gate is
**v3 Phase 2**: if the rebuilt perception indices fail their validation battery
(hand-labelled precision, correlation with published GPR, event face validity,
mutual non-collinearity), stop and reconsider before investing in Blocks B–E.
The gate's collinearity threshold is still stated qualitatively and should be
fixed numerically *before* the ingest, the way
[`equity_validation.md`](equity_validation.md) §3 fixes the basket
criteria.

## Immediate next action

Start v3 Phase 5 (the test module — Diebold–Mariano, Clark–West, Campbell–Thompson
R²_OS, MCS, Benjamini–Hochberg). It closes supervisor comment #4, needs no data
and no credentials, and is required under every possible framing — and the
preview's predictability null makes the power statement it produces load-bearing
rather than decorative. In parallel, configure BigQuery (blocker 2) so v3 Phase 2
can start, and send the supervisor the informational note, now with the
preview's build-up result attached as a first empirical deliverable.
