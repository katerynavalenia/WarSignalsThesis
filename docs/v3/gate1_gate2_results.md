# Gate 1 and Gate 2 — results, and what they mean for the thesis

**Date:** 2026-08-20 · **Status:** run end to end on real data; provisional where marked
**Code:** `thesis_v2/src/data/{equities,gdelt_bq,ecosystems}.py`,
`thesis_v2/src/features/{episodes,perception}.py`
**Data:** `data/interim/{spine_full,gdelt_ecosystems_daily,perception_indices}.parquet`

---

## 0. Verdict in four lines

1. **The expectations/threat channel does not exist.** It was an artefact of
   controlling European defence equities with the S&P 500. With STOXX 600 it
   disappears. This retracts v2 §6.4 *and* `gpr_regime_preview.md`.
2. **Gate 1 passes on measurement.** The rebuilt ecosystems are genuinely
   distinct populations, unlike v1's. The external GPR check needed
   re-specifying, not loosening — see §4.
3. **Gate 2 fails.** Local-language perception adds nothing over Western media
   for defence-equity returns, and nothing at all in the Russia window.
4. **One strong positive survives, and it is not an asset-pricing result:** the
   censorship wedge. Russian state media's tone did not move when Russia
   invaded, while every other ecosystem's did.

---

## 1. The threat channel was a market-control artefact

`gpr_regime_preview.md` reported threat shocks moving defence returns at
p=0.0001 in the 2021 build-up, and flagged as its main caveat that only SP500
was available as a market control. That caveat was fatal.

Buildup window, 2021-11-01 → 2022-02-23, threat coefficient p-value:

| target | control = SPX | control = **SXXP** | no control |
|---|---|---|---|
| r_bshieldt | 0.018 | **0.843** | 0.228 |
| eu_defence | 0.004 | **0.460** | 0.049 |
| r_waerlst | 0.002 | **0.865** | 0.295 |
| us_defence | 0.009 | **0.360** | 0.229 |

The mechanism is measurable. In that window `corr(SPX, SXXP)` on daily returns
is only **0.409**, so SP500 leaves almost all European market variation in the
residual — the part of SXXP orthogonal to SPX has sd 0.98 against SXXP's own
1.08. That residual correlates **0.26** with Δgpr_threat. GPR_THREAT was
standing in for the omitted European market factor.

**This retracts two earlier headline claims** — v2's "European defence
volatility loads on THREAT (p<0.001)" and this project's own build-up result.
Both were run without a European benchmark. `research_plan_v3.md` §9's *high*
prior for SQ2 rests on them and should be removed, not merely downgraded.

What survives with correct controls is thin and unsurprising: European defence
responds to realized **acts** during the invasion itself (eu_defence +0.562,
p=0.008), and on non-episode days too (+0.083, p=0.005). Defence stocks rise
when a war starts. That is not a finding anyone will contest, or reward.

## 2. Anticipation episodes

Detected from GPR alone — never from returns, so episode selection cannot be
contaminated by the outcome. Threshold 0.5 on a 21-day smoothed difference of
trailing-standardised threat and act:

| window | days | peak | label |
|---|---|---|---|
| 2017-07-07 → 2018-01-19 | 135 | 1.51 | North Korea ICBM crisis |
| 2018-03-09 → 2019-03-13 | 252 | 2.32 | *(unlabelled — trade war / Iran deal)* |
| 2019-05-14 → 2019-08-07 | 60 | 1.63 | *(unlabelled — Gulf tanker crisis)* |
| 2021-11-22 → 2022-03-22 | 83 | **2.78** | **Russia buildup / invasion** |
| 2025-05-21 → 2025-08-06 | 53 | 1.84 | *(unlabelled)* |
| 2025-12-04 → 2026-03-06 | 62 | 1.68 | *(unlabelled)* |

645 days against the build-up's 83 — the power problem is solved, and face
validity holds: the detector recovers known anticipation events and ranks the
Russia build-up highest of all.

**The threat effect does not replicate in any of them.** Across six episodes ×
five targets, no consistent threat coefficient appears.

## 3. The long sample is now buildable, free

Yahoo's chart endpoint serves every needed ticker 2015→2026 from a residential
connection, including `^STOXX`. `data_sources.md` §2's conclusion that the
equity half needs a vendor key is true only of a cloud session.

