# Supervisor Audit — Scientific Review of the Research Plan and State

**Reviewer role:** Supervisor / professor, data-driven financial research
**Date:** 2026-07-01
**Scope:** Independent scientific audit of `Master_Thesis_Research_Completion_Plan.md`
against the actual data and results (Phases 1–7). Verifies the load-bearing
empirical claims directly rather than trusting the phase audits, then refines
the plan.

---

## 0. Bottom line (read this first)

**The plan is methodologically excellent and largely already executed. The
research is *not* wasted — but its centre of gravity must move.**

Three findings, verified directly against `data/processed/model_matrix.parquet`:

1. **The returns arm is a dead null and cannot be rescued.** Every attack and
   news feature correlates with the next-day return at |ρ| < 0.07; the strongest
   predictors are all financial (VIX 0.12, realized vol 0.11). No amount of
   XGBoost tuning changes a signal that is absent in the raw correlations. This
   is *economically expected*: defense primes are priced on multi-year
   procurement, not on last night's drone count.

2. **The volatility arm looked promising in-sample but fails the proper
   out-of-sample test (UPDATE, 2026-07-01).** In-sample, war signals appeared to
   add adjusted-R² over a *trend-free* financial baseline (+0.0095 at h=1,
   +0.0274 at h=5). But the F baseline **already contains `days_since_invasion`**,
   and once that war-regime trend is in *both* models — and features are
   standardised and Ridge-regularised, i.e. the realistic implementation — a
   proper OOS nested test (last-25% block, Clark–West) shows war signals make
   the forecast **20% worse at h=1 and ~85% worse at h=5** (CW p = 0.78 / 0.996;
   the baseline is significantly *better*). The apparent in-sample volatility
   signal was attack intensity **proxying the war regime, which VIX + the time
   trend already capture** — it is not incremental. See §1.5.

3. **The titular outcome quietly disappeared.** The primary target drifted from
   `WAERLST` (global A&D, in the title) to **`ITA`, a US ETF**, because the
   WAERLST reconstruction is noise (ρ = 0.15 vs proxy). Both "robustness"
   series (`WAERLST_recon`, `BSHIELDT_recon`) are too noisy to support the
   geographic-robustness hypothesis (H6). **H6 is currently untestable, not
   null** — the Phase 7 audit's "H6 null (consistent)" claim is unsupportable
   because it rests on a noise series.

**Verdict on the user's question ("are we wasting time / can it be significant?"):**
- A *positive predictive discovery* — on returns **or** volatility, on the
  current outcomes — is unlikely. Both arms fail the properly-specified OOS
  incremental test. Do not plan the thesis around finding one.
- A **rigorous, powered NULL + the descriptive multilingual-narrative
  contribution + the methodological pipeline** is a defensible, honest Master 2
  thesis — *if* the institution accepts a null and the write-up supplies the
  mechanism (regime pricing + VIX absorption; efficiency).
- If a *positive* result is required, the highest-probability path is **not**
  more modelling of ITA — it is a **pivot of the dependent variable** to a
  market mechanically exposed to Ukrainian attacks (European gas/TTF, grain
  futures, European defense names, or an event study of the largest attacks).
  See §5 and the recommendation memo.

---

## 1. What I verified independently

All numbers below were recomputed from `data/processed/model_matrix.parquet`
(1,342 × 136), not taken from the phase audits.

### 1.1 Sample coverage
- **Window: 2022-09-29 → 2026-06-02** (bounded by GDELT + attack availability).
- **The Feb–Sep 2022 defense re-rating is entirely out of sample.** The largest
  war-driven repricing of defense equities (LMT/RTX/Rheinmetall all re-rated in
  early 2022) is *not observed*. The sample is the "systematic drone-war
  plateau," where the identifying variation in the *war regime* is weakest.

