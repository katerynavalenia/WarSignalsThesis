"""Time-series CV grid search for XGBoost (Phase 7.3).

Per Master Plan §10.4 + §11.2:

- **Time-series CV** is the only valid way to tune a forecasting model.
  We use **expanding-window splits** with an **embargo gap** of ``embargo``
  trading days between the train end and the validation start (prevents
  look-ahead from rolling / lagged features that span the boundary).
- **Tuning happens once, before the OOS run** (per decision_log 2026-07-01).
  The best (hyperparams) per (info_set, horizon) is saved to a CSV and
  reused for all 18 OOS refits in the expanding-window engine.
- **Grid is exhaustive** (no random search / Bayesian). With 6
  hyperparameters and a ~200-cell grid, total compute is bounded
  (~6,480 fits for the headline run).

The module is **driver-only** — it does not implement the XGBoost model
itself; it uses :class:`src.models.ml.XGBoostForecaster` for each fit.

Usage
-----
::

    from src.models.ml_tuning import tune_per_info_set, save_tuning_results

    results = tune_per_info_set(
        model_matrix=mm,
        info_sets=("F", "P", "N", "PN", "PNG"),
        horizons=(1, 5),
        targets=("r_WAERLST", "r_BSHIELDT", "r_ITA"),
        param_grid=param_grid,
        n_splits=3,
        embargo=5,
    )
    save_tuning_results(results, Path("outputs/model_objects/xgb_best_params.csv"))
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.models.baselines import _BaseForecaster
from src.models.ml import XGBoostForecaster


logger = logging.getLogger(__name__)


__all__ = [
    "TuningResult",
    "time_series_cv_splits",
    "grid_search_xgb",
    "tune_per_info_set",
    "save_tuning_results",
    "load_tuning_results",
]


# ── Data class ──────────────────────────────────────────────────────────────


@dataclass
class TuningResult:
    """One row of the tuning output table.

    Attributes
    ----------
    info_set : str
        The information set name (F / P / N / PN / PNG).
    horizon : int
        Forecast horizon (1 or 5).
    target : str
        Target column name (``r_WAERLST`` primary, or ``r_BSHIELDT`` /
        ``r_ITA`` robustness; decision_log 2026-07-02).
    best_params : dict
        Best hyperparameter dict.
    mean_val_mae : float
        Mean MAE across the CV folds for the best config.
    n_folds : int
        Number of CV folds actually used (may be < n_splits if data is
        too short for the requested number of splits).
    n_train_rows : int
        Number of training rows used in the first fold.
    total_fits : int
        Total number of XGBoost fits executed.
    elapsed_sec : float
        Wall-clock time spent on this (info_set, horizon) pair.
    """
    info_set: str
    horizon: int
    target: str
    best_params: Dict[str, Any]
    mean_val_mae: float
    n_folds: int
    n_train_rows: int
    total_fits: int
    elapsed_sec: float
    # Optional: per-fold MAEs for diagnostics
    fold_maes: List[float] = field(default_factory=list)


# ── CV split helper ─────────────────────────────────────────────────────────


def time_series_cv_splits(
    n: int,
    n_splits: int = 3,
    embargo: int = 5,
    min_train_size: int = 200,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Return expanding-window time-series CV splits with embargo.

    The splits are (train_idx, val_idx) tuples. ``val_idx`` always lies
    strictly after the end of ``train_idx`` plus the embargo gap.

    For example, with ``n=1000, n_splits=3, embargo=5, min_train_size=200``:

    - Fold 1: train=[0:500], val=[505:670]
    - Fold 2: train=[0:670], val=[675:840]
    - Fold 3: train=[0:840], val=[845:1000]

    Parameters
    ----------
    n : int
        Total number of rows in the training data (i.e. rows 0..n_train
        of the model matrix).
    n_splits : int, default 3
        Number of CV folds. Final fold uses the remaining rows.
    embargo : int, default 5
        Trading-day gap between train end and val start. Prevents
        look-ahead from rolling / lagged features.
    min_train_size : int, default 200
        Minimum number of train rows in the FIRST fold. If the data is
        too short for ``n_splits`` folds with this constraint, the
        returned list will be shorter than ``n_splits``.

    Returns
    -------
    list of (np.ndarray, np.ndarray)
        Each tuple is (train_idx, val_idx) for one fold. Indices are
        0-based positions into the input data.
    """
    if n < 2 * min_train_size:
        # Not enough data; return a single split
        n_val = max(1, n // 5)
        train_end = n - n_val - embargo
        if train_end < min_train_size:
            return []
        return [(np.arange(0, train_end), np.arange(train_end + embargo, n))]

    # We divide the post-min-train data into (n_splits + 1) equal windows;
    # the last n_splits windows become val sets, with the train extending
    # up to the val start (minus embargo).
    n_val_target = max(1, (n - min_train_size) // (n_splits + 1))
    splits: List[Tuple[np.ndarray, np.ndarray]] = []
    train_end = min_train_size
    for i in range(n_splits):
        val_start = train_end + embargo
        val_end = val_start + n_val_target
        if val_end > n:
            val_end = n
        if val_end <= val_start:
            break
        train_idx = np.arange(0, train_end)
        val_idx = np.arange(val_start, val_end)
        splits.append((train_idx, val_idx))
        train_end = val_end  # expanding
    return splits


# ── Grid search ─────────────────────────────────────────────────────────────


def _param_product(param_grid: Dict[str, Sequence]) -> Iterable[Dict[str, Any]]:
    """Yield all combinations of param_grid values as dicts."""
    keys = list(param_grid.keys())
    value_lists = [list(param_grid[k]) for k in keys]
    for combo in product(*value_lists):
        yield dict(zip(keys, combo))


def grid_search_xgb(
    X: pd.DataFrame,
    y: pd.Series,
    param_grid: Dict[str, Sequence],
    cv_splits: List[Tuple[np.ndarray, np.ndarray]],
    val_fraction: float = 0.15,
    metric: str = "mae",
    random_state: int = 42,
    verbose: bool = False,
) -> Tuple[Dict[str, Any], float, List[float]]:
    """Exhaustive grid search over ``param_grid`` using ``cv_splits``.

    Parameters
    ----------
    X : pd.DataFrame
        Training feature matrix (rows = train period 0..n_train).
    y : pd.Series
        Training target (in percent).
    param_grid : dict
        ``{param_name: [value1, value2, ...]}``.
    cv_splits : list of (np.ndarray, np.ndarray)
        CV splits from :func:`time_series_cv_splits`.
    val_fraction : float, default 0.15
        Forwarded to ``XGBoostForecaster`` for early stopping.
    metric : str, default "mae"
        Evaluation metric. Currently only ``"mae"`` is supported
        (the XGBoost eval_metric is also ``"mae"`` by default).
    random_state : int, default 42
        Forwarded to ``XGBoostForecaster`` for reproducibility.
    verbose : bool, default False
        Print per-config progress.

    Returns
    -------
    (best_params, best_score, fold_scores) : tuple
        ``best_params`` is the param dict with the lowest mean MAE.
        ``best_score`` is the mean MAE across folds.
        ``fold_scores`` is the list of per-fold MAEs for the best config.
    """
    if not cv_splits:
        raise ValueError("cv_splits is empty — cannot run grid search")
    if metric != "mae":
        raise ValueError(f"unsupported metric {metric!r}; only 'mae' is implemented")

    n_configs = int(np.prod([len(v) for v in param_grid.values()]))
    logger.info(
        "grid_search_xgb: %d configs × %d folds = %d fits",
        n_configs, len(cv_splits), n_configs * len(cv_splits),
    )

    best_params: Optional[Dict[str, Any]] = None
    best_score = np.inf
    best_fold_scores: List[float] = []

    for i, params in enumerate(_param_product(param_grid), start=1):
        fold_maes: List[float] = []
        for fold_idx, (train_idx, val_idx) in enumerate(cv_splits):
            X_tr = X.iloc[train_idx]
            y_tr = y.iloc[train_idx] if hasattr(y, "iloc") else y[train_idx]
            X_va = X.iloc[val_idx]
            y_va = y.iloc[val_idx] if hasattr(y, "iloc") else y[val_idx]
            # XGBoost does its own early-stopping val split (val_fraction).
            # The CV val here is held out for the FINAL evaluation of the
            # config (i.e. we don't let XGBoost see it during fit).
            model = XGBoostForecaster(
                val_fraction=val_fraction,
                random_state=random_state,
                **params,
            )
            try:
                model.fit(X_tr, y_tr)
                preds = np.asarray(model.predict(X_va), dtype=float)
            except Exception as exc:  # pragma: no cover
                if verbose:
                    logger.warning("config %d fold %d failed: %s", i, fold_idx, exc)
                preds = np.full(len(y_va), np.nan)
            mask = np.isfinite(preds) & np.isfinite(np.asarray(y_va, dtype=float))
            if mask.sum() == 0:
                mae = np.nan
            else:
                mae = float(np.mean(np.abs(preds[mask] - np.asarray(y_va, dtype=float)[mask])))
            fold_maes.append(mae)
        mean_mae = float(np.nanmean(fold_maes)) if fold_maes else np.inf
        if verbose and (i % 25 == 0 or i == n_configs):
            logger.info("  [%d/%d] mean_val_mae=%.4f params=%s",
                        i, n_configs, mean_mae, params)
        if mean_mae < best_score:
            best_score = mean_mae
            best_params = dict(params)
            best_fold_scores = list(fold_maes)

    if best_params is None:
        # All configs failed
        raise RuntimeError("grid_search_xgb: all configs failed")
    return best_params, best_score, best_fold_scores


# ── Top-level: tune per (info_set, horizon) ─────────────────────────────────


def tune_per_info_set(
    model_matrix: pd.DataFrame,
    info_sets: Sequence[str] = ("F", "P", "N", "PN", "PNG"),
    horizons: Sequence[int] = (1, 5),
    targets: Sequence[str] = ("r_WAERLST", "r_BSHIELDT", "r_ITA"),
    param_grid: Optional[Dict[str, Sequence]] = None,
    n_splits: int = 3,
    embargo: int = 5,
    min_train_size: int = 200,
    val_fraction: float = 0.15,
    random_state: int = 42,
    train_end_row: Optional[int] = None,
    verbose: bool = True,
) -> List[TuningResult]:
    """Run the full grid search across all (info_set, horizon) pairs.

    For each pair we extract the training block (rows 0..train_end_row),
    select the info-set features, build a target Series, run the CV
    grid search, and return a :class:`TuningResult` per pair.

    Parameters
    ----------
    model_matrix : pd.DataFrame
        The model matrix (output of
        :func:`src.features.build_model_matrix.build_model_matrix`).
    info_sets : sequence of str
        The five info set names.
    horizons : sequence of int
        Forecast horizons.
    targets : sequence of str
        Target source names.
    param_grid : dict, optional
        ``{param_name: [value1, ...]}``. Defaults to a small grid.
    n_splits, embargo, min_train_size, val_fraction, random_state
        Forwarded to :func:`time_series_cv_splits` and the XGBoost
        model.
    train_end_row : int, optional
        Where the test split begins (i.e. where the OOS run starts).
        Defaults to ``int(len(mm) * 0.75)`` (matches ``test_fraction=0.25``).
    verbose : bool, default True
        Print progress.

    Returns
    -------
    list of :class:`TuningResult`
        One result per (info_set, horizon, target) triple.
    """
    if param_grid is None:
        param_grid = {
            "max_depth": [3, 5],
            "learning_rate": [0.03, 0.05, 0.1],
            "n_estimators": [200, 500, 1000],
            "min_child_weight": [5, 20],
            "reg_alpha": [0.0, 0.1],
            "reg_lambda": [1.0, 5.0],
        }

    if train_end_row is None:
        train_end_row = int(len(model_matrix) * 0.75)

    info_sets_map = model_matrix.attrs.get("info_sets", {})
    results: List[TuningResult] = []
    n_total = len(info_sets) * len(horizons) * len(targets)
    t_overall = time.time()
    counter = 0
    for info_set in info_sets:
        feat_cols = [c for c in info_sets_map.get(info_set, []) if c in model_matrix.columns]
        if not feat_cols:
            logger.warning("tune_per_info_set: info set %s has no features in matrix", info_set)
            continue
        for horizon in horizons:
            for target in targets:
                counter += 1
                target_col = f"target_{target}_t{horizon}"
                if target_col not in model_matrix.columns:
                    logger.warning("tune_per_info_set: %s not in matrix; skipping", target_col)
                    continue
                t0 = time.time()
                # Slice the train block
                train_block = model_matrix.iloc[:train_end_row]
                X_train = train_block[feat_cols]
                y_train = train_block[target_col]
                # Build CV splits on the train block
                splits = time_series_cv_splits(
                    n=len(train_block),
                    n_splits=n_splits,
                    embargo=embargo,
                    min_train_size=min_train_size,
                )
                if not splits:
                    logger.warning(
                        "tune_per_info_set: no CV splits for %s/%s/%s (train block too small)",
                        info_set, horizon, target,
                    )
                    continue
                # Run the grid search
                best_params, best_score, fold_maes = grid_search_xgb(
                    X=X_train,
                    y=y_train,
                    param_grid=param_grid,
                    cv_splits=splits,
                    val_fraction=val_fraction,
                    random_state=random_state,
                    verbose=verbose,
                )
                elapsed = time.time() - t0
                n_fits = int(
                    np.prod([len(v) for v in param_grid.values()])
                ) * len(splits)
                res = TuningResult(
                    info_set=info_set,
                    horizon=horizon,
                    target=target,
                    best_params=best_params,
                    mean_val_mae=best_score,
                    n_folds=len(splits),
                    n_train_rows=len(train_block),
                    total_fits=n_fits,
                    elapsed_sec=elapsed,
                    fold_maes=fold_maes,
                )
                results.append(res)
                logger.info(
                    "[%d/%d] %s horizon=%d target=%s → MAE=%.4f (params=%s, %.1fs)",
                    counter, n_total, info_set, horizon, target,
                    best_score, best_params, elapsed,
                )
    total_elapsed = time.time() - t_overall
    logger.info(
        "tune_per_info_set: %d runs in %.1fs total", len(results), total_elapsed,
    )
    return results


# ── Save / load helpers ─────────────────────────────────────────────────────


def save_tuning_results(
    results: List[TuningResult],
    out_path: Path,
) -> Path:
    """Save a list of :class:`TuningResult` to a CSV.

    The CSV has one row per (info_set, horizon, target), with columns:

    - ``info_set, horizon, target``
    - ``max_depth, learning_rate, n_estimators, min_child_weight, reg_alpha, reg_lambda``
    - ``mean_val_mae, n_folds, n_train_rows, total_fits, elapsed_sec``
    - ``fold_maes`` (semicolon-separated list, e.g. ``"1.1;1.2;1.05"``)
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for r in results:
        row = {
            "info_set": r.info_set,
            "horizon": r.horizon,
            "target": r.target,
            "mean_val_mae": r.mean_val_mae,
            "n_folds": r.n_folds,
            "n_train_rows": r.n_train_rows,
            "total_fits": r.total_fits,
            "elapsed_sec": r.elapsed_sec,
            "fold_maes": ";".join(f"{m:.6f}" for m in r.fold_maes),
        }
        # Flatten best_params into top-level columns
        for k, v in r.best_params.items():
            row[k] = v
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    logger.info("Saved %d tuning results to %s", len(results), out_path)
    return out_path


def load_tuning_results(csv_path: Path) -> Dict[Tuple[str, int, str], Dict[str, Any]]:
    """Load a tuning CSV and return a ``{(info_set, horizon, target): best_params}`` dict."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    param_keys = [
        "max_depth", "learning_rate", "n_estimators",
        "min_child_weight", "reg_alpha", "reg_lambda",
    ]
    out: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
    for _, row in df.iterrows():
        key = (str(row["info_set"]), int(row["horizon"]), str(row["target"]))
        params = {k: row[k] for k in param_keys if k in df.columns}
        out[key] = params
    return out


# ── CLI entry point ─────────────────────────────────────────────────────────


def _main() -> int:
    """Run tuning from the command line. Used by the Colab notebook."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Phase 7.3 — XGBoost time-series CV grid search",
    )
    parser.add_argument(
        "--data-path", type=Path,
        default=Path("data/processed/model_matrix.parquet"),
        help="Path to the model matrix (parquet). On Colab, point this to the Drive copy.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("outputs/model_objects/xgb_best_params.csv"),
        help="Where to write the best-params CSV.",
    )
    parser.add_argument(
        "--n-splits", type=int, default=3,
        help="Number of expanding-window CV folds (default 3).",
    )
    parser.add_argument(
        "--embargo", type=int, default=5,
        help="Embargo gap in trading days between train and val (default 5).",
    )
    parser.add_argument(
        "--min-train-size", type=int, default=200,
        help="Minimum train rows in the first fold (default 200).",
    )
    parser.add_argument(
        "--val-fraction", type=float, default=0.15,
        help="XGBoost early-stopping val fraction (default 0.15).",
    )
    parser.add_argument(
        "--info-sets", type=str, default="F,P,N,PN,PNG",
        help="Comma-separated info sets (default F,P,N,PN,PNG).",
    )
    parser.add_argument(
        "--targets", type=str, default="r_WAERLST,r_BSHIELDT,r_ITA",
        help="Comma-separated targets.",
    )
    parser.add_argument(
        "--horizons", type=str, default="1,5",
        help="Comma-separated horizons.",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default 42).",
    )
    args = parser.parse_args()

    # Add repo root to path
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if not args.data_path.exists():
        logger.error("model matrix not found at %s", args.data_path)
        return 1

    mm = pd.read_parquet(args.data_path)
    # Reconstruct info_sets if parquet didn't preserve attrs (defensive —
    # matches the pattern in scripts/phase7_run_ml.py::_load_model_matrix).
    if "info_sets" not in mm.attrs or not mm.attrs["info_sets"]:
        from src.features.build_model_matrix import build_info_sets
        logger.info("Reconstructing info_sets (not in attrs)")
        mm.attrs["info_sets"] = build_info_sets(mm.columns)
    logger.info("Loaded model matrix: %s", mm.shape)

    info_sets = tuple(s.strip() for s in args.info_sets.split(",") if s.strip())
    targets = tuple(s.strip() for s in args.targets.split(",") if s.strip())
    horizons = tuple(int(s.strip()) for s in args.horizons.split(",") if s.strip())

    results = tune_per_info_set(
        model_matrix=mm,
        info_sets=info_sets,
        horizons=horizons,
        targets=targets,
        n_splits=args.n_splits,
        embargo=args.embargo,
        min_train_size=args.min_train_size,
        val_fraction=args.val_fraction,
        random_state=args.seed,
    )
    save_tuning_results(results, args.output)
    logger.info("Tuning complete: %d results written to %s", len(results), args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_main())
