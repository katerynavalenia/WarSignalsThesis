"""Phase 5C.4 — Calendar and regime features.

Pure deterministic features — no randomness, no data-dependent fitting.
All values are computable from the ``date`` column alone, except
``days_since_invasion`` (needs the invasion date) and the VIX regime dummies
(need the ``VIX`` column from the merge).

The "days since invasion" anchor is the Russian full-scale invasion date
**2022-02-24** (master plan §3.1). Pre-invasion dates are clamped to 0 so
``days_since_invasion`` is non-negative everywhere in the modeling window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

INVASION_DATE = "2022-02-24"

# VIX regime thresholds (per master plan §6.1 calendar variables).
VIX_THRESHOLDS = (15.0, 25.0, 35.0)  # low/normal, normal/high, high/crisis


def add_calendar_features(
    master: pd.DataFrame,
    invasion_date: str = INVASION_DATE,
) -> pd.DataFrame:
    """Add calendar, invasion-tenure, and VIX-regime features to ``master``.

    New columns:

    - ``day_of_week`` (0=Mon, 6=Sun), ``day_of_month``, ``month``, ``quarter``.
    - ``is_month_start``, ``is_month_end``, ``is_quarter_end`` (Int8).
    - ``days_since_invasion`` (clamped to 0 for pre-invasion rows).
    - ``vix_low``, ``vix_normal``, ``vix_high``, ``vix_crisis`` (Int8 dummies).

    Returns
    -------
    pd.DataFrame
        New DataFrame; input is not mutated.
    """
    out = master.copy()
    d = out["date"]

    # Date components.
    out["day_of_week"] = d.dt.dayofweek.astype(np.int8)
    out["day_of_month"] = d.dt.day.astype(np.int8)
    out["month"] = d.dt.month.astype(np.int8)
    out["quarter"] = d.dt.quarter.astype(np.int8)

    # Flags.
    out["is_month_start"] = d.dt.is_month_start.astype(np.int8)
    out["is_month_end"] = d.dt.is_month_end.astype(np.int8)
    out["is_quarter_end"] = d.dt.is_quarter_end.astype(np.int8)

    # Days since invasion (clamped to 0 for pre-invasion dates).
    invasion = pd.Timestamp(invasion_date)
    delta = (d - invasion).dt.days
    out["days_since_invasion"] = delta.clip(lower=0).astype("Int32")

    # VIX regime dummies (only if VIX is present).
    if "VIX" in out.columns:
        vix = out["VIX"]
        lo, mid, hi = VIX_THRESHOLDS
        out["vix_low"] = (vix < lo).astype(np.int8)
        out["vix_normal"] = ((vix >= lo) & (vix < mid)).astype(np.int8)
        out["vix_high"] = ((vix >= mid) & (vix < hi)).astype(np.int8)
        out["vix_crisis"] = (vix >= hi).astype(np.int8)

    return out
