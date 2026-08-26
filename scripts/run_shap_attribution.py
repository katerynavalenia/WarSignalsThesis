"""Where does the tree model actually look?

The forecast comparison says the war blocks do not improve on a financial
benchmark. This asks a different and more direct question of the same model: of
the weight it places on its inputs, how much goes to physical attacks and news at
all? A gradient-boosted model given 72 predictors will use whatever it finds
useful, and its own attribution is evidence about the information content of each
block that does not depend on whether the forecast beat a benchmark.

Attribution is by TreeSHAP, computed natively by XGBoost, which decomposes each
prediction exactly into per-feature contributions summing to the prediction.
Contributions are averaged in absolute value over the held-out period, so a
feature that pushes forecasts up as often as down still registers.

One caution is built into how this is read. The model being decomposed does not
beat the historical mean by a statistically detectable margin, so the *ranking*
inside a block should not be over-interpreted -- it is the attribution across
blocks that carries the argument.

    python scripts/run_shap_attribution.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_horse_race import (  # noqa: E402
    TEST_FRACTION,
    XGB_PARAMS,
    build_panel,
)
from src.data.attacks import UAF_REPORTING_START  # noqa: E402

OUT_TABLES = Path("outputs/tables")
OUT_FIGURES = Path("outputs/figures")

TARGET = "r_waerlst"
HORIZON = 1
INFO_SET = "PN"


def block_of(col: str, fin: set[str], phys: set[str], news: set[str]) -> str:
    if col in phys:
        return "Physical attacks"
    if col in news:
        return "News attention and tone"
    if col in fin:
        return "Financial controls"
    return "Other"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--table-dir", type=Path, default=OUT_TABLES)
    ap.add_argument("--figure-dir", type=Path, default=OUT_FIGURES)
    args = ap.parse_args()
    args.table_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)

    panel, sets = build_panel()
    panel = panel[~panel["attack_unobserved"].fillna(False).astype(bool)]
    panel = panel[panel.date >= UAF_REPORTING_START].reset_index(drop=True)

    fin = set(sets["F"])
    phys = {c for c in sets["P"]} - fin
    news = {c for c in sets["N"]} - fin
    cols = [c for c in sets[INFO_SET] if c in panel.columns]

    y = panel[TARGET].rename("y")
    frame = pd.concat([y, panel[cols]], axis=1).dropna()
    ts = int(len(frame) * (1 - TEST_FRACTION))
    X_tr, y_tr = frame[cols].iloc[:ts], frame["y"].iloc[:ts]
    X_te = frame[cols].iloc[ts:]

    model = XGBRegressor(**XGB_PARAMS).fit(X_tr, y_tr)
    # The final column of the contribution matrix is the model's base value and
    # is not a feature, so it is dropped before aggregating.
    import xgboost as xgb

    dmat = xgb.DMatrix(X_te, feature_names=list(cols))
    contribs = np.asarray(model.get_booster().predict(dmat, pred_contribs=True))
    contribs = contribs[:, :-1]

    per_feature = pd.DataFrame({
        "feature": cols,
        "mean_abs_shap": np.abs(contribs).mean(axis=0),
    })
    per_feature["block"] = [block_of(c, fin, phys, news) for c in cols]
    per_feature = per_feature.sort_values("mean_abs_shap", ascending=False)

    total = per_feature.mean_abs_shap.sum()
    by_block = (per_feature.groupby("block")
                .agg(features=("feature", "size"),
                     mean_abs_shap=("mean_abs_shap", "sum"))
                .assign(share_pct=lambda d: 100 * d.mean_abs_shap / total)
                .sort_values("share_pct", ascending=False))

    per_feature.to_csv(args.table_dir / "shap_by_feature.csv", index=False)
    by_block.to_csv(args.table_dir / "shap_by_block.csv")

    print(f"model: XGBoost, {INFO_SET} set, {TARGET}, h={HORIZON}, "
          f"{len(X_tr)} training and {len(X_te)} held-out days\n")
    print("=== attribution by variable block ===\n")
    print(by_block.round(4).to_string())
    print("\n=== ten largest individual contributions ===\n")
    print(per_feature.head(10).round(5).to_string(index=False))

    war = by_block.loc[by_block.index.isin(
        ["Physical attacks", "News attention and tone"]), "share_pct"].sum()
    print(f"\n  war variables carry {war:.1f}% of the model's total attribution, "
          f"from {len(phys) + len(news)} of {len(cols)} predictors")

    # --- figure ---------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200, "font.size": 9,
                         "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.4),
                                 gridspec_kw={"width_ratios": [1, 1.5]})

    # Share of total on the axis, with the per-predictor average annotated
    # beside each bar. A block of 41 predictors accumulates attribution simply
    # by being large, so the per-predictor figure is what says whether any
    # individual variable carries weight -- but the two are on different scales
    # and plotting them as one series would misrepresent both.
    order = by_block.sort_values("share_pct")
    labels = [i.replace(" attention and tone", "\nattention/tone")
              .replace(" controls", "\ncontrols").replace(" attacks", "\nattacks")
              for i in order.index]
    a1.barh(range(len(order)), order.share_pct, color="0.45")
    a1.set_yticks(range(len(order)))
    a1.set_yticklabels(labels, fontsize=7)
    a1.set_xlabel("Share of total attribution, percent")
    a1.set_xlim(0, order.share_pct.max() * 1.45)
    for i, (_, row) in enumerate(order.iterrows()):
        a1.text(row.share_pct + order.share_pct.max() * 0.03, i,
                f"{row.share_pct / row.features:.2f}% each",
                va="center", fontsize=6.5, color="0.25")

    top = per_feature.head(12).iloc[::-1]
    colors = {"Financial controls": "0.45", "Physical attacks": "firebrick",
              "News attention and tone": "steelblue", "Other": "0.7"}
    a2.barh(range(len(top)), top.mean_abs_shap,
            color=[colors.get(b, "0.7") for b in top.block])
    a2.set_yticks(range(len(top)))
    a2.set_yticklabels([(c[:25] + "..." if len(c) > 28 else c).replace("_", " ")
                        for c in top.feature], fontsize=7)
    a2.set_xlabel("Mean absolute contribution")
    fig.tight_layout()
    fig.savefig(args.figure_dir / "fig4_shap_attribution.png")
    plt.close(fig)
    print(f"\nwrote {args.figure_dir / 'fig4_shap_attribution.png'}")


if __name__ == "__main__":
    main()