### 1.2 Returns signal (next-day, `target_r_ITA_t1`)
| Feature group | Top |ρ| with next-day return |
|---|---|
| Financial | VIX 0.12, vol_5d 0.11, vol_20d 0.075 |
| Attack | penetrations / attack-surprise ≈ 0.067 (max) |
| News | tone / counts ≤ 0.027 |

→ Return predictability from war signals is absent at the correlation level.

### 1.3 Volatility signal (`target_var_r_ITA_t*`), in-sample OLS, common subsample
| Model | adj-R² (h=1) | adj-R² (h=5) |
|---|---|---|
| Financial only (VIX, vol_5d, vol_20d, vix_crisis) | 0.109 | 0.118 |
| Financial + attack intensity + news | 0.119 | **0.145** |
| **Incremental** | **+0.0095** | **+0.0274** |

Univariate attack-intensity → vol correlation rises from 0.145 (h=1) to **0.229
(h=5)**; news volume from −0.118 to −0.145.

**Caveat (important for honesty):** the univariate attack→vol correlation
collapses to a **partial correlation of ≈ 0.03–0.05** once VIX, realized vol,
and the war-time trend are removed. Much of the raw signal is co-trending with
VIX and the war regime. The h=5 increment is the strongest case, but it is
still small and in-sample; OOS after Clark-West it may not survive.

### 1.5 DECISIVE test — proper OOS incremental comparison (added 2026-07-01)
I ran the exact test the thesis will run, correctly specified: NaN→0 recode
applied; features standardised on train; Ridge (α = 1, 10) to prevent
extrapolation; the war-regime trend `days_since_invasion` (already in the F set)
included in **both** models; last-25% OOS block; Clark–West nested test.

| Target | OOS MSE, financial | OOS MSE, financial + war | Improvement | Clark–West p |
|---|---|---|---|---|
| `var_r_ITA_t1` | 6.98 | 8.34 | **−19.5%** (worse) | 0.78 |
| `var_r_ITA_t5` | 40.97 | 76.68 | **−87.2%** (worse) | 0.996 |

War signals **degrade** the OOS volatility forecast, more so at h=5. The
"significant" Clark–West seen with raw OLS (p<0.001) was an artifact of an
overfit, extrapolating model — it vanishes under regularisation. **Conclusion:
the volatility arm is a null too, once the war-regime trend (which the F set
already contains) is properly controlled.** This is *why* the Phase 7 in-sample
CV val-MAE clustered at 0.716 across all info sets: the features add nothing
beyond F. A tree model (XGBoost) or GARCH-X should be run to confirm, but is
unlikely to reverse this — GARCH's own lagged variance already captures the
volatility clustering that made attack-intensity look correlated.

### 1.4 Data-integrity issue: no-attack days coded NaN, not 0
Attack features are non-null on only ~788 / 1,342 calendar days. Days with no
reported air attack are stored as **missing**, not **zero**. A day with no
drone launch is a *true zero*, not an absent observation. This (a) forced the
awkward `standardize=True` / `impute_mean` patches in Phase 6 (C6), and (b)
means the incremental-R² comparisons above run on *different samples*
(n = 920 financial-only vs 786 with attacks). **Recode no-attack days to 0
before re-running**, so every horse-race cell uses a common sample.

### 1.6 Real Bloomberg index files added (2026-07-01) — tested, verdict unchanged
The user supplied `WAERLST Index.xlsx` (USD, global A&D) and `BSHIELDT Index.xlsx`
(EUR) — genuine Bloomberg index levels (`PX_LAST` + `PX_VOLUME`), daily,
**2020-01-01 → 2026-06-30**. These fix three real problems: the ρ=0.15
reconstruction noise, the WAERLST→ITA scope drift, and they make **H6 (global
vs European) genuinely testable**; they also add trading volume and pre-invasion
history. **Adopt them.** But re-running the §1.5 OOS incremental test on the
*real* series does **not** overturn the null:

