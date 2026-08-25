"""Gate 5 — does local media anticipate escalation? Confirmatory, on held-out days.

Executes ``docs/v3/gate5_preregistration.md`` without deviation, on 954 days that
were never ingested when the hypothesis was written down.

One implementation note the pre-registration did not specify. The held-out days
are two non-contiguous blocks (2019-10 → 2021-05 and calendar 2024). Lags and
first differences are computed **within** each block and rows spanning the
boundary are dropped, because a lag taken across a two-and-a-half-year gap is not
a lag. This is the faithful reading of "estimated as a single sample" — one
regression, but no fabricated dynamics.

    python scripts/run_gate5_escalation.py
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
WESTERN = ("WEST", "EN_GLOBAL")
HORIZONS = (1, 5)
OUTCOMES = ("gpr_act", "gpr_threat")  # gpr_act primary, gpr_threat secondary
OWN_LAGS = 6
MAX_GAP_DAYS = 7  # a jump larger than this starts a new contiguous block


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def load_holdout() -> pd.DataFrame:
    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_holdout.parquet")
    idx = build_indices(daily)
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    d = idx.join(spine[["gpr", "gpr_act", "gpr_threat"]], how="inner").sort_index()
    gap = d.index.to_series().diff().dt.days.fillna(1)
    d["block"] = (gap > MAX_GAP_DAYS).cumsum()
    return d


def build_design(d: pd.DataFrame, outcome: str, h: int, own_lags: int, shuffle_seed=None):
    """Design matrix with lags taken within contiguous blocks only."""
    frame = d.copy()
    if shuffle_seed is not None:
        rng = np.random.default_rng(shuffle_seed)
        perm = rng.permutation(len(frame))
        for e in ECO:
            frame[f"att_{e}"] = frame[f"att_{e}"].to_numpy()[perm]
            frame[f"tone_{e}"] = frame[f"tone_{e}"].to_numpy()[perm]

    parts_y, parts_X = [], []
    for _, blk in frame.groupby("block"):
        if len(blk) < own_lags + h + 30:
            continue
        y = blk[outcome].shift(-h) - blk[outcome]
        X = pd.DataFrame(index=blk.index)
        for e in ECO:
            X[f"att_{e}"] = blk[f"att_{e}"]
            X[f"tone_{e}"] = blk[f"tone_{e}"]
        for lag in range(own_lags):
            X[f"out_l{lag}"] = blk[outcome].shift(lag)
            X[f"dout_l{lag}"] = blk[outcome].diff().shift(lag)
        keep = X.notna().all(axis=1) & y.notna()
        parts_y.append(y[keep])
        parts_X.append(X[keep])

    if not parts_y:
        return None, None
    y = pd.concat(parts_y)
    X = pd.concat(parts_X)
    return y, X.apply(zscore)


def test(d, outcome, h, own_lags=OWN_LAGS, shuffle_seed=None):
    y, X = build_design(d, outcome, h, own_lags, shuffle_seed)
    if y is None or len(y) < 150:
        return None
    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": h + 5})
    loc = [c for c in X.columns if any(c.endswith(e) for e in LOCAL)]
    wst = [c for c in X.columns if any(c.endswith(e) for e in WESTERN)]
    return {"n": int(m.nobs), "r2": float(m.rsquared),
            "p_local": float(np.squeeze(m.f_test(" = 0, ".join(loc) + " = 0").pvalue)),
            "p_west": float(np.squeeze(m.f_test(" = 0, ".join(wst) + " = 0").pvalue))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    d = load_holdout()
    print(f"held-out sample: {len(d)} days, {d.index.min().date()} -> "
          f"{d.index.max().date()}, {d.block.nunique()} contiguous blocks")
    for b, blk in d.groupby("block"):
        print(f"  block {b}: {len(blk)} days, {blk.index.min().date()} -> "
              f"{blk.index.max().date()}")

    rows = []
    for outcome in OUTCOMES:
        for h in HORIZONS:
            r = test(d, outcome, h)
            if r:
                rows.append({"outcome": outcome, "h": h, **r})
    grid = pd.DataFrame(rows)
    rej, padj, _, _ = multipletests(grid["p_local"], alpha=0.05, method="fdr_bh")
    grid["p_bh"], grid["survives"] = padj, rej

    print("\n=== CONFIRMATORY: local block conditional on Western, held-out days ===")
    print(grid.round(4).to_string(index=False))

    print("\n=== CONDITION 2: time-shuffle placebo (must be p > 0.20) ===")
    prows = [{"outcome": o, "h": h, **test(d, o, h, shuffle_seed=s)}
             for s, (o, h) in enumerate([("gpr_act", 1), ("gpr_act", 5)])]
    pl = pd.DataFrame(prows)
    print(pl[["outcome", "h", "n", "p_local"]].round(4).to_string(index=False))

    print("\n=== CONDITION 3: twelve lags of own dynamics ===")
    drows = [{"outcome": "gpr_act", "h": h, **test(d, "gpr_act", h, own_lags=12)}
             for h in HORIZONS]
    dl = pd.DataFrame(drows)
    print(dl[["outcome", "h", "n", "p_local", "p_west"]].round(4).to_string(index=False))

    act = grid[grid.outcome == "gpr_act"]
    c1 = bool(len(act) == len(HORIZONS) and act.survives.all())
    c2 = bool((pl.p_local > 0.20).all())
    c3 = bool((dl.p_local < 0.05).all())

    print("\n=== PRE-REGISTERED VERDICT ===")
    for name, ok in [("1 GPR_ACT survives BH at BOTH horizons", c1),
                     ("2 shuffle placebo p > 0.20", c2),
                     ("3 survives twelve own-dynamics lags", c3)]:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  OVERALL: {'PASS' if all([c1, c2, c3]) else 'FAIL'}")

    grid.to_csv(args.out_dir / "gate5_escalation.csv", index=False)
    print(f"\nwrote {args.out_dir/'gate5_escalation.csv'}")


if __name__ == "__main__":
    main()
