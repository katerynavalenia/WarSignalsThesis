"""Regression tests for forecast-target alignment and the AR(1) baseline.

Both bugs these cover were live and neither announced itself. Every feature in
the race is dated t-1 or earlier, so a target that is also shifted forward opens
a gap and silently discards the most recent return; and an AR(1) on an
overlapping h-day target, lagged one day instead of h, reads part of its own
answer out of the future. The second produced an out-of-sample R2 of 0.65 and
thirty-two specifications surviving multiple-testing correction, which is what a
look-ahead looks like from the outside.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_horse_race import expanding_oos  # noqa: E402
from scripts.run_volatility_race import realised_variance  # noqa: E402


class TestRealisedVarianceAlignment:
    """Row t must carry the variance realised over t .. t+h-1.

    That is exactly the span a GARCH forecast made from data through t-1 covers.
    A target shifted one day further compares every model against a window it
    never forecast, and penalises the GARCH family specifically, because their
    forecasts are aligned correctly by construction.
    """

    def test_one_day_target_is_the_current_squared_return(self):
        r = pd.Series([1.0, 2.0, 3.0, 4.0])
        rv = realised_variance(r, 1)
        assert list(rv) == [1.0, 4.0, 9.0, 16.0]

    def test_five_day_target_starts_at_the_current_day(self):
        r = pd.Series([1.0] * 10)
        rv = realised_variance(r, 5)
        # rows 0..5 each cover five days of unit squared returns
        assert rv.iloc[0] == pytest.approx(5.0)
        assert rv.iloc[5] == pytest.approx(5.0)
        assert np.isnan(rv.iloc[6])

    def test_five_day_target_sums_the_right_window(self):
        r = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        rv = realised_variance(r, 5)
        # row 0 must be r_0^2 + ... + r_4^2, not r_1^2 + ... + r_5^2
        assert rv.iloc[0] == pytest.approx(1 + 4 + 9 + 16 + 25)
        assert rv.iloc[1] == pytest.approx(4 + 9 + 16 + 25 + 36)


class TestAR1UsesOnlyRealisedInformation:
    """The AR(1) predictor must be fully observed before the forecast date."""

    def _series(self, n=400, seed=0):
        rng = np.random.default_rng(seed)
        return pd.Series(rng.normal(size=n))

    def test_overlapping_target_is_not_predicted_from_its_own_future(self):
        """The failing case: a 5-day overlapping sum lagged by one day shares
        four of its five days with the target. Lagged by h it shares none."""
        r = self._series()
        y = r.rolling(5).sum().shift(-4).dropna().reset_index(drop=True)
        X = pd.DataFrame(index=y.index)
        ts = int(len(y) * 0.75)

        fc = expanding_oos(y, X, "ar1", ts, horizon=5)
        ok = pd.concat([y, fc.rename("f")], axis=1).dropna()
        r2 = 1 - ((ok.iloc[:, 0] - ok["f"]) ** 2).sum() / (
            (ok.iloc[:, 0] - ok.iloc[:, 0].mean()) ** 2).sum()
        # On white noise an honest AR(1) cannot explain the target. The buggy
        # version scored above 0.6 here.
        assert r2 < 0.2, f"AR(1) is reading the future: R2 = {r2:.3f}"

    def test_one_day_ar1_still_works(self):
        y = self._series()
        fc = expanding_oos(y, pd.DataFrame(index=y.index), "ar1", 300, horizon=1)
        assert fc.iloc[300:].notna().all()
        assert np.isfinite(fc.iloc[300:]).all()

    def test_ar1_on_a_persistent_series_beats_the_mean(self):
        """Sanity in the other direction: where persistence genuinely exists,
        AR(1) should exploit it, so the guard above is not simply breaking it."""
        rng = np.random.default_rng(3)
        n, y = 500, [0.0]
        for _ in range(n - 1):
            y.append(0.9 * y[-1] + rng.normal(scale=0.1))
        s = pd.Series(y)
        X = pd.DataFrame(index=s.index)
        ar = expanding_oos(s, X, "ar1", 375, horizon=1)
        mean = expanding_oos(s, X, "mean", 375, horizon=1)
        ok = pd.concat([s, ar.rename("a"), mean.rename("m")], axis=1).dropna()
        sse_ar = ((ok.iloc[:, 0] - ok["a"]) ** 2).sum()
        sse_mean = ((ok.iloc[:, 0] - ok["m"]) ** 2).sum()
        assert sse_ar < sse_mean

    def test_short_history_falls_back_rather_than_indexing_backwards(self):
        """t - horizon can go negative early in the sample; that must degrade to
        the mean rather than wrap around to the end of the array."""
        y = self._series(n=60)
        fc = expanding_oos(y, pd.DataFrame(index=y.index), "ar1", 3, horizon=5)
        assert np.isfinite(fc.iloc[3:]).all()
