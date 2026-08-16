# Real Bloomberg Index Integration — Action Plan (Phases 5–7 rebuild)

**Created:** 2026-07-01
**Trigger:** Real Bloomberg daily series `WAERLST Index.xlsx` and `BSHIELDT Index.xlsx`
(PX_LAST + PX_VOLUME, 2020-01-01 → 2026-06-30) received. These replace the noisy
`r_WAERLST_recon` reconstruction and the reconstructed BSHIELDT used through Phase 7.
**Status:** Plan for review — no code/data changed yet.

---

## 0. Framing (read before executing)

Two separate problems live in the current Phase 6/7 results. The new data fixes
**only the first**:

1. **Noisy target — FIXED by real data.** `r_WAERLST_recon` had MAE ~1.9, ρ=0.15 vs
   ITA, std 2.4×. The real series are clean (verified 2026-07-01): WAERLST **1,694 daily
   rows**, std **1.51%**, 0 gaps >4d, 0 NaNs; BSHIELDT std **1.77%**, same coverage
   (2020-01-01 → 2026-06-29). Both comparable to ITA (~1.7%).
2. **Features don't help *returns* — WILL NOT change.** XGBoost dir-acc ~54%, corr≈0,
   P/N/PN/PNG add nothing (MAE 1.047→1.045). Daily equity returns are near-unpredictable.
   A null result on returns is **valid** per `instructions.md`. Do **not** frame this
   rebuild as "making returns forecasting work."

**What the real data actually buys us:**
- The **correct primary target** (WAERLST *is* the thesis title).
- A **war-exposed robustness index** (BSHIELDT = European defense, most exposed to the
  RU–UA war → where the attack/news signal is most likely to appear → hypothesis **H6**).
- **Clean series + volume** for the **volatility** work (H1/H2 live here), where Phase 7
  currently has a hole: the volatility benchmark ran but produced **0 rows**.

**Approved target hierarchy (2026-07-01):**
| Role | Target | Source |
|---|---|---|
| **Primary** | `r_WAERLST` | Real Bloomberg WAERLST Index (global A&D) |
| **Robustness (European)** | `r_BSHIELDT` | Real Bloomberg BSHIELDT Index |
| Optional (US robustness) | `r_ITA` | iShares ETF proxy (yfinance) — keep |
| **Demoted** | `r_WAERLST_recon` | Reconstruction — kept as lagged *feature* only, no longer a target |

---

## 1. Gates & constraints (do not violate)

- **Common sample stays news-gated at 2022-09-29.** The extra 2020–2022 financial
  history does **not** widen the horse race — it is used **only for GARCH warm-up**
  (master plan §5.2). Widening the OOS test window would break common-date comparability.
- **Processed attack/news parquets live on Google Drive, not locally.** Rebuilding the
  model matrix requires pulling them first (Step 2). The new `.xlsx` are the only
  local pieces.
- **Raw data is immutable.** Move the two `.xlsx` into `data/raw/bloomberg/` unchanged;
  never edit them.
- **Leakage discipline unchanged:** info through day `t` predicts trading day `t+1`;
  fit all transforms within training folds; no full-sample scaling/selection.

---

## 2. Step-by-step plan

### Step 0 — Log the decision (documentation only)
- Add a `decision_log.md` entry: target restructure (WAERLST primary, BSHIELDT
  European robustness, ITA optional, recon demoted), with rationale = real Bloomberg
  index series now available; supersedes the 2026-06-28 ITA-primary decision.

### Step 1 — Land the raw data
- `git mv`/move `WAERLST Index.xlsx`, `BSHIELDT Index.xlsx` → `data/raw/bloomberg/`.
- **Verified 2026-07-01:** each file = sheet `Worksheet`, 3 cols (`Date`,`PX_LAST`,
  `PX_VOLUME`), ~1,694 rows, ascending. **No OHLC and no total-return column** —
  `PX_LAST` only. This **confirms** the close-only volatility path (Case C, master
  plan §5.3): abs/squared returns + GARCH; no range-based estimator possible.
- **TR vs PR is NOT resolvable from the file** (no TR column). Phase 1 claimed both
  tickers are total-return per TradingView/Bloomberg — leave as a **question for the
  user to confirm on the Bloomberg terminal** (which variant the ticker is), note in
  `docs/source_inventory.md`. Non-blocking for daily vol/direction.

### Step 2 — Pull processed dependencies from Drive (hard gate)
```bash
rclone copy --update --progress \
  gdrive:WarSignalsThesis_Data/data/processed/ data/processed/
```
Needed: `attacks/attack_daily.parquet`, `news/news_daily_enriched.parquet`,
`news/news_query_group_pivot.parquet`, `financial/financial_daily.parquet`,
plus existing `model_matrix.parquet` for a before/after diff.

### Step 3 — Add a real-index loader (`src/data/financial.py`)
- New function `load_bloomberg_index_xlsx(path)` for the **single-index** sheet format
  (sheet `Worksheet`; header row located dynamically where col0 == "Date"; columns
  Date/PX_LAST/PX_VOLUME). This is a **different layout** from the existing constituent
  `load_bloomberg_xlsx` ("values only" sheet) — do not reuse that one.
- **Sort by date ascending defensively** — the export order flipped between deliveries
  (was descending, now ascending); never assume order.
- Return a clean daily frame: `px_WAERLST`, `vol_WAERLST` (and BSHIELDT), indexed by date.
- Compute `r_WAERLST = 100·pct_change(px)`, `r_BSHIELDT` likewise.
- Add unit tests in `tests/test_financial.py` (row count ≈1,694, std ≈1.51/1.77,
  no NaNs, date range 2020-01-01 → 2026-06-29, monotonic ascending).

