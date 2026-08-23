# Gate 5 — pre-registration: does local media anticipate escalation?

**Written 2026-08-23, before the held-out days are ingested.** The exploratory
evidence below uses the 2,278 days currently in hand. The confirmatory test uses
roughly 950 days that are **not yet collected** — the gaps in the existing
ingest, 2019-10 → 2021-05 and calendar 2024.

## The idea

Four gates established that local-language perception is not priced, in defence
equities and in European gas. That is what market efficiency predicts and it is
not, on its own, surprising.

But escalation is not a traded asset. No arbitrage force makes media coverage
uninformative about *future conflict events*. So the question that the price
nulls leave open is whether the information exists at all. If local media
anticipate realized escalation while markets do not price it, the thesis has a
mechanism rather than an absence: **the information is there and markets do not
use it.**

## Exploratory evidence (not confirmatory — already seen)

Outcome: change in GPR_ACT over the next *h* days. Predictors: ecosystem
attention and tone **in levels**. Controls: six lags each of the outcome's level
and first difference, plus the Western block. HAC(h+5). Joint F on the three
local ecosystems, conditional on the two Western ones.

| outcome | h | first half 2017-04→2021-12 | second half 2022-01→2026-05 |
|---|---|---|---|
| GPR_ACT | 1 | p=0.039 | p=0.0001 |
| GPR_ACT | 5 | p=0.024 | p=0.0000 |
| GPR_THREAT | 1 | p=0.464 | p=0.0003 |
| GPR_THREAT | 5 | p=0.135 | p=0.0008 |

Both halves significant for realized **acts**; only the later half for threat
rhetoric. In the first half the Western block is null (0.19, 0.89) while the
local block is not — the asymmetry Bondarenko et al. (2024) report for Russian
macro aggregates, appearing here on conflict escalation.

Robustness already run: survives twelve lags of own dynamics (p rises from
0.0000 to 0.0003–0.019 but does not die); a time-shuffle placebo of the
perception series gives p=0.616.

## Why levels rather than changes

The changes specification is null, and that must be argued rather than hidden.
The reading is that anticipation is a **level** phenomenon: an ecosystem
sustaining elevated conflict attention for weeks is the signal, while day-to-day
movement in that attention is noise. This is consistent with a fact already
established in Chapter 4 — the perception indices agree with published GPR at
0.87 in levels and near zero in daily changes.

The risk this creates is the persistence trap that killed an earlier result in
this project, and it is why the confirmatory design below controls the outcome's
own dynamics heavily and why a held-out sample is required.

## Data to be collected

The current ingest covers 2,278 of about 4,151 available days, in episode and
crisis windows. The gaps — **2019-10-22 → 2021-05-31** and **2024-01-01 →
2024-12-31**, roughly 950 days — have never been ingested and no result has been
computed on them. They are the held-out sample.

## The confirmatory test, fixed now

- **Outcome:** GPR_ACT, cumulative change over h ∈ {1, 5}.
- **Predictors:** the five ecosystems' attention and tone, in levels.
- **Controls:** six lags each of GPR_ACT's level and first difference.
- **Statistic:** joint F on UA, RU_STATE, RU_INDEP conditional on WEST and
  EN_GLOBAL, HAC(h+5).
- **Sample:** the held-out days only, estimated as a single sample.
- **Correction:** Benjamini–Hochberg across the four cells (2 outcomes × 2
  horizons), where GPR_THREAT is included as the secondary outcome.

## Pass rule, fixed now

**PASS** requires all three:

1. GPR_ACT local block survives BH at FDR 5% on the held-out sample, at **both**
   horizons;
2. the time-shuffle placebo on the held-out sample gives p > 0.20;
3. the result survives twelve lags of own dynamics rather than six.

**FAIL** otherwise. On failure the finding is reported in the thesis as an
exploratory observation that did not replicate, and the thesis's conclusion is
unchanged.

## What a pass changes

The thesis stops being a null and becomes a mechanism: local media carry
information about coming escalation that Western media do not, and neither
defence equities nor European gas price it. The four price nulls become the
second half of that story rather than the whole of it.

## What a pass does not license

Any claim that this is tradeable. Chapter 7's power statement already bounds
what predictability of returns this sample could detect, and Gates 1–4 found
none. An informational lead about escalation is not an investment strategy, and
the thesis will not present it as one.
