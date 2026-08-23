# Will free equity data reproduce Bloomberg?

**Date:** 2026-08-20 · **Status:** protocol fixed in advance; **test since run — see result below**

> **Result, 2026-08-22.** The test was run on the 2020–2026 overlap and
> **all five candidates fail** the criteria in §3, reported as they came out:
>
> | series | ret ρ | vol ρ | beta | R² | TE | passed |
> |---|---|---|---|---|---|---|
> | us_defence vs WAERLST | 0.890 | 0.964 | 0.888 | 0.793 | 0.725 | no |
> | eu_defence vs BSHIELDT | 0.904 | 0.875 | 0.926 | 0.817 | 0.794 | no |
> | **ITA vs WAERLST** | **0.955** | **0.987** | **1.032** | **0.911** | 0.501 | no — by 0.001 |
> | XAR vs WAERLST | 0.895 | 0.961 | 1.033 | 0.801 | 0.799 | no |
> | PPA vs WAERLST | 0.934 | 0.976 | 0.893 | 0.873 | 0.554 | no |
>
> ITA clears four of five criteria and misses tracking error by 0.0013, so under
> §3's overriding criterion it is usable as a global-A&D proxy. **The European
> basket is genuinely weak at ρ=0.904**, and no long-history European defence
> ETF exists, so European results before 2020 rest on a hand-built basket. Table:
> `thesis_v2/outputs/tables/basket_validation.csv`.

Short answer: **no, and it cannot.** WAERLST and BSHIELDT are proprietary
Bloomberg indices. There is no free equivalent — only a *different portfolio*
that may or may not be close enough. The right question is therefore not "is it
the same information" but "does the thesis reach the same conclusions under
both", and that is answered by a test on the 2020–2026 overlap, with criteria
fixed before the test is run.

This has not been run, because a cloud session has neither the Bloomberg files
(they are on Drive) nor a reachable equity source
(see [`data_sources.md`](data_sources.md) §2).

---

## 1. Six reasons the series will differ

None of these is a data-quality complaint about the free vendors. They are
structural.

1. **A different portfolio.** WAERLST holds 118 constituents at float-adjusted
   weights. A basket of ten listed defence names, equal- or cap-weighted, is a
   different object. In 2022 an equal-weight European basket would be dominated
   by Rheinmetall, which rose several hundred percent — concentration alone
   could drive a large divergence.
2. **Total return vs price return.** Bloomberg `PX_LAST` is a price index;
   Yahoo's adjusted close is dividend-adjusted. This affects drift much more
   than daily volatility, but it biases any level comparison.
3. **Currency.** WAERLST is quoted in USD, BSHIELDT in EUR. Free tickers trade
   in local currency, so a converted basket carries FX volatility that the index
   does not.
4. **Close-time misalignment.** European exchanges close roughly six hours
   before US ones. A "daily return" on a mixed-region basket blends two
   different information sets — which matters specifically for the
   contemporaneous response estimates and for horizon 0 of the local
   projections.
5. **Corporate actions inside the sample.** The United Technologies–Raytheon
   merger (April 2020) and the L3–Harris merger (2019) both fall in or near the
   window. Free history for merged and renamed tickers is unreliable.
6. **Survivorship.** Index membership changes over eleven years; a fixed basket
   is a static portfolio and quietly drops the entrants and keeps the leavers.

## 2. The precedent, and the trap it exposes

v1 reconstructed both indices from constituents. From the committed
`thesis_v1/outputs/tables/descriptive_stats.csv`:

| Series | n | mean | std | min | max |
|---|---|---|---|---|---|
| `r_WAERLST` (real) | 970 | 0.109 | **1.059** | −8.66 | 4.86 |
| `r_WAERLST_recon` | 918 | 0.151 | **2.456** | −11.67 | 11.01 |
| `r_BSHIELDT` (real) | 970 | 0.150 | **1.446** | −8.55 | 10.13 |
| `r_BSHIELDT_recon` | 914 | 0.149 | **1.498** | −8.16 | 10.07 |

The WAERLST reconstruction is 2.3× too volatile — obviously broken, and it
correlated with the proxy at ρ = 0.15.

**The BSHIELDT reconstruction is the instructive one.** Its mean (0.149 vs
0.150) and standard deviation (1.498 vs 1.446) are nearly identical to the real
series, and it was still rejected as unusable. Matching moments is not evidence
of matching series — two series can share a distribution and share almost no
common variation. So nothing below is scored on means, standard deviations, or
distribution shape.

## 3. Acceptance criteria — fixed in advance

Computed on daily log returns over the 2020-01 → 2026-06 overlap, per region
(a US basket against WAERLST, a European basket against BSHIELDT). Implemented
in `thesis_v2/src/data/validate_basket.py`; a test asserts these numbers so they
cannot be quietly loosened later.

| Criterion | Threshold | Why here |
|---|---|---|
| Correlation of daily returns | **≥ 0.95** | Below this the substitute has meaningfully different daily variation, which is what every regression uses. |
| Correlation of 20-day realized volatility | **≥ 0.90** | The volatility results are half the thesis; a basket can track returns and still misstate volatility. |
| Regression beta on the index | **0.85 – 1.15** | Rules out a systematically more or less volatile portfolio. |
| Regression R² | **≥ 0.90** | The share of the substitute's variation the index explains. |
| Tracking error (sd of the daily difference) | **≤ 0.50 pp/day** | Roughly a third of BSHIELDT's own daily sd. |

**And one criterion that outranks all of them:** re-run the headline regression
on both series. If the sign, magnitude and significance verdict agree, the
substitution is safe *for this thesis* even if a statistic above is marginal. If
they disagree, the substitution is unsafe even if every statistic passes. Report
both versions either way.

## 4. Design consequence — do not splice

The tempting move is to stitch free data for 2015–2019 onto Bloomberg for
2020–2026. **Don't.** That places a change in measurement roughly two months
before the single event the thesis is built around, and any break estimated at
February 2022 would be partly a measurement artefact. Splicing is how a clean
result turns into an unfalsifiable one.

Instead:

- **Main sample:** one consistent free-data series across the whole
  2015-02 → 2026-06 window. No internal break.
- **Robustness:** Bloomberg over 2020–2026, reported alongside. Where the two
  agree, that is a strong robustness result; where they disagree, that is
  something we need to know before the defence, not after.

This also answers a fair objection to the free-data route — that it is lower
quality — by making the high-quality series the referee rather than dropping it.

## 5. What is needed to run this

1. The Bloomberg daily series for WAERLST and BSHIELDT, 2020-01 → 2026-06,
   synced from Drive and committed as a small CSV. That alone unblocks the test.
2. A candidate basket, from a vendor key or a Colab run
   ([`data_sources.md`](data_sources.md) §3).

Then `validate_basket()` produces the table, and the answer is either a pass, or
a specific reason to reconsider the basket's composition.