| Series | Target | OOS improvement over financial baseline | Clark–West p | Note |
|---|---|---|---|---|
| WAERLST (USD) | vol h=1 | −0.3% | 0.103 | null |
| WAERLST (USD) | vol h=5 | −17% | 0.154 | null |
| WAERLST (USD) | ret h=1 | −1.4% | 0.256 | null (dir-acc 0.525→0.492) |
| BSHIELDT (EUR) | vol h=1 | −26% | 0.880 | baseline better |
| BSHIELDT (EUR) | vol h=5 | −123% | 1.000 | baseline much better |
| BSHIELDT (EUR) | **ret h=1** | **+2.2%** | **0.006** | **fragile — see below** |

The one nominally "significant" cell (BSHIELDT returns, h=1, CW p=0.006) is
almost certainly noise: directional accuracy actually *drops* (0.530→0.514),
n_oos = 181, it is a single split, and it is one cell out of dozens with **no
multiple-testing correction**. A better MSE with worse direction is the
signature of variance-shrinkage, not a usable return signal. It must survive
MCS + multiple-testing correction + expanding-window replication before it can
be believed; I would bet against it.

Genuinely useful side-effect: univariate attack-intensity → volatility
correlation *rises* with proximity to Europe (ITA 0.23 → WAERLST 0.26 →
**BSHIELDT 0.33**), consistent with the rearmament channel — but it is still the
war-regime trend, so it dies in the incremental OOS test. This supports a
**contemporaneous/associational** or **event-study** framing (which can be
positive) but not an OOS-forecasting-beats-VIX claim (which stays null).

---

## 2. Assessment: are the questions good?

**Yes.** The main question — *do physical attack signals, multilingual
narratives, or their combination add incremental OOS predictive information
beyond financial baselines?* — is well-posed, novel in its physical-vs-narrative
separation, and correctly framed as **predictive, not causal**. The subquestions
(narrative gap vs raw volume; weapon composition vs count; horizon; geography)
are sharp and individually testable.

**One caveat:** the question implicitly presumes daily tactical intensity should
move defense-equity *prices*. Economic theory predicts otherwise (procurement,
not tactics, drives primes). This is not a flaw in the question — a
well-designed null is valuable — but it means **H1/H2-on-returns were unlikely
to be positive from the outset**, and the write-up should own that ex ante
rather than present the null as a surprise.

---

## 3. Assessment: is the plan correct?

**Yes — arguably over-engineered relative to the available signal.** Strengths:
- Nested information-set horse race (F ⊂ P ⊂ PN ⊂ PNG) is the right design for
  incremental-value testing.
- Leakage policy is genuinely rigorous (pre-lagged features, expanding window,
  `market_info_date` for overnight attacks, recursive surprise/gap models,
  `--audit-leakage`). Zero critical leakage flags across 98 features.
- Explicit pre-authorization of a null result (§12.1, §23) — correct and mature.
- Predictive-language discipline, SHAP-not-causal, common test dates.

Gaps / mismatches between plan and execution:
- **Volatility is designated the fallback that "makes the thesis worthwhile if
  returns are null" (§12.1) — yet the volatility-with-exogenous-signals test
  (GARCH-X) and the higher-signal horizon (h=5) are both unrun.** The plan's own
  logic makes these the critical path, not an afterthought.
- **No formal significance test has been run.** Diebold–Mariano / Clark–West /
  MCS are deferred to Phase 8. Until then the "nulls" are informal point-estimate
  gaps, not statistical nulls — and any vol "positive" is un-defended against
  multiple testing (~40 cells across info-set × target × horizon × model).
- **The N information set is degenerate** (N = 21 columns ⊆ F = 23; adds no news
  columns over F). H2's standalone N-vs-F test is not actually implemented; only
  PN-vs-P tests news. Fix or drop N.
- The plan treats WAERLST as primary throughout; the code silently uses ITA.
  The plan was never updated to record this scope change (decision-log gap).