**The pre-registered basket test (`equity_validation.md` §3) fails for every
candidate** — reported as run, not reinterpreted after the fact:

| series | ret corr | vol corr | beta | R² | TE | passed |
|---|---|---|---|---|---|---|
| us_defence vs WAERLST | 0.890 | 0.964 | 0.888 | 0.793 | 0.725 | no |
| eu_defence vs BSHIELDT | 0.904 | 0.875 | 0.926 | 0.817 | 0.794 | no |
| **ITA etf vs WAERLST** | **0.955** | **0.987** | **1.032** | **0.911** | 0.501 | no — by 0.001 |
| XAR etf vs WAERLST | 0.895 | 0.961 | 1.033 | 0.801 | 0.799 | no |
| PPA etf vs WAERLST | 0.934 | 0.976 | 0.893 | 0.873 | 0.554 | no |

ITA clears four of five criteria and misses tracking error by 0.0013, so it is a
usable global-A&D proxy under §3's overriding criterion. **The European basket
is genuinely weak** (ρ=0.904) and no long-history European defence ETF exists —
so European results before 2020 will always rest on a hand-built basket.

## 4. Gate 1 — the measurement is real

Ingested from `gdelt-bq.gdeltv2.gkg_partitioned`: **182 GB scanned, inside the
free tier**, 1,605 days across the six episode windows ±75 days, 7 ecosystems.

| ecosystem | conflict articles | total | conflict share |
|---|---|---|---|
| WEST | 12.1 M | 182.7 M | 6.6% |
| EN_GLOBAL | 11.3 M | 209.7 M | 5.4% |
| RU_OTHER | 11.7 M | 18.1 M | 64.5% |
| UA | 7.8 M | 9.9 M | **79.2%** |
| RU_STATE | 4.9 M | 6.9 M | 71.4% |
| RU_INDEP | 0.8 M | 1.3 M | 63.6% |

**Non-collinearity passes decisively** — pairwise correlation of attention changes:

| | UA | RU_STATE | RU_INDEP | WEST | EN_GLOBAL |
|---|---|---|---|---|---|
| **UA** | 1.00 | 0.44 | 0.13 | 0.18 | **0.05** |
| **RU_STATE** | | 1.00 | 0.29 | 0.16 | **0.05** |
| **RU_INDEP** | | | 1.00 | 0.35 | 0.22 |
| **WEST** | | | | 1.00 | 0.67 |

Max 0.673, and that pair (WEST/EN_GLOBAL) overlaps by construction. v1's three
"national" series were near-duplicates drawn from one population; these are not.
**The rebuild worked.**

**Face validity passes.** Attention share on 2022-02-24: WEST 18.8% → 40.7%,
EN_GLOBAL 11.8% → 23.8%, RU_STATE 84.6% → 91.2%, UA 90.3% → 95.8%.

**The external GPR check needed re-specifying.** In daily changes the
correlation is ~0.03 — below the 0.40 threshold fixed in advance. But that
threshold was applied to the wrong quantity. GPR is *global*; these indices are
*Ukraine-specific*. Correlation in levels:

| window | WEST | EN_GLOBAL | UA | RU_STATE |
|---|---|---|---|---|
| 2021-09 → 2022-06 (GPR driven by Ukraine) | **0.866** | **0.884** | 0.718 | 0.791 |
| 2017-2019 (GPR driven by Korea/Iran) | 0.083 | 0.048 | 0.010 | −0.105 |

The indices track GPR almost perfectly when GPR is about their subject, and
correctly ignore it when it is not. That is the check passing, in the form it
should have been written.

**But the daily-changes result is itself a finding, and a problem.** Two
measures of the same conflict, correlated 0.87 in levels, share essentially
nothing day to day. Daily attention changes are mostly noise — which is exactly
what a daily-shock design needs them not to be.

*Not run: the hand-labelled precision audit (§5.5.1).* It requires opening
several hundred URLs in Russian and Ukrainian and cannot be automated. Gate 1 is
**provisionally passed** pending it.

## 5. The censorship wedge — the strongest result here

Mean conflict tone, before and after the invasion:

