"""Top-level horse-race runner for the Phase 6 benchmark table.

This module is the "glue" between the model library (baselines, GARCH) and
the expanding-window engine. It:

1. Registers the canonical Phase 6 model specifications (4 return baselines
   × 5 information sets + 3 GARCH variants).
2. Runs the engine and aggregates the long-form predictions into the
   benchmark tables (one row per ``model × info_set × target × horizon``).
3. Optionally writes the benchmark CSV to ``outputs/tables/``.

The returned ``benchmark`` and ``vol_benchmark`` DataFrames match the
schema promised in the Phase 6 plan:

- ``target``      — source target name (``r_ITA`` or ``r_WAERLST_recon``)
- ``horizon``     — 1 or 5
- ``model``       — short model name
- ``info_set``    — ``F / P / N / PN / PNG`` (or ``"-"`` for GARCH)
- ``n_obs``       — number of non-NaN forecast/realized pairs
- ``MAE``         — mean absolute error
- ``RMSE``        — root mean squared error
- ``dir_acc``     — directional accuracy
- ``corr``        — Pearson correlation
- ``QLIKE``       — QLIKE loss (NaN for return models)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.baselines import (
    AR1Forecaster,
    HistoricalMeanForecaster,
    LinearRegressionForecaster,
    RidgeForecaster,
)
from src.models.evaluation import (
    compute_return_metrics,
    compute_vol_metrics,
)
from src.models.expanding_window import (
    ExpandingWindowEngine,
    ModelSpec,
    run_horse_race_engine,
)
from src.models.garch import GARCHForecaster


logger = logging.getLogger(__name__)


__all__ = [
    "default_return_specs",
    "default_vol_specs",
    "build_benchmark_tables",
    "run_horse_race",
    "save_benchmark_csvs",
]


# ── Default model registries ───────────────────────────────────────────────


RETURN_BASELINES: Dict[str, callable] = {
    "historical_mean": HistoricalMeanForecaster,
    "ar1": AR1Forecaster,
    "ols": LinearRegressionForecaster,
    "ridge": RidgeForecaster,
}


def default_return_specs(
    info_sets: Tuple[str, ...] = ("F", "P", "N", "PN", "PNG"),
    ridge_alpha: float = 1.0,
) -> List[ModelSpec]:
    """Return the canonical list of return-baseline ModelSpecs for Phase 6.

    Four model families × five information sets = 20 specifications.

    OLS and Ridge use ``standardize=True`` to z-score features with train
    statistics. This is the **only correct way** to handle features that
    have NaN in train (because the standardized mean is 0, so the NaN
    imputation doesn't shift test predictions off-distribution). It is
    the only valid comparison between info sets that mix many-sparse
    features (P, PN, PNG) and the F set.
    """
    specs: List[ModelSpec] = []
    for set_name in info_sets:
        specs.append(ModelSpec(
            name="historical_mean",
            factory=HistoricalMeanForecaster,
            info_set=set_name,
            model_type="returns",
        ))
        specs.append(ModelSpec(
            name="ar1",
            factory=AR1Forecaster,
            info_set=set_name,
            model_type="returns",
        ))
        specs.append(ModelSpec(
            name="ols",
            factory=lambda: LinearRegressionForecaster(standardize=True),
            info_set=set_name,
            model_type="returns",
        ))
        specs.append(ModelSpec(
            name="ridge",
            factory=lambda: RidgeForecaster(alpha=ridge_alpha, standardize=True),
            info_set=set_name,
            model_type="returns",
        ))
    return specs


def default_vol_specs() -> List[ModelSpec]:
    """Return the canonical list of GARCH-family ModelSpecs for Phase 6.

    Three variants: GARCH(1,1), GJR-GARCH(1,1), EGARCH(1,1).
    """
    return [
        ModelSpec(
            name="garch",
            factory=lambda: GARCHForecaster(
                variant="GARCH", p=1, q=1, dist="t", rescale=True, mean="Zero",
            ),
            info_set=None,
            model_type="vol",
        ),
        ModelSpec(
            name="gjr_garch",
            factory=lambda: GARCHForecaster(
                variant="GJR_GARCH", p=1, q=1, dist="t", rescale=True, mean="Zero",
            ),
            info_set=None,
            model_type="vol",
        ),
        ModelSpec(
            name="egarch",
            factory=lambda: GARCHForecaster(
                variant="EGARCH", p=1, q=1, dist="t", rescale=True, mean="Zero",
            ),
            info_set=None,
            model_type="vol",
        ),
    ]


# ── Benchmark aggregation ──────────────────────────────────────────────────


def build_benchmark_tables(
    predictions: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate the long-form predictions into two benchmark tables.

    Parameters
    ----------
    predictions : pd.DataFrame
        Output of :meth:`ExpandingWindowEngine.run`. Must have columns
        ``model, info_set, target, horizon, prediction, realized``.

    Returns
    -------
    benchmark, vol_benchmark : (pd.DataFrame, pd.DataFrame)
        - ``benchmark`` contains all ``model_type == "returns"`` rows
          (one row per ``model × info_set × target × horizon``).
        - ``vol_benchmark`` contains all GARCH rows
          (``info_set == "-"``).
    """
    required = {"model", "info_set", "target", "horizon", "prediction", "realized"}
    missing = required - set(predictions.columns)
    if missing:
        raise KeyError(f"predictions missing required columns: {missing}")

    # Partition returns vs vol by info_set column (vol → "-")
    returns = predictions[predictions["info_set"] != "-"].copy()
    vol = predictions[predictions["info_set"] == "-"].copy()

    benchmark = _aggregate(returns, model_type="returns")
    vol_benchmark = _aggregate(vol, model_type="vol")
    return benchmark, vol_benchmark


def _aggregate(df: pd.DataFrame, model_type: str) -> pd.DataFrame:
    """Aggregate the long-form predictions into one row per group."""
    if df.empty:
        return pd.DataFrame(columns=[
            "target", "horizon", "model", "info_set",
            "n_obs", "MAE", "RMSE", "dir_acc", "corr", "QLIKE",
        ])
    rows: List[Dict[str, Any]] = []
    for (target, horizon, model, info_set), sub in df.groupby(
        ["target", "horizon", "model", "info_set"], sort=False
    ):
        yhat = sub["prediction"].to_numpy(dtype=float)
        y = sub["realized"].to_numpy(dtype=float)
        # Drop NaN pairs
        mask = ~(np.isnan(yhat) | np.isnan(y))
        n_obs = int(mask.sum())
        if n_obs == 0:
            row = {
                "target": target, "horizon": horizon, "model": model,
                "info_set": info_set, "n_obs": 0, "MAE": np.nan, "RMSE": np.nan,
                "dir_acc": np.nan, "corr": np.nan, "QLIKE": np.nan,
            }
        else:
            if model_type == "returns":
                m = compute_return_metrics(y[mask], yhat[mask])
                row = {
                    "target": target, "horizon": horizon, "model": model,
                    "info_set": info_set, "n_obs": n_obs,
                    "MAE": m["MAE"], "RMSE": m["RMSE"],
                    "dir_acc": m["dir_acc"], "corr": m["corr"],
                    "QLIKE": np.nan,
                }
            else:
                m = compute_vol_metrics(yhat[mask], y[mask])
                row = {
                    "target": target, "horizon": horizon, "model": model,
                    "info_set": info_set, "n_obs": n_obs,
                    "MAE": m["MAE"], "RMSE": float(np.sqrt(m["MSE"])),
                    "dir_acc": np.nan, "corr": np.nan,
                    "QLIKE": m["QLIKE"],
                }
        rows.append(row)
    out = pd.DataFrame(rows)
    # Stable sort: target, horizon, info_set, model
    sort_cols = [c for c in ("target", "horizon", "info_set", "model") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    return out


# ── Convenience: full runner ───────────────────────────────────────────────


def run_horse_race(
    model_matrix: pd.DataFrame,
    horizons: Tuple[int, ...] = (1, 5),
    targets: Tuple[str, ...] = ("r_ITA", "r_WAERLST_recon"),
    info_sets: Tuple[str, ...] = ("F", "P", "N", "PN", "PNG"),
    test_fraction: float = 0.25,
    min_train_obs: int = 500,
    refit_every: int = 20,
    quick: bool = False,
    ridge_alpha: float = 1.0,
) -> Dict[str, pd.DataFrame]:
    """Run the full Phase 6 horse race and return benchmark tables.

    Returns
    -------
    dict with keys:
        - ``predictions`` : long-form predictions from the engine
        - ``benchmark``   : return-models benchmark (4 models × 5 sets × 2 targets × 2 horizons = 80 rows)
        - ``vol_benchmark`` : GARCH benchmark (3 variants × 2 targets × 2 horizons = 12 rows)
        - ``info_set_cardinality`` : per-set feature counts
    """
    specs = (
        default_return_specs(info_sets=info_sets, ridge_alpha=ridge_alpha)
        + default_vol_specs()
    )
    logger.info("Phase 6 horse race: %d specs, horizons=%s, targets=%s",
                len(specs), horizons, targets)
    predictions = run_horse_race_engine(
        model_matrix=model_matrix,
        specs=specs,
        horizons=list(horizons),
        targets=list(targets),
        test_fraction=test_fraction,
        min_train_obs=min_train_obs,
        refit_every=refit_every,
        quick=quick,
    )
    benchmark, vol_benchmark = build_benchmark_tables(predictions)
    info_set_card = _cardinality_from_mm(model_matrix)
    return {
        "predictions": predictions,
        "benchmark": benchmark,
        "vol_benchmark": vol_benchmark,
        "info_set_cardinality": info_set_card,
    }


def _cardinality_from_mm(mm: pd.DataFrame) -> pd.DataFrame:
    info_sets = mm.attrs.get("info_sets", {})
    rows = [{"information_set": k, "n_features": len(v)} for k, v in info_sets.items()]
    return pd.DataFrame(rows).sort_values("information_set").reset_index(drop=True)


# ── Save helpers ───────────────────────────────────────────────────────────


def save_benchmark_csvs(
    out_dir: Path,
    benchmark: pd.DataFrame,
    vol_benchmark: pd.DataFrame,
    info_set_card: Optional[pd.DataFrame] = None,
    suffix: str = "",
) -> Dict[str, Path]:
    """Save benchmark CSVs to ``out_dir`` and return the file paths.

    File names:
    - ``phase6_benchmark{suffix}.csv``          — return-models table
    - ``phase6_volatility_benchmark{suffix}.csv`` — GARCH table
    - ``phase6_info_set_cardinality{suffix}.csv``  — info-set counts (if provided)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    paths = {
        "benchmark": out_dir / f"phase6_benchmark{suffix}.csv",
        "vol_benchmark": out_dir / f"phase6_volatility_benchmark{suffix}.csv",
    }
    benchmark.to_csv(paths["benchmark"], index=False)
    written["benchmark"] = paths["benchmark"]
    vol_benchmark.to_csv(paths["vol_benchmark"], index=False)
    written["vol_benchmark"] = paths["vol_benchmark"]
    if info_set_card is not None:
        card_path = out_dir / f"phase6_info_set_cardinality{suffix}.csv"
        info_set_card.to_csv(card_path, index=False)
        written["info_set_cardinality"] = card_path
    return written
