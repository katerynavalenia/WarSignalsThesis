# What the surviving data already says about threat vs act

**Date:** 2026-08-20 · **Status:** estimated, reproducible, not yet sent to the supervisor
**Code:** `thesis_v2/scripts/phase1_gpr_regime_preview.py` · **Tables:** `thesis_v2/outputs/tables/phase1_*.csv`

The GDELT rebuild is the expensive part of the v3 plan, and
[`research_plan_v3.md`](research_plan_v3.md) §9 assigns probabilities to its
outcomes. Those probabilities were set before anything had been estimated on a
sample containing the 2021 build-up. This note tests them with data available
today: the two Bloomberg index workbooks (2020-01 → 2026-06, which already span
the build-up and the invasion), plus GPR and FRED, both free.

**GPR is not a stand-in for the thesis's own indices, but it is not arbitrary
either.** Caldara & Iacoviello build it from US, UK and Canadian newspapers, so
`GPRD_ACT` / `GPRD_THREAT` is a *Western-media* realized-vs-anticipated
decomposition. This is therefore a preview of the **WEST arm specifically** —
and of the series the rebuilt indices are validated against (§5.5).

---

## 1. Bottom line

Three findings, each of which changes something in the plan.

1. **The response is in returns, in the build-up, and nowhere else.** Standardized
   threat shocks move defence-equity returns at p<0.001 during
   2021-11 → 2022-02-23, and are indistinguishable from zero in the pre-war,
   invasion and attrition regimes.
2. **v2's volatility headline does not survive first-differencing.** It was a
   levels result on regressors with AR(1) ≈ 0.6–0.7 against a dependent variable
   with AR(1) ≈ 0.17.
3. **Neither channel forecasts tomorrow.** Every in-sample next-day p-value
   exceeds 0.11. Plan the forecasting chapter as a *powered null*, not a hope.

The first finding is the important one, and it sharpens the diagnosis of v1's
failure. The problem was not only that the sample was short — it is that
**v1's sample was the one regime in which the effect does not exist.**

## 2. The result

Both channels interacted with every regime dummy, one pooled regression,
common controls (market return, lagged VIX), HAC(5), standardized. Dependent
variable: daily log return.

| Regime | n | BSHIELDT threat | BSHIELDT act | WAERLST threat | WAERLST act |
|---|---|---|---|---|---|
| pre_war | 475 | −0.085 (0.34) | +0.020 (0.85) | −0.078 (0.32) | +0.058 (0.45) |
| **buildup** | **83** | **+0.369 (0.0001)** | **+0.355 (0.009)** | **+0.279 (0.0001)** | +0.127 (0.30) |
| invasion | 155 | +0.136 (0.27) | −0.012 (0.92) | +0.053 (0.53) | −0.056 (0.45) |
| attrition *(= the whole v1 sample)* | 979 | −0.012 (0.78) | +0.054 (0.19) | −0.013 (0.67) | +0.043 (0.12) |

Separate per-regime regressions agree (`phase1_race_returns_*.csv`).

**Threat beats act, but not uniformly.** For European defence (BSHIELDT) both
channels are significant in the build-up and threat is the larger; for global
A&D (WAERLST) only threat is significant. Report this asymmetry — it is a
result, and overclaiming "threat, not act" would misstate the BSHIELDT column.

### Volatility: nothing, anywhere

`phase1_race_vol_*.csv`: in changes, no regime × index × channel cell reaches
p<0.08. The v1/v2 focus on volatility as the responsive outcome is not
supported once the transform is right.

## 3. Robustness

| Check | Result |
|---|---|
| Build-up start moved 2021-08 → 2021-12 (end fixed) | Significant at every start; strengthens monotonically as the window tightens (WAERLST threat 0.153 → 0.279) |
| Controls dropped entirely | Survives (BSHIELDT +0.342, p=0.004) |
| Ten largest \|return\| days removed from build-up+invasion | Survives (BSHIELDT +0.175, p=0.047; WAERLST +0.116, p=0.085) |
| **Placebo: same calendar window one year earlier** | **Null** (BSHIELDT p=0.20, WAERLST p=0.47) |

The placebo is the one that matters most: the effect is not a seasonal or
window-length artefact.

## 4. Why v2's headline dies

