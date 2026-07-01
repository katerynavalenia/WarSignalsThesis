"""Forecasting model modules (Phase 6+).

Public API:
- :mod:`src.models.baselines` — return-forecast baselines (HistoricalMean,
  AR1, OLS, Ridge).
- :mod:`src.models.garch` — GARCH-family volatility forecasters
  (GARCH, GJR_GARCH, EGARCH).
- :mod:`src.models.evaluation` — MAE, RMSE, dir-acc, QLIKE, bias, correlation.
- :mod:`src.models.expanding_window` — strict no-leakage OOS engine with
  refit cadence.
- :mod:`src.models.horse_race` — top-level runner that pivots engine
  output into the benchmark table.
"""
from __future__ import annotations

from src.models import baselines, evaluation, expanding_window, garch, horse_race

__all__ = [
    "baselines",
    "evaluation",
    "expanding_window",
    "garch",
    "horse_race",
]
