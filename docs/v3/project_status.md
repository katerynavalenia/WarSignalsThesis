# Project Status — v3

**Last updated:** 2026-08-17

> Plan: [`research_plan_v3.md`](research_plan_v3.md).
> Why v3 exists: [`decision_log.md`](decision_log.md).
> Setup: [`environment_setup.md`](environment_setup.md) and
> [`../cloud_sessions.md`](../cloud_sessions.md).

## Current phase

**Phase 0 — Notify, then execute** 🟢 Unblocked

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
      [`research_plan_v3.md`](research_plan_v3.md) §8 "Why Phase 0 does not block".
- [ ] Send the supervisor an informational note (does not block anything)
- [ ] Decide the headline framing — **defer to Phase 3**, when the descriptive
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

## Not yet started

Phases 1–9 of [`research_plan_v3.md`](research_plan_v3.md) §8. The gate is
**Phase 2**: if the rebuilt perception indices fail their validation battery
(hand-labelled precision, correlation with published GPR, event face validity,
mutual non-collinearity), stop and reconsider before investing in Blocks B–E.

## Immediate next action

Start Phase 5 (the test module — Diebold–Mariano, Clark–West, Campbell–Thompson
R²_OS, MCS, Benjamini–Hochberg). It closes supervisor comment #4, needs no data
and no credentials, and is required under every possible framing. In parallel,
configure BigQuery (blocker 2) so Phase 2 can start, and send the supervisor the
informational note.
