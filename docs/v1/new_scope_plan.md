# New Scope Plan — Post-Supervisor-Audit Pivot

**Created:** 2026-07-01
**Trigger:** `docs/supervisor_audit.md` — independent scientific review found both returns and volatility arms fail the proper OOS incremental test on ITA. The highest-upside change is pivoting the dependent variable to real Bloomberg indices + European defense equities.

---

## What the supervisor found (summary)

1. **Returns = dead null.** Every attack/news feature correlates with next-day return at |ρ| < 0.07. Economically expected: defense primes price procurement, not daily tactics.
2. **Volatility = likely null on ITA, untested on European.** In-sample signal was attack intensity proxying the war regime (which VIX + time trend already capture). OOS Clark-West shows war signals make vol forecast 20% worse at h=1, 85% worse at h=5. But GARCH-X hasn't been run, and European defense names are untested.
3. **WAERLST→ITA scope drift.** The titular outcome was replaced by a US ETF. Now real Bloomberg index files are available (WAERLST Index.xlsx, BSHIELDT Index.xlsx) — daily, 2020-2026, PX_LAST + PX_VOLUME.
4. **No-attack days coded NaN, not 0.** Data integrity issue. A day with no drone launch is a true zero, not missing.
5. **H6 untestable with reconstructed data.** WAERLST_recon ρ=0.15 vs ITA — too noisy. Real indices fix this.

## The pivot

**Keep the data infrastructure. Change the dependent variable.**

| Dimension | Before (broken) | After (fixed) |
|---|---|---|
| Primary target | ITA (US ETF proxy) | **WAERLST** (real Bloomberg, USD, global A&D) |
| Secondary target | WAERLST_recon (noise) | **BSHIELDT** (real Bloomberg, EUR, European) |
| Tertiary target | — | **European defense basket** (Rheinmetall, Leonardo, BAE, Thales, Hensoldt via yfinance) |
| Attack NaN | NaN for no-attack days | **0** (true zero) + `has_attack_report` flag |
| Volatility test | GARCH-X not run | **GARCH-X on all targets, h=1 and h=5** |
| Statistical test | Informal point-estimate gaps | **Clark-West + DM + MCS + power + multiple-testing correction** |
| Thesis framing | "War signals predict defense equity" | **"War signals and defense equity risk: a rigorous null + descriptive narrative contribution"** |

## Why European defense is the highest-upside path

- European defense names (Rheinmetall, BAE, Leonardo) are **far more Ukraine-narrative-sensitive** than US primes (LMT/RTX price multi-year procurement, not daily tactics).
- Univariate attack→vol correlation rises with proximity to Europe: ITA 0.23 → WAERLST 0.26 → BSHIELDT 0.33.
- The rearmament repricing channel runs through European names.
- Makes **H6 (geographic robustness) genuinely testable** for the first time.

---

## Phase A: Data Infrastructure Fixes (local, before Colab)

### A1. Move Bloomberg index files
- Move `WAERLST Index.xlsx` and `BSHIELDT Index.xlsx` from workspace root to `data/raw/bloomberg/`

### A2. Write `load_bloomberg_index()` loader
- New function in `src/data/financial.py`
- Parses the simple format: row 6 = headers (Date, PX_LAST, PX_VOLUME), row 7+ = data (descending)
- Returns DataFrame with columns: `date`, `PX_LAST`, `PX_VOLUME`, `log_return`

### A3. Add European defense equities via yfinance
- Tickers: Rheinmetall (`RHM.DE`), Leonardo (`LDO.MI`), BAE Systems (`BA.L`), Thales (`HO.PA`), Hensoldt (`HGT.DE`)
- Build equal-weight basket: `r_EUDEF` = mean of individual log returns
- Also keep individual names for firm-level robustness (H7)

### A4. Fix NaN→0 for attack features
- In `src/features/merge.py::build_daily_master()`: after left-joining attack data, fill attack count columns with 0 (not NaN)
- Add `has_attack_report` flag = 1 where attack data was present, 0 where filled
- Keep `interception_rate` as NaN when `launched_total = 0` (undefined, not zero)

