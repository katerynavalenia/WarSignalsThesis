# Thesis assembly map — every claim, its number, and its source

**Purpose:** a 3-day write-up needs no analysis decisions left open. Every number
the thesis will state is listed here with the file it comes from, so drafting is
transcription rather than recomputation. If a number is not on this page, it does
not go in the thesis.

**Before using any number from `docs/v3/`, check
[`../docs/findings_status.md`](../docs/findings_status.md).** Six
claims in those documents have been retracted and the documents still state them
in their own voice, because the retraction sequence is itself part of the
thesis. That file is the authority on which results are live.

**Title:** *Whose Perception of Geopolitical Risk Is Priced in Defence Equities?
Evidence from the Russia–Ukraine War*

**One-sentence answer:** the Western narrative's — and we can show the test had
the power to find otherwise.

---

## The three-day plan

| day | output |
|---|---|
| 1 | Ch. 3 Data, Ch. 4 Measurement, Ch. 5 Stylized facts — the secured chapters, all inputs exist |
| 2 | Ch. 6 Response, Ch. 7 Efficiency, Ch. 8 Robustness — the results, all tables exist |
| 3 | Ch. 1 Introduction, Ch. 2 Literature, Ch. 9 Conclusion, assembly, reference check |

Introduction last, deliberately: it is easiest to write once the result is on
the page, and it is the chapter most often rewritten if drafted first.

---

## Chapter map

### Ch. 1 — Introduction
Frame the question, state the answer, state the power. The three contributions:
(i) an eleven-year publisher-classified multilingual perception dataset;
(ii) the finding that local-language perception is not priced in Western defence
equities, with a positive control and a power statement; (iii) three
methodological corrections, each of which killed a plausible positive.

### Ch. 2 — Literature
Caldara & Iacoviello (2022) for GPR and the ACT/THREAT decomposition.
**Bondarenko, Lewis, Rottner & Schüler (2024, JIE 152:104005)** as the primary
anchor — they find local-language geopolitical risk moves the Russian economy
while English-language risk does not. This thesis runs the mirror test on the
counterparty's equities and finds the opposite asymmetry. Campbell & Thompson
(2008), Clark & West (2007), Diebold & Mariano (1995) for evaluation.

### Ch. 3 — Data
| item | number | source |
|---|---|---|
| GDELT translingual archive | 2015-02-18 onward; 390,440 files, 4.19 TB | `gdelt_measurement_diagnosis.md` |
| BigQuery table | `gkg_partitioned`, 1.83 bn rows, 21.8 TB, day-partitioned | `gate1_gate2_results.md` §4 |
| Perception-index coverage | **2015-02-18 → 2026-05-20, 4,027 days, 98% of calendar**; ~3× the reviewed version on matched units (2,837 trading days vs 931, or 4,027 calendar days vs 1,370). **Do not write "4.4×"** — that divides calendar days by trading days | ingest logs |
| In-sample corpus (Gates 1-2, 4, Ch7) | 3,073 days, 2015-02-18 -> 2026-05-20 | ingest logs |
| Held-out block (Gate 5 only) | 954 days, never used in-sample | ingest logs |
| Gate 3 threat/act | **4,027 days** (2,422 filled at 706 GB after the initial 1,605) | `gate3_results.md` |
| Equity spine | 2015-02-18 → 2026-06-29, 2,837 trading days, 19 tickers | `data_sources.md` |
| Regimes | pre_war 1,678 / buildup 79 / invasion 149 / attrition 931 | spine build log |
| Bloomberg | WAERLST, BSHIELDT, 2020-01 → 2026-06, 1,698 days | `bloomberg.py` |

**Free-basket validation, reported as it ran** (`basket_validation.csv`): all five
candidates fail the pre-registered criteria; ITA clears four of five and misses
tracking error by 0.0013; the European basket is genuinely weak at ρ=0.904.

### Ch. 4 — Measurement (answers supervisor comment #3)
**The error being fixed.** v1 used GKG 1.0, effectively English-only: **7 `.ru`
and 21 `.ua` articles out of 60,690** on 2025-03-01, with 88.6% of articles
assigned a nationality by the country *mentioned*. The translingual stream on the
same day carries ~9,700 Russian-language and ~3,200 Ukrainian-language records —
three orders of magnitude more.

