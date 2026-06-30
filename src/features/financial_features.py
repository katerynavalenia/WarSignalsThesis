"""Phase 5C.1 — Financial return/volatility features.

All features use past-only semantics. We use :func:`rolling_compute` from
:mod:`src.utils.recursive` rather than ``series.rolling(closed='left')``
because in pandas 3.0+ the ``closed='left'`` argument on a fixed window does
not exclude the current observation as expected; ``rolling_compute`` is a
small Python loop that unambiguously uses the past ``W`` values only.

Per Phase 1 audit, the data is close-only (no OHLC), so volatility must be
returns-based (5/20-day rolling std of ``r_ITA``). GARCH estimates are
deferred to Phase 6.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.recursive import rolling_compute


def _past_std(x: np.ndarray) -> float:
    """Sample standard deviation (ddof=1) using ``nanstd`` to ignore NaN.

    Returns NaN if fewer than 2 non-NaN values are in the window. This is
    critical because ``r_ITA`` is NaN on weekends/holidays, and a naive
    ``np.std`` would return NaN for any 5/20-day window that includes a
    weekend day. Using ``np.nanstd`` makes the volatility computation robust
    to the calendar/trading-day mismatch.
    """
    clean = x[~np.isnan(x)]
    if len(clean) < 2:
        return np.nan
    return float(np.std(clean, ddof=1))


def add_financial_features(master: pd.DataFrame) -> pd.DataFrame:
    """Add financial return lags and volatility features to ``master``.

    New columns (all past-only):

    - ``vol_5d``       — 5-day rolling std of ``r_ITA`` (min_periods=5).
    - ``vol_20d``      — 20-day rolling std of ``r_ITA`` (min_periods=20).
    - ``abs_r_ITA``    — ``|r_ITA|`` (proxy for realized variance).
    - ``r_ITA_lag1``   — ``r_ITA`` shifted by 1 trading day.
    - ``r_ITA_lag2``   — shifted by 2.
    - ``r_ITA_lag5``   — shifted by 5.

    Returns
    -------
    pd.DataFrame
        New DataFrame; input is not mutated.
    """
    out = master.copy()

    r_ita = out["r_ITA"]

    # Volatility (returns-based; close-only data per Phase 1 audit).
    out["vol_5d"] = rolling_compute(r_ita, window=5, func=_past_std, min_periods=5)
    out["vol_20d"] = rolling_compute(r_ita, window=20, func=_past_std, min_periods=20)

    # Absolute return (proxy for realized variance per §6.1).
    out["abs_r_ITA"] = r_ita.abs()

    # Lagged returns.
    out["r_ITA_lag1"] = r_ita.shift(1)
    out["r_ITA_lag2"] = r_ita.shift(2)
    out["r_ITA_lag5"] = r_ita.shift(5)

    return out
