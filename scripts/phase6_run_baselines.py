#!/usr/bin/env python3
"""Phase 6 — Econometric baselines (first-milestone OOS forecast table).

Runs the full Phase 6 horse race:

- 4 return baselines (HistoricalMean, AR1, OLS, Ridge)
- 5 information sets (F, P, N, PN, PNG)
- 2 targets (r_ITA primary, r_WAERLST_recon secondary)
- 2 horizons (1-day, 5-day)
- 3 GARCH-family volatility baselines (GARCH, GJR_GARCH, EGARCH)

The engine enforces a strict no-leakage, expanding-window OOS design with
a refit cadence (default 20 trading days) and writes:

- ``outputs/tables/phase6_benchmark.csv``         — return-models table
- ``outputs/tables/phase6_volatility_benchmark.csv`` — GARCH table
- ``outputs/tables/phase6_info_set_cardinality.csv``  — info-set sizes
- ``outputs/figures/fig14_oos_forecast_vs_realized.png``
- ``outputs/figures/fig15_loss_by_info_set.png``
- ``outputs/figures/fig16_garch_vol_diagnostic.png``

Usage
-----
    python scripts/phase6_run_baselines.py [--paths-yaml CONFIG] [--quick]
                                          [--refit-every N]
                                          [--info-sets F,P,N,PN,PNG]
                                          [--targets r_ITA,r_WAERLST_recon]
                                          [--horizons 1,5]
                                          [--out-suffix _TAG]
                                          [--audit-leakage]

The ``--quick`` flag runs on the last 60 OOS days with ``--refit-every 5``
(useful for CI / dev smoke tests).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.build_model_matrix import build_model_matrix
from src.features.merge import load_paths_config
from src.models.expanding_window import assert_no_future_data
from src.models.horse_race import (
    run_horse_race,
    save_benchmark_csvs,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("phase6")


# ── Figure helpers ─────────────────────────────────────────────────────────


def _fig14_forecast_vs_realized(
    predictions: pd.DataFrame,
    out_path: Path,
    target: str = "r_ITA",
    horizon: int = 1,
) -> Path:
    """Time-series plot: realized vs OLS predictions under F, PN, PNG.

    4 panels: realized (top), F OLS, PN OLS, PNG OLS.
    """
    sel = predictions[
        (predictions["target"] == target)
        & (predictions["horizon"] == horizon)
        & (predictions["model"] == "ols")
        & (predictions["info_set"].isin(["F", "PN", "PNG"]))
    ].copy()
    realized = (
        predictions[
            (predictions["target"] == target)
            & (predictions["horizon"] == horizon)
            & (predictions["model"] == "ols")
        ][["date", "realized"]]
        .drop_duplicates(subset="date")
        .sort_values("date")
    )
    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(realized["date"], realized["realized"],
                 color="black", lw=0.6, alpha=0.8)
    axes[0].axhline(0, color="grey", lw=0.5, ls="--")
    axes[0].set_title(f"Realized {target} (horizon={horizon})")
    axes[0].set_ylabel(f"{target} (%)")
    axes[0].grid(True, alpha=0.3)
    colors = {"F": "steelblue", "PN": "seagreen", "PNG": "darkorange"}
    for ax, set_name in zip(axes[1:], ["F", "PN", "PNG"]):
        sub = sel[sel["info_set"] == set_name].sort_values("date")
        ax.plot(sub["date"], sub["prediction"], color=colors[set_name],
                lw=0.6, alpha=0.8)
        ax.axhline(0, color="grey", lw=0.5, ls="--")
        ax.set_title(f"OLS prediction — info set {set_name}")
        ax.set_ylabel("Prediction (%)")
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Date")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def _fig15_loss_by_info_set(
    benchmark: pd.DataFrame,
    out_path: Path,
    target: str = "r_ITA",
    horizon: int = 1,
) -> Path:
    """Grouped bar chart of MAE, RMSE, dir-acc by info set for OLS.

    One panel per metric, with one bar per info set.
    """
    sel = benchmark[
        (benchmark["target"] == target)
        & (benchmark["horizon"] == horizon)
        & (benchmark["model"].isin(["ols", "ridge", "historical_mean"]))
    ].copy()
    if sel.empty:
        logger.warning("fig15: no OLS/Ridge/HM rows for %s h=%d", target, horizon)
        return out_path
    info_sets = ["F", "P", "N", "PN", "PNG"]
    models = ["historical_mean", "ols", "ridge"]
    metrics = ["MAE", "RMSE", "dir_acc"]
    titles = {
        "MAE": "Mean Absolute Error (lower = better)",
        "RMSE": "Root Mean Squared Error (lower = better)",
        "dir_acc": "Directional Accuracy (higher = better)",
    }
    model_colors = {
        "historical_mean": "seagreen",
        "ols": "steelblue",
        "ridge": "firebrick",
    }
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    width = 0.25
    x = np.arange(len(info_sets))
    for ax, metric in zip(axes, metrics):
        for j, m in enumerate(models):
            sub = sel[(sel["model"] == m)].set_index("info_set").reindex(info_sets)
            vals = sub[metric].astype(float).values
            offset = (j - 1) * width
            bars = ax.bar(x + offset, vals, width,
                          color=model_colors[m], edgecolor="white",
                          alpha=0.9, label=m)
            for i, v in enumerate(vals):
                if np.isfinite(v):
                    ax.text(i + offset, v, f"{v:.2f}",
                            ha="center", va="bottom", fontsize=6)
        ax.set_xticks(x)
        ax.set_xticklabels(info_sets)
        ax.set_title(titles[metric])
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.3, axis="y")
        if metric == "dir_acc":
            ax.set_ylim(0, 1)
        ax.legend(fontsize=8, loc="best")
    fig.suptitle(
        f"Return-forecast loss by information set — {target}, horizon={horizon}",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def _fig16_garch_vol_diagnostic(
    predictions: pd.DataFrame,
    out_path: Path,
    target: str = "r_ITA",
) -> Path:
    """GARCH(1,1) conditional variance vs realized variance, h=1 and h=5.

    2 panels (h=1 and h=5), each showing the model's σ² forecast (constant
    within each refit fold) against the realized variance target.
    """
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax, h in zip(axes, (1, 5)):
        sub = predictions[
            (predictions["target"] == target)
            & (predictions["horizon"] == h)
            & (predictions["model"] == "garch")
        ].sort_values("date")
        if sub.empty:
            ax.set_title(f"horizon={h} — no GARCH rows")
            continue
        ax.plot(sub["date"], sub["realized"], color="black", lw=0.5,
                alpha=0.7, label="realized variance")
        ax.plot(sub["date"], sub["prediction"], color="firebrick", lw=0.8,
                alpha=0.8, label="GARCH(1,1) forecast")
        ax.set_title(f"GARCH(1,1) vs realized variance — {target}, h={h}")
        ax.set_ylabel("Variance (%²)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Date")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# ── Main entry point ───────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml", default="config/paths.yaml",
        help="Path to the paths config (default: config/paths.yaml).",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Smoke-test mode: last 60 OOS days, refit_every=5.",
    )
    parser.add_argument(
        "--refit-every", type=int, default=20,
        help="Refit cadence in trading days (default 20).",
    )
    parser.add_argument(
        "--info-sets", default="F,P,N,PN,PNG",
        help="Comma-separated list of info sets (default F,P,N,PN,PNG).",
    )
    parser.add_argument(
        "--targets", default="r_ITA,r_WAERLST_recon",
        help="Comma-separated list of source targets.",
    )
    parser.add_argument(
        "--horizons", default="1,5",
        help="Comma-separated list of forecast horizons.",
    )
    parser.add_argument(
        "--out-suffix", default="",
        help="Optional suffix for output files (e.g. _quick).",
    )
    parser.add_argument(
        "--audit-leakage", action="store_true",
        help="Run the strict no-leakage check before training and exit if it fails.",
    )
    parser.add_argument(
        "--min-train-obs", type=int, default=500,
        help="Minimum training observations required (default 500).",
    )
    args = parser.parse_args()

    print("Phase 6 — Econometric baselines (first-milestone OOS forecast table)")
    print("=" * 70)

    paths = load_paths_config(args.paths_yaml)
    mm_path = Path(paths["processed_files"]["model_matrix"])
    if not mm_path.exists():
        print(f"ERROR: {mm_path} not found. Run scripts/phase5_build_model_matrix.py first.")
        return 1

    fig_dir = Path(paths["outputs"]["figures"])
    tab_dir = Path(paths["outputs"]["tables"])
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    info_sets = tuple(s.strip() for s in args.info_sets.split(",") if s.strip())
    targets = tuple(s.strip() for s in args.targets.split(",") if s.strip())
    horizons = tuple(int(s.strip()) for s in args.horizons.split(",") if s.strip())

    print(f"Loading {mm_path} …")
    mm = pd.read_parquet(mm_path)
    print(f"  model_matrix: {mm.shape}  (columns: {mm.shape[1]})")
    print(f"  date range: {mm['date'].min().date()} → {mm['date'].max().date()}")

    if args.audit_leakage:
        from src.features.build_model_matrix import make_train_test_split
        train_mask, test_mask, split_date = make_train_test_split(
            mm, test_fraction=0.25, min_train_obs=500,
        )
        try:
            assert_no_future_data(
                mm["date"][train_mask], mm["date"][test_mask]
            )
        except ValueError as e:
            print(f"Leakage audit FAIL: {e}")
            return 1
        print(f"Leakage audit PASS (split at {split_date.date()})")
        return 0

    # ── Run the horse race ────────────────────────────────────────────────
    suffix = args.out_suffix
    t0 = time.time()
    out = run_horse_race(
        model_matrix=mm,
        horizons=horizons,
        targets=targets,
        info_sets=info_sets,
        refit_every=(5 if args.quick else args.refit_every),
        min_train_obs=args.min_train_obs,
        test_fraction=0.25,
        quick=args.quick,
    )
    elapsed = time.time() - t0
    print(f"Horse race done in {elapsed:.1f}s")
    print(f"  predictions: {len(out['predictions']):,} rows")
    print(f"  benchmark:   {len(out['benchmark'])} rows  (return models)")
    print(f"  vol_benchmark: {len(out['vol_benchmark'])} rows  (GARCH)")

    # ── Save CSVs ─────────────────────────────────────────────────────────
    written = save_benchmark_csvs(
        out_dir=tab_dir,
        benchmark=out["benchmark"],
        vol_benchmark=out["vol_benchmark"],
        info_set_card=out["info_set_cardinality"],
        suffix=suffix,
    )
    for label, p in written.items():
        print(f"  {label}: {p}  ({p.stat().st_size} bytes)")

    # ── Save predictions parquet (useful for downstream phases) ───────────
    pred_path = tab_dir / f"phase6_predictions{suffix}.parquet"
    out["predictions"].to_parquet(pred_path, index=False)
    print(f"  predictions parquet: {pred_path}")

    # ── Figures ───────────────────────────────────────────────────────────
    if "r_ITA" in targets:
        fig14_path = fig_dir / f"fig14_oos_forecast_vs_realized{suffix}.png"
        _fig14_forecast_vs_realized(
            out["predictions"], fig14_path, target="r_ITA", horizon=1,
        )
        print(f"  figure 14: {fig14_path}")

        fig15_path = fig_dir / f"fig15_loss_by_info_set{suffix}.png"
        _fig15_loss_by_info_set(
            out["benchmark"], fig15_path, target="r_ITA", horizon=1,
        )
        print(f"  figure 15: {fig15_path}")

        fig16_path = fig_dir / f"fig16_garch_vol_diagnostic{suffix}.png"
        _fig16_garch_vol_diagnostic(
            out["predictions"], fig16_path, target="r_ITA",
        )
        print(f"  figure 16: {fig16_path}")

    print("\nPhase 6 baseline run complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