**The classifier.** Four tiers, country dominant, language splitting within
country. The rule is not cosmetic: `24tv.ua` publishes 2,595 Ukrainian-language
and 1,865 Russian-language articles; `censor.net.ua` and `nv.ua` are
Russian-language throughout. A language-first rule would file Ukrainian media as
Russian and manufacture agreement between the two ecosystems.

**Attention shares** (`gate1_gate2_results.md` §4): UA 79.2%, RU_STATE 71.4%,
RU_OTHER 64.5%, RU_INDEP 63.6%, WEST 6.6%, EN_GLOBAL 5.4%.

**Gate 1 validation.**
- Non-collinearity: max pairwise 0.673 (WEST/EN_GLOBAL, overlapping by
  construction); UA↔EN_GLOBAL **0.05**, RU_STATE↔EN_GLOBAL 0.05, UA↔WEST 0.18.
- External validity, levels: WEST **0.866** and EN_GLOBAL **0.884** against
  published GPR in the Ukraine-driven window; 0.083 and 0.048 in 2017-19 when
  GPR is driven by Korea and Iran — correct behaviour for a Ukraine-specific
  index, and the reason the original changes-based threshold was the wrong test.
- Face validity: attention share on 2022-02-24 — WEST 18.8→40.7%,
  EN_GLOBAL 11.8→23.8%.
- **Limitation, stated plainly:** the hand-labelled precision audit was not run.
  Gate 1 is provisional. `dw.com` was found misclassified by a robustness run,
  which is the argument for the audit and is reported as such.

### Ch. 5 — Stylized facts (answers supervisor comment #2)
**Full-sample plots** (§5.1): `outputs/figures/fig1_attention_full_sample.png` and
`fig2_tone_full_sample.png`, generated by `scripts/plot_stylized_facts.py` over
all 4,027 days, regimes shaded and 2022-02-24 marked. **Breaks** (§5.4): Chow at 2022-02-24 rejects for all 10 series; supremum scan puts 6 of 10 within 60 days, tone_UA exactly on the date, tone_RU_STATE 393 days later. **Correlations** (§5.6):
the cross-ecosystem attention-change matrix (`outputs/tables/gate1_collinearity.csv`)
and the levels correlations against published GPR, both windows.

**The centerpiece.** Mean conflict tone, pre- vs post-invasion:

| ecosystem | pre | post | shift |
|---|---|---|---|
| UA | −1.77 | −3.43 | **−1.66** |
| EN_GLOBAL | −1.87 | −2.51 | −0.64 |
| WEST | −1.88 | −2.25 | −0.38 |
| RU_INDEP | −2.23 | −2.49 | −0.26 |
| **RU_STATE** | **−1.81** | **−1.79** | **+0.02** |

Russian state media's tone did not move when Russia invaded Ukraine. On a fixed
outlet panel — 24 state outlets present on both sides with ≥200 articles each —
the mean shift is **−0.05**, with several outlets turning *more positive*
(regnum.ru +0.23, gazeta.ru +0.48, ren.tv +0.43, mskagency.ru +0.40).

**Report the state-vs-Ukraine contrast, not state-vs-independent.** The latter
does not survive the fixed panel (p=0.323 with the corrected register; p=0.151 before it), because most of the independent
ecosystem is exiled or was shut down — echo.msk.ru falls from 13,951 articles to
1,043 after liquidation — so the ecosystem-level version was measured partly on a
change of membership across the event it claims to measure.

**Anticipation episodes** (`episodes.py`): six detected from GPR alone, never
from returns; 645 days. Face validity — North Korea 2017, Gulf tanker 2019, and
the Russia buildup ranked highest of all at peak 2.78. Threat-to-act ratio 3.43
in the buildup against 1.12 in attrition.

### Ch. 6 — Response (SQ2, SQ4)
**The headline null.** Local ecosystems conditional on Western, joint F, HAC(5),
BH across the grid:

| test | specs | nominal 5% | survive BH |
|---|---|---|---|
| Gate 2 — attention + tone | 31 | 8 | 3 (all in one thin window) |
| Gate 2 — news lagged | 31 | 6 | **0** |
| Gate 3 — threat/act, primary | 31 | 9 | 2 |
| Gate 3 — threat/act, same-day | 31 | 6 | **0** |

