#!/usr/bin/env python3
"""Phase 5B+5C — Build the daily master panel and feature matrix from Phase 1–3 sources.

Usage
-----
    python scripts/phase5_build_master.py [--paths-yaml CONFIG]
                                         [--no-figure]
                                         [--no-features]

Produces
--------
    data/processed/daily_master.parquet      (72 cols, raw merged panel)
    data/processed/feature_matrix.parquet    (141 cols, with engineered features)
    outputs/figures/fig10_master_coverage.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Allow running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.attack_features import add_attack_features
from src.features.calendar_features import add_calendar_features
from src.features.financial_features import add_financial_features
from src.features.merge import (
    build_daily_master,
    load_attack,
    load_financial,
    load_news_enriched,
    load_news_pivot,
    load_paths_config,
)
from src.features.news_features import add_news_features


def make_coverage_figure(master: pd.DataFrame, out_path: Path) -> None:
    """Plot a calendar-month × column-group missingness heatmap."""
    df = master.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # Group columns by source so the heatmap is readable.
    groups = {
        "financial": [c for c in df.columns if c.startswith(("ITA", "BSHIELDT", "WAERLST", "r_", "VIX", "d_VIX", "vol_", "interest")) and c != "waerlst_missing"],
        "attack": [c for c in df.columns if c.startswith(("launched_", "destroyed_", "n_", "interception", "war_intensity", "weapon_"))],
        "news": [c for c in df.columns if c.startswith(("n_articles_", "tone_", "narrative_", "n_tone_"))],
    }
    # The news_pivot columns overlap with the news columns; keep them separate.
    pivot_cols = [c for c in df.columns if c.startswith(("n_ukrainian_", "n_russian_", "n_western_", "n_other_"))]
    groups["news_pivot"] = pivot_cols

    # Compute missingness % per month per group.
    months = sorted(df["month"].unique())
    rows = []
    for label, cols in groups.items():
        cols = [c for c in cols if c in df.columns]
        if not cols:
            continue
        miss = df.groupby("month")[cols].apply(lambda x: x.isna().mean().mean())
        for m in months:
            rows.append({"group": label, "month": m, "missing_pct": miss.get(m, np.nan) * 100})

    cov = pd.DataFrame(rows)
    if cov.empty:
        print("WARNING: no source groups found; skipping figure")
        return

    # Pivot to a matrix for the heatmap.
    matrix = cov.pivot(index="group", columns="month", values="missing_pct").fillna(0)
    matrix = matrix.reindex(sorted(matrix.index))

    fig, ax = plt.subplots(figsize=(max(12, len(months) * 0.3), 3.5))
    im = ax.imshow(matrix.values, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    # X-axis: every Nth month to avoid overlap.
    n = len(matrix.columns)
    step = max(1, n // 12)
    ax.set_xticks(range(0, n, step))
    ax.set_xticklabels([matrix.columns[i] for i in range(0, n, step)], rotation=45, ha="right")
    ax.set_xlabel("Month")
    ax.set_title("Phase 5 daily_master: % missing by source group × month")
    fig.colorbar(im, ax=ax, label="% missing")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  wrote {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml",
        default="config/paths.yaml",
        help="Path to the local paths config (default: config/paths.yaml).",
    )
    parser.add_argument(
        "--no-figure",
        action="store_true",
        help="Skip generating the coverage figure.",
    )
    parser.add_argument(
        "--no-features",
        action="store_true",
        help="Skip building the feature matrix (only build daily_master).",
    )
    args = parser.parse_args()

    print("Phase 5B+5C — Building daily_master.parquet and feature_matrix.parquet")
    print("=" * 60)

    paths = load_paths_config(args.paths_yaml)
    out_path = Path(paths["processed_files"]["daily_master"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig_path = Path(paths["outputs"]["figures"]) / "fig10_master_coverage.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading source tables …")
    fin = load_financial(paths)
    print(f"  financial:   {fin.shape}  ({fin['date'].min().date()} → {fin['date'].max().date()})")
    atk = load_attack(paths)
    print(f"  attack:      {atk.shape}  ({atk['date'].min().date()} → {atk['date'].max().date()})")
    nws = load_news_enriched(paths)
    print(f"  news:        {nws.shape}  ({nws['date'].min().date()} → {nws['date'].max().date()})")
    pvt = load_news_pivot(paths)
    print(f"  news_pivot:  {pvt.shape}  ({pvt['date'].min().date()} → {pvt['date'].max().date()})")

    print("Merging …")
    master = build_daily_master(fin, atk, nws, pvt)
    print(f"  master:      {master.shape}  ({master['date'].min().date()} → {master['date'].max().date()})")
    print(f"  columns:     {len(master.columns)} (incl. date, waerlst_missing, is_weekend, is_holiday)")

    print(f"Writing {out_path} …")
    master.to_parquet(out_path, index=False)

    if not args.no_figure:
        print("Generating coverage figure …")
        make_coverage_figure(master, fig_path)

    # Quick summary.
    print("\nMissingness summary:")
    for col in ("ITA", "launched_total", "n_articles_total", "n_ukrainian_russian_attack_direct"):
        if col in master.columns:
            miss = master[col].isna().mean() * 100
            print(f"  {col:50s}  {miss:5.1f}% missing")
    print(f"  {'waerlst_missing=1 count':50s}  {int(master['waerlst_missing'].sum()):5d} / {len(master)}")
    print(f"  {'is_weekend=1 count':50s}  {int(master['is_weekend'].sum()):5d} / {len(master)}")
    print(f"  {'is_holiday=1 count':50s}  {int(master['is_holiday'].sum()):5d} / {len(master)}")

    if args.no_features:
        print("\nPhase 5B complete (features skipped) ✓")
        return 0

    # ── Phase 5C — Feature engineering ────────────────────────────────────
    print("\n" + "=" * 60)
    print("Phase 5C — Building feature_matrix.parquet")
    print("=" * 60)

    feat_path = Path(paths["processed_files"]["feature_matrix"])
    feat = master.copy()
    feat = add_financial_features(feat)
    print(f"  + financial:  {feat.shape}")
    feat = add_attack_features(feat)
    print(f"  + attack:     {feat.shape}")
    feat = add_news_features(feat)
    print(f"  + news:       {feat.shape}")
    feat = add_calendar_features(feat)
    print(f"  + calendar:   {feat.shape}")

    print(f"\nWriting {feat_path} …")
    feat.to_parquet(feat_path, index=False)

    # Quick summary of key engineered features.
    print("\nFeature coverage in modeling window (2022-09-29+):")
    win = feat[feat["date"] >= "2022-09-29"]
    print(f"  modeling window rows: {len(win)}")
    for col in (
        "vol_5d",
        "vol_20d",
        "attack_surprise_total_7d",
        "attack_surprise_total_30d",
        "attack_surprise_total_90d",
        "n_ukrainian_share",
        "n_ukrainian_log",
        "n_ukrainian_z30",
        "days_since_invasion",
        "vix_crisis",
    ):
        if col in feat.columns:
            nn = win[col].notna().sum()
            print(f"  {col:36s}  {nn:5d} non-null / {len(win)} ({100*nn/len(win):.1f}%)")

    print("\nPhase 5B + 5C complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
