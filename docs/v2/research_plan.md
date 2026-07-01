# Research Plan v2 — Defense-Equity Response to Conflict Intensity vs. Media Expectations

**Status:** active — authoritative execution plan and source of truth for
`thesis_v2/`. All agents read this first.
**Supersedes:** v1's forecasting question (see [`../v1/README.md`](../v1/README.md)).
**Last updated:** 2026-07-01 (after running the make-or-break identification
tests — see §6; several hypotheses were revised by the evidence).

---

## 1. Research question

> **Do defence and defence-related stocks respond more strongly to realized
> conflict intensity or to media-driven geopolitical expectations? Evidence
> from the Russia–Ukraine war.**

A **contemporaneous response** question (not forecasting). It asks what moves
defense equities *when it happens*, and which channel — the physical event or
the expectations/narrative about it — dominates.

---

## 2. Honest empirical reality (read before planning anything)

This plan was stress-tested with real regressions on the existing data
*before* being written, per the supervisor mandate "do not waste time." The
results reshaped it. **What survives rigorous identification:**

| Claim | Verdict | Strength |
|---|---|---|
| Defense-equity **volatility** is elevated on high-intensity attack days (firm level, controlling firm FE + contemporaneous market + VIX) | **Holds** (b≈+0.23, p<0.001) | but **uniform across firms** — see next row |
| This response **scales with defense-revenue exposure** (pure-plays react more) — *the intended novel centerpiece, H4* | **FALSIFIED** | Two-way FE interaction null (p=0.82–0.99); descriptively *reversed*. Defense pure-plays do **not** react more than civil firms. |
| Because H4 is null, the uniform vol bump is **not defense-specific** → likely a residual A&D-sector/industrial confound, not a clean "war response" | **Working interpretation** | weak foundation for a headline |
| **Media attention** (GDELT article volume) drives defense-equity volatility | **NULL / negative** | robust |
| European defense **volatility responds to GPR_THREAT (media-driven expectations) more than GPR_ACT (realized acts)** — the fair, symmetric test | **Holds** (BSHIELDT: THREAT b=+0.19, p<0.001; ACT p=0.21) | modest, index-level, GPR-is-global caveat |
| For global/US defense, ACT ≈ THREAT | Holds | both ~+0.09, p<0.05 |
| War signals **forecast** returns/volatility out-of-sample | **NULL** (from v1) | robust, multi-angle |
| UA/RU/Western media frame the same events with stable, measurable tone divergence | **Holds** (descriptive) | robust, novel — but about the *news*, not the market |

**Net:** the clean, novel firm-level heterogeneity thesis does **not** exist
in this data. What survives is (a) a modest, real **expectations/threat
channel** for (especially European) defense volatility — which *answers the
research question*, with the counter-intuitive result that **expectations ≥
realized** when measured cleanly; (b) a set of robust **nulls** (no
forecastability, no exposure gradient, no attention effect) that are
scientifically informative; and (c) a **descriptive** multilingual-narrative
contribution. See §11 for the honest odds of a "significant" thesis.

---

## 3. Hypotheses (revised by §6 evidence)

| # | Hypothesis | Status |
|---|---|---|
| **H1** | Defense-equity volatility rises on high realized-intensity days. | Holds, but uniform (not defense-specific) — treat as descriptive/confound-prone, not the headline. |
| **H2 (headline candidate)** | Defense-equity volatility responds to **media-driven geopolitical expectations (GPR_THREAT)** at least as strongly as to realized acts (GPR_ACT), **especially for European defense**. | **Preliminary support** (§6.4). This is the most defensible positive and directly answers the question. |
| **H3** | The channel comparison is **measurement-dependent**: with sharp physical counts vs. noisy news volume, realized appears to win; with the symmetric GPR ACT/THREAT decomposition, expectations win for Europe. Characterizing this is itself a contribution. | **Preliminary support** — the two horse races give opposite answers. |
| **H4** | The response scales with firm defense-revenue exposure (SIPRI); pure-plays react more. | **FALSIFIED** (§6.2). Report as a clean negative result. |
| **H5** | Response differs US vs. Europe. | **Partial** — European vol loads on THREAT; US on both. Worth formalizing. |
| **H6** | Cross-ecosystem narrative divergence carries independent info. | Small, negative, dominated — descriptive only. |
| **H7 (efficiency)** | The response is contemporaneous and **not forecastable**. | **Established in v1** (null forecasting). Supporting leg. |

The thesis contribution is now **the pattern across H1–H7**, not a single
positive: *defense equities price a broad geopolitical **threat/expectations**
environment (not firm-specific war exposure, not raw media volume, not
realized-act intensity per se), the effect is in **volatility not direction**,
strongest for **European** defense, and it is **contemporaneous and
efficient** (not forecastable).*

---

