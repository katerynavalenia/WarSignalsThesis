# Gate 4 — pre-registration: European gas

**Written 2026-08-22, before the continuous 2021–2023 ingest exists.** The
exploratory run that motivated this used 81 days in the build-up window; the
confirmatory test below uses data not yet collected.

## Why change the asset

The thesis asks whose perception of geopolitical risk is priced. Three gates
answered "not local media" for defence equities. Defence equities were always a
weak testbed for that question: the causal link from Russian or Ukrainian
reporting to Lockheed's share price runs entirely through Western investor
sentiment, so finding that only Western media matter is close to definitional.

European natural gas is the asset through which this conflict actually
transmitted. Russia supplied roughly 40% of EU gas; TTF moved from about €20 to
over €300. Russian state media is the outlet through which Gazprom and the
Russian state signalled supply intentions, so if any asset prices *local*
perception, it is this one. The question is unchanged — only the testbed is
better matched to it.

## Exploratory evidence that motivated this (not confirmatory)

Build-up window 2021-11-22 → 2022-03-22, n=81, one-day-lagged news, HAC(5),
joint F-test of the local block conditional on the Western block:

| specification | p_local |
|---|---|
| STOXX + VIX controls | 0.0056 |
| Brent + VIX | 0.0008 |
| Brent + EURUSD + VIX | 0.0014 |
| Brent + EURUSD + STOXX + VIX | 0.0005 |

Placebos, same window and specification: **US Henry Hub gas p=0.588**, Brent
p=0.514, wheat p=0.280, Unilever p=0.546.

Two things distinguish this from the three positives this project has already
retracted. It **strengthens** under correct controls rather than dissolving, and
the placebo that discriminates the mechanism — US gas, which carries no Russian
supply — is cleanly null. Two things warn against it: n=81, and the result does
not extend to the full sample (p=0.39).

## Hypothesis, fixed now

**H:** Changes in local-media (UA, RU_STATE, RU_INDEP) attention and tone explain
European gas returns **conditional on** Western-media (WEST, EN_GLOBAL) attention
and tone, during the period in which Russian supply to Europe was in question.

**Directional sub-hypothesis, fixed now:** the RU_STATE block carries the effect.
The mechanism is state signalling of supply intent, so if the effect is real it
should load on state media rather than on Ukrainian or independent Russian media.

## Data to be collected

Continuous daily ecosystem indices for **2021-06-01 → 2023-12-31** — the gas
crisis from pre-build-up through the Nord Stream shutdown and the subsequent
price normalisation. Currently only episode windows are ingested. Estimated 100–
120 GB of BigQuery scan.

## Test, fixed now

- **Primary asset:** TTF front-month (`TTF=F`), daily log returns.
- **Controls:** Brent, EUR/USD, lagged own return, lagged VIX. Not STOXX as the
  sole control — a gas future is not a European equity.
- **Timing:** news lagged one day.
- **Statistic:** joint F-test of the six local terms conditional on the four
  Western terms, HAC(5).
- **Windows:** (a) 2021-06→2022-06 build-up and invasion; (b) 2022-06→2023-06
  Nord Stream shutdown and aftermath — an *independent* window within the same
  crisis; (c) the full 2021-06→2023-12 period.
- **Correction:** Benjamini–Hochberg across the full grid of window × frequency.

## Placebos, fixed now

The result must be **absent** in: US Henry Hub gas, Brent crude, and a
war-unexposed equity (Unilever). If local perception explains US gas as strongly
as European gas, the channel is a global risk factor rather than Russian supply,
and the hypothesis is rejected regardless of the European p-value.

## Pass rule, fixed now

**PASS** requires all four:

1. BH-surviving local block in window (a) **and** in window (b) — two
   non-overlapping periods within the crisis;
2. placebos null (p > 0.10) in both windows;
3. survives dropping the ten largest absolute TTF moves in each window;
4. the RU_STATE terms are individually the largest contributors, consistent with
   the directional sub-hypothesis.

Anything less is **FAIL**, reported as exploratory, and the thesis reverts to the
defence-equity write-up — for which Chapters 3, 4 and 5 are already drafted and
unaffected, since the measurement and descriptive work is shared.

## Why the rule is this strict

Three positives have already been retracted here: a threat channel that was an
omitted European market factor, a build-up result with the same defect, and a
Gate-3 pass that existed only on a truncated sample. Each looked convincing at
the moment of discovery. Condition 3 exists because the exploratory run lost
significance when five days were dropped (p=0.063), which is the single clearest
warning sign in the evidence above.