`phase1_levels_vs_changes.csv`, dependent variable `vol_bshieldt`, attrition
sample — the specification v2 reported as its strongest positive:

| Transform | act | p | threat | p |
|---|---|---|---|---|
| levels | +0.071 | 0.062 | +0.073 | 0.111 |
| **changes** | −0.005 | 0.857 | −0.014 | 0.626 |

v2 reported act +0.067 (p=0.21) and **threat +0.188 (p<0.001)**. The act
coefficient reproduces almost exactly; the threat coefficient does not, and the
difference is plausibly the market control (v2 used SXXP for BSHIELDT; only
SP500 is reachable here). Either way the substantive point stands: in changes
there is nothing, and persistence is the reason. `GPRD_ACT` and `GPRD_THREAT`
have AR(1) of 0.68 and 0.61 in the attrition sample; `vol_bshieldt` has 0.17.

**Consequence for the plan:** §9's "significant volatility response — *high*
probability" rests on this result and should be downgraded. Commit to
changes/shocks as the primary transform now, in Block A, rather than deferring
the levels-vs-changes choice to the descriptive chapter.

## 5. The threat/act separation is a levels phenomenon

| Regime | threat/act ratio | corr (levels) | corr (changes) |
|---|---|---|---|
| pre_war | 1.85 | 0.30 | 0.24 |
| buildup | **3.43** | 0.48 | 0.13 |
| invasion | 1.49 | 0.61 | 0.21 |
| attrition | 1.12 | 0.56 | 0.26 |

The plan argues v1 could not separate threat from act because the two correlate
at ~0.59 in attrition. That is true **in levels only** — in changes they
correlate 0.26 there and are perfectly separable. So the reason v1 found
nothing is not that the channels were indistinguishable; it is that in the
attrition regime *neither channel does anything*.

## 6. Predictability

`phase1_predictability.csv` — next-day returns on today's shocks, in sample:
every p-value above 0.11, R² between 0.0004 and 0.03. An in-sample regression is
the friendlier test, so the Phase-5 out-of-sample battery will not do better.
This is fine, and it is the efficiency leg: the market prices anticipation *as
it arrives* and it is not exploitable afterwards.

## 7. What this implies for the plan

1. **Reframe the identification claim.** "n rises to ~2,850" overstates it — the
   identifying variation is concentrated in anticipation windows, and the
   build-up is 83 trading days. The right argument for the long sample is that
   it contains **more such episodes** (the spring-2021 Russian build-up, and
   other GPR threat spikes), not that it is three times longer.
2. **Lead with returns.** Promote returns; demote volatility to secondary.
3. **Consider "defence equities price anticipation, and only during
   anticipation"** as the headline. It is sharper than "whose perception is
   priced", already evidenced, and the ecosystem decomposition then answers
   *whose* anticipation — which is the novel part, and still open.
4. **The WEST arm works.** Whatever the GDELT rebuild finds, it must beat this
   benchmark; if a rebuilt WEST index cannot reproduce the build-up result, that
   is a red flag for the index, not a finding about markets.

## 8. Caveats

- **GPR ≠ the thesis's indices.** It is Western/English-language by
  construction, global rather than Ukraine-specific, and monthly-revised.
- **SP500 is the market control for both indices**, because it is what is
  reachable without a vendor key. BSHIELDT needs SXXP; magnitudes will move.
  FRED truncates SP500 to a rolling ten years, so this control cannot reach 2015.
- **No currency adjustment** (BSHIELDT in EUR, WAERLST in USD).
- **83 trading days** in the build-up, and many specifications were run without
  multiple-testing correction. Indicative, not a result to quote.
- The February-2022 move is large: BSHIELDT returned **+13.9%** cumulatively
  from 2022-02-23 to 2022-03-11, with +5.1% and +7.7% on 25 and 28 February.

## 9. Reproducing

```bash
cd thesis_v2 && python scripts/phase1_gpr_regime_preview.py
```

Needs the two Bloomberg workbooks in `thesis_v1/data/raw/bloomberg/` (gitignored;
mirrored to `gdrive:WarSignalsThesis_Data/data/raw/bloomberg/` on 2026-08-20) and
network access for GPR and FRED. Estimator and loader are unit-tested offline in
`thesis_v2/tests/test_regime_response.py`.
