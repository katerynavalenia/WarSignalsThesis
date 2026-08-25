"""Gate 4 — does local perception explain European gas? Confirmatory test.

Executes ``docs/v3/gate4_preregistration.md`` without deviation. The pass rule
has four conditions and all four must hold; the reason it is that strict is that
three earlier positives in this project each looked convincing at the moment of
discovery and none survived.

    python scripts/run_gate4_gas.py
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

from src.data.equities import fetch_many  # noqa: E402
from src.features.perception import build_indices  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

ECO = ("WEST", "EN_GLOBAL", "UA", "RU_STATE", "RU_INDEP")
LOCAL = ("UA", "RU_STATE", "RU_INDEP")
WESTERN = ("WEST", "EN_GLOBAL")

TICKERS = {"TTF=F": "ttf", "NG=F": "hh", "BZ=F": "brent",
           "UNA.AS": "unilever", "EURUSD=X": "eurusd"}

WINDOWS = {
    "(a) buildup+invasion 2021-06..2022-06": ("2021-06-01", "2022-06-05"),
    "(b) shutdown+aftermath 2022-06..2023-06": ("2022-06-06", "2023-06-30"),
    "(c) full crisis 2021-06..2023-12": ("2021-06-01", "2023-12-31"),
}
PLACEBOS = ("hh", "brent", "unilever")
CONTROLS = ("brent", "eurusd", "lvix")


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def build_panel() -> pd.DataFrame:
    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_daily.parquet")
    idx = build_indices(daily)
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")

    frames = fetch_many(list(TICKERS))
    px = {
        TICKERS[t]: 100.0 * np.log(f.set_index("date")["adjclose"].astype(float)).diff()
        for t, f in frames.items()
    }
    assets = pd.DataFrame(px).sort_index()
    assets.index.name = "date"

    d = idx.join(assets, how="inner").join(spine[["vix_yf"]], how="inner")
    d["lvix"] = np.log(d["vix_yf"]).shift(1)
    return d


def fit(d, target, window, freq="D", drop_extreme=0, news_lag=1):
    sub = d.loc[window[0]: window[1]].copy()
    if target not in sub or sub[target].notna().sum() < 40:
        return None
    if drop_extreme:
        sub = sub.drop(sub[target].abs().nlargest(drop_extreme).index)

    cols = [f"{p}_{e}" for e in ECO for p in ("att", "tone")]
    if freq == "W":
        agg = {c: "mean" for c in cols}
        agg |= {target: "sum", "lvix": "last"}
        agg |= {c: "sum" for c in CONTROLS if c != "lvix"}
        sub = sub[list(agg)].resample("W-FRI").agg(agg)

    X = pd.DataFrame(index=sub.index)
    for c in cols:
        X[c] = zscore(sub[c].diff().shift(news_lag))
    for c in CONTROLS:
        X[c] = zscore(sub[c]) if c == "lvix" else sub[c]
    X[f"lag_{target}"] = sub[target].shift(1)

    y = sub[target]
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < max(40, 4 * (X.shape[1] + 1)):
        return None

    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    loc = [c for c in X.columns if any(c.endswith(e) for e in LOCAL)]
    wst = [c for c in X.columns if any(c.endswith(e) for e in WESTERN)]
    p_local = float(np.squeeze(m.f_test(" = 0, ".join(loc) + " = 0").pvalue))
    p_west = float(np.squeeze(m.f_test(" = 0, ".join(wst) + " = 0").pvalue))
    if not np.isfinite(p_local):
        return None

    # Which local ecosystem contributes most, for the directional sub-hypothesis.
    contrib = {}
    for e in LOCAL:
        terms = [c for c in X.columns if c.endswith(e)]
        contrib[e] = float(np.squeeze(m.f_test(" = 0, ".join(terms) + " = 0").fvalue))
    return {"n": int(m.nobs), "r2": float(m.rsquared), "p_local": p_local,
            "p_west": p_west, "top_local": max(contrib, key=contrib.get), **contrib}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    d = build_panel()
    print(f"panel: {len(d)} days, {d.index.min().date()} -> {d.index.max().date()}\n")

    rows = []
    for wlab, w in WINDOWS.items():
        for freq in ("D", "W"):
            r = fit(d, "ttf", w, freq)
            if r:
                rows.append({"window": wlab, "freq": freq, "asset": "ttf", **r})
    grid = pd.DataFrame(rows)
    rej, padj, _, _ = multipletests(grid["p_local"], alpha=0.05, method="fdr_bh")
    grid["p_bh"], grid["survives"] = padj, rej

    print("=== PRIMARY: TTF gas, local block conditional on Western ===")
    print(grid[["window", "freq", "n", "r2", "p_local", "p_west", "p_bh",
                "survives", "top_local"]].round(4).to_string(index=False))

    print("\n=== CONDITION 2: placebos (must be p > 0.10) ===")
    prows = []
    for wlab, w in list(WINDOWS.items())[:2]:
        for a in PLACEBOS:
            r = fit(d, a, w)
            if r:
                prows.append({"window": wlab[:28], "asset": a, "n": r["n"],
                              "p_local": r["p_local"]})
    pl = pd.DataFrame(prows)
    print(pl.round(4).to_string(index=False))

    print("\n=== CONDITION 3: drop the ten largest TTF moves ===")
    drows = []
    for wlab, w in list(WINDOWS.items())[:2]:
        for k in (0, 10):
            r = fit(d, "ttf", w, drop_extreme=k)
            if r:
                drows.append({"window": wlab[:28], "dropped": k, "n": r["n"],
                              "p_local": r["p_local"]})
    dr = pd.DataFrame(drows)
    print(dr.round(4).to_string(index=False))

    # --- the pre-registered verdict ---
    a_lab, b_lab = list(WINDOWS)[0], list(WINDOWS)[1]
    surv = grid[grid.survives]
    c1 = (surv.window == a_lab).any() and (surv.window == b_lab).any()
    c2 = bool(len(pl)) and (pl.p_local > 0.10).all()
    c3 = bool(len(dr)) and (dr[dr.dropped == 10].p_local < 0.05).all()
    c4 = bool(len(surv)) and (surv.top_local == "RU_STATE").all()

    print("\n=== PRE-REGISTERED VERDICT ===")
    for name, ok in [("1 BH survivor in BOTH windows (a) and (b)", c1),
                     ("2 all placebos p > 0.10", c2),
                     ("3 survives dropping 10 largest moves", c3),
                     ("4 RU_STATE is the leading local block", c4)]:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  OVERALL: {'PASS' if all([c1, c2, c3, c4]) else 'FAIL'}")

    grid.to_csv(args.out_dir / "gate4_gas.csv", index=False)
    pl.to_csv(args.out_dir / "gate4_placebos.csv", index=False)
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
