"""Tests for the free-basket-vs-Bloomberg validation gate."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.validate_basket import (  # noqa: E402
    THRESHOLDS,
    realized_vol,
    validate_basket,
    validation_table,
)


def _series(values, start="2020-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.Series(values, index=idx)


@pytest.fixture
def bloomberg() -> pd.Series:
    rng = np.random.default_rng(42)
    return _series(rng.normal(0.1, 1.4, 600))


class TestValidateBasket:
    def test_a_near_perfect_tracker_passes(self, bloomberg):
        rng = np.random.default_rng(7)
        cand = bloomberg + rng.normal(0, 0.25, len(bloomberg))
        res = validate_basket(cand, bloomberg, name="close_tracker")
        assert res.passed, res.failures
        assert res.return_corr > 0.95

    def test_an_unrelated_series_fails_on_correlation(self, bloomberg):
        rng = np.random.default_rng(11)
        cand = _series(rng.normal(0.1, 1.4, len(bloomberg)))
        res = validate_basket(cand, bloomberg, name="unrelated")
        assert not res.passed
        assert any("return corr" in f for f in res.failures)

    def test_matching_moments_does_not_earn_a_pass(self, bloomberg):
        # The v1 lesson: r_BSHIELDT_recon matched the real series' standard
        # deviation almost exactly (1.4983 vs 1.4462) and was still wrong.
        # A series drawn with identical mean and sd but no common variation
        # must fail.
        rng = np.random.default_rng(3)
        cand = _series(rng.normal(bloomberg.mean(), bloomberg.std(), len(bloomberg)))
        res = validate_basket(cand, bloomberg, name="moment_twin")
        assert res.std_ratio == pytest.approx(1.0, abs=0.15)
        assert not res.passed

    def test_a_leveraged_tracker_fails_on_beta(self, bloomberg):
        res = validate_basket(bloomberg * 1.6, bloomberg, name="levered")
        assert not res.passed
        assert any("beta" in f for f in res.failures)

    def test_overlap_is_the_intersection_of_dates(self, bloomberg):
        cand = bloomberg.iloc[100:]
        res = validate_basket(cand, bloomberg, name="short")
        assert res.n_overlap == len(bloomberg) - 100

    def test_too_little_overlap_raises_rather_than_reporting_noise(self, bloomberg):
        with pytest.raises(ValueError, match="at least 60"):
            validate_basket(bloomberg.iloc[:30], bloomberg, name="tiny")

    def test_nan_rows_are_dropped_not_filled(self, bloomberg):
        cand = bloomberg.copy()
        cand.iloc[:50] = np.nan
        res = validate_basket(cand, bloomberg, name="gappy")
        assert res.n_overlap == len(bloomberg) - 50

    def test_thresholds_are_overridable_but_default_is_strict(self, bloomberg):
        rng = np.random.default_rng(5)
        cand = bloomberg + rng.normal(0, 0.9, len(bloomberg))
        assert not validate_basket(cand, bloomberg).passed
        loose = validate_basket(
            cand,
            bloomberg,
            thresholds={
                "return_corr_min": 0.5,
                "vol_corr_min": 0.5,
                "r2_min": 0.5,
                "tracking_error_max": 2.0,
            },
        )
        assert loose.passed, loose.failures

    def test_table_reports_every_candidate(self, bloomberg):
        rng = np.random.default_rng(13)
        good = validate_basket(bloomberg + rng.normal(0, 0.2, 600), bloomberg, "good")
        bad = validate_basket(_series(rng.normal(0, 1.4, 600)), bloomberg, "bad")
        tbl = validation_table([good, bad])
        assert list(tbl["series"]) == ["good", "bad"]
        assert tbl.loc[tbl.series == "bad", "failures"].iloc[0] != ""


class TestRealizedVol:
    def test_excludes_the_current_day(self):
        # Backward-looking by construction, matching v1's rolling_compute.
        s = _series([1.0] * 20 + [50.0])
        rv = realized_vol(s, window=20)
        assert rv.iloc[20] == pytest.approx(0.0)

    def test_warmup_rows_are_nan(self):
        rv = realized_vol(_series(np.arange(30.0)), window=20)
        assert rv.iloc[:20].isna().all()


def test_thresholds_are_the_documented_ones():
    # Guards against silent loosening; docs/v3/phase1_equity_validation.md
    # quotes these numbers.
    assert THRESHOLDS["return_corr_min"] == 0.95
    assert THRESHOLDS["vol_corr_min"] == 0.90
    assert THRESHOLDS["r2_min"] == 0.90
