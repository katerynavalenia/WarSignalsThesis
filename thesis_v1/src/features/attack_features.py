"""Phase 5C.2 — Attack composition, surprise, and lag features.

Adds to ``master``:

- **Composition features** (per Master Plan §8.3): ``attack_uav_share``,
  ``attack_cruise_share``, ``attack_ballistic_share``, ``penetrations_estimated``,
  ``large_attack_indicator``.
- **Surprise features** (per §8.4): ``attack_surprise_{series}_{W}d`` for
  ``series ∈ {total, uav, cruise, ballistic, penetrations}`` and
  ``W ∈ {7, 30, 90}`` (15 features). Each is
  ``series_t − mean(series[t-W, t))`` — past-only via
  :func:`rolling_compute` from :mod:`src.utils.recursive`.
- **Lag features**: ``launched_total_lag{1,3}``, ``launched_total_{7,30}d_rolling_mean``.
- **AR(1) hook** (:func:`compute_attack_surprise_ar1`) is exported for Phase 6
  to swap in within CV folds. Not called in Phase 5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.recursive import rolling_compute

# Weapon series for which we build a surprise triplet.
SURPRISE_SERIES = (
    "launched_total",
    "launched_uav",
    "launched_cruise_missile",
    "launched_ballistic_missile",
)
PENETRATIONS_SERIES = "penetrations_estimated"  # launched_total − destroyed_total
SURPRISE_WINDOWS = (7, 30, 90)

# A large attack is the top-10% of `launched_total`. We compute the threshold
# on the *training* set; for Phase 5 we use the full sample as an approximation.
LARGE_ATTACK_QUANTILE = 0.90


def add_attack_features(master: pd.DataFrame) -> pd.DataFrame:
    """Add attack composition, surprise, and lag features to ``master``.

    Returns
    -------
    pd.DataFrame
        New DataFrame; input is not mutated.
    """
    out = master.copy()

    # 1. Composition features (per §8.3).
    safe_total = out["launched_total"].replace(0, np.nan)
    out["attack_uav_share"] = out["launched_uav"] / safe_total
    out["attack_cruise_share"] = out["launched_cruise_missile"] / safe_total
    out["attack_ballistic_share"] = out["launched_ballistic_missile"] / safe_total
    out["penetrations_estimated"] = (
        out["launched_total"] - out["destroyed_total"]
    )

    # 2. Large-attack indicator. Phase 6 should compute the threshold on the
    #    training fold only.
    if out["launched_total"].notna().any():
        threshold = out["launched_total"].quantile(LARGE_ATTACK_QUANTILE)
    else:
        threshold = np.nan
    out["large_attack_indicator"] = (
        (out["launched_total"] > threshold).astype("Int8")
    )

    # 3. Surprise features (per §8.4). past-only via rolling_compute.
    #    Use ``np.nanmean`` so windows with NaN days (e.g. days with no
    #    attack reports) don't propagate NaN into the surprise value.
    for series in SURPRISE_SERIES:
        if series not in out.columns:
            continue
        s = out[series]
        for w in SURPRISE_WINDOWS:
            expected = rolling_compute(s, window=w, func=np.nanmean, min_periods=w)
            short = series.replace("launched_", "")
            out[f"attack_surprise_{short}_{w}d"] = s - expected

    # Surprise triplet for penetrations_estimated.
    pen = out[PENETRATIONS_SERIES]
    for w in SURPRISE_WINDOWS:
        expected = rolling_compute(pen, window=w, func=np.nanmean, min_periods=w)
        out[f"attack_surprise_penetrations_{w}d"] = pen - expected

    # 4. Lag features for `launched_total`. Use ``np.nanmean`` for the
    #    rolling means (ignore NaN days).
    lt = out["launched_total"]
    out["launched_total_lag1"] = lt.shift(1)
    out["launched_total_lag3"] = lt.shift(3)
    out["launched_total_7d_rolling"] = rolling_compute(
        lt, window=7, func=np.nanmean, min_periods=7
    )
    out["launched_total_30d_rolling"] = rolling_compute(
        lt, window=30, func=np.nanmean, min_periods=30
    )

    return out


def compute_attack_surprise_ar1(
    series: pd.Series,
    min_train: int = 180,
) -> float:
    """AR(1) hook for Phase 6 — fit on the *given* series and return the
    one-step-ahead prediction.

    This function is **not** called by Phase 5 (which uses rolling means
    instead). Phase 6 will call it within each CV fold, passing only the
    *training* portion of the series so the prediction is leakage-free.

    Parameters
    ----------
    series : pd.Series
        Time series of attack counts (any index). NaNs are dropped.
    min_train : int, default 180
        Minimum number of observations required to fit. Returns NaN
        otherwise.

    Returns
    -------
    float
        AR(1) one-step-ahead forecast, or NaN if insufficient data.

    Raises
    ------
    ImportError
        If ``statsmodels`` is not installed.
    """
    try:
        from statsmodels.tsa.ar_model import AutoReg
    except ImportError as e:
        raise ImportError(
            "statsmodels is required for AR(1) attack surprise. "
            "Install with `pip install statsmodels`."
        ) from e

    clean = series.dropna().astype(float).values
    if len(clean) < min_train:
        return np.nan
    model = AutoReg(clean, lags=1).fit()
    # statsmodels AutoReg.forecast() returns an ndarray, not a Series.
    return float(model.forecast(steps=1)[0])
