"""
Leakage-free recursive / expanding / rolling computation utilities.

The functions in this module are the building blocks for the Phase 5 surprise
features (attack-surprise, news-z-score) and the Phase 6 recursive baselines
(GARCH, AR(1) attack expectation). They enforce past-only semantics so callers
cannot accidentally introduce look-ahead bias.

Conventions
-----------
- ``expanding_compute(series, func, min_periods)`` at index ``t`` returns
  ``func(series.iloc[:t+1])`` (i.e. uses the value at ``t`` as well).
- ``rolling_compute(series, window, func, min_periods)`` at index ``t`` returns
  ``func(series.iloc[t-window:t])`` (i.e. **excludes** the value at ``t`` —
  this matches pandas' ``closed="left"`` rolling).
- Both functions return a ``pd.Series`` of the same length as ``series`` with
  ``NaN`` for indices where ``min_periods`` is not yet satisfied.
"""
from __future__ import annotations

import warnings
from typing import Callable, Optional

import numpy as np
import pandas as pd


def _safe_call(func: Callable[[np.ndarray], float], x: np.ndarray) -> float:
    """Call ``func(x)`` while suppressing the empty-slice RuntimeWarning
    raised by ``np.nanmean``/``np.nanstd`` on all-NaN windows."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return func(x)


def expanding_compute(
    series: pd.Series,
    func: Callable[[np.ndarray], float],
    min_periods: int = 30,
) -> pd.Series:
    """Apply ``func`` to the **expanding** window of all past values.

    At each index ``t >= min_periods - 1`` this returns
    ``func(series.values[:t+1])``. Indices before that point are ``NaN``.

    Notes
    -----
    This is a naive Python loop — fine for our ~1,300-day series, but for much
    larger inputs consider a vectorized ``.expanding().agg(func)`` if ``func``
    supports it.

    Parameters
    ----------
    series : pd.Series
        Input time series. ``name`` and ``index`` are preserved on the output.
    func : callable
        Function that takes a 1D ``np.ndarray`` and returns a scalar.
    min_periods : int, default 30
        Minimum number of past observations required before producing a value.

    Returns
    -------
    pd.Series
        Length-``len(series)`` with ``NaN`` for the first ``min_periods-1`` rows.
    """
    if min_periods < 1:
        raise ValueError("min_periods must be >= 1")
    values = series.values
    n = len(values)
    result = np.full(n, np.nan, dtype=float)

    for t in range(min_periods - 1, n):
        result[t] = func(values[: t + 1])

    return pd.Series(result, index=series.index, name=series.name)


def rolling_compute(
    series: pd.Series,
    window: int,
    func: Callable[[np.ndarray], float],
    min_periods: Optional[int] = None,
) -> pd.Series:
    """Apply ``func`` to a past-only **rolling** window (closed='left').

    At each index ``t >= min_periods`` this returns
    ``func(series.values[t-window:t])``. The current value ``t`` is **excluded**
    so this matches ``series.rolling(window).agg(func, closed='left')``.

    Parameters
    ----------
    series : pd.Series
        Input time series. ``name`` and ``index`` are preserved on the output.
    window : int
        Window size in observations.
    func : callable
        Function that takes a 1D ``np.ndarray`` and returns a scalar.
    min_periods : int, optional
        Minimum past observations required before producing a value.
        Defaults to ``window`` (a full window is required).

    Returns
    -------
    pd.Series
        Length-``len(series)`` with ``NaN`` for the first ``min_periods`` rows.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    if min_periods is None:
        min_periods = window
    if min_periods < 1:
        raise ValueError("min_periods must be >= 1")

    values = series.values
    n = len(values)
    result = np.full(n, np.nan, dtype=float)

    for t in range(min_periods, n):
        start = max(0, t - window)
        result[t] = _safe_call(func, values[start:t])

    return pd.Series(result, index=series.index, name=series.name)