Russia buildup+invasion window, Gate 3 primary: p = 0.012 to 0.597, nothing
surviving. **Positive control passes** — the Western block is detected in 2 of 31
cells (2 of 31 on the full corpus), min p=0.0002 — so the design can see what is there.

**Out-of-sample sign test.** The weekly cells showed a coherent structure
(`act_RU_INDEP` 7/7 same sign, `act_UA` and `thr_UA` 6/7) reading as *buy the
rumour, sell the fact*. Formed on 2021–2026 and tested on 2017-19, which had not
been ingested when the four signs were written down: **7 of 12 signs match,
binomial p=0.387.** US targets partly replicate, the European target inverts.

### Ch. 7 — Efficiency (answers supervisor comment #4)
50 specifications, expanding-window one-day-ahead, Campbell–Thompson R²_OS with
Clark–West (nested, so DM is invalid):

- best R²_OS **+0.0011**; 3 of 50 positive
- Clark–West p<0.05: **0**, against 2.5 expected by chance
- surviving BH: 0

**The power statement**, simulated on 1,855 out-of-sample days:

| true R²_OS | 0.0% | 0.2% | 0.5% | 1.0% | 2.0% | 4.0% |
|---|---|---|---|---|---|---|
| rejection rate | 0.02 | 0.43 | **0.82** | 0.98 | 1.00 | 1.00 |

So: **0.5% detectable at 82% power, 0.2% at 43%**, size at zero effect 0.02.
The claim is bounded — predictability across most of the range this literature
reports is ruled out; only the region below it is not.

### Ch. 8 — Robustness, and three corrections that killed a positive
This chapter is a contribution, not an appendix. Three times a plausible positive
appeared and dissolved:

1. **The market control.** GPR_THREAT appeared to move European defence returns
   at p=0.0001 in the buildup. With STOXX 600 instead of the S&P 500 it goes to
   p=0.843, and the same flip happens for all four targets. `corr(SPX, SXXP)` is
   **0.409** in that window, so SP500 leaves nearly all European market variation
   in the residual, and that residual correlates 0.26 with the threat shock. This
   retracts v2's headline and an intermediate result of this thesis.
   **What survives is better:** SXXP *itself* loads on threat at **+0.474
   (p<0.0001)** — threat is priced market-wide in Europe, not differentially in
   defence.
2. **The truncated sample.** On a partial ingest of 694 days the pre-registered
   Gate-3 test returned **7 BH survivors and a PASS**. Adding the held-out
   2017-19 window — same grid, nothing else changed — took it to 2 survivors and
   a FAIL. A pre-registered test on a truncated sample is not a pre-registered
   test.
3. **The register error.** `dw.com` — Deutsche Welle, a German public
   broadcaster — sat in the Russian-independent register, contributing that
   ecosystem's largest volume and largest negative tone shift. It survived every
   downstream check and was caught by a fixed-panel robustness run, not by
   validation.

### Ch. 9 — Conclusion
The question is answered and the answer is a null with power. Bondarenko et al.
find local-language risk moves the Russian economy while English-language risk
does not; this thesis runs the mirror test on Western defence equities and finds
the reverse asymmetry — the Western narrative is what is priced, and local
perception adds nothing in volume, in tone, or in anticipation structure.

---

## Do not claim
- Any threat/expectations channel specific to defence equities — retracted, Ch. 8.
- The state-vs-independent censorship wedge — p=0.323 on a fixed panel with the corrected register.
- Any Gate-3 pass — it exists only on the truncated sample.
- Hand-validated ecosystem precision — the audit was not run.
- Firm-level or SIPRI-exposure results — that data no longer exists anywhere.

## Open limitations to state in Ch. 8
- Precision audit not run; Gate 1 provisional.
- Ecosystem tables predate the `dw.com` fix.
- Coverage is 4,027 of 4,151 calendar days; the shortfall is gaps in GDELT itself.
- Conflict filter is coarse: V1 `Locations` containing Ukraine or Russia.
- 2017-19 is now used and is no longer a held-out window.
- Daily equity data against 15-minute news; no intraday lead-lag test.