### Step 4 — Rebuild the financial table (`build_financial_table`)
- Merge real WAERLST/BSHIELDT (returns + **PX_VOLUME**) into `financial_daily.parquet`.
- Add volume-based features (candidate, training-fit only): `logvol`, `vol_z30`,
  `dvol` (Δlog volume) for WAERLST and BSHIELDT — a new liquidity signal now that
  volume exists. Keep `r_ITA`; keep `r_WAERLST_recon` as a column but tag it demoted.
- **Guard against zero/holiday volume (verified data issue):** BSHIELDT `PX_VOLUME`
  has 0 on non-trading days (e.g. 2020-01-01) and WAERLST's first day is anomalously
  low (5.2M vs 355M mean). Use `log1p`, and/or mask zero-volume rows as NaN and
  forward-fill within the training fold only — a naive `log()` yields `-inf`.
  Also consider dropping carried-forward holiday rows (2020-01-01) before returns.
- Regenerate figures fig1–4 with the real indices rebased.

### Step 5 — Regenerate the model matrix (`src/features/build_model_matrix.py`)
- `PRIMARY_TARGET = "r_WAERLST"`, robustness `= "r_BSHIELDT"`, optional `= "r_ITA"`.
- Emit weekend-rule next-day targets: `target_r_WAERLST_t1`, `target_r_BSHIELDT_t1`,
  `target_r_ITA_t1` (+ h=5 variants). Retire `target_r_WAERLST_recon_t1` from the
  target set; keep `r_WAERLST_recon_lag1` as a feature.
- Add the new volume features into the **F** info set (and thus P/N/PN/PNG).
- **Fix the N==F redundancy** noted in `docs/phase7_audit.md §1.5`: ensure the
  `INFO_SET_PATTERNS["N"]` include list actually selects the news lag-1 columns so
  N ≠ F. If not fixable cleanly, drop N from the horse race and document why.
- Re-run leakage audit → expect 0 critical flags. Regenerate `data_dictionary.csv`,
  `info_set_cardinality.csv`.

### Step 6 — Re-run Phase 6 baselines
- Update `src/models/horse_race.py`, `baselines.py`, `garch.py` target tuples:
  `("r_WAERLST", "r_BSHIELDT", "r_ITA")`.
- Re-run returns + **volatility** benchmarks for **both h=1 and h=5**.
- Warm-start GARCH on 2020–2022 history; test window stays 2022-09-29+.
- Outputs overwrite `phase6_benchmark.csv`, `phase6_volatility_benchmark.csv`.
- Update `docs/phase6_audit.md` with real-target numbers.

### Step 7 — Fix + re-run Phase 7 (the actual gap)
- **Volatility benchmark is empty (0 rows) — this is the real bug to fix.** Root-cause
  the GARCH-X run (`src/models/garch.py` GARCH-X path + `ExpandingWindowEngine`
  `X_exog_train` plumbing). H1/H2 depend on the volatility results existing.
- Update `src/models/ml_tuning.py` target tuples to the new hierarchy (currently
  hard-codes `("r_ITA", "r_WAERLST_recon")` in 4 places).
- Re-run XGBoost horse race for **h=1 and h=5** (current run only did h=1) across
  F/P/N/PN/PNG × {WAERLST, BSHIELDT, ITA}.
- Regenerate SHAP summaries; populate `docs/phase7_audit.md §2–6` with real numbers
  and H1/H2/H3/H5/H6 verdicts.
- Push new outputs to Drive; pull tables locally; commit.

### Step 8 — Verify & document
- `python scripts/verify_setup.py` + full `pytest` green.
- Update `README.md`, `docs/project_status.md`, `docs/data_dictionary.md` to reflect
  WAERLST-primary and the real indices (remove "ITA primary / recon secondary" language).
- Mark Phase 7 ✅ Complete once volatility rows exist and the audit is populated.

---

## 3. Files touched (summary)

| File | Change |
|---|---|
| `data/raw/bloomberg/*.xlsx` | Land the two raw files |
| `src/data/financial.py` | `load_bloomberg_index_xlsx`; real targets + volume features |
| `src/features/build_model_matrix.py` | New PRIMARY/robustness targets; N-set fix; volume features |
| `src/models/{horse_race,baselines,garch,ml_tuning,ml_explain}.py` | Target tuples → real indices |
| `src/models/garch.py` + `expanding_window.py` | **Fix empty GARCH-X volatility output** |
| `tests/test_financial.py` (+ others) | Loader + target regression tests |
| `docs/*`, `decision_log.md`, `README.md` | Reflect new target hierarchy + Phase 7 results |

## 4. Expected outcome (set expectations honestly)

- **Returns:** likely still ~50–55% direction, near-zero corr — a **valid null**. WAERLST/
  BSHIELDT won't magically become predictable. The win is a *clean, correctly-named*
  primary target and a proper h=1/h=5 comparison.
- **Volatility (the real prize):** once the GARCH-X output is fixed, H1/H2 become
  testable for the first time. BSHIELDT (war-exposed) is the most likely place to see
  attack/news lift — watch `garch_x_P` vs `garch` QLIKE there.
- **Robustness (H6):** WAERLST vs BSHIELDT vs ITA gives a genuine geographic comparison.

## 5. Definition of "7 phases completed"

Phases 1–6 already complete. This plan finishes **Phase 7** properly:
returns + **non-empty volatility** benchmarks on the **real primary target**, both
horizons, SHAP, and a populated `phase7_audit.md` with hypothesis verdicts — then the
project is at the intended first-milestone state with all 7 phases done and Phase 8
(statistical comparison / robustness) unblocked.