## 4. Conceptual framework & identification

### 4.1 The core identification problem
All candidate treatments — attack intensity, GPR, news volume — vary at the
**day** level (common to all firms on a date). This creates a hard tension:
- Firm-panel with **day fixed effects** cleanly removes market/VIX/macro
  confounds — but **absorbs any day-level treatment**, so a day-level channel
  cannot be identified this way.
- The only way to keep day FE *and* identify a channel is a **firm-level
  interaction** (treatment × firm characteristic). We used
  `intensity × defense-exposure`. **It is null** (§6.2) — so there is no
  clean firm-level identification of the channel available.
- Therefore channel identification falls back to **time-series / index-level**
  regressions with market + VIX controls (imperfect but standard), where the
  GPR ACT/THREAT decomposition provides the cleanest, symmetrically-measured
  contrast (§6.4).

### 4.2 Why the level matters
- **Index/time-series level**: right for the H2/H3 channel horse race
  (GPR ACT vs THREAT, attack vs news), with regional market + VIX + trend
  controls and HAC SEs.
- **Firm-panel level**: retained only to (a) document the uniform vol bump
  and (b) *report the null exposure gradient* (H4) as a finding, using
  two-way FE and date-clustered SEs.

### 4.3 Measurement-fairness (H3)
"Intensity vs expectations" is contaminated by differential measurement
error: attack counts are sharp, GDELT volume is noisy → attenuation
mechanically favors intensity. **GPR_ACT vs GPR_THREAT are built symmetrically
from the same news corpus**, so that horse race is the *fair* test and is the
primary channel specification. Report both (attack-vs-GDELT and GPR
ACT-vs-THREAT) and treat the divergence in their answers as the H3 result.

---

## 5. Data (all verified present, 2026-07-01)

Paths relative to `thesis_v1/` (reuse) or as noted. Copy/symlink needed raw
files into `thesis_v2/data/raw/` at Phase 1.

| Data | Location | Coverage / notes |
|---|---|---|
| WAERLST/BSHIELDT index levels | `data/raw/bloomberg/{WAERLST,BSHIELDT} Index.xlsx` | daily close + volume, 2020–2026-06, USD/EUR |
| Constituent daily prices | `data/interim/financial/{waerlst,bshieldt}_constituents_long.parquet` | 118 + 36 firms, 2020–2026 |
| Firm metadata | `data/external/firms_metadata_old.csv` | **118/118 + 36/36 matched**; region, country, currency, mktcap, index_weight |
| Attack daily | `data/processed/attacks/attack_daily.parquet` | 809 days, launches/interception/composition, 2022-09-29→2026-06 |
| GDELT daily by ecosystem | `data/processed/news/news_daily_enriched.parquet`, `news_query_group_pivot.parquet` | UA/RU/Western/Other tone, volume, narrative gaps, 1,342 days |
| Market controls | `data/processed/financial/benchmarks_log_returns.parquet` | SPX, SXXP, VIX, Brent, EURUSD, MSCI_World |
| **GPR daily** | `thesis_old_try/data/raw/gpr/data_gpr_daily_recent.xls` | 1985→2026-06-15; `GPRD`, `GPRD_ACT`, `GPRD_THREAT` all populated. Use `date` col; ignore `DAY`. |
| **SIPRI Top-100** | `thesis_old_try/data/raw/sipri/SIPRI-Top-100-2002-2024 (2).xlsx` | per-year sheets, header row 3; `Arms revenues as a % of total revenues`. **87/128 firms matched** by fuzzy name → ticker (exposure range 0.06–1.00). |

**Structural limitation (cannot fix):** attack + GDELT data begin **Sep 2022**;
the Feb–Sep 2022 invasion re-rating is out of sample. Document, don't fight.

**Scope discipline (decided):** no new markets (gas/grain), no event-study
pivot, no sample back-extension unless a blocker. "Defense-related" is
operationalized via the SIPRI exposure spectrum within the A&D universe.

---

## 6. Preliminary evidence (real regressions, already run)

All firm-level tests: WAERLST+BSHIELDT constituents, **war sample
(2022-09-29→)**, regional market-adjusted abnormal returns
(US→SPX, Europe→SXXP, else MSCI_World), SEs clustered by **date** (the
treatment dimension; firm-clustering understates SEs and was rejected).

### 6.1 Index-level naive result is a war-vs-peace artifact
Pooling 2020–2026, intensity→vol looks significant; restricted to war sample
it vanishes (p 0.26–0.97). ⇒ use war sample only; index aggregation hides
firm effects.

### 6.2 Firm-level exposure interaction — NULL (the decisive test)
Two-way (firm + day) FE, `spike × SIPRI-exposure`, cluster by firm & date:

