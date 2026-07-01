"""Forecasting model modules (Phase 6+).

Public API:
- :mod:`src.models.baselines` — return-forecast baselines (HistoricalMean,
  AR1, OLS, Ridge).
- :mod:`src.models.garch` — GARCH-family volatility forecasters
  (GARCH, GJR_GARCH, EGARCH) and GARCH-X (Phase 7.5).
- :mod:`src.models.evaluation` — MAE, RMSE, dir-acc, QLIKE, bias, correlation.
- :mod:`src.models.expanding_window` — strict no-leakage OOS engine with
  refit cadence and a ``post_run_hook`` callback.
- :mod:`src.models.horse_race` — top-level runner that pivots engine
  output into the benchmark table. Includes ``default_ml_specs``,
  ``default_garch_x_specs``, and ``run_phase7`` (Phase 7).
- :mod:`src.models.ml` — XGBoost forecaster (Phase 7 principal algorithm).
- :mod:`src.models.ml_tuning` — time-series CV grid search for XGBoost.
- :mod:`src.models.ml_explain` — SHAP-based feature attribution.
"""
from __future__ import annotations

from src.models import (
    baselines,
    evaluation,
    expanding_window,
    garch,
    horse_race,
    ml,
    ml_explain,
    ml_tuning,
)

__all__ = [
    "baselines",
    "evaluation",
    "expanding_window",
    "garch",
    "horse_race",
    "ml",
    "ml_explain",
    "ml_tuning",
]
