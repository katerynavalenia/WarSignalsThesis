"""The efficiency chapter: forecast defence returns, and say how much was detectable.

Supervisor comment #4 asked for a Diebold–Mariano test. Under the thesis's final
framing the more important half is the **power statement**: the thesis's answer
is that local perception is not priced, and a null is only a finding if you can
say what size of effect you could have found.

Design, deliberately simple because the point is the evaluation rather than the
model:

* expanding-window one-day-ahead forecasts, re-estimated every day
* benchmark = historical mean (the standard hurdle for return prediction)
* model = benchmark plus one perception predictor
* judged by Campbell–Thompson R²_OS with a Clark–West test, because the model
  nests the benchmark and Diebold–Mariano is invalid there
* Benjamini–Hochberg across the predictor × target grid

    cd thesis_v2 && python scripts/run_forecast_null.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.evaluation import (  # noqa: E402
    benjamini_hochberg,
    campbell_thompson_r2_oos,
    clark_west,
    simulate_power_r2_oos,
)

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")
MIN_TRAIN = 250  # about one trading year before the first forecast


def expanding_forecasts(
    y: pd.Series, x: pd.Series | None, min_train: int = MIN_TRAIN
) -> pd.Series:
    """One-step-ahead expanding-window forecasts of ``y``.

    With ``x=None`` this is the historical mean. Otherwise it is an OLS of y on
    a constant and lagged x, re-fit at every step. Only information available
    strictly before the forecast date enters — the predictor is lagged before it
    reaches this function, and the fit uses observations up to t-1 only.
    """
    out = pd.Series(index=y.index, dtype=float)
    yv = y.to_numpy(dtype=float)
    xv = x.to_numpy(dtype=float) if x is not None else None

    for t in range(min_train, len(y)):
        ytr = yv[:t]
        if xv is None:
            out.iloc[t] = float(np.nanmean(ytr))
            continue
        xtr = xv[:t]
        ok = np.isfinite(ytr) & np.isfinite(xtr)
        if ok.sum() < 30 or not np.isfinite(xv[t]):
            out.iloc[t] = float(np.nanmean(ytr))
            continue
        design = np.column_stack([np.ones(ok.sum()), xtr[ok]])
        beta, *_ = np.linalg.lstsq(design, ytr[ok], rcond=None)
        out.iloc[t] = float(beta[0] + beta[1] * xv[t])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--n-sims", type=int, default=150)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(INTERIM / "perception_indices.parquet")
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    d = idx.join(spine, how="inner").sort_index()

    targets = [t for t in ("r_ita", "us_defence", "eu_defence", "r_bshieldt", "r_waerlst")
               if t in d and d[t].notna().sum() > 400]
    predictors = [c for c in d.columns if c.startswith(("att_", "tone_"))]

    rows = []
    for tgt in targets:
        y = d[tgt].dropna()
        bench = expanding_forecasts(y, None)
        for p in predictors:
            x = d[p].diff().shift(1).reindex(y.index)  # lagged: known before t
            fc = expanding_forecasts(y, x)
            common = pd.concat([y, bench, fc], axis=1).dropna()
            if len(common) < 200:
                continue
            a, b, f = common.iloc[:, 0], common.iloc[:, 1], common.iloc[:, 2]
            try:
                cw = clark_west(a, b, f)
            except ValueError:
                continue
            rows.append({
                "target": tgt, "predictor": p, "n_oos": len(common),
                "r2_oos": campbell_thompson_r2_oos(a, f, b),
                "cw_stat": cw.statistic, "cw_p": cw.pvalue,
            })

    res = pd.DataFrame(rows)
    if res.empty:
        print("no evaluable specifications")
        return

    bh = benjamini_hochberg(res.set_index(res.target + " / " + res.predictor)["cw_p"])
    res = res.set_index(res.target + " / " + res.predictor)
    res["cw_p_bh"] = bh["p_adjusted"]
    res["survives_bh"] = bh["reject"]
    res = res.sort_values("cw_p")

    print("=== out-of-sample forecasting, expanding window, one day ahead ===\n")
    print(res.head(15).round(4).to_string())

    n_oos = int(res["n_oos"].median())
    print(f"\n  specifications            : {len(res)}")
    print(f"  positive R2_OS            : {(res.r2_oos > 0).sum()}")
    print(f"  Clark-West p<0.05         : {(res.cw_p < 0.05).sum()} "
          f"(expected by chance {0.05*len(res):.1f})")
    print(f"  surviving BH at FDR 5%    : {int(res.survives_bh.sum())}")
    print(f"  best R2_OS                : {res.r2_oos.max():+.4f}")

    print("\n=== THE POWER STATEMENT (simulated on the actual sample) ===")
    longest = max(targets, key=lambda t: d[t].notna().sum())
    curve = simulate_power_r2_oos(d[longest].dropna(), n_sims=args.n_sims)
    print(f"  target used: {longest}, n_oos = {int(curve.n_oos.iloc[0])}, "
          f"{int(curve.n_sims.iloc[0])} simulations per point\n")
    print(curve.round(4).to_string(index=False))

    powered = curve[curve.rejection_rate >= 0.80]
    if len(powered):
        thresh = powered.true_r2_oos.min()
        print(f"\n  Detectable at 80% power: R2_OS >= {thresh:.3f} ({thresh*100:.1f}%).")
        print(f"  Observed best: {res.r2_oos.max():+.4f}. Nothing near the threshold,")
        print("  and no Clark-West rejection survives correction.")
    else:
        print("\n  No grid point reaches 80% power. The honest statement is that this")
        print("  sample cannot detect effects of the size this literature reports")
        print("  (0.3-1%), so the forecasting result bounds nothing and must be")
        print("  reported as uninformative rather than as a null.")

    res.to_csv(args.out_dir / "forecast_null.csv")
    curve.to_csv(args.out_dir / "forecast_power_curve.csv", index=False)
    print(f"\nwrote {args.out_dir/'forecast_null.csv'} and "
          f"{args.out_dir/'forecast_power_curve.csv'}")


if __name__ == "__main__":
    main()
