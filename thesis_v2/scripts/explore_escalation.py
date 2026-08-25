"""The escalation hypothesis, and why its in-sample evidence was not enough — §8.5.

Four price gates found local perception is not priced. That is what market
efficiency predicts, so it leaves open whether the information exists at all.
Escalation is not a traded asset — no arbitrage force makes media coverage
uninformative about future conflict events — so this asks whether local media
anticipate realized geopolitical acts.

The in-sample evidence was the best this project produced: significant in **both
halves independently**, surviving twelve lags of the outcome's own dynamics, with
a clean time-shuffle placebo. On 651 held-out days it is p=0.16.

The lesson is the one Chapter 8 draws: **split-half replication inside a sample
is not out-of-sample replication.** Both halves shared the same construction,
outlet register, coverage regime and persistent-levels specification, so whatever
produced significance in one produced it in the other for the same reason.

``run_gate5_escalation.py`` is the confirmatory run. This is the exploratory work,
including the diagnostic that made the levels specification defensible enough to
pre-register.

    cd thesis_v2 && python scripts/explore_escalation.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.perception import build_indices  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

ECO = ("WEST", "EN_GLOBAL", "UA", "RU_STATE", "RU_INDEP")
LOCAL = ("UA", "RU_STATE", "RU_INDEP")
HALVES = {"first half 2017-04..2021-12": ("2017-04-24", "2021-12-31"),
          "second half 2022-01..2026-05": ("2022-01-01", "2026-05-20")}


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def load() -> pd.DataFrame:
    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_daily.parquet")
    idx = build_indices(daily)
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    return idx.join(spine[["gpr", "gpr_act", "gpr_threat"]], how="inner").sort_index()


def fit(d, outcome, h, window=None, own_lags=6, use_levels=True, shuffle_seed=None):
    sub = d if window is None else d.loc[window[0]: window[1]]
    frame = sub.copy()
    if shuffle_seed is not None:
        rng = np.random.default_rng(shuffle_seed)
        perm = rng.permutation(len(frame))
        for e in ECO:
            frame[f"att_{e}"] = frame[f"att_{e}"].to_numpy()[perm]
            frame[f"tone_{e}"] = frame[f"tone_{e}"].to_numpy()[perm]

    y = frame[outcome].shift(-h) - frame[outcome]
    X = pd.DataFrame(index=frame.index)
    for e in ECO:
        base_a = frame[f"att_{e}"] if use_levels else frame[f"att_{e}"].diff()
        base_t = frame[f"tone_{e}"] if use_levels else frame[f"tone_{e}"].diff()
        X[f"att_{e}"] = zscore(base_a)
        X[f"tone_{e}"] = zscore(base_t)
    for lag in range(own_lags):
        X[f"out_l{lag}"] = zscore(frame[outcome].shift(lag))
        X[f"dout_l{lag}"] = zscore(frame[outcome].diff().shift(lag))
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < 150:
        return None
    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": h + 5})
    loc = [c for c in X.columns if any(c.endswith(e) for e in LOCAL)]
    wst = [c for c in X.columns if c.endswith("WEST") or c.endswith("EN_GLOBAL")]
    return {"n": int(m.nobs), "r2": float(m.rsquared),
            "p_local": float(np.squeeze(m.f_test(" = 0, ".join(loc) + " = 0").pvalue)),
            "p_west": float(np.squeeze(m.f_test(" = 0, ".join(wst) + " = 0").pvalue))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    d = load()
    print(f"panel: {len(d)} days, {d.index.min().date()} -> {d.index.max().date()}")

    print("\n=== 1. levels vs changes, full sample ===")
    rows = []
    for outcome in ("gpr_act", "gpr_threat", "gpr"):
        for h in (1, 3, 5, 10):
            for form, lv in (("levels", True), ("changes", False)):
                r = fit(d, outcome, h, use_levels=lv)
                if r:
                    rows.append({"outcome": outcome, "h": h, "form": form, **r})
    grid = pd.DataFrame(rows).sort_values("p_local").reset_index(drop=True)
    rej, padj, _, _ = multipletests(grid["p_local"], alpha=0.05, method="fdr_bh")
    grid["p_bh"], grid["survives"] = padj, rej
    print(grid.head(14).round(4).to_string(index=False))
    print("\nLevels significant, changes null. The reading is that anticipation is")
    print("a level phenomenon - sustained elevated attention is the signal, daily")
    print("movement is noise - consistent with the indices agreeing with GPR at")
    print("0.87 in levels and near zero in changes.")

    print("\n\n=== 2. is it just the outcome's own persistence? ===")
    print("If richer own-dynamics controls kill it, the regressor is a proxy.\n")
    pers = []
    for outcome in ("gpr_act", "gpr_threat"):
        for h in (1, 5):
            rec = {"outcome": outcome, "h": h}
            for L in (1, 3, 6, 12):
                r = fit(d, outcome, h, own_lags=L)
                rec[f"{L}_lags"] = round(r["p_local"], 4) if r else np.nan
            pers.append(rec)
    print(pd.DataFrame(pers).to_string(index=False))
    print("\nThey rise but do not die, so it is not simply mean reversion.")

    print("\n\n=== 3. split-half: does it hold in both halves independently? ===")
    half_rows = []
    for outcome in ("gpr_act", "gpr_threat"):
        for h in (1, 5):
            for label, w in HALVES.items():
                r = fit(d, outcome, h, window=w)
                if r:
                    half_rows.append({"outcome": outcome, "h": h,
                                      "half": label, **r})
    halves = pd.DataFrame(half_rows)
    print(halves[["outcome", "h", "half", "n", "p_local", "p_west"]]
          .round(4).to_string(index=False))

    print("\n\n=== 4. time-shuffle placebo ===")
    shuf = fit(d, "gpr_act", 1, shuffle_seed=0)
    print(f"  shuffled perception, gpr_act h=1: p_local={shuf['p_local']:.4f} "
          f"(should be far from zero)")

    grid.to_csv(args.out_dir / "escalation_levels_vs_changes.csv", index=False)
    halves.to_csv(args.out_dir / "escalation_split_half.csv", index=False)
    print(f"\nwrote two tables to {args.out_dir}")
    print("\nThe confirmatory test is scripts/run_gate5_escalation.py, on days")
    print("never ingested when this hypothesis was written down. It FAILS.")


if __name__ == "__main__":
    main()
