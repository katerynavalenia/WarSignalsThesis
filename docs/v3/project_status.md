# Project Status — v3

**Last updated:** 2026-08-17

> Plan: [`research_plan_v3.md`](research_plan_v3.md).
> Why v3 exists: [`decision_log.md`](decision_log.md).
> Setup: [`environment_setup.md`](environment_setup.md) and
> [`../cloud_sessions.md`](../cloud_sessions.md).

## Current phase

**Phase 0 — Sign-off** 🟡 In progress

- [x] Supervisor review received (5 comments) and answered point by point
      ([`supervisor_response_matrix.md`](supervisor_response_matrix.md))
- [x] Root causes of the v1 nulls diagnosed: short sample, invalid news
      indicators, insensitive forecast evaluation ([`research_plan_v3.md`](research_plan_v3.md) §1)
- [x] GDELT stream audit — v1 used the English-only GKG 1.0 daily stream;
      translingual archive verified available from 2015-02-18
      ([`gdelt_measurement_diagnosis.md`](gdelt_measurement_diagnosis.md))
- [x] Bondarenko et al. (2024, *JIE*) read and adopted as the methodological anchor
- [ ] **Kateryna's decision on the five open questions** ([`research_plan_v3.md`](research_plan_v3.md) §11)
- [ ] **Supervisor sign-off on the reframing** before the data rebuild starts
- [ ] Bloomberg: confirm whether WAERLST/BSHIELDT can be re-pulled from 2015

## Blockers

1. **GitHub write access from cloud sessions is not yet configured.** Push
   returns 403: *"GitHub access is not enabled for this session. An org admin
   must connect the Claude GitHub App for this organization."* Fix: `/web-setup`
   from a local CLI, or authorize the Claude GitHub App — see
   [`../cloud_sessions.md`](../cloud_sessions.md) §1. Until then no cloud session
   can save work to the repo.
2. **No BigQuery credentials.** Without them the GDELT rebuild cannot run from a
   cloud session at all. See [`environment_setup.md`](environment_setup.md) §3.2.
3. **Data is on Google Drive, not in git.** A cloud checkout has no parquets;
   the dataless test baseline is 426 passed / 4 failed / 33 skipped.

## Not yet started

Phases 1–9 of [`research_plan_v3.md`](research_plan_v3.md) §8. The gate is
**Phase 2**: if the rebuilt perception indices fail their validation battery
(hand-labelled precision, correlation with published GPR, event face validity,
mutual non-collinearity), stop and reconsider before investing in Blocks B–E.

## Immediate next action

Connect GitHub (blocker 1), then send the supervisor the memo described in
[`research_plan_v3.md`](research_plan_v3.md) §11.5 — the measurement diagnosis,
the sample-extension plan, and the revised question — and ask for approval
before the ~2-week data build.
