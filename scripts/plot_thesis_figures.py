"""The three figures the write-up uses.

Kept to three so that tables and figures together stay inside the ten the
research design allows. Each one carries something the tables cannot: the
outcomes on a common scale, the two war-information layers side by side, and the
forecast comparison that the numbers in the results table only imply.

    python scripts/plot_thesis_figures.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.attacks import UAF_REPORTING_START, load_attack_panel  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/figures")
INVASION = pd.Timestamp("2022-02-24")

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200,
    "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
    "axes.spines.top": False, "axes.spines.right": False,
})


def fig1_outcomes(out_dir: Path) -> None:
    """The three defence-equity outcomes on a common scale."""
    s = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    cols = {"r_waerlst": "WAERLST (global)",
            "r_bshieldt": "BSHIELDT (Europe)",
            "r_ita": "ITA (United States)"}
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    for c, label in cols.items():
        r = s[c].dropna()
        r = r[r.index >= "2020-01-01"]
        ax.plot(r.index, 100 * (1 + r / 100).cumprod(), lw=1.1, label=label)
    ax.axvline(INVASION, color="0.35", ls="--", lw=0.9)
    ax.annotate("24 Feb 2022", (INVASION, ax.get_ylim()[1]),
                xytext=(6, -12), textcoords="offset points",
                fontsize=8, color="0.35")
    ax.set_ylabel("Index, 1 Jan 2020 = 100")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "fig1_outcomes.png")
    plt.close(fig)


def fig2_layers(out_dir: Path) -> None:
    """The two war-information layers: what happened, and how it was reported."""
    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    atk = load_attack_panel(spine["date"]).set_index("date")
    idx = pd.read_parquet(INTERIM / "perception_indices.parquet")

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.0, 5.0), sharex=True)

    w = atk.loc[atk.index >= UAF_REPORTING_START, "launched_total_lag1"]
    w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="D"))
    a1.fill_between(w.index, w.rolling(7, min_periods=3).mean(),
                    color="0.35", lw=0)
    a1.set_ylabel("Weapons launched\n(7-day mean)")
    a1.set_title("Physical layer: Russian air attacks", fontsize=9, loc="left")

    # Reindex onto a complete daily calendar first. The corpus has gaps -- days
    # absent from the GDELT archive and windows collected separately -- and a
    # rolling mean computed over the surviving rows would bridge them with a
    # flat line, which reads as a long period of unchanging attention rather
    # than as missing data. On a complete index the gaps break the line.
    full = pd.date_range(idx.index.min(), idx.index.max(), freq="D")
    idx = idx.reindex(full)
    for c, label in (("att_UA", "Ukrainian"), ("att_RU_STATE", "Russian state"),
                     ("att_WEST", "Western")):
        if c in idx:
            a2.plot(idx.index, 100 * idx[c].rolling(30, min_periods=20).mean(),
                    lw=1.0, label=label)
    a2.axvline(INVASION, color="0.35", ls="--", lw=0.9)
    a2.set_ylabel("Conflict share of\noutput, % (30-day mean)")
    a2.set_title("Narrative layer: conflict attention by source group",
                 fontsize=9, loc="left")
    a2.legend(frameon=False, ncol=3, fontsize=8)
    a2.set_xlim(pd.Timestamp("2021-01-01"), idx.index.max())
    a1.set_xlim(pd.Timestamp("2021-01-01"), idx.index.max())
    fig.tight_layout()
    fig.savefig(out_dir / "fig2_war_layers.png")
    plt.close(fig)


def fig3_forecast_error(out_dir: Path) -> None:
    """One-day forecast error by information set, against the benchmark."""
    h = pd.read_csv("outputs/tables/horse_race.csv")
    d = h[(h["sample"] == "measured") & (h.horizon == 1)
          & (h.model.isin(["xgb", "ridge"]))]
    bench = h[(h["sample"] == "measured") & (h.horizon == 1)
              & (h.model == "historical mean")].set_index("target")["mae"]

    order = ["F", "P", "N", "PN", "PNG"]
    names = {"r_waerlst": "WAERLST", "r_bshieldt": "BSHIELDT", "r_ita": "ITA"}
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9), sharey=False)
    for ax, (tgt, label) in zip(axes, names.items()):
        sub = d[d.target == tgt]
        vals = [sub[(sub.info_set == s) & (sub.model == "xgb")]["mae"].mean()
                for s in order]
        ax.bar(order, vals, color="0.45", width=0.65)
        if tgt in bench.index:
            ax.axhline(bench[tgt], color="firebrick", ls="--", lw=1.0)
        ax.set_title(label, fontsize=9)
        ax.set_ylim(min(v for v in vals if v == v) * 0.96,
                    max(v for v in vals if v == v) * 1.02)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("Mean absolute error")
    fig.tight_layout()
    fig.savefig(out_dir / "fig3_forecast_error.png")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fig1_outcomes(args.out_dir)
    fig2_layers(args.out_dir)
    fig3_forecast_error(args.out_dir)
    for f in ("fig1_outcomes.png", "fig2_war_layers.png",
              "fig3_forecast_error.png"):
        print(f"wrote {args.out_dir / f}")


if __name__ == "__main__":
    main()
