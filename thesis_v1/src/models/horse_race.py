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

- ``target``      — source target name (``r_WAERLST`` primary, or
  ``r_BSHIELDT`` / ``r_ITA`` robustness; decision_log 2026-07-02)
- ``horizon``     — 1 or 5
- ``model``       — short model name
- ``info_set``    — ``F / P / N / PN / PNG`` (or ``"-"`` for GARCH)
- ``n_obs``       — number of non-NaN forecast/realized pairs
- ``MAE``         — mean absolute error
- ``RMSE``        — root mean squared error
- ``dir_acc``     — directional accuracy
- ``corr``        — Pearson correlation
- ``QLIKE``       — QLIKE loss (NaN for return models)

Phase 7 extensions (decision_log 2026-07-01):

- :func:`default_ml_specs` — XGBoost specs across the 5 info sets.
- :func:`default_garch_x_specs` — GARCH-X variants with exogenous
  regressors in the mean equation.
- :func:`run_phase7` — unified runner for the Phase 7 benchmark.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
from src.models.garch import GARCHForecaster, GARCHXForecaster
from src.models.ml import XGBoostForecaster
from src.models.ml_explain import SHAPRecorder


logger = logging.getLogger(__name__)


__all__ = [
    "default_return_specs",
    "default_vol_specs",
    "default_ml_specs",
    "default_garch_x_specs",
    "build_benchmark_tables",
    "run_horse_race",
    "run_phase7",
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


# ── Phase 7 — ML specs ─────────────────────────────────────────────────────


def default_ml_specs(
    info_sets: Tuple[str, ...] = ("F", "P", "N", "PN", "PNG"),
    tuned_params: Optional[Dict[Tuple[str, int, str], Dict[str, Any]]] = None,
    default_xgb_params: Optional[Dict[str, Any]] = None,
) -> List[ModelSpec]:
    """Return the canonical list of XGBoost ModelSpecs for Phase 7.

    Parameters
    ----------
    info_sets : tuple of str
        Information set names.
    tuned_params : dict, optional
        ``{(info_set, horizon, target): {param: value}}`` from a Phase
        7.3 grid search. If provided, the XGBoost factory uses these
        per-(info_set, horizon, target) hyperparameters. If missing for
        a particular triple, falls back to ``default_xgb_params``.
    default_xgb_params : dict, optional
        Fallback hyperparameters for triples not in ``tuned_params``.

    Returns
    -------
    list of ModelSpec
        One XGBoost spec per info set. The factory looks up the right
        per-(horizon, target) params at fit time via the spec's
        ``info_set`` and the train context.

    Notes
    -----
    The :class:`XGBoostForecaster` does not know about the horizon or
    target — those are encoded in the target column name passed to
    ``fit``. To use per-horizon / per-target tuned params, the engine's
    OOS loop is responsible for selecting the right dict and creating
    a fresh XGBoost instance with those params. The simplest way to
    achieve this is to pass the ``tuned_params`` dict to the spec's
    factory via a closure that uses the spec's name and the
    horizon/target.

    For Phase 7's headline run we use a SIMPLER approach: one spec per
    info set, using the **horizon-1, target=r_WAERLST** (primary target,
    decision_log 2026-07-02) tuned params as the default. The OOS loop
    then uses these params for ALL horizons and targets. Per-horizon /
    per-target tuning can be enabled by the user via the
    ``--per-horizon-params`` CLI flag (which the phase7_run_ml.py script
    implements via a per-fit lookup).
    """
    fallback = default_xgb_params or {
        "max_depth": 5,
        "learning_rate": 0.05,
        "n_estimators": 500,
        "min_child_weight": 5,
        "reg_alpha": 0.0,
        "reg_lambda": 1.0,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    }
    specs: List[ModelSpec] = []
    for set_name in info_sets:
        # Pick the (h=1, r_WAERLST) tuned params as the default for this set
        # (r_WAERLST is the primary target, decision_log 2026-07-02).
        params_for_set: Dict[str, Any] = dict(fallback)
        if tuned_params:
            key = (set_name, 1, "r_WAERLST")
            if key in tuned_params:
                params_for_set.update(tuned_params[key])
        params_for_set.setdefault("random_state", 42)
        params_for_set.setdefault("val_fraction", 0.15)
        params_for_set.setdefault("early_stopping_rounds", 50)
        specs.append(ModelSpec(
            name="xgboost",
            factory=lambda p=dict(params_for_set): XGBoostForecaster(**p),
            info_set=set_name,
            model_type="returns",
            # Phase 7.6: marker so the post-run hook only fires on XGBoost
            # (and any future ML spec) — we use ``collect_shap`` to make
            # the SHAP recorder self-identify.
            collect_shap=True,
        ))
    return specs


def default_garch_x_specs(
    garch_x_info_set: str = "F",
    variants: Tuple[str, ...] = ("GARCH", "GJR_GARCH", "EGARCH"),
) -> List[ModelSpec]:
    """Return the canonical list of GARCH-X ModelSpecs for Phase 7.5.

    Each variant is fit with exogenous regressors from the specified
    info set (default: F = financial baseline). The exog enters the
    mean equation (``mean="ARX"``).
    """
    specs: List[ModelSpec] = []
    for variant in variants:
        specs.append(ModelSpec(
            name=f"garch_x_{variant.lower()}",
            factory=lambda v=variant: GARCHXForecaster(
                variant=v, p=1, q=1, dist="t", rescale=True, fallback=True,
            ),
            info_set=None,
            model_type="vol",
            garch_x_info_set=garch_x_info_set,
        ))
    return specs


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
    vol_benchmark = _aggregate(vol, model_type="vol", full_vol_df=vol)
    return benchmark, vol_benchmark


# Degenerate-forecast guard threshold: a vol-model fold prediction more
# than this multiple above/below the sanity-check scale is treated as a
# numerically degenerate fit (optimizer non-convergence) rather than a
# genuine forecast. See ``_aggregate``.
DEGENERATE_VOL_RATIO = 1_000.0


def _vol_scale_reference(full_vol_df: Optional[pd.DataFrame], target: str, horizon: int) -> float:
    """Point-in-time-safe scale reference for the degenerate-forecast guard.

    We deliberately do NOT use the realized (future) variance as the
    sanity-check scale — that would be outcome-dependent sample
    selection (discarding a model's worst *forecasts* using knowledge
    of the future truth it is being scored against, which flatters the
    model and is exactly the kind of leakage this project's rules
    prohibit).

    Instead we use the median **prediction** of the plain (non-X)
    ``garch`` / ``gjr_garch`` / ``egarch`` models for the same
    ``(target, horizon)``. Those are themselves out-of-sample forecasts
    (available at the same information time as the GARCH-X forecast
    being checked, not future information), and are already verified to
    be well-behaved (Master Plan-scale variance, not degenerate) — so
    they provide a reasonable order-of-magnitude reference for "what a
    sane variance forecast on this target looks like right now."
    """
    if full_vol_df is None or full_vol_df.empty:
        return np.nan
    plain_names = {"garch", "gjr_garch", "egarch"}
    ref = full_vol_df[
        (full_vol_df["target"] == target)
        & (full_vol_df["horizon"] == horizon)
        & (full_vol_df["model"].isin(plain_names))
    ]
    if ref.empty:
        return np.nan
    preds = pd.to_numeric(ref["prediction"], errors="coerce").to_numpy(dtype=float)
    preds = preds[np.isfinite(preds) & (preds > 0)]
    if preds.size == 0:
        return np.nan
    return float(np.median(preds))


def _aggregate(
    df: pd.DataFrame,
    model_type: str,
    full_vol_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Aggregate the long-form predictions into one row per group."""
    if df.empty:
        return pd.DataFrame(columns=[
            "target", "horizon", "model", "info_set",
            "n_obs", "MAE", "RMSE", "dir_acc", "corr", "QLIKE", "n_degenerate",
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
                "n_degenerate": 0,
            }
        else:
            if model_type == "returns":
                m = compute_return_metrics(y[mask], yhat[mask])
                row = {
                    "target": target, "horizon": horizon, "model": model,
                    "info_set": info_set, "n_obs": n_obs,
                    "MAE": m["MAE"], "RMSE": m["RMSE"],
                    "dir_acc": m["dir_acc"], "corr": m["corr"],
                    "QLIKE": np.nan, "n_degenerate": 0,
                }
            else:
                yhat_masked = yhat[mask]
                y_masked = y[mask]
                # Degenerate-forecast guard (2026-07): the ``arch``
                # package's ARX-mean optimizer can occasionally fail to
                # converge on a given expanding-window fold (few hundred
                # obs, correlated exogenous regressors), producing a
                # variance forecast that is off by many orders of
                # magnitude from a sane scale. A single such fold
                # dominates QLIKE (which is `realized/forecast`) and
                # MAE/RMSE, making the aggregate benchmark meaningless.
                #
                # IMPORTANT: the sanity-check scale must NOT be derived
                # from the realized (future) variance — that would be
                # outcome-dependent sample selection (discarding a
                # model's worst *forecasts* using knowledge of the
                # future truth it is scored against), which flatters
                # the model and violates this project's leakage rules
                # (instructions.md: no look-ahead). Instead we use the
                # median prediction of the plain (non-X) GARCH models
                # for the same (target, horizon) as a point-in-time-safe
                # reference for "what a sane variance forecast looks
                # like right now" — see ``_vol_scale_reference``.
                # We exclude folds whose forecast is more than
                # ``DEGENERATE_VOL_RATIO``x larger or smaller than that
                # reference and record how many were dropped, rather
                # than silently clipping to a plausible value.
                target_scale = _vol_scale_reference(full_vol_df, target, horizon)
                if np.isfinite(target_scale) and target_scale > 0:
                    ratio = yhat_masked / target_scale
                    degenerate = (ratio > DEGENERATE_VOL_RATIO) | (ratio < 1.0 / DEGENERATE_VOL_RATIO)
                    n_degenerate = int(degenerate.sum())
                    if n_degenerate > 0:
                        logger.warning(
                            "vol model %s (target=%s, horizon=%s, info_set=%s): "
                            "dropped %d/%d folds with degenerate variance "
                            "forecast (>%gx or <%gx the plain-GARCH "
                            "prediction scale) before computing "
                            "MAE/RMSE/QLIKE",
                            model, target, horizon, info_set, n_degenerate,
                            len(yhat_masked), DEGENERATE_VOL_RATIO,
                            1.0 / DEGENERATE_VOL_RATIO,
                        )
                        yhat_masked = yhat_masked[~degenerate]
                        y_masked = y_masked[~degenerate]
                else:
                    n_degenerate = 0
                if yhat_masked.size == 0:
                    row = {
                        "target": target, "horizon": horizon, "model": model,
                        "info_set": info_set, "n_obs": 0, "MAE": np.nan,
                        "RMSE": np.nan, "dir_acc": np.nan, "corr": np.nan,
                        "QLIKE": np.nan, "n_degenerate": n_degenerate,
                    }
                else:
                    m = compute_vol_metrics(yhat_masked, y_masked)
                    row = {
                        "target": target, "horizon": horizon, "model": model,
                        "info_set": info_set, "n_obs": int(yhat_masked.size),
                        "MAE": m["MAE"], "RMSE": float(np.sqrt(m["MSE"])),
                        "dir_acc": np.nan, "corr": np.nan,
                        "QLIKE": m["QLIKE"], "n_degenerate": n_degenerate,
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
    targets: Tuple[str, ...] = ("r_WAERLST", "r_BSHIELDT", "r_ITA"),
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
    prefix: str = "phase6",
) -> Dict[str, Path]:
    """Save benchmark CSVs to ``out_dir`` and return the file paths.

    File names:
    - ``{prefix}_benchmark{suffix}.csv``          — return-models table
    - ``{prefix}_volatility_benchmark{suffix}.csv`` — GARCH table
    - ``{prefix}_info_set_cardinality{suffix}.csv``  — info-set counts (if provided)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    paths = {
        "benchmark": out_dir / f"{prefix}_benchmark{suffix}.csv",
        "vol_benchmark": out_dir / f"{prefix}_volatility_benchmark{suffix}.csv",
    }
    benchmark.to_csv(paths["benchmark"], index=False)
    written["benchmark"] = paths["benchmark"]
    vol_benchmark.to_csv(paths["vol_benchmark"], index=False)
    written["vol_benchmark"] = paths["vol_benchmark"]
    if info_set_card is not None:
        card_path = out_dir / f"{prefix}_info_set_cardinality{suffix}.csv"
        info_set_card.to_csv(card_path, index=False)
        written["info_set_cardinality"] = card_path
    return written


# ── Phase 7 runner ──────────────────────────────────────────────────────────


def run_phase7(
    model_matrix: pd.DataFrame,
    horizons: Tuple[int, ...] = (1, 5),
    targets: Tuple[str, ...] = ("r_WAERLST", "r_BSHIELDT", "r_ITA"),
    info_sets: Tuple[str, ...] = ("F", "P", "N", "PN", "PNG"),
    tuned_params: Optional[Dict[Tuple[str, int, str], Dict[str, Any]]] = None,
    include_garch_x: bool = True,
    garch_x_info_set: str = "F",
    include_econometric_baselines: bool = True,
    test_fraction: float = 0.25,
    min_train_obs: int = 500,
    refit_every: int = 20,
    quick: bool = False,
    random_seed: int = 42,
    collect_shap: bool = True,
) -> Dict[str, Any]:
    """Run the Phase 7 horse race: XGBoost returns + (optional) GARCH-X.

    Parameters
    ----------
    model_matrix : pd.DataFrame
        Output of :func:`build_model_matrix` (must have
        ``mm.attrs['info_sets']``).
    tuned_params : dict, optional
        ``{(info_set, horizon, target): {param: value}}`` from
        :func:`src.models.ml_tuning.tune_per_info_set`. If ``None``,
        the XGBoost specs use the default hyperparameters from
        :func:`default_ml_specs`.
    include_garch_x : bool, default True
        Whether to add the 3 GARCH-X variants.
    garch_x_info_set : str, default "F"
        Which info set to use as exogenous regressors for GARCH-X.
    include_econometric_baselines : bool, default True
        Whether to also run the 4 Phase 6 return baselines (HM, AR1,
        OLS, Ridge) on the 5 info sets. Set to ``False`` for a
        standalone XGBoost-only run.
    collect_shap : bool, default True
        If True, install a SHAP recorder as the post-run hook so that
        per-fold SHAP values are saved to ``outputs/model_objects/``.

    Returns
    -------
    dict with keys
        - ``predictions`` (long-form DataFrame)
        - ``benchmark`` (return-models benchmark, including XGBoost)
        - ``vol_benchmark`` (GARCH + GARCH-X rows)
        - ``shap_recorder`` (the SHAPRecorder, or None)
    """
    # Build specs
    specs: List[ModelSpec] = []
    if include_econometric_baselines:
        specs.extend(default_return_specs(info_sets=info_sets))
    specs.extend(
        default_ml_specs(info_sets=info_sets, tuned_params=tuned_params)
    )
    specs.extend(default_vol_specs())
    if include_garch_x:
        specs.extend(
            default_garch_x_specs(garch_x_info_set=garch_x_info_set)
        )

    # Set up the SHAP recorder
    shap_recorder: Optional[SHAPRecorder] = None
    if collect_shap:
        shap_recorder = SHAPRecorder()

        def _shap_hook(
            model, X_test, spec, target, horizon, fold,
        ) -> None:
            if X_test is None or len(X_test) == 0:
                return
            if not spec.extra.get("collect_shap", False):
                return
            shap_recorder.record_fold(
                info_set=spec.info_set or "-",
                horizon=horizon,
                target=target,
                fold=fold,
                model=model,
                X_test=X_test,
            )

        # The hook will be set per-engine-instance below
        hook = _shap_hook
    else:
        hook = None

    logger.info("Phase 7 horse race: %d specs, horizons=%s, targets=%s",
                len(specs), horizons, targets)
    eng = ExpandingWindowEngine(
        model_matrix=model_matrix,
        info_sets=model_matrix.attrs.get("info_sets", {}),
        targets=list(targets),
        horizons=list(horizons),
        test_fraction=test_fraction,
        min_train_obs=min_train_obs,
        refit_every=refit_every,
        quick=quick,
        random_seed=random_seed,
    )
    if hook is not None:
        eng.set_post_run_hook(hook)
    for s in specs:
        eng.add_spec(s)
    predictions = eng.run()

    benchmark, vol_benchmark = build_benchmark_tables(predictions)
    info_set_card = _cardinality_from_mm(model_matrix)
    return {
        "predictions": predictions,
        "benchmark": benchmark,
        "vol_benchmark": vol_benchmark,
        "info_set_cardinality": info_set_card,
        "shap_recorder": shap_recorder,
    }