### A5. Update `build_financial_table()`
- Replace `reconstruct_index()` calls with `load_bloomberg_index()` for WAERLST and BSHIELDT
- Add European defense basket
- Keep ITA as a US comparison (no longer primary)
- Add trading volume columns (`WAERLST_VOLUME`, `BSHIELDT_VOLUME`)

### A6. Update model matrix
- New targets: `r_WAERLST` (primary), `r_BSHIELDT` (secondary), `r_EUDEF` (tertiary)
- Keep `r_ITA` as US comparison
- Update `INFO_SET_PATTERNS` to include new return source columns
- Update `PRIMARY_TARGET` and `SECONDARY_TARGET` constants
- Rebuild feature matrix + model matrix

### A7. Push to Drive
- `rclone copy` updated model matrix + feature matrix to Drive

---

## Phase B: Re-run Experiments (Colab)

### B1. Re-run tuning
- `--horizons 1,5 --targets r_WAERLST,r_BSHIELDT,r_EUDEF,r_ITA`
- Produces 40 rows (5 info sets × 2 horizons × 4 targets)

### B2. Re-run horse race
- `--horizons 1,5 --garch-x-info-set F`
- Produces 200 return rows (5 models × 5 info sets × 4 targets × 2 horizons)
- Produces 24+ vol rows (3 GARCH + 3 GARCH-X × 4 targets × 2 horizons)
- Produces 40 SHAP figures

### B3. Pull results
- `rclone copy` outputs back to local

---

## Phase C: Statistical Tests (local, after Colab)

### C1. Clark-West tests (nested)
- P vs F (does attack info add value?)
- PN vs P (does news info add value?)
- PNG vs PN (does narrative gap add value?)
- For each target × horizon combination

### C2. Diebold-Mariano tests (non-nested)
- XGBoost vs HistoricalMean
- XGBoost vs AR(1)
- XGBoost vs OLS/Ridge

### C3. Model Confidence Set
- Across all models in the horse race
- Identifies the set of models not significantly worse than the best

### C4. Power statement
- Given n≈337 OOS days and observed incremental adj-R², what effect size is detectable
- A null without power is not a scientific null

### C5. Multiple-testing correction
- ~40+ cells across info-set × target × horizon × model
- Benjamini-Hochberg or Holm correction
- Any single positive must survive

---

## Phase D: Reframing (local, writing)

### D1. Update decision log
- Real Bloomberg indices adopted (supersedes reconstruction)
- European defense basket added
- NaN→0 recoding
- Volatility/h=5 re-centring
- H6 reclassification (untestable → testable)

### D2. Update research plan
- Re-centre empirical claim on volatility, especially h=5
- Promote European defense from "robustness" to "primary test of significance"
- Returns become documented, expected null (motivation for vol focus)
- Add power statement requirement

### D3. Correct Phase 7 audit
- "H6 null (consistent)" → "H6 untestable with reconstructed data; now testable with real indices"
- Update headline result with new targets

### D4. Thesis narrative reframing
- **Returns null = motivation, not failure.** Defense equities price the war regime (one-time level shift), not daily tactical intensity. VIX already absorbs ambient war-risk.
- **Volatility = the finding.** Whether war signals add incremental OOS vol forecasting value, especially for European defense names at h=5.
- **Descriptive contribution = guaranteed content.** Multilingual narrative divergence (UA −3.5 / RU −3.6 / West −1.9, stable over 46 months) is a standalone novel finding.
- **Methodological contribution = reusable pipeline.** Leakage-safe GDELT→attack→equity pipeline, physical-vs-narrative feature design.

---

## Risk assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| All-null on all targets | **modal outcome** | Plan write-up so a powered null is satisfying (efficiency finding) |
| European vol positive but fragile | possible | Must survive MCS + multiple-testing correction |
| News-vol negative sign is time-trend artifact | likely | Always control for `days_since_invasion` |
| GARCH-X h>1 forecast limitation | known | Use MC simulation (C4 fix pattern); document limitation |
| yfinance European data gaps | possible | Check coverage; fall back to Bloomberg if available |

---

## Execution order (what stops at Colab)

```
Phase A (local) → A1-A7 → rebuild data → push to Drive
    ↓
Phase B (Colab) → B1-B2 → tuning + horse race → STOP
    ↓
Phase C (local) → C1-C5 → statistical tests
    ↓
Phase D (local) → D1-D4 → reframing + writing
```