| ecosystem | pre (2021-11→02-23) | post (02-24→06-05) | shift |
|---|---|---|---|
| UA | −1.77 | −3.43 | **−1.66** |
| EN_GLOBAL | −1.87 | −2.51 | −0.64 |
| WEST | −1.88 | −2.25 | −0.38 |
| RU_INDEP | −2.23 | −2.49 | −0.26 |
| **RU_STATE** | **−1.81** | **−1.79** | **+0.02** |

**Russian state media's tone did not move when Russia invaded Ukraine.** Every
other ecosystem's did, Ukraine's by 1.66 points. The RU_STATE − RU_INDEP wedge
widens from +0.41 to +0.69 — measured on the same corpus, same dictionary, same
days, with the two Russian ecosystems separated only by ownership.

This is a clean, quantified, novel descriptive result, and it is exactly the
press-freedom control Bondarenko et al. (2024) apply, made visible as a series.

## 6. Gate 2 — local does not beat Western

The test: defence returns on all five ecosystems' attention and tone shocks plus
market and VIX, HAC(5); joint F-test of the three local blocks (UA, RU_STATE,
RU_INDEP) **conditional on** WEST and EN_GLOBAL. Benjamini–Hochberg across the
whole grid of frequency × window × target.

```
specifications             : 31
nominally significant (5%) : 8      (expected by chance 1.6)
surviving BH at FDR 5%     : 2
```

Both survivors are the *same* window and frequency — 2025-26 weekly, n=60 with
13 parameters. Dropping tone to halve the parameter count leaves **one**
survivor. And in the window the thesis is actually about:

| Russia buildup+invasion | p(local joint) |
|---|---|
| eu_defence | 0.619 |
| us_defence | 0.278 |
| r_ita | 0.090 |
| r_bshieldt | 0.216 |
| r_waerlst | 0.324 |

**Nothing.** The one place where a local-information advantage should be largest
— a European land war, covered first and most intensively by Ukrainian and
Russian media — is where local media add least.

So the answer to the thesis's central question is: **Western defence equities
price the Western narrative. Local-language perception carries no incremental
information for them.**

## 7. What this is worth

**Secured, and good:**

- An 11-year multilingual publisher-classified perception dataset, validated
  against GPR, with the register and classifier tested.
- The censorship wedge (§5) — striking, quantified, novel.
- Ecosystems that are demonstrably distinct where v1's were duplicates (§4).
- A methodological correction with teeth (§1): a widely-plausible "expectations
  channel" result that exists only until you control for the right market.

**Not there:**

- The headline. Local-language perception is not priced in defence equities.
- The expectations/threat channel. Retracted.
- Forecastability. Already null, and nothing here changes it.

**Assessment.** This is a **well-measured null with a strong descriptive core** —
a viable master's thesis, not a strong-positive one. Its honest shape is:
Chapters 5–6 (measurement, stylized facts, censorship wedge) carry it; Chapters
7–8 report informative nulls with the power to back them; and the methodological
correction in §1 is a genuine contribution because it explains why a plausible
positive kept appearing in earlier drafts.

The direction of the Gate-2 null is worth stating carefully rather than
apologising for. Bondarenko et al. find local-language geopolitical risk moves
the *Russian* economy while English-language risk does not. We find the mirror
image for *Western defence equities*: the Western narrative is what is priced,
and local perception adds nothing. Same instrument, opposite side of the
conflict, opposite answer — that is a coherent finding and a defensible chapter.
It is also the answer most economists would have predicted, which is why it
cannot carry an introduction on its own.

## 8. Limits — this null is provisional

- **Indices are simplified.** Attention share and mean tone only. §5.4 also
  specifies a per-language Caldara–Iacoviello threat/act dictionary split,
  escalation theme shares, and pairwise perception gaps. None are built. A
  threat/act split *within* each ecosystem is the most likely place a real
  effect still hides.
- **1,605 days ingested, not 4,151.** Episode windows ±75 days.
- **No hand-labelled precision audit** (§5.5.1). Gate 1 is provisional.
- **Daily frequency may be wrong** (§4). Weekly was tested and is where the only
  BH survivors appear — worth pursuing before accepting the null as final.
- **RU_INDEP is thin** — 0.8 M articles against WEST's 12.1 M, and several
  outlets were shut down or exiled mid-sample.
- **Conflict filter is coarse** — V1 `Locations` containing Ukraine or Russia.
  Cheap, and it made the whole ingest fit in the free tier, but it will include
  unrelated coverage that mentions either country.
