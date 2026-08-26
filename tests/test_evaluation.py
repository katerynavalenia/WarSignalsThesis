"""Tests for the forecast-evaluation module.

Each statistic is checked against a case where the right answer is known by
construction — a forecast that is exactly the truth, two identical forecasts, a
predictor with real content — rather than against a stored number from a
previous run, which would only prove the code has not changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.evaluation import (  # noqa: E402
    benjamini_hochberg,
    campbell_thompson_r2_oos,
    clark_west,
    diebold_mariano,
    min_detectable_effect_sd,
    simulate_power_r2_oos,
    mse_ratio,
    romano_wolf,
)


@pytest.fixture
def series():
    rng = np.random.default_rng(11)
    n = 400
    idx = pd.date_range("2021-01-01", periods=n, freq="B")
    signal = pd.Series(rng.normal(0, 1, n), index=idx)
    noise = pd.Series(rng.normal(0, 1, n), index=idx)
    actual = signal + noise
    return {
        "idx": idx,
        "actual": actual,
        "benchmark": pd.Series(0.0, index=idx),      # historical-mean benchmark
        "informed": signal * 0.9,                     # genuinely predictive
        "useless": pd.Series(rng.normal(0, 1, n), index=idx),
    }


# --- R²_OS -------------------------------------------------------------------


def test_r2_oos_is_one_for_a_perfect_forecast(series):
    r2 = campbell_thompson_r2_oos(series["actual"], series["actual"], series["benchmark"])
    assert r2 == pytest.approx(1.0)


def test_r2_oos_is_zero_when_model_equals_benchmark(series):
    r2 = campbell_thompson_r2_oos(series["actual"], series["benchmark"], series["benchmark"])
    assert r2 == pytest.approx(0.0)


def test_r2_oos_positive_for_an_informed_forecast(series):
    assert campbell_thompson_r2_oos(series["actual"], series["informed"], series["benchmark"]) > 0.2


def test_r2_oos_negative_for_a_useless_forecast(series):
    assert campbell_thompson_r2_oos(series["actual"], series["useless"], series["benchmark"]) < 0


def test_mse_ratio_is_the_complement(series):
    r2 = campbell_thompson_r2_oos(series["actual"], series["informed"], series["benchmark"])
    ratio = mse_ratio(series["actual"], series["informed"], series["benchmark"])
    assert ratio == pytest.approx(1 - r2)


# --- Diebold-Mariano ---------------------------------------------------------


def test_dm_finds_no_difference_between_identical_forecasts(series):
    with pytest.raises(ValueError, match="variance"):
        diebold_mariano(series["actual"], series["informed"], series["informed"])


def test_dm_detects_a_better_forecast(series):
    r = diebold_mariano(series["actual"], series["useless"], series["informed"])
    assert r.statistic > 0  # A (useless) has the larger loss
    assert r.pvalue < 0.01
    assert r.n == len(series["idx"])


def test_dm_is_symmetric_under_argument_swap(series):
    ab = diebold_mariano(series["actual"], series["useless"], series["informed"])
    ba = diebold_mariano(series["actual"], series["informed"], series["useless"])
    assert ab.statistic == pytest.approx(-ba.statistic)
    assert ab.pvalue == pytest.approx(ba.pvalue)


def test_dm_small_sample_correction_shrinks_the_statistic(series):
    on = diebold_mariano(series["actual"], series["useless"], series["informed"], small_sample=True)
    off = diebold_mariano(series["actual"], series["useless"], series["informed"], small_sample=False)
    assert abs(on.statistic) < abs(off.statistic)
    assert "Harvey" in on.note


def test_dm_rejects_an_unknown_loss(series):
    with pytest.raises(ValueError, match="loss"):
        diebold_mariano(series["actual"], series["useless"], series["informed"], loss="huber")


# --- Clark-West --------------------------------------------------------------


def test_clark_west_detects_a_real_nested_predictor(series):
    r = clark_west(series["actual"], series["benchmark"], series["informed"])
    assert r.statistic > 0
    assert r.pvalue < 0.01


def test_clark_west_does_not_reject_for_a_useless_predictor(series):
    r = clark_west(series["actual"], series["benchmark"], series["useless"])
    assert r.pvalue > 0.05


def test_clark_west_is_more_favourable_than_dm_when_nested(series):
    """The whole point: DM penalises the nested model for estimation noise."""
    cw = clark_west(series["actual"], series["benchmark"], series["useless"])
    dm = diebold_mariano(series["actual"], series["useless"], series["benchmark"])
    assert cw.statistic > -abs(dm.statistic)


# --- power -------------------------------------------------------------------


def test_min_detectable_effect_falls_with_sample_size():
    assert min_detectable_effect_sd(2500) < min_detectable_effect_sd(250)


def test_min_detectable_effect_rises_with_required_power():
    assert min_detectable_effect_sd(1000, power=0.95) > min_detectable_effect_sd(1000, power=0.80)


def test_min_detectable_effect_rejects_a_degenerate_sample():
    with pytest.raises(ValueError, match="two"):
        min_detectable_effect_sd(1)


def test_simulated_power_rises_with_the_implanted_effect():
    """The curve must be monotone, or the power statement means nothing."""
    rng = np.random.default_rng(2)
    y = pd.Series(rng.normal(0, 1, 500))
    out = simulate_power_r2_oos(y, r2_grid=(0.0, 0.05), n_sims=25, min_train=200)
    assert out.loc[out.true_r2_oos == 0.05, "rejection_rate"].iloc[0] > \
        out.loc[out.true_r2_oos == 0.0, "rejection_rate"].iloc[0]


def test_simulated_power_at_zero_effect_is_near_the_nominal_size():
    rng = np.random.default_rng(6)
    y = pd.Series(rng.normal(0, 1, 500))
    out = simulate_power_r2_oos(y, r2_grid=(0.0,), n_sims=60, min_train=200)
    assert out.loc[0, "rejection_rate"] < 0.25  # generous: 60 sims is noisy


def test_simulate_power_rejects_a_short_sample():
    with pytest.raises(ValueError, match="more than"):
        simulate_power_r2_oos(pd.Series(np.zeros(100)), min_train=250)


# --- multiple testing --------------------------------------------------------


def test_benjamini_hochberg_adjusts_upward_and_orders():
    p = pd.Series({"a": 0.001, "b": 0.04, "c": 0.20, "d": 0.90})
    out = benjamini_hochberg(p)
    assert (out["p_adjusted"] >= out["pvalue"] - 1e-12).all()
    assert out.index[0] == "a"
    assert out.loc["a", "reject"]
    assert not out.loc["d", "reject"]


def test_benjamini_hochberg_ignores_missing_pvalues():
    p = pd.Series({"a": 0.01, "b": np.nan, "c": 0.5})
    out = benjamini_hochberg(p)
    assert "b" not in out.index
    assert len(out) == 2


def test_romano_wolf_rejects_only_the_extreme_statistic():
    rng = np.random.default_rng(4)
    stats_ = pd.Series({"big": 6.0, "mid": 0.4, "small": 0.1})
    draws = rng.normal(0, 1, size=(4000, 3))
    out = romano_wolf(stats_, draws)
    assert out.loc["big", "reject"]
    assert not out.loc["small", "reject"]


def test_romano_wolf_stops_stepping_after_a_failure():
    """Step-down: once a hypothesis survives, everything weaker survives too."""
    rng = np.random.default_rng(5)
    stats_ = pd.Series({"a": 0.5, "b": 0.4, "c": 0.3})
    draws = rng.normal(0, 1, size=(2000, 3))
    out = romano_wolf(stats_, draws)
    assert not out["reject"].any()


def test_romano_wolf_validates_the_draw_shape():
    with pytest.raises(ValueError, match="n_tests"):
        romano_wolf(pd.Series({"a": 1.0, "b": 2.0}), np.zeros((10, 3)))


class TestQLIKELoss:
    """QLIKE for variance forecasts — Patton (2011).

    Squared error on a variance is dominated by a handful of extreme days and
    ranks forecasts unreliably, which is why the volatility race is decided on
    QLIKE. These tests pin the properties that make it usable.
    """

    def _dm(self, actual, fa, fb, **kw):
        from src.models.evaluation import diebold_mariano

        return diebold_mariano(pd.Series(actual), pd.Series(fa),
                               pd.Series(fb), loss="qlike", **kw)

    def test_a_perfect_forecast_beats_a_biased_one(self):
        rng = np.random.default_rng(0)
        rv = rng.chisquare(2, 400)
        perfect = np.full(400, 2.0)      # the true mean of chi2(2)
        biased = np.full(400, 8.0)
        r = self._dm(rv, biased, perfect)
        assert r.statistic > 0, "positive statistic must mean the first is worse"
        assert r.pvalue < 0.01

    def test_direction_reverses_when_arguments_swap(self):
        rng = np.random.default_rng(1)
        rv = rng.chisquare(2, 400)
        a, b = np.full(400, 8.0), np.full(400, 2.0)
        assert self._dm(rv, a, b).statistic == pytest.approx(
            -self._dm(rv, b, a).statistic, rel=1e-9)

    def test_zero_realised_variance_does_not_explode(self):
        """A flat day gives a squared return of exactly zero. Without a floor the
        logarithm sends the loss to infinity and one day decides the test."""
        rv = np.concatenate([np.full(199, 1.0), [0.0]])
        r = self._dm(rv, np.full(200, 1.0), np.full(200, 2.0))
        assert np.isfinite(r.statistic) and np.isfinite(r.pvalue)

    def test_qlike_penalises_under_forecasting_asymmetrically(self):
        """QLIKE is asymmetric by design: under-forecasting risk costs more than
        over-forecasting it by the same factor. That asymmetry is the point."""
        from src.models.evaluation import diebold_mariano

        rv = np.full(300, 4.0)
        under, over = np.full(300, 1.0), np.full(300, 16.0)
        # same factor of four in each direction
        r = diebold_mariano(pd.Series(rv), pd.Series(under), pd.Series(over),
                            loss="qlike", small_sample=False)
        assert r.statistic > 0, "under-forecasting should carry the larger loss"

    def test_unknown_loss_is_rejected(self):
        from src.models.evaluation import diebold_mariano

        with pytest.raises(ValueError, match="unknown loss"):
            diebold_mariano(pd.Series([1.0, 2.0]), pd.Series([1.0, 1.0]),
                            pd.Series([2.0, 2.0]), loss="qlik")
