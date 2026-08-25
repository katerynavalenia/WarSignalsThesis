"""Full-sample plots of the perception indicators (supervisor comment 2).

Plots every ecosystem's conflict-attention share and conflict tone over the
whole 2015-02-18 -> 2026-05-20 coverage, with the war regimes shaded and
24 February 2022 marked. Writes to outputs/figures/.

Run from thesis_v2/:  python scripts/plot_stylized_facts.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "outputs" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

ECOSYSTEMS = ["UA", "RU_STATE", "RU_INDEP", "WEST", "EN_GLOBAL"]
LABELS = {
    "UA": "Ukrainian",
    "RU_STATE": "Russian state",
    "RU_INDEP": "Russian independent",
    "WEST": "Western",
    "EN_GLOBAL": "native-English",
}
COLORS = {
    "UA": "#1b6ca8",
    "RU_STATE": "#c0392b",
    "RU_INDEP": "#e08a1e",
    "WEST": "#2e7d4f",
    "EN_GLOBAL": "#6c5b8c",
}
REGIMES = [
    ("build-up", "2021-11-01", "2022-02-23", "#f3e3c3", 0.055),
    ("invasion", "2022-02-24", "2022-09-28", "#f0c9c9", 0.0),
    ("attrition", "2022-09-29", "2026-05-20", "#e4ecf4", 0.0),
]
INVASION = pd.Timestamp("2022-02-24")


def load() -> pd.DataFrame:
    interim = ROOT / "data" / "interim"
    frames = [
        pd.read_parquet(interim / "gdelt_ecosystems_daily.parquet"),
        pd.read_parquet(interim / "gdelt_ecosystems_holdout.parquet"),
    ]
    df = pd.concat(frames).drop_duplicates(subset=["day", "ecosystem"])
    return df.sort_values("day")


def shade(ax, ymin, ymax):
    span = ymax - ymin
    for name, start, end, color, drop in REGIMES:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=color, zorder=0)
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        ax.text(
            mid,
            ymax - drop * span,
            name,
            ha="center",
            va="top",
            fontsize=7,
            color="#666",
        )
    ax.axvline(INVASION, color="#000000", lw=0.9, ls="--", zorder=3)
    ax.set_ylim(ymin, ymax)


def panel(df, value, ylabel, title, outfile, smooth=30, pct=False):
    wide = df.pivot(index="day", columns="ecosystem", values=value)
    wide = wide[ECOSYSTEMS].rolling(smooth, min_periods=max(1, smooth // 3)).mean()
    if pct:
        wide = wide * 100.0

    fig, ax = plt.subplots(figsize=(10, 4.2))
    lo = float(wide.min().min())
    hi = float(wide.max().max())
    pad = 0.10 * (hi - lo)
    shade(ax, lo - pad, hi + pad)
    for eco in ECOSYSTEMS:
        ax.plot(wide.index, wide[eco], lw=1.0, color=COLORS[eco], label=LABELS[eco])
    ax.annotate(
        "24 Feb 2022",
        xy=(INVASION, lo),
        xytext=(6, 4),
        textcoords="offset points",
        fontsize=8,
    )
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11, loc="left")
    ax.legend(ncol=5, fontsize=8, frameon=False, loc="lower left")
    ax.margins(x=0.01)
    ax.grid(axis="y", lw=0.4, color="#dddddd")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGDIR / outfile, dpi=160)
    plt.close(fig)
    print("wrote", FIGDIR / outfile)
    return wide


def main():
    df = load()
    days = df["day"].nunique()
    print(f"{days} days, {df['day'].min().date()} -> {df['day'].max().date()}")

    panel(
        df,
        "share",
        "conflict share of own output (%)",
        f"Conflict attention by media ecosystem, 30-day mean, {days} days",
        "fig1_attention_full_sample.png",
        pct=True,
    )
    panel(
        df,
        "tone_conflict",
        "mean GDELT tone of conflict articles",
        f"Conflict tone by media ecosystem, 30-day mean, {days} days",
        "fig2_tone_full_sample.png",
    )


if __name__ == "__main__":
    main()
