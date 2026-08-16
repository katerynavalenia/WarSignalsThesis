#!/usr/bin/env python3
"""Phase 5E — Descriptive statistics on the model matrix.

Usage
-----
    python scripts/phase5_descriptive_stats.py [--paths-yaml CONFIG]

Produces
--------
    outputs/tables/descriptive_stats.csv
    outputs/figures/fig11_target_distribution.png
    outputs/figures/fig12_correlation_heatmap.png
    outputs/figures/fig13_feature_distributions.png
    docs/phase5_descriptive_stats.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.build_model_matrix import build_model_matrix
from src.features.merge import load_paths_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml",
        default="config/paths.yaml",
        help="Path to the local paths config (default: config/paths.yaml).",
    )
    args = parser.parse_args()

    print("Phase 5E — Descriptive statistics")
    print("=" * 60)

    paths = load_paths_config(args.paths_yaml)
    feat_path = Path(paths["processed_files"]["feature_matrix"])
    mm_path = Path(paths["processed_files"]["model_matrix"])

    if not mm_path.exists():
        print(f"ERROR: {mm_path} not found. Run phase5_build_model_matrix.py first.")
        return 1

    fig_dir = Path(paths["outputs"]["figures"])
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir = Path(paths["outputs"]["tables"])
    tab_dir.mkdir(parents=True, exist_ok=True)
    doc_path = Path("docs/phase5_descriptive_stats.md")

    print(f"Loading {feat_path} …")
    feat = pd.read_parquet(feat_path)
    print(f"  feature_matrix: {feat.shape}")

    print("Building model matrix …")
    mm = build_model_matrix(feat)
    primary = mm.attrs["primary_target"]
    print(f"  model_matrix: {mm.shape}  ({mm['date'].min().date()} → {mm['date'].max().date()})")

    # ── Descriptive statistics table ────────────────────────────────────────
    target = mm[primary]
    print(f"\nTarget '{primary}': mean={target.mean():.4f}, std={target.std():.4f}, "
          f"min={target.min():.4f}, max={target.max():.4f}")

    # Per-column summary.
    rows = []
    for c in mm.columns:
        if c == "date":
            continue
        s = mm[c]
        nn = int(s.notna().sum())
        if nn == 0:
            continue
        rows.append({
            "column": c,
            "n": nn,
            "mean": s.mean(),
            "std": s.std(),
            "min": s.min(),
            "q25": s.quantile(0.25),
            "median": s.median(),
            "q75": s.quantile(0.75),
            "max": s.max(),
            "skew": s.skew(),
            "kurtosis": s.kurtosis(),
        })
    stats_df = pd.DataFrame(rows)
    stats_csv = tab_dir / "descriptive_stats.csv"
    stats_df.to_csv(stats_csv, index=False)
    print(f"Writing {stats_csv} ({len(stats_df)} rows) …")

    # ── Figure 11: target distribution ──────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(target, bins=60, color="steelblue", edgecolor="white", alpha=0.85)
    axes[0].axvline(0, color="black", lw=0.8)
    axes[0].set_xlabel(f"{primary} (%)")
    axes[0].set_ylabel("Count")
    axes[0].set_title(f"Target distribution (n={len(target):,})")
    axes[0].grid(True, alpha=0.3)
    axes[1].hist(target, bins=60, color="steelblue", edgecolor="white", alpha=0.85)
    axes[1].axvline(0, color="black", lw=0.8)
    axes[1].set_yscale("log")
    axes[1].set_xlabel(f"{primary} (%)")
    axes[1].set_ylabel("Count (log)")
    axes[1].set_title("Target distribution (log y)")
    axes[1].grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    fig11 = fig_dir / "fig11_target_distribution.png"
    fig.savefig(fig11, dpi=120)
    plt.close(fig)
    print(f"Writing {fig11} …")

    # ── Figure 12: correlation heatmap of top features vs target ───────────
    # Show the top |ρ| features with the target, plus a clustered heatmap of
    # the most-correlated 25 features.
    numeric_cols = [c for c in mm.columns
                    if c != "date" and mm[c].dtype.kind in "biufc"
                    and mm[c].notna().sum() > 30]
    corrs_with_target = (
        mm[numeric_cols].corrwith(target).abs().sort_values(ascending=False)
    )
    top_25 = corrs_with_target.head(25).index.tolist()

    corr_mat = mm[top_25].corr().values
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(corr_mat, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(len(top_25)))
    ax.set_yticks(range(len(top_25)))
    # Shorten tick labels for readability
    short = [c[:30] + "…" if len(c) > 30 else c for c in top_25]
    ax.set_xticklabels(short, rotation=90, fontsize=7)
    ax.set_yticklabels(short, fontsize=7)
    ax.set_title("Top-25 features by |ρ| with target — pair correlations")
    fig.colorbar(im, ax=ax, label="Pearson ρ")
    fig.tight_layout()
    fig12 = fig_dir / "fig12_correlation_heatmap.png"
    fig.savefig(fig12, dpi=120)
    plt.close(fig)
    print(f"Writing {fig12} …")

    # ── Figure 13: distributions of key features ────────────────────────────
    key_features = [
        "r_WAERLST_lag1", "r_ITA_lag1", "vol_5d_lag1", "vol_20d_lag1",
        "launched_total_lag1", "attack_surprise_total_7d_lag1",
        "n_articles_total_lag1", "n_ukrainian_share_lag1",
        "VIX_lag1", "days_since_invasion",
    ]
    key_features = [c for c in key_features if c in mm.columns]
    n_cols = 3
    n_rows = (len(key_features) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(11, 2.6 * n_rows))
    axes = np.atleast_1d(axes).flatten()
    for ax, c in zip(axes, key_features):
        s = mm[c].dropna()
        ax.hist(s, bins=40, color="seagreen", edgecolor="white", alpha=0.85)
        ax.set_title(c, fontsize=10)
        ax.grid(True, alpha=0.3)
    for ax in axes[len(key_features):]:
        ax.set_visible(False)
    fig.tight_layout()
    fig13 = fig_dir / "fig13_feature_distributions.png"
    fig.savefig(fig13, dpi=120)
    plt.close(fig)
    print(f"Writing {fig13} …")

    # ── Markdown report ────────────────────────────────────────────────────
    with open(doc_path, "w") as f:
        f.write("# Phase 5 descriptive statistics\n\n")
        f.write(f"Date: 2026-06-30. Auto-generated by `scripts/phase5_descriptive_stats.py`.\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Modeling window: **{mm['date'].min().date()} → {mm['date'].max().date()}** ")
        f.write(f"({len(mm):,} rows)\n")
        f.write(f"- Total columns: **{mm.shape[1]}**\n")
        f.write(f"- Primary target `{primary}`: mean **{target.mean():.4f}%**, "
                f"std **{target.std():.4f}%**, "
                f"min **{target.min():.4f}%**, max **{target.max():.4f}%**\n")
        for rob_col, rob_label in (
            ("target_r_BSHIELDT_t1", "Robustness target (European, war-exposed)"),
            ("target_r_ITA_t1", "Robustness target (US, optional)"),
        ):
            if rob_col in mm.columns:
                f.write(f"- {rob_label} `{rob_col}`: "
                        f"mean **{mm[rob_col].mean():.4f}%**, "
                        f"std **{mm[rob_col].std():.4f}%**\n")
        f.write("\n")
        f.write("## Top-15 features by |ρ| with primary target\n\n")
        f.write("| Feature | |ρ| with target |\n|---|---|\n")
        for c, rho in corrs_with_target.head(15).items():
            f.write(f"| `{c}` | {rho:.3f} |\n")
        f.write("\n## Per-information-set cardinality\n\n")
        f.write("| Information set | n_features |\n|---|---|\n")
        for s, cs in mm.attrs["info_sets"].items():
            f.write(f"| {s} | {len(cs)} |\n")
        f.write("\n## Figures\n\n")
        f.write("- `outputs/figures/fig11_target_distribution.png` — target histogram\n")
        f.write("- `outputs/figures/fig12_correlation_heatmap.png` — top-25 feature correlations\n")
        f.write("- `outputs/figures/fig13_feature_distributions.png` — key feature histograms\n")
    print(f"Writing {doc_path} …")

    print("\nPhase 5E descriptive stats complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