| DV | Interaction b | p |
|---|---|---|
| \|abnormal return\| (vol) | −0.024 | 0.83 |
| signed abnormal return | −0.044 | 0.76 |
| binary pure-play × spike (vol) | +0.014 | 0.82 |
| continuous exposure (firm FE, no day FE) | −0.002 | 0.99 |

Descriptive vol bump: civil +0.35 vs pure-play +0.29. **No exposure gradient.**

### 6.3 Uniform vol bump survives, but isn't defense-specific
Firm FE + contemporaneous |market return| + VIX, cluster-date:
`spike b=+0.234, p<0.001` (and |market| b=+0.25, p<0.001). Present, but §6.2
shows it does not scale with defense exposure ⇒ interpret as an A&D-sector
volatility bump on high-attack days, likely a residual confound.

### 6.4 GPR ACT vs THREAT — the fair channel horse race (index, war sample)
Standardized, HAC(5) SEs, regional market + lagged VIX controls:

| Target | DV | ACT (realized) | THREAT (expectations) |
|---|---|---|---|
| WAERLST | vol | +0.098 (p=0.032) | +0.088 (p=0.015) |
| WAERLST | return | ns | ns |
| **BSHIELDT** | **vol** | +0.067 (p=0.21) | **+0.188 (p<0.001)** |
| BSHIELDT | return | ns | ns |

⇒ **Expectations (THREAT) ≥ realized (ACT) for volatility; THREAT dominates
for European defense; nothing on returns.**

### 6.5 Not yet run (Phase 3 tasks)
UA/RU/Western channels tested separately in one model; attack-vs-GDELT horse
race re-run alongside GPR; formal multiple-testing correction; robustness.

---

## 7. Tools & compute

- **Python**: pandas, numpy, statsmodels (OLS, HAC/cluster SEs), scipy.
- **Panel**: install `linearmodels` (not currently in env) for `PanelOLS`
  with entity+time effects and clustered/2-way-clustered SEs. Fallback:
  iterative two-way demeaning (used in §6, works).
- **Multiple testing**: `statsmodels.stats.multitest` (Benjamini–Hochberg);
  Romano–Wolf via a small bootstrap if step-down FWER control is wanted.
- **Fuzzy matching** (SIPRI→ticker): `difflib`/`rapidfuzz`.
- **Compute**: this study is **light** — panel regressions on ~100k rows run
  in seconds locally. **Colab Pro (GPU/High-RAM) is NOT needed for the core
  analysis.** It is only relevant if the thesis later (a) re-derives GDELT
  features from the raw article corpus, or (b) adds a transformer-based
  multilingual sentiment score as an extension. Do not architect the core
  pipeline around Colab.

---

## 8. Phases & steps

### Phase 0 — Setup ✅ (this plan, skeleton, docs/v2)

