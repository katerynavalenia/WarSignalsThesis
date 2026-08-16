#!/usr/bin/env python3
"""Phase 7 — Machine-learning horse race (XGBoost returns + GARCH-X vol).

Runs the full Phase 7 benchmark:

- 4 econometric return baselines (HM, AR1, OLS, Ridge) on 5 info sets
- 1 XGBoost return model on 5 info sets (tuned hyperparams from
  ``--tuned-params`` CSV or default values from model_config.yaml)
- 3 GARCH-family volatility baselines (GARCH, GJR_GARCH, EGARCH)
- 3 GARCH-X variants with exogenous regressors in the mean equation

Identical test dates and evaluation metrics to Phase 6
(per decision_log 2026-07-01 and Master Plan §11).

Usage
-----
    # On local (with default model matrix)
    python scripts/phase7_run_ml.py \\
        --data-path data/processed/model_matrix.parquet \\
        --output-dir outputs/tables/ \\
        --tuned-params outputs/model_objects/xgb_best_params.csv

    # On Colab Pro (data from Drive, outputs to Drive)
    DRIVE=/content/drive/MyDrive/WarSignalsThesis_Data
    python scripts/phase7_run_ml.py \\
        --data-path $DRIVE/data/processed/model_matrix.parquet \\
        --output-dir $DRIVE/outputs/tables/ \\
        --tuned-params $DRIVE/outputs/model_objects/xgb_best_params.csv

The CLI is a thin wrapper over :func:`src.models.horse_race.run_phase7`.
Outputs:
    ``<output-dir>/phase7_benchmark.csv``
    ``<output-dir>/phase7_volatility_benchmark.csv``
    ``<output-dir>/phase7_info_set_cardinality.csv``
    ``<output-dir>/phase7_predictions.parquet``
    ``<output-dir>/../model_objects/shap_*.npy``  (per-fold SHAP)
    ``<output-dir>/../figures/fig17_shap_summary_*.png``
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.build_model_matrix import build_info_sets
from src.models.horse_race import (
    build_benchmark_tables,
    run_phase7,
    save_benchmark_csvs,
)
from src.models.ml_explain import plot_all_shap_summaries


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("phase7_run_ml")


def _load_model_matrix(path: Path) -> pd.DataFrame:
    """Load model matrix from parquet, reconstructing info_sets if needed."""
    df = pd.read_parquet(path)
    if "info_sets" not in df.attrs or not df.attrs["info_sets"]:
        logger.info("Reconstructing info_sets (not in attrs)")
        df.attrs["info_sets"] = build_info_sets(df)
    return df


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 7 — ML horse race (XGBoost + GARCH-X) with strict "
            "out-of-sample evaluation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-path",
        default="data/processed/model_matrix.parquet",
        help="Path to model_matrix.parquet (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/tables/",
        help="Directory for output CSVs/parquets (default: %(default)s)",
    )
    parser.add_argument(
        "--tuned-params",
        default=None,
        help="Path to xgb_best_params.csv from scripts/phase7_tune.py "
        "(if not given, defaults from model_config.yaml are used)",
    )
    parser.add_argument(
        "--info-sets",
        default="F,P,N,PN,PNG",
        help="Comma-separated info sets (default: %(default)s)",
    )
    parser.add_argument(
        "--targets",
        default="r_WAERLST,r_BSHIELDT,r_ITA",
        help="Comma-separated targets (default: %(default)s)",
    )
    parser.add_argument(
        "--horizons",
        default="1,5",
        help="Comma-separated horizons (default: %(default)s)",
    )
    parser.add_argument(
        "--garch-x-info-set",
        default="F",
        help="Info set used as exogenous regressors for GARCH-X "
        "(default: %(default)s, 'none' to skip GARCH-X)",
    )
    parser.add_argument(
        "--no-garch-x",
        action="store_true",
        help="Skip GARCH-X variants (returns only)",
    )
    parser.add_argument(
        "--no-econometric-baselines",
        action="store_true",
        help="Skip the 4 Phase 6 return baselines (XGBoost only)",
    )
    parser.add_argument(
        "--no-shap",
        action="store_true",
        help="Skip SHAP computation and figures",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke test: last 60 OOS days, refit_every=5",
    )
    parser.add_argument(
        "--refit-every",
        type=int,
        default=20,
        help="Refit cadence in trading days (default: %(default)s)",
    )
    parser.add_argument(
        "--out-suffix",
        default="",
        help="Suffix appended to output filenames (default: empty)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed (default: %(default)s)",
    )
    args = parser.parse_args()

    # Load model matrix
    mm_path = Path(args.data_path)
    if not mm_path.exists():
        raise FileNotFoundError(
            f"Model matrix not found at: {mm_path}\n"
            f"Phase 7.0 of the plan requires it to be on Drive (or local). "
            f"Local: rclone copy --update --progress data/processed/ "
            f"gdrive:WarSignalsThesis_Data/data/processed/"
        )
    logger.info("Loading model matrix from %s", mm_path)
    mm = _load_model_matrix(mm_path)
    logger.info("Model matrix: %d rows × %d cols", *mm.shape)

    # Load tuned params (if provided)
    tuned_params = None
    if args.tuned_params:
        tp_path = Path(args.tuned_params)
        if not tp_path.exists():
            raise FileNotFoundError(
                f"Tuned params not found at: {tp_path}\n"
                f"Run scripts/phase7_tune.py first, or omit --tuned-params."
            )
        logger.info("Loading tuned params from %s", tp_path)
        tp_df = pd.read_csv(tp_path)
        tuned_params = {
            (row["info_set"], int(row["horizon"]), row["target"]): {
                k: row[k] for k in (
                    "max_depth", "learning_rate", "n_estimators",
                    "min_child_weight", "reg_alpha", "reg_lambda",
                ) if k in row
            }
            for _, row in tp_df.iterrows()
        }
        logger.info("Loaded %d (info_set, horizon, target) → params entries",
                    len(tuned_params))

    # Parse args
    info_sets = tuple(s.strip() for s in args.info_sets.split(",") if s.strip())
    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    targets = tuple(t.strip() for t in args.targets.split(",") if t.strip())
    garch_x_info_set = None if (
        args.no_garch_x or args.garch_x_info_set.lower() == "none"
    ) else args.garch_x_info_set

    # Run the horse race
    t0 = time.time()
    out = run_phase7(
        model_matrix=mm,
        horizons=horizons,
        targets=targets,
        info_sets=info_sets,
        tuned_params=tuned_params,
        include_garch_x=(garch_x_info_set is not None),
        garch_x_info_set=(garch_x_info_set or "F"),
        include_econometric_baselines=(not args.no_econometric_baselines),
        refit_every=args.refit_every,
        quick=args.quick,
        random_seed=args.random_seed,
        collect_shap=(not args.no_shap),
    )
    elapsed = time.time() - t0
    logger.info("Phase 7 horse race done in %.1f min", elapsed / 60)

    # Save CSVs
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    save_benchmark_csvs(
        out_dir=out_dir,
        benchmark=out["benchmark"],
        vol_benchmark=out["vol_benchmark"],
        info_set_card=out["info_set_cardinality"],
        suffix=args.out_suffix,
        prefix="phase7",
    )
    # Also save long-form predictions separately
    preds_path = out_dir / f"phase7_predictions{args.out_suffix}.parquet"
    out["predictions"].to_parquet(preds_path, index=False)
    logger.info("Wrote predictions to %s", preds_path)

    # SHAP figures
    if not args.no_shap and out.get("shap_recorder") is not None:
        sr = out["shap_recorder"]
        n_with_shap = len(sr.shap_per_fold)
        if n_with_shap == 0:
            logger.warning(
                "No SHAP values were recorded (XGBoost may have failed to fit)."
            )
        else:
            logger.info("Recorded SHAP for %d (info_set, horizon, target) groups",
                        n_with_shap)
            fig_dir = out_dir.parent / "figures"
            fig_dir.mkdir(parents=True, exist_ok=True)
            try:
                plot_all_shap_summaries(
                    sr,
                    out_dir=fig_dir,
                    max_features=20,
                )
            except Exception as exc:  # defensive — don't fail the run
                logger.warning("SHAP figure generation failed: %s", exc)

            # Also save raw SHAP values per (info_set, horizon, target)
            try:
                model_objects_dir = out_dir.parent / "model_objects"
                model_objects_dir.mkdir(parents=True, exist_ok=True)
                sr.save_npz(
                    model_objects_dir / f"shap_phase7{args.out_suffix}.npz"
                )
                logger.info(
                    "Saved raw SHAP arrays to %s",
                    model_objects_dir / f"shap_phase7{args.out_suffix}.npz",
                )
            except Exception as exc:
                logger.warning("SHAP save failed: %s", exc)

    # Summary
    logger.info("=" * 60)
    logger.info("Phase 7 done. Outputs:")
    logger.info("  %s", out_dir / f"phase7_benchmark{args.out_suffix}.csv")
    logger.info("  %s", out_dir / f"phase7_volatility_benchmark{args.out_suffix}.csv")
    logger.info("  %s", out_dir / f"phase7_info_set_cardinality{args.out_suffix}.csv")
    logger.info("  %s", out_dir / f"phase7_predictions{args.out_suffix}.parquet")
    logger.info("Elapsed: %.1f min", elapsed / 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
