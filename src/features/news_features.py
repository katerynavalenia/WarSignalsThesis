"""Phase 5C.3 — News attention normalizations, narrative gaps, and lags.

Per Master Plan §8.5, news attention for each source group ``g`` is computed
in three ways so Phase 6/7 can pick the best via CV:

- **Share** (primary, per §8.5):
  ``n_<group>_share = n_articles_<group> / n_articles_total`` — bounded [0, 1].
- **Z-score** (30-day rolling, past-only):
  ``n_<group>_z30 = (n_<group> − μ_30d) / σ_30d`` where μ/σ are computed on
  ``series[t-30, t)`` (excludes the current value).
- **Log**: ``n_<group>_log = log1p(n_<group>)``.

Narrative-gap features (``narrative_gap_ua_west`` etc.) are already present
from Phase 3 (see :mod:`src.data.gdelt_postprocess`); this module only adds
their *lagged* versions and the count-normalizations.

We use :func:`rolling_compute` from :mod:`src.utils.recursive` for the
z-score and rolling-mean features because pandas 3.0+ ``rolling(closed='left')``
does not exclude the current observation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.recursive import rolling_compute

SOURCE_GROUPS = ("ukrainian", "russian", "western", "other")
Z_WINDOW = 30
ROLLING_WINDOWS = (7, 30)


def _past_std(x: np.ndarray) -> float:
    """Sample standard deviation (ddof=1) using ``nanstd`` to ignore NaN."""
    clean = x[~np.isnan(x)]
    if len(clean) < 2:
        return np.nan
    return float(np.std(clean, ddof=1))


def add_news_features(master: pd.DataFrame) -> pd.DataFrame:
    """Add news attention normalizations, narrative-gap lags, and count lags.

    New columns per source group ``g ∈ {ukrainian, russian, western, other}``:

    - ``n_<g>_share``  — row-normalized share of total articles.
    - ``n_<g>_log``    — ``log1p(n_<g>)``.
    - ``n_<g>_z30``    — 30-day rolling z-score (past-only).
    - ``tone_<g>_lag1`` and ``tone_<g>_lag3`` — tone lags.

    Plus total-count lags:

    - ``n_articles_total_lag1``, ``_lag3``.
    - ``n_articles_total_{7,30}d_rolling_mean``.

    And the *lagged* versions of the three narrative-gap features
    (``narrative_gap_*_lag1``).

    Returns
    -------
    pd.DataFrame
        New DataFrame; input is not mutated.
    """
    out = master.copy()

    total = out["n_articles_total"]
    # Safe denominator: 0 → NaN (avoids div-by-zero and the share "blow-up").
    safe_total = total.replace(0, np.nan)

    for g in SOURCE_GROUPS:
        count_col = f"n_articles_{g}"
        if count_col not in out.columns:
            continue
        count = out[count_col]

        # 1. Share.
        out[f"n_{g}_share"] = count / safe_total

        # 2. Log.
        out[f"n_{g}_log"] = np.log1p(count)

        # 3. Z-score (30-day rolling, past-only). Use ``np.nanmean`` so the
        #    mean is computed over the non-NaN days in the window (NaN days
        #    are pre-coverage days and shouldn't drag the mean down to 0).
        mu = rolling_compute(
            count, window=Z_WINDOW, func=np.nanmean, min_periods=Z_WINDOW
        )
        sigma = rolling_compute(
            count, window=Z_WINDOW, func=_past_std, min_periods=Z_WINDOW
        )
        out[f"n_{g}_z30"] = (count - mu) / sigma.replace(0, np.nan)

        # Tone lags.
        tone_col = f"tone_{g}"
        if tone_col in out.columns:
            out[f"{tone_col}_lag1"] = out[tone_col].shift(1)
            out[f"{tone_col}_lag3"] = out[tone_col].shift(3)

    # Total article count lags. Use ``np.nanmean`` to ignore NaN days.
    out["n_articles_total_lag1"] = total.shift(1)
    out["n_articles_total_lag3"] = total.shift(3)
    for w in ROLLING_WINDOWS:
        out[f"n_articles_total_{w}d_rolling_mean"] = rolling_compute(
            total, window=w, func=np.nanmean, min_periods=w
        )

    # Narrative-gap lags.
    for ng in ("narrative_gap_ua_west", "narrative_gap_ru_west", "narrative_gap_ua_ru"):
        if ng in out.columns:
            out[f"{ng}_lag1"] = out[ng].shift(1)

    return out
