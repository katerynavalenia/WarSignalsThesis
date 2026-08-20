# Gate 3 — result: FAIL. The Gate-2 null is final.

**Date:** 2026-08-20 · **Pre-registration:** [`gate3_preregistration.md`](gate3_preregistration.md)
**Code:** `thesis_v2/scripts/run_gate3.py` · **Data:** `data/interim/gdelt_threat_act_daily.parquet`
(1,605 days, 2017-04-23 → 2026-05-20, six ecosystems)

## Verdict

Under the rule fixed before the test was built: **FAIL**, under both timing
conventions, on the complete sample.

| specification | specs | nominal 5% | survive BH | verdict |
|---|---|---|---|---|
| primary (news lagged 1 day) | 31 | 9 | 2 | **FAIL** |
| secondary (same-day) | 31 | 6 | 0 | **FAIL** |

Positive control passes — the Western block is detected in 6 of 31 cells
(min p=0.0028) — so this is a real null, not a power failure. The design finds
Western media where Western media matter, and does not find local media
anywhere that survives.

**The asset-pricing headline is now closed.** Attention share, tone, and
anticipation structure have each been tested; local-language perception adds
nothing over Western coverage in any of them.

## The pass that evaporated — worth recording

On a partial ingest (694 days: the Russia window plus 2025-26), the primary
specification produced **7 BH survivors and a PASS**. Adding the held-out
2017-19 window — the same pre-registered grid, simply more data — reduced that
to 2 survivors and a FAIL.

Nothing was changed except sample coverage. Had the ingest stopped at the
BigQuery guard, this document would have reported a positive headline. That is
the single most useful methodological observation in the whole project, and it
belongs in the robustness chapter: **a pre-registered test on a truncated sample
is not a pre-registered test.**

## Applying the rule strictly

The runner's verdict logic was looser than the pre-registration. Applied strictly:

**Arm 1** — a BH survivor in the Russia window on a Bloomberg target or ITA.
The only Russia-window survivor is `us_defence`, a free basket, which
`gate3_preregistration.md` explicitly excludes from this arm. **FAIL.**

**Arm 2** — survivors in ≥2 independent episode windows, *same sign*. Two
windows do carry survivors, but the sign condition fails: the Russia daily cell
has the opposite sign to all six weekly cells on every local term. **FAIL.**

The `run_gate3.py` verdict line does not encode the target restriction or the
sign condition and will print PASS where the document says FAIL. The document
governs; the script is a convenience.

## What the coefficients showed, and why it is not a result

Among the weekly cells the sign structure was strikingly coherent:

| term | same-sign across survivors | mean |
|---|---|---|
| `act_RU_INDEP` | 7/7 | +0.72 |
| `act_UA` | 6/7 | −0.85 |
| `act_RU_STATE` | 6/7 | −0.85 |
| `thr_UA` | 6/7 | +0.79 |

Read literally that is *buy the rumour, sell the fact* in Ukrainian media: a
shift toward anticipation (`thr_UA` ↑) raises defence returns, a shift toward
realization (`act_UA` ↑) lowers them. Interpretable, and exactly the mechanism
the thesis hoped for.

**It does not survive an out-of-sample test.** Those four signs were formed on
2021–2026 and tested on 2017-19, which had not been ingested when the hypothesis
was written down:

| target | n | act_UA | thr_UA | act_RU_STATE | act_RU_INDEP | matches |
|---|---|---|---|---|---|---|
| r_ita | 129 | −0.402 ✓ | +0.284 ✓ | +0.084 ✗ | +0.051 ✓ | 3/4 |
| us_defence | 129 | −0.357 ✓ | +0.352 ✓ | −0.006 ✓ | +0.105 ✓ | 4/4 |
| eu_defence | 129 | +0.230 ✗ | −0.098 ✗ | −0.128 ✓ | −0.290 ✗ | 1/4 |

**8 of 12 signs match; binomial p = 0.194.** Indistinguishable from coin-flips.
The US-facing targets replicate well and the European target inverts, which is
the signature of a pattern that is not structural.

## Consequences for the plan

1. **Close SQ2/SQ3 as nulls with power.** Three independent operationalisations
   of "whose perception is priced" — volume, tone, anticipation structure — all
   return nothing for local media, with a positive control demonstrating the
   design can detect Western media.
2. **`research_plan_v3.md` §9's odds table is now settled empirically.** The
   "moderate" prior for the local-language headline resolves to no; the "high"
   prior for a volatility response was already retracted
   (`gate1_gate2_results.md` §1).
3. **The thesis rests on measurement, not on pricing.** Chapters 5–6 — the
   validated multilingual dataset and the censorship wedge — plus two
   methodological contributions: the market-control retraction, and the
   truncated-sample lesson above.
4. **A methodological chapter is now available on its own evidence.** Three
   times in this project a plausible positive appeared and dissolved under a
   better control, a longer sample, or an out-of-sample test. Documenting that
   sequence is a genuine contribution to how this kind of media-and-markets
   study should be run.

## What was not tested

- The **2017-19 window is now used**, so it is no longer held out. Any further
  hypothesis needs a fresh test window; the honest options are a different asset
  class or a different conflict.
- **Intraday timing.** GDELT is 15-minute; equities here are daily. A genuine
  lead-lag test of whether Ukrainian media move before Western wires needs
  intraday prices and was never in scope.
- **The hand-labelled precision audit** (§5.5.1) still governs Gate 1's
  provisional status, and becomes mandatory if the censorship wedge is promoted
  to the centerpiece.
- **Composition stability of RU_INDEP** across the invasion: echo.msk.ru was
  liquidated in March 2022, so the ecosystem's membership changes at the event
  the wedge is measured on. This needs a fixed-outlet-panel re-run before the
  wedge is published.
