#!/usr/bin/env python3
"""Phase 7.3 — Time-series CV grid search for XGBoost hyperparameters.

Runs the TS-CV grid search (per decision_log 2026-07-01) and writes
the best (hyperparams) per (info_set, horizon, target) to a CSV.

Usage
-----
    # On local
    python scripts/phase7_tune.py --data-path data/processed/model_matrix.parquet \\
        --output outputs/model_objects/xgb_best_params.csv

    # On Colab Pro
    DRIVE=/content/drive/MyDrive/WarSignalsThesis_Data
    python scripts/phase7_tune.py \\
        --data-path $DRIVE/data/processed/model_matrix.parquet \\
        --output $DRIVE/outputs/model_objects/xgb_best_params.csv

The default param grid is taken from ``config/model_config.yaml`` and
contains 216 combinations × 3 CV folds × 5 info sets × 2 horizons =
~6,480 XGBoost fits (~110 min on Colab Pro CPU).

After this script finishes, the next step is
``scripts/phase7_run_ml.py --tuned-params <output>``.
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
from src.models.ml_tuning import save_tuning_results, tune_per_info_set


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("phase7_tune")


def _resolve_data_path(path_str: str) -> Path:
    """Resolve a data path; raises if the file doesn't exist."""
    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(
            f"Model matrix not found at: {p}\n"
            f"Did you push it to Drive? (Phase 7.0 of the plan)\n"
            f"  rclone copy --update --progress data/processed/ "
            f"gdrive:WarSignalsThesis_Data/data/processed/"
        )
    return p


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 7.3 — TS-CV grid search for XGBoost hyperparameters. "
            "Writes best_params CSV per (info_set, horizon, target)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-path",
        default="data/processed/model_matrix.parquet",
        help="Path to model_matrix.parquet "
        "(default: %(default)s; Colab: pass Drive path)",
    )
    parser.add_argument(
        "--output",
        default="outputs/model_objects/xgb_best_params.csv",
        help="Path to write best_params CSV "
        "(default: %(default)s; Colab: pass Drive path)",
    )
    parser.add_argument(
        "--info-sets",
        default="F,P,N,PN,PNG",
        help="Comma-separated info sets (default: %(default)s)",
    )
    parser.add_argument(
        "--horizons",
        default="1,5",
        help="Comma-separated horizons (default: %(default)s)",
    )
    parser.add_argument(
        "--targets",
        default="r_ITA,r_WAERLST_recon",
        help="Comma-separated targets (default: %(default)s)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke test: use a smaller grid (4 configs × 2 folds)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed (default: %(default)s)",
    )
    args = parser.parse_args()

    # Resolve data path
    mm_path = _resolve_data_path(args.data_path)
    logger.info("Loading model matrix from %s", mm_path)
    mm = _load_minimal_mm(mm_path)
    if "info_sets" not in mm.attrs or not mm.attrs["info_sets"]:
        mm.attrs["info_sets"] = build_info_sets(mm)

    # Parse args
    info_sets = tuple(s.strip() for s in args.info_sets.split(",") if s.strip())
    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    targets = tuple(t.strip() for t in args.targets.split(",") if t.strip())

    if args.quick:
        # Smaller grid for CI / dev smoke tests
        param_grid = {
            "max_depth": [3, 5],
            "learning_rate": [0.05, 0.1],
            "n_estimators": [200, 500],
            "min_child_weight": [5],
            "reg_alpha": [0.0],
            "reg_lambda": [1.0],
        }
        n_splits = 2
        logger.info("Quick mode: 8 configs × %d folds", n_splits)
    else:
        # Full grid from model_config.yaml
        param_grid = {
            "max_depth": [3, 5],
            "learning_rate": [0.03, 0.05, 0.1],
            "n_estimators": [200, 500, 1000],
            "min_child_weight": [5, 20],
            "reg_alpha": [0.0, 0.1],
            "reg_lambda": [1.0, 5.0],
        }
        n_splits = 3

    n_configs = 1
    for v in param_grid.values():
        n_configs *= len(v)
    total_fits = n_configs * n_splits * len(info_sets) * len(horizons)
    logger.info(
        "Grid: %d configs × %d folds × %d info sets × %d horizons = %d fits",
        n_configs, n_splits, len(info_sets), len(horizons), total_fits,
    )

    t0 = time.time()
    results = tune_per_info_set(
        model_matrix=mm,
        info_sets=info_sets,
        horizons=horizons,
        targets=targets,
        param_grid=param_grid,
        n_splits=n_splits,
        embargo=5,
        min_train_size=200,
        random_state=args.random_seed,
    )
    elapsed = time.time() - t0
    logger.info("Tuning done in %.1f min", elapsed / 60)

    # Save via the official helper
    out_path = save_tuning_results(results, Path(args.output))
    return 0


def _load_minimal_mm(path: Path) -> pd.DataFrame:
    """Load a parquet file as a DataFrame (no model-matrix build)."""
    df = pd.read_parquet(path)
    return df


if __name__ == "__main__":
    sys.exit(main())
