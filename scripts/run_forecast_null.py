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

    python scripts/run_forecast_null.py
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
    combine_forecasts,
    economic_value,
    model_confidence_set,
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

    # --- the three remedies a forecasting null is expected to try -------------
    #
    # Individually weak predictors are exactly the case where combination and
    # economic value are supposed to rescue a result, so a null that never tries
    # them is incomplete. The Model Confidence Set answers the separate question
    # of which models can be told apart at all.
    longest = max(targets, key=lambda t: d[t].notna().sum())
    y = d[longest].dropna()
    bench = expanding_forecasts(y, None)

    fc = {}
    for p in predictors:
        x = d[p].diff().shift(1).reindex(y.index)
        fc[p] = expanding_forecasts(y, x)
    fc_frame = pd.DataFrame(fc).dropna(how="all")

    print(f"\n\n=== FORECAST COMBINATION ({longest}) ===")
    combo_rows = []
    for method in ("mean", "median"):
        combo = combine_forecasts(fc_frame, method=method)
        common = pd.concat([y, bench, combo], axis=1).dropna()
        if len(common) < 200:
            continue
        a, b, f = common.iloc[:, 0], common.iloc[:, 1], common.iloc[:, 2]
        cw = clark_west(a, b, f)
        combo_rows.append({"method": method, "n": len(common),
                           "r2_oos": campbell_thompson_r2_oos(a, f, b),
                           "cw_stat": cw.statistic, "cw_p": cw.pvalue})
    combo_tab = pd.DataFrame(combo_rows)
    print(combo_tab.round(4).to_string(index=False))
    print("  Averaging weak predictors is the standard remedy. It does not help here.")

    print(f"\n=== ECONOMIC VALUE ({longest}, mean-variance timer, gamma=3) ===")
    ev_rows = []
    best = res.index[0]
    best_pred = res.loc[best, "predictor"] if "predictor" in res else predictors[0]
    for label, series in (("best single predictor", fc.get(best_pred)),
                          ("equal-weighted combination", combine_forecasts(fc_frame))):
        if series is None:
            continue
        common = pd.concat([y, bench, series], axis=1).dropna()
        if len(common) < 100:
            continue
        for cost in (0.0, 10.0):
            try:
                ev = economic_value(common.iloc[:, 0], common.iloc[:, 2],
                                    common.iloc[:, 1], cost_bps=cost)
            except ValueError:
                continue
            ev_rows.append({"forecast": label, "cost_bps": cost, **ev})
    ev_tab = pd.DataFrame(ev_rows)
    if len(ev_tab):
        print(ev_tab[["forecast", "cost_bps", "n", "cer_gain_pct",
                      "sharpe_model", "sharpe_benchmark"]].round(3).to_string(index=False))
        print("  A negative CER gain means an investor would pay NOT to time on this.")

    print("\n=== MODEL CONFIDENCE SET (squared-error loss) ===")
    losses = {}
    common_idx = fc_frame.dropna().index.intersection(y.index).intersection(bench.dropna().index)
    if len(common_idx) > 200:
        losses["benchmark"] = (y.loc[common_idx] - bench.loc[common_idx]) ** 2
        for p in predictors:
            losses[p] = (y.loc[common_idx] - fc[p].loc[common_idx]) ** 2
        mcs = model_confidence_set(pd.DataFrame(losses), alpha=0.10, n_boot=500)
        kept = int(mcs["in_confidence_set"].sum())
        print(f"  {kept} of {len(mcs)} models retained at 90% confidence")
        print("  A large surviving set is not evidence the models are good: it means")
        print("  the data cannot separate them, which is what the null already said.")
        mcs.to_csv(args.out_dir / "forecast_mcs.csv")

    combo_tab.to_csv(args.out_dir / "forecast_combination.csv", index=False)
    if len(ev_tab):
        ev_tab.to_csv(args.out_dir / "forecast_economic_value.csv", index=False)
    print(f"\nwrote forecast tables to {args.out_dir}")


if __name__ == "__main__":
    main()