### Phase 1 — Data assembly & validation
- 1.1 Parse GPR daily → clean `date, GPRD, GPRD_ACT, GPRD_THREAT`.
- 1.2 Parse SIPRI (per-year, header=3) → long `year, company, country,
  arms_pct`; fuzzy-match company→ticker; save the **match table** for audit
  (document the ~40 unmatched firms and how they're handled).
- 1.3 Reference/copy reused v1 tables into `thesis_v2/data/`.
- 1.4 Build firm return panel + **regional market-model abnormal returns**
  (estimate β per firm on a pre/rolling window; DV = residual and |residual|).
- 1.5 Coverage/validation report; timing/leakage check (all channels dated
  to the day they are public).
- **Acceptance:** clean panel + channel tables, documented coverage, match table.

### Phase 2 — Channel construction
- 2.1 Realized intensity: attack level, surprise, composition, interception;
  + `GPRD_ACT`.
- 2.2 Expectations: `GPRD_THREAT`; GDELT volume/tone by UA/RU/Western/Other;
  narrative divergence.
- 2.3 Standardize all channels (comparable coefficients).
- **Acceptance:** merged analysis tables (index-level time series + firm panel).

### Phase 3 — Channel horse race (H1–H3, H5) — the core
- 3.1 Reproduce §6 results in clean, tested code.
- 3.2 GPR ACT vs THREAT, index level, WAERLST/BSHIELDT/EUDEF, vol + return,
  market+VIX+trend controls, HAC SEs. **Primary (fair) channel test.**
- 3.3 Attack-intensity vs GDELT-attention horse race (the noisy proxy test),
  by UA/RU/Western channel — contrast with 3.2 for H3.
- 3.4 US vs Europe (H5).
- **Acceptance:** channel-comparison tables with a clear H2/H3/H5 verdict.

### Phase 4 — Firm-level structure (report H1 + the H4 null honestly)
- 4.1 Uniform vol bump (firm FE + contemporaneous market + VIX).
- 4.2 **Exposure interaction, two-way FE — report the null** as a finding
  ("the market does not price firm-specific war exposure").
- 4.3 Robustness of the null (binary pure-play, continuous, by region).
- **Acceptance:** firm-level section that honestly presents H1 + the H4 null.

### Phase 5 — Efficiency/predictability leg (H7)
- Reuse v1's OOS forecasting result; if re-running, fix v1's 48 failing
  Phase-6 tests first. Frame: the contemporaneous response is not
  forecastable ⇒ efficiency.
- **Acceptance:** one clean efficiency table/paragraph.

### Phase 6 — Robustness & multiple-testing
- Multiple-testing correction across the horse-race grid (channels × targets
  × DVs); alternative spike thresholds; exclude extreme days / early months;
  placebo (shifted dates); alternative market model.
- **Acceptance:** robustness matrix; every headline survives correction or is
  demoted.

### Phase 7 — Writing (chapters per §9).
### Phase 8 — Final validation (re-run from raw, verify numbers, archive).

---

## 9. Suggested chapters
1. Introduction (frame via §11 "what's non-obvious").
2. Background & mechanism. 3. Literature (GPR/geopolitical-risk pricing,
event-driven equity response, media economics). 4. Data. 5. Methodology &
identification (§4). 6. Channel results (H2/H3/H5). 7. Firm-level results
(H1 + H4 null). 8. Efficiency (H7). 9. Descriptive multilingual narrative
(H6). 10. Robustness & limitations. 11. Conclusion.

---

## 10. Threats to validity
- **Residual confound in the uniform vol bump** (§6.3) — mitigate with
  regional market model, sector factor, and by *not* making it the headline.
- **GPR is global, not Ukraine-specific** — frame H2 as "defense equities
  price the broad geopolitical *threat* environment," and use the
  Ukraine-specific attack/GDELT channels as the localized complement.
- **Measurement error asymmetry** (§4.3) — rely on GPR ACT/THREAT as the fair
  test.
- **Multiple testing** — correction mandatory (Phase 6).
- **Out-of-sample invasion period** — documented limitation.

---

## 11. SUPERVISOR REVIEW & SIGNIFICANCE ASSESSMENT

*(The critical self-review the task requested. Honest odds, not optimism.)*

### 11.1 What is non-obvious / interesting (the "so what")
The professor's challenge ("stocks react to war/news — obviously") is
answered **not** by "we quantify it" but by four non-obvious results, three of
which are already evidenced:
1. Firm war-**exposure does not matter** — the market does *not* price how
   defense-dependent a firm is when conflict intensifies (clean, surprising
   null, §6.2).
2. It is **expectations/threat, not realized acts**, that move (European)
   defense volatility when measured symmetrically (§6.4) — contrary to the
   intuitive "physical facts" story *and* to the naive attention proxy.
3. The answer is **measurement-dependent** (§6.4 vs the attack/attention
   race) — a methodological cautionary contribution.
4. It is **volatility, not direction**, and **not forecastable** (efficiency).

### 11.2 Honest odds of "significant results"
| Thesis version | Chance of significant, defensible result | Note |
|---|---|---|
| Clean firm-level heterogeneity ("pure-plays react more") | **LOW** | key test already null (§6.2) — do **not** build on this |
| Index-level expectations/threat channel (H2/H3/H5) as headline | **MODERATE** | one strong cell (BSHIELDT THREAT p<0.001) + a coherent measurement-dependence story; but modest magnitudes, GPR-global caveat, must survive multiple-testing |
| Comprehensive **efficiency + null-map + descriptive** thesis | **HIGH** | robustly supported; the "market prices threat environment, not firm war-exposure, not raw narrative, and not predictably" story is defensible and honest |
| A single clean, strong, novel positive headline | **LOW–MODERATE** | the data does not offer a slam-dunk |

### 11.3 Verdict
This is a **viable Master-2 thesis, but not a slam-dunk positive.** Its
strength is a *coherent, well-identified set of findings* (one modest
positive — the threat/expectations channel — plus several robust,
scientifically-informative nulls, plus a novel descriptive multilingual
measurement), framed by an honest efficiency interpretation. Its risk is that
the single clearest positive (GPR_THREAT → European defense vol) is modest and
partly measurement-/instrument-dependent, so the thesis must be *sold on the
pattern*, not on one coefficient.

**Recommendation to the researcher (a decision is required):** the plan's
centre of gravity must move from the (falsified) firm-exposure heterogeneity
to the **expectations/threat channel + the null-map + efficiency +
descriptive multilingual** contribution. Confirm you accept this framing (a
strong, honest thesis whose headline is "defense equities price the *threat
environment*, not firm-specific war exposure, and not predictably") before
Phase 1 begins. If a *clean strong positive* is required by the programme,
this question — like v1 — is unlikely to deliver one, and that should be
faced now, not after Phase 6.
