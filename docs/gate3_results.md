# Gate 3 — result: FAIL. The Gate-2 null is final.

> **Coverage closed, 2026-08-25.** This gate was first run on 1,605 days, because
> the threat/act split reads GDELT's `Themes` field at roughly four times the scan
> cost of the `Locations` field the other tests use. That left it testing on about
> 40% of the corpus while everything else used all of it. The remaining 2,422 days
> were ingested (706 GB) and the test re-run on the full **4,027 days**.
>
> **The verdict did not change** — FAIL under both timing conventions, 9 nominal
> and 2 BH survivors on the primary arm, 3 and 0 on the secondary. What changed is
> the weight behind it: the pooled daily cell now carries **2,754 observations
> instead of 1,097**, and returns p = 0.10. Both surviving cells are weekly, in
> the 2025–26 episode, on 58 observations against 13 parameters.
>
> The numbers below are from the original 1,605-day run and are kept because the
> pre-registration was written against it. Where they differ from the full-corpus
> figures, the full-corpus figures are the ones the thesis reports.

**Date:** 2026-08-20 · **Pre-registration:** [`gate3_preregistration.md`](gate3_preregistration.md)
**Code:** `scripts/run_gate3.py` · **Data:** `data/interim/gdelt_threat_act_daily.parquet`
(originally 1,605 days; re-run on the full 4,027 after the corpus was completed)

## Verdict

Under the rule fixed before the test was built: **FAIL**, under both timing
conventions, on the complete sample.

| specification | specs | nominal 5% | survive BH | verdict |
|---|---|---|---|---|
| primary (news lagged 1 day) | 31 | 9 | 2 | **FAIL** |
| secondary (same-day) | 31 | 3 | 0 | **FAIL** |

Positive control passes — on the full corpus the Western block is detected in 2 of 31 cells
(min p=0.0002) — so this is a real null, not a power failure. The design finds
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

**7 of 12 signs match; binomial p = 0.387.** Indistinguishable from coin-flips.
The US-facing targets replicate well and the European target inverts, which is
the signature of a pattern that is not structural.

## Consequences for the plan

1. **Close SQ2/SQ3 as nulls with power.** Three independent operationalisations
   of "whose perception is priced" — volume, tone, anticipation structure — all
   return nothing for local media, with a positive control demonstrating the
   design can detect Western media.
2. **`research_plan.md` §9's odds table is now settled empirically.** The
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
## Addendum — the censorship wedge does not survive a fixed outlet panel

The wedge was the strongest surviving result, so it was re-run on outlets
present on **both** sides of the invasion with ≥200 conflict articles in each
period — 30 outlets, 24 state and 6 independent — rather than on whatever each
ecosystem contained at the time.

| | outlets | tone pre | tone post | shift |
|---|---|---|---|---|
| RU_STATE | 24 | −1.745 | −1.797 | **−0.052** |
| RU_INDEP | 6 | −2.239 | −2.544 | −0.305 |

Welch test on the difference in shifts: **p = 0.151. Not significant.**

Two separate problems:

1. **The contrast is underpowered.** Six independent outlets survive the fixed
   panel, because most of that ecosystem is thin, exiled or was shut down —
   meduza.io, tvrain.ru, zona.media, znak.com and themoscowtimes.com all drop
   out, and echo.msk.ru falls from 13,951 articles to 1,043 after its
   liquidation. The ecosystem-level wedge in `gate1_gate2_results.md` §5 was
   therefore measured partly on a change of membership, which is exactly the
   confound a fixed panel is for.
2. **A register error inflated it.** `dw.com` — Deutsche Welle, a German public
   broadcaster with a Russian-language service — was classified RU_INDEP. It is
   the largest contributor to that ecosystem's volume and carries the largest
   negative shift (−0.73). It is a *Western* outlet by publisher, which is the
   criterion this project exists to apply. Fixed in `ecosystems.py`; the
   committed tables predate the fix.

**What still stands.** Russian state media's tone genuinely did not move: 24
outlets, mean shift −0.05, with several turning *more positive* across the
invasion (regnum.ru +0.23, gazeta.ru +0.48, ren.tv +0.43, mskagency.ru +0.40).
Against Ukrainian media's −1.66 that contrast is enormous and will survive any
reasonable test. **The state-versus-independent wedge specifically does not**,
and should be reported as directional-but-not-significant until the register is
audited and the independent panel is deepened.

That the audit-class error was found by a robustness run rather than by the
audit is the argument for doing the audit: `dw.com` sat in the register from the
start and nothing downstream flagged it.

## What was not tested

- The **2017-19 window is now used**, so it is no longer held out. Any further
  hypothesis needs a fresh test window; the honest options are a different asset
  class or a different conflict.
- **Intraday timing.** GDELT is 15-minute; equities here are daily. A genuine
  lead-lag test of whether Ukrainian media move before Western wires needs
  intraday prices and was never in scope.
- **The hand-labelled precision audit** (§5.5.1) still governs Gate 1's
  provisional status, and is now mandatory rather than advisable — see the
  addendum above.
