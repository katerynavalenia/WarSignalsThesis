# Gate 4 — result: FAIL. And the null is now stronger for it.

> **Figures re-derived 2026-08-25** on the corrected outlet register (Deutsche
> Welle and RFE/RL's two services moved to the Western block) and the full
> 4,027-day corpus. Verdicts are unchanged. Where a figure here differs from an
> earlier draft, the current tables under `outputs/tables/` are authoritative.

**Date:** 2026-08-22 · **Pre-registration:** [`gate4_preregistration.md`](gate4_preregistration.md)
**Code:** `scripts/run_gate4_gas.py` · **Data:** 944 continuous days of
gas-crisis coverage, ingested after the pre-registration was written (57 GB)

## Verdict

All four pre-registered conditions fail.

| condition | result |
|---|---|
| 1. BH survivor in both windows (a) and (b) | **FAIL** — no survivors in either |
| 2. all placebos p > 0.10 | **FAIL** — Brent 0.0014 in window (a), Unilever 0.087 in window (b) |
| 3. survives dropping 10 largest TTF moves | **FAIL** — 0.399 → 0.840 |
| 4. RU_STATE leads the local block | **FAIL** — RU_INDEP leads in two of four cells |

## What happened, precisely

The exploratory run gave p=0.0005 on **81 days** in the build-up window. The
confirmatory run, same asset, same specification, same controls, on **222 days**
of continuous coverage of the same period, gives **p=0.399**.

| window | n | p_local | p_west |
|---|---|---|---|
| (a) build-up and invasion, 2021-06 → 2022-06 | 222 | 0.399 | 0.00005 |
| (b) shutdown and aftermath, 2022-06 → 2023-06 | 231 | 0.573 | 0.197 |
| (c) full crisis, 2021-06 → 2023-12 | 563 | 0.352 | 0.081 |

Nothing was changed except the amount of data. The Western block, meanwhile, is
detected at p=0.001 in window (a) — the positive control passes, so this is a
null with power rather than a failure to measure.

The placebo pattern in window (b) is the second tell. Brent, Unilever and US gas
all show local-block p-values near or below 0.10. If local perception "explains"
an unexposed consumer-staples equity as readily as European gas, what is being
picked up is a common factor, not a supply channel.

## The fourth instance of the same pattern

This is now the fourth plausible positive this project has produced and
retracted, and the four failure modes are distinct:

| # | claim | killed by |
|---|---|---|
| 1 | GPR_THREAT raises European defence volatility (v2 §6.4) | the correct regional market control |
| 2 | Threat shocks move defence returns in the build-up | the same, SPX → SXXP |
| 3 | Threat/act structure of local media is priced (Gate 3) | adding the held-out window to a truncated sample |
| 4 | Local perception is priced in European gas (Gate 4) | pre-registered replication on continuous data |

Each was significant at conventional levels when found. Each looked mechanically
plausible. None survived. Two were killed by better controls, one by more data,
one by a test written down before the data existed.

That sequence is a contribution in its own right, and a more useful one than any
single coefficient would have been. It is also the reason the thesis's null
should be believed: it was not obtained by failing to look.

## The null is now broader, and better

Gate 4 was not a detour. It extends the thesis's central claim from one asset
class to two, and the second is the one with the *direct* causal channel:

> Local-language perception of the Russia–Ukraine conflict is not priced —
> not in Western defence equities, and not in European natural gas, the asset
> through which this conflict physically transmitted to Europe.

That is a materially stronger statement than the defence-only version. The
obvious objection to the original finding was that defence equities are a weak
testbed, since the link from Russian reporting to a US defence contractor runs
entirely through Western investors, making "only Western media matter" close to
definitional. European gas has no such excuse: Russia supplied roughly 40% of EU
gas, TTF moved from about €20 to over €300, and Russian state media is the
channel through which supply intent was signalled. Local perception still adds
nothing beyond Western coverage.

## Consequence

**No further asset switches.** The question has been tested on the asset class it
was designed for and on the asset class with the strongest prior, with a
pre-registered protocol, a passing positive control, and null placebos where the
mechanism requires them. Adding a fifth asset would be searching, not testing —
and this project's record establishes what searching produces here.

The thesis is the null, its power, the measurement chapter, and the four
retractions. Chapters 3, 4 and 5 are unaffected: the data, measurement and
descriptive work are shared across both asset classes, and Chapter 6 now reports
two nulls instead of one.
