"""The gas exploration and the attempts to kill it — Chapter 8 §8.4.

Two stages, in the order they happened.

**The scan.** Defence equities were always a weak testbed: the link from Russian
reporting to a US contractor runs entirely through Western investors, which makes
"only Western media matter" close to definitional. So the same conditional design
was run across assets through which the conflict physically transmitted — European
gas, grain, the rouble, gas-exposed utilities.

**The adversarial tests.** European gas came back at p=0.0005 under proper
controls, and this project's record on exploratory positives was already 0-for-3.
So before believing it: are the controls right, is it one event, and does an asset
with no Russian supply respond just as strongly? The placebos were clean and the
result strengthened under correct controls — the opposite of how the defence
threat channel died — which is why it earned a pre-registered test rather than a
footnote.

That pre-registered test then failed on continuous data. ``run_gate4_gas.py`` is
the confirmatory run; this is the exploratory work that motivated it, kept
because Chapter 8 documents both halves.

    python scripts/diagnose_gas.py
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

SCAN_ASSETS = {"TTF=F": "ttf_gas", "NG=F": "hh_gas", "BZ=F": "brent",
               "ZW=F": "wheat", "ZC=F": "corn", "RUB=X": "usdrub",
               "ENGI.PA": "engie", "OMV.VI": "omv", "RWE.DE": "rwe",
               "UNG": "ung", "UNA.AS": "unilever", "EURUSD=X": "eurusd"}
BUILDUP = ("2021-11-22", "2022-03-22")


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def build_panel() -> pd.DataFrame:
    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_daily.parquet")
    idx = build_indices(daily)
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    frames = fetch_many(list(SCAN_ASSETS))
    px = {SCAN_ASSETS[t]: 100.0 * np.log(f.set_index("date")["adjclose"].astype(float)).diff()
          for t, f in frames.items()}
    assets = pd.DataFrame(px).sort_index()
    assets.index.name = "date"
    d = idx.join(assets, how="inner").join(spine[["spx", "sxxp", "vix_yf"]], how="inner")
    d["lvix"] = np.log(d["vix_yf"]).shift(1)
    return d


def fit(d, target, controls, window=BUILDUP, drop_extreme=0, lag=1):
    sub = d.loc[window[0]: window[1]].copy()
    if target not in sub or sub[target].notna().sum() < 40:
        return None
    if drop_extreme:
        sub = sub.drop(sub[target].abs().nlargest(drop_extreme).index)
    X = pd.DataFrame(index=sub.index)
    for e in ECO:
        X[f"att_{e}"] = zscore(sub[f"att_{e}"].diff().shift(lag))
        X[f"tone_{e}"] = zscore(sub[f"tone_{e}"].diff().shift(lag))
    for c in controls:
        X[c] = zscore(sub[c]) if c == "lvix" else sub[c]
    X[f"lag_{target}"] = sub[target].shift(1)
    y = sub[target]
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < 4 * (X.shape[1] + 1):
        return None
    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
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

    d = build_panel()
    print(f"panel: {len(d)} days, {d.index.min().date()} -> {d.index.max().date()}\n")

    print("=== 1. THE SCAN: which assets respond to local media at all? ===")
    rows = []
    for asset in SCAN_ASSETS.values():
        if asset in ("eurusd",):
            continue
        r = fit(d, asset, ["brent", "eurusd", "lvix"])
        if r:
            rows.append({"asset": asset, **r})
    scan = pd.DataFrame(rows).sort_values("p_local")
    if len(scan):
        rej, padj, _, _ = multipletests(scan["p_local"], alpha=0.05, method="fdr_bh")
        scan["p_bh"], scan["survives"] = padj, rej
    print(scan.round(4).to_string(index=False))

    print("\n\n=== 2. Does the gas result survive energy-specific controls? ===")
    ctrl_rows = []
    for label, controls in (("STOXX + VIX (original)", ["sxxp", "lvix"]),
                            ("Brent + VIX", ["brent", "lvix"]),
                            ("Brent + EURUSD + VIX", ["brent", "eurusd", "lvix"]),
                            ("Brent + EURUSD + STOXX + VIX",
                             ["brent", "eurusd", "sxxp", "lvix"])):
        r = fit(d, "ttf_gas", controls)
        if r:
            ctrl_rows.append({"controls": label, **r})
    print(pd.DataFrame(ctrl_rows).round(4).to_string(index=False))
    print("\nIt strengthens under correct controls. The defence threat channel")
    print("did the opposite, which is why this one earned a pre-registered test.")

    print("\n\n=== 3. Is it one event? ===")
    drop_rows = [{"dropped": k, **fit(d, "ttf_gas", ["brent", "eurusd", "lvix"],
                                      drop_extreme=k)}
                 for k in (0, 3, 5, 10)]
    print(pd.DataFrame(drop_rows).round(4).to_string(index=False))

    print("\n\n=== 4. PLACEBOS: assets with no Russian supply exposure ===")
    plac_rows = []
    for asset, ctrl in (("hh_gas", ["brent", "eurusd", "lvix"]),
                        ("brent", ["eurusd", "sxxp", "lvix"]),
                        ("wheat", ["brent", "eurusd", "lvix"]),
                        ("unilever", ["sxxp", "eurusd", "lvix"])):
        r = fit(d, asset, ctrl)
        if r:
            plac_rows.append({"asset": asset, **r})
    print(pd.DataFrame(plac_rows).round(4).to_string(index=False))
    print("\nUS gas is the discriminating test: it carries no Russian supply, so")
    print("if it responded as strongly the channel would be a global risk factor.")

    scan.to_csv(args.out_dir / "gas_asset_scan.csv", index=False)
    pd.DataFrame(ctrl_rows).to_csv(args.out_dir / "gas_controls.csv", index=False)
    pd.DataFrame(plac_rows).to_csv(args.out_dir / "gas_placebos.csv", index=False)
    print(f"\nwrote three tables to {args.out_dir}")
    print("The confirmatory test is scripts/run_gate4_gas.py, and it FAILS.")


if __name__ == "__main__":
    main()
