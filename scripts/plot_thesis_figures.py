"""The figures the manuscript uses, under the manuscript's own filenames.

Three in the body and one in the appendix, matching the layout the write-up
describes. Filenames are kept as the manuscript references them so the LaTeX
source does not have to change when the figures are regenerated.

    python scripts/plot_thesis_figures.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.attacks import UAF_REPORTING_START, load_attack_panel  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/figures")
INVASION = pd.Timestamp("2022-02-24")

GROUPS = (("att_UA", "tone_UA", "Ukrainian"),
          ("att_RU_STATE", "tone_RU_STATE", "Russian state"),
          ("att_RU_INDEP", "tone_RU_INDEP", "Russian independent"),
          ("att_WEST", "tone_WEST", "Western"))

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3,
    "axes.spines.top": False, "axes.spines.right": False,
})


def _indices() -> pd.DataFrame:
    """Perception indices on a complete daily calendar.

    Reindexing first matters for every figure that smooths: the corpus has days
    the archive does not cover, and a rolling mean over only the surviving rows
    would bridge them with a flat line that reads as real, unchanging data.
    """
    idx = pd.read_parquet(INTERIM / "perception_indices.parquet")
    return idx.reindex(pd.date_range(idx.index.min(), idx.index.max(), freq="D"))


def fig1_defense_indices(out: Path) -> None:
    s = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for c, label in (("r_waerlst", "WAERLST (global)"),
                     ("r_bshieldt", "BSHIELDT (Europe)"),
                     ("r_ita", "ITA (United States)")):
        r = s[c].dropna()
        r = r[r.index >= "2020-01-01"]
        ax.plot(r.index, 100 * (1 + r / 100).cumprod(), lw=1.1, label=label)
    ax.axvline(INVASION, color="0.3", ls="--", lw=0.9)
    ax.axvline(UAF_REPORTING_START, color="0.3", ls=":", lw=0.9)
    ax.set_ylabel("Index, 1 January 2020 = 100")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "fig1_defense_indices.png")
    plt.close(fig)


def fig2_attacks_news(out: Path) -> None:
    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    atk = load_attack_panel(spine["date"]).set_index("date")
    idx = _indices()

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(7.2, 6.6), sharex=True)

    w = atk.loc[atk.index >= UAF_REPORTING_START, "launched_total_lag1"]
    w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="D"))
    weekly = w.resample("W").sum(min_count=1)
    a1.fill_between(weekly.index, weekly.values, color="0.35", lw=0)
    a1.set_ylabel("Weapons launched\n(weekly sum)")

    for att, _, label in GROUPS:
        if att in idx:
            a2.plot(idx.index, 100 * idx[att].rolling(30, min_periods=20).mean(),
                    lw=1.0, label=label)
    a2.set_ylabel("Conflict share of\noutput, % (30-day mean)")
    a2.legend(frameon=False, ncol=2, fontsize=8)

    for _, tone, label in GROUPS:
        if tone in idx:
            a3.plot(idx.index, idx[tone].rolling(30, min_periods=20).mean(),
                    lw=1.0, label=label)
    a3.set_ylabel("Mean conflict tone\n(30-day mean)")

    for ax in (a1, a2, a3):
        ax.axvline(INVASION, color="0.3", ls="--", lw=0.9)
        # The whole sample, not just the war years: the point of extending the
        # news extraction back to 2015 is to show the indicators in a quiet
        # period as well as a loud one.
        ax.set_xlim(idx.index.min(), idx.index.max())
    fig.tight_layout()
    fig.savefig(out / "fig2_attacks_news.png")
    plt.close(fig)


def fig3_return_mae(out: Path) -> None:
    h = pd.read_csv("outputs/tables/horse_race.csv")
    d = h[(h["sample"] == "measured") & (h.horizon == 1) & (h.model == "xgb")]
    bench = (h[(h["sample"] == "measured") & (h.horizon == 1)
               & (h.model == "historical mean")].set_index("target")["mae"])

    order = ["F", "P", "N", "PN", "PNG"]
    names = {"r_waerlst": "WAERLST", "r_bshieldt": "BSHIELDT", "r_ita": "ITA"}
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9))
    for ax, (tgt, label) in zip(axes, names.items()):
        sub = d[d.target == tgt]
        vals = [sub[sub.info_set == s]["mae"].mean() for s in order]
        ax.bar(order, vals, color="0.45", width=0.65)
        if tgt in bench.index:
            ax.axhline(bench[tgt], color="firebrick", ls="--", lw=1.0)
        ax.set_title(label, fontsize=9)
        finite = [v for v in vals if v == v]
        lo = min(finite + [bench.get(tgt, min(finite))])
        hi = max(finite + [bench.get(tgt, max(finite))])
        ax.set_ylim(lo * 0.97, hi * 1.02)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("Mean absolute error")
    fig.tight_layout()
    fig.savefig(out / "fig3_return_mae_infosets.png")
    plt.close(fig)


def figA1_diagnostics(out: Path) -> None:
    """Target distribution and news coverage, as one appendix exhibit.

    Both are diagnostics that support the main results without being needed to
    follow them, and they are combined so the appendix carries one figure rather
    than two near-identical ones.
    """
    s = pd.read_parquet(INTERIM / "spine_full.parquet")
    r = s.loc[s.date >= UAF_REPORTING_START, "r_waerlst"].dropna()
    idx = _indices()

    fig = plt.figure(figsize=(7.2, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], hspace=0.45, wspace=0.28)

    for col, log in ((0, False), (1, True)):
        ax = fig.add_subplot(gs[0, col])
        ax.hist(r, bins=60, color="0.45")
        ax.set_xlabel("Daily log return, %")
        ax.set_ylabel("Count (log scale)" if log else "Count")
        if log:
            ax.set_yscale("log")

    # One series, not four. Every source group is derived from the same
    # extraction, so a day is observed for all of them or for none; drawing four
    # identical lines would show only the last one plotted while the legend
    # implied they differed.
    ax = fig.add_subplot(gs[1, :])
    share = idx["att_UA"].notna().resample("ME").mean()
    ax.fill_between(share.index, 100 * share, color="0.55", lw=0, step="mid")
    ax.axvline(UAF_REPORTING_START, color="0.15", ls="--", lw=1.0)
    ax.set_ylabel("Days observed in month, %")
    ax.set_ylim(0, 103)
    ax.set_title("Coverage is common to all five source groups",
                 fontsize=8, loc="left")
    fig.savefig(out / "figA1_diagnostics.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for fn in (fig1_defense_indices, fig2_attacks_news, fig3_return_mae,
               figA1_diagnostics):
        fn(args.out_dir)
    for f in sorted(args.out_dir.glob("fig*.png")):
        print(f"wrote {f}")


if __name__ == "__main__":
    main()
