"""Forecast evaluation metrics for the Phase 6 horse race.

All metrics are NaN-safe: pairs with a NaN in either ``y`` or ``yhat`` are
dropped before computing the score. Empty / all-NaN inputs raise
``ValueError`` so silent failures are impossible.

Return metrics (Master Plan §12.1)
----------------------------------
- :func:`mae`           — mean absolute error
- :func:`rmse`          — root mean squared error
- :func:`directional_accuracy` — fraction of times sign(y) == sign(yhat)
- :func:`correlation`   — Pearson correlation between y and yhat

Volatility metrics (Master Plan §12.2)
---------------------------------------
- :func:`qlike`         — QLIKE loss for variance forecasts
                          (Patton 2011; lower is better; non-negative)
- :func:`bias`          — mean(σ²_hat) / mean(σ²_realized) − 1
"""
from __future__ import annotations

from typing import Optional, Union

import numpy as np
import pandas as pd

ArrayLike = Union[np.ndarray, pd.Series, list]


__all__ = [
    "mae",
    "rmse",
    "directional_accuracy",
    "correlation",
    "qlike",
    "bias",
    "compute_return_metrics",
    "compute_vol_metrics",
]


# ── Helpers ────────────────────────────────────────────────────────────────


def _to_arrays(y: ArrayLike, yhat: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Coerce to aligned 1D ``np.ndarray``s."""
    a = np.asarray(y, dtype=float)
    b = np.asarray(yhat, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: y={a.shape}, yhat={b.shape}")
    return a, b


def _drop_nan(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return arrays with rows where either is NaN dropped."""
    mask = ~(np.isnan(a) | np.isnan(b))
    return a[mask], b[mask]


def _check_nonempty(a: np.ndarray, b: np.ndarray, name: str) -> None:
    if a.size == 0 or b.size == 0:
        raise ValueError(f"{name}: empty input after dropping NaN")


# ── Return metrics ─────────────────────────────────────────────────────────


def mae(y: ArrayLike, yhat: ArrayLike) -> float:
    """Mean absolute error (lower is better)."""
    a, b = _to_arrays(y, yhat)
    a, b = _drop_nan(a, b)
    _check_nonempty(a, b, "mae")
    return float(np.mean(np.abs(a - b)))


def rmse(y: ArrayLike, yhat: ArrayLike) -> float:
    """Root mean squared error (lower is better)."""
    a, b = _to_arrays(y, yhat)
    a, b = _drop_nan(a, b)
    _check_nonempty(a, b, "rmse")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def directional_accuracy(y: ArrayLike, yhat: ArrayLike) -> float:
    """Fraction of times ``sign(y) == sign(yhat)`` (range: [0, 1]).

    Zero in both ``y`` and ``yhat`` is counted as a *match* (a correct "no
    movement" call). Rows with either value exactly 0 in ``y`` only are
    excluded from the denominator (no clear direction to compare against).
    """
    a, b = _to_arrays(y, yhat)
    a, b = _drop_nan(a, b)
    _check_nonempty(a, b, "directional_accuracy")
    sign_a = np.sign(a)
    sign_b = np.sign(b)
    # If y is exactly 0, skip (no direction to verify)
    valid = a != 0.0
    if not valid.any():
        return 0.5  # no information
    return float(np.mean(sign_a[valid] == sign_b[valid]))


def correlation(y: ArrayLike, yhat: ArrayLike) -> float:
    """Pearson correlation between ``y`` and ``yhat`` (range: [-1, 1])."""
    a, b = _to_arrays(y, yhat)
    a, b = _drop_nan(a, b)
    _check_nonempty(a, b, "correlation")
    if np.std(a) == 0.0 or np.std(b) == 0.0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ── Volatility metrics ─────────────────────────────────────────────────────


def qlike(
    sigma2_forecast: ArrayLike,
    realized_var: ArrayLike,
) -> float:
    """QLIKE loss for positive variance forecasts and realized variance.

    Definition (Patton 2011, eq. 11):
        QLIKE = mean( realized / forecast − log(realized / forecast) − 1 )

    Lower is better. Always ≥ 0, with equality iff the two distributions
    match. Robust to the multiplicative structure of variance.

    Both inputs must be strictly positive where they are observed; any
    non-positive (≤ 0) forecast or realized value is dropped.
    """
    f = np.asarray(sigma2_forecast, dtype=float)
    r = np.asarray(realized_var, dtype=float)
    if f.shape != r.shape:
        raise ValueError(
            f"shape mismatch: sigma2_forecast={f.shape}, realized_var={r.shape}"
        )
    mask = (f > 0.0) & (r > 0.0) & ~np.isnan(f) & ~np.isnan(r)
    f_clean = f[mask]
    r_clean = r[mask]
    if f_clean.size == 0:
        raise ValueError("qlike: no strictly-positive (forecast, realized) pairs")
    ratio = r_clean / f_clean
    return float(np.mean(ratio - np.log(ratio) - 1.0))


def bias(sigma2_forecast: ArrayLike, realized_var: ArrayLike) -> float:
    """Multiplicative bias: ``mean(forecast) / mean(realized) − 1``.

    A bias of 0 means the forecast is centered on the realized variance.
    Positive = over-forecast, negative = under-forecast.
    """
    f = np.asarray(sigma2_forecast, dtype=float)
    r = np.asarray(realized_var, dtype=float)
    if f.shape != r.shape:
        raise ValueError(
            f"shape mismatch: sigma2_forecast={f.shape}, realized_var={r.shape}"
        )
    mask = ~np.isnan(f) & ~np.isnan(r)
    f_clean = f[mask]
    r_clean = r[mask]
    if f_clean.size == 0:
        raise ValueError("bias: empty input after dropping NaN")
    if np.mean(r_clean) == 0.0:
        return 0.0
    return float(np.mean(f_clean) / np.mean(r_clean) - 1.0)


# ── Bundles for the benchmark table ─────────────────────────────────────────


def compute_return_metrics(
    y: ArrayLike, yhat: ArrayLike
) -> dict:
    """Compute MAE, RMSE, dir-acc, correlation in one call."""
    return {
        "MAE": mae(y, yhat),
        "RMSE": rmse(y, yhat),
        "dir_acc": directional_accuracy(y, yhat),
        "corr": correlation(y, yhat),
    }


def compute_vol_metrics(
    sigma2_forecast: ArrayLike, realized_var: ArrayLike
) -> dict:
    """Compute QLIKE, MAE, MSE, bias in one call (Master Plan §12.2)."""
    f = np.asarray(sigma2_forecast, dtype=float)
    r = np.asarray(realized_var, dtype=float)
    mask = ~np.isnan(f) & ~np.isnan(r)
    return {
        "QLIKE": qlike(f, r),
        "MAE": float(np.mean(np.abs(f[mask] - r[mask]))),
        "MSE": float(np.mean((f[mask] - r[mask]) ** 2)),
        "bias": bias(f, r),
    }