---

## 4. Assessment: can it be done, and can it be significant?

**Can it be done:** yes — ~80% is already built and reproducible.

**Can it be significant:** the honest probabilities, updated after the §1.5 OOS test:

| Outcome path | Realistic likelihood | Contribution if it lands |
|---|---|---|
| Positive on **returns** (any outcome/horizon) | ~nil | — (don't pursue) |
| Positive & robust on **volatility** for ITA/US defense | **low** — fails OOS incremental test (§1.5) | — |
| Positive on **volatility for European defense names** (untested) | uncertain, speculative | Would revive H6; most plausible remaining positive |
| **Descriptive:** multilingual narrative divergence (UA −3.5 / RU −3.6 / West −1.9, stable over 46 months) | **already established** | Standalone novel contribution |
| **Methodological:** leakage-safe GDELT→attack→equity pipeline, physical-vs-narrative feature design | **already established** | Reusable, citable |
| **Rigorous powered NULL** on the current question | **this is the modal result** | Honest market-efficiency finding — defensible IF institution accepts nulls |

### 4.1 The decision the student actually faces
Given §1.5, there are three honest options — this is a choice for the student and
supervisor, not something the data alone settles:

- **Option A — Keep the topic, commit to a NULL thesis.** Report that neither
  physical attack intensity nor multilingual narratives improve OOS forecasts of
  defense-equity returns *or* volatility beyond financial baselines, and explain
  *why*: defense equities price the war **regime** (a one-time level shift, whose
  identifying variation in Feb–Sep 2022 sits outside the sample), not daily
  tactical intensity, and VIX already absorbs the ambient war-risk. Add the
  descriptive narrative-divergence chapter. **Viable and honest** for a Master 2
  *if* the institution accepts a null-result thesis. Low risk, low upside.
- **Option B — Keep the data/infrastructure, pivot the dependent variable to a
  market mechanically exposed to Ukrainian attacks.** This is where a genuine
  *positive* most likely lives, and it reuses almost everything already built:
  - European natural gas / TTF futures (attacks on Ukrainian/European energy
    infrastructure) — strong mechanical channel;
  - grain / wheat futures (attacks on Black Sea ports / grain corridor);
  - European defense names (Rheinmetall, Leonardo, BAE) where a rearmament-
    narrative channel is plausible;
  - an **event study** of the ~20 largest attacks on defense/gas volatility.
  **Recommended if a positive result is required.** Moderate risk, real upside.
- **Option C — Change topic entirely.** Only if neither a null thesis nor a
  pivot is acceptable. **Not recommended** — it discards ~80% built
  infrastructure for no clear gain; a within-data pivot (B) dominates it.

**My recommendation:** do **not** change topic. Choose A if a clean, honest,
lower-risk thesis is acceptable; choose B if the programme expects a positive
empirical finding. Both reuse the existing pipeline. Running GARCH-X / vol-XGBoost
on ITA is still worth ~1 day to *document* the vol null rigorously, but should not
be expected to produce a positive.

---

## 5. Refined research plan (concrete changes)

These are edits to `Master_Thesis_Research_Completion_Plan.md`, not a new plan.

### 5.1 Re-centre the empirical claim on volatility, especially h=5
- Promote **volatility at h=5** from "secondary/optional" to the **primary
  test of significance**. Returns become a documented, expected null used to
  motivate the volatility focus.
- Update H1/H2/H3 to be stated *for the volatility target first*, returns second.

### 5.2 Fix the outcome variable (highest-upside change)
- Add **real European defense equities** — long free histories via `yfinance`:
  Rheinmetall (`RHM.DE`), Leonardo (`LDO.MI`), BAE (`BA.L`), Hensoldt, Thales,
  plus a STOXX Europe A&D index if obtainable. Use singly and as an
  equal-weight basket.
- Rationale: European defense is *far* more Ukraine-narrative-sensitive than US
  primes (rearmament repricing runs through Rheinmetall et al.), so a vol effect
  is *most economically plausible there*; it makes **H6 actually testable**; and
  it repairs the WAERLST→ITA scope drift. (Present as "most plausible," not
  guaranteed — the ITA signal is faint enough that European is not assured
  stronger.)
- Reclassify `WAERLST_recon` / `BSHIELDT_recon` as **exploratory only**; correct
  the Phase 7 "H6 null" claim to **"H6 untestable with current data."**

### 5.3 Data-integrity fix
- **Recode no-attack days as 0, not NaN**, for launch/interception/penetration
  counts (keep a separate `has_report` flag for genuine missing reports). Re-run
  the horse race on the resulting common sample; this also removes the need for
  the `standardize`/`impute_mean` scaffolding.

### 5.4 Close the open experiments (C7/C8) — the critical path
- Run **GARCH-X and vol-XGBoost on `target_var_*_t1` AND `target_var_*_t5`**,
  info sets F/P/N/PN/PNG, ITA + European outcomes.
- This is cheap (minutes of compute) and is the one place a real positive can
  still appear.

### 5.5 Formalise the null (Phase 8, bring forward)
- Run **Clark–West** (nested comparisons: P vs F, PN vs P, PNG vs PN),
  **Diebold–Mariano** where non-nested, and a **Model Confidence Set** across
  the horse race.
- Add a short **power statement**: given n ≈ 337 OOS days and the observed
  incremental adj-R², what effect size is detectable. A null without power is
  not a scientific null.
- Apply an explicit **multiple-testing correction** across the ~40 cells; any
  single vol positive must survive it.

### 5.6 Fix or retire the N information set
- Populate N with genuine news-only lag columns, or drop N and test news solely
  via PN-vs-P. Document either way.

### 5.7 Optional, only if 5.2–5.5 leave time
- A supplementary **event study of the ~20 largest attacks** on European-defense
  volatility. The plan excludes event studies as the *main* method, which is
  correct; as a *supplement* it can surface an effect that daily-average
  regressions wash out. Keep it clearly secondary.

### 5.8 Update the decision log
- Record: (a) ITA-as-primary decision + its scope consequences; (b) volatility/
  h=5 re-centring; (c) NaN→0 recoding; (d) European-names addition; (e) H6
  reclassification. None of these should be silent.

---

## 6. Prioritised action list

1. **Recode no-attack days 0-not-NaN; rebuild model matrix on a common sample.** (data integrity; unblocks clean comparisons)
2. **Run GARCH-X + vol-XGBoost on `target_var_*_t5` (and t1), all info sets.** (the live experiment)
3. **Add European defense equities via yfinance; make H6 testable; re-run vol horse race there.** (highest upside)
4. **Run Clark–West / DM / MCS + a power statement + multiple-testing correction.** (turns nulls into *powered* nulls and defends any positive)
5. **Fix or drop the N info set; correct the Phase 7 "H6 null" wording.** (integrity)
6. **Reframe the thesis narrative around regime-pricing / efficiency; write the returns null as motivation, the vol/h=5 result as the finding.** (framing)
7. (Optional) largest-attacks event study on European vol.

---

## 7. Risks & framing

- **The modal outcome is all-null.** Do not let "volatility is alive" become
  false hope; even the h=5 signal is in-sample and modest. Plan the write-up so
  a *powered null* is a satisfying result on its own.
- **Multiple testing is the integrity linchpin.** If the one positive is, say,
  vol-PN-h5-ITA out of ~40 cells, it must survive MCS or it is noise-mining.
- **News sign is negative** (more news → lower next-day vol) and partly a
  time-trend artifact (news volume declined as the war routinised). Treat any
  news-vol result cautiously and always with the trend controlled.
- **Descriptive + methodological contributions are already secured** — foreground
  them so the thesis has guaranteed content independent of the vol test's outcome.
