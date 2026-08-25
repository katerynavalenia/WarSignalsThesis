"""Tests for the structural-break tests and the three added evaluation methods.

Offline, and checked against cases where the answer is known by construction: a
series with an implanted level shift, a series with none, a set of identical
models, and a forecast that is the truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.breaks import chow_test, supremum_break  # noqa: E402
from src.models.evaluation import (  # noqa: E402
    combine_forecasts,
    economic_value,
    model_confidence_set,
)


@pytest.fixture
def with_break() -> pd.Series:
    """Flat, then a one-unit level shift a third of the way through."""
    idx = pd.date_range("2020-01-01", periods=600, freq="D")
    rng = np.random.default_rng(0)
    y = rng.normal(0, 0.3, 600)
    y[200:] += 1.0
    return pd.Series(y, index=idx)


@pytest.fixture
def without_break() -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=600, freq="D")
    return pd.Series(np.random.default_rng(1).normal(0, 0.3, 600), index=idx)


# --- Chow --------------------------------------------------------------------


def test_chow_detects_a_break_at_the_true_date(with_break):
    r = chow_test(with_break, with_break.index[200])
    assert r.pvalue < 0.001
    assert r.n == 600


def test_chow_does_not_reject_when_there_is_no_break(without_break):
    assert chow_test(without_break, without_break.index[300]).pvalue > 0.05


def test_chow_at_the_wrong_date_is_weaker_than_at_the_right_one(with_break):
    right = chow_test(with_break, with_break.index[200]).statistic
    wrong = chow_test(with_break, with_break.index[450]).statistic
    assert right > wrong


def test_chow_rejects_a_break_too_close_to_the_edge(with_break):
    with pytest.raises(ValueError, match="at least 10"):
        chow_test(with_break, with_break.index[3])


# --- supremum / Bai-Perron ---------------------------------------------------


def test_supremum_finds_the_break_without_being_told(with_break):
    r = supremum_break(with_break, n_boot=100)
    assert r.pvalue < 0.05
    offset = abs((r.break_date - with_break.index[200]).days)
    assert offset < 30, f"located the break {offset} days from the truth"


def test_supremum_does_not_reject_on_a_stationary_series(without_break):
    assert supremum_break(without_break, n_boot=200).pvalue > 0.05


def test_supremum_needs_enough_observations():
    short = pd.Series(np.zeros(30), index=pd.date_range("2020-01-01", periods=30))
    with pytest.raises(ValueError, match="at least 60"):
        supremum_break(short)


# --- Model Confidence Set ----------------------------------------------------


def test_mcs_keeps_everything_when_models_are_identical():
    rng = np.random.default_rng(2)
    base = rng.normal(1, 0.1, 400)
    losses = pd.DataFrame({f"m{i}": base + rng.normal(0, 1e-9, 400) for i in range(3)})
    out = model_confidence_set(losses, n_boot=200)
    assert out["in_confidence_set"].all()


def test_mcs_eliminates_a_clearly_worse_model():
    rng = np.random.default_rng(3)
    n = 600
    losses = pd.DataFrame({
        "good": rng.normal(1.0, 0.2, n),
        "also_good": rng.normal(1.0, 0.2, n),
        "terrible": rng.normal(5.0, 0.2, n),
    })
    out = model_confidence_set(losses, n_boot=300)
    assert not out.loc["terrible", "in_confidence_set"]


def test_mcs_needs_two_models():
    with pytest.raises(ValueError, match="at least two"):
        model_confidence_set(pd.DataFrame({"only": [1.0, 2.0, 3.0]}))


# --- combination -------------------------------------------------------------


def test_combination_averages_and_reduces_noise():
    rng = np.random.default_rng(4)
    n = 500
    signal = rng.normal(0, 1, n)
    noisy = pd.DataFrame({f"f{i}": signal + rng.normal(0, 2, n) for i in range(8)})
    combo = combine_forecasts(noisy)
    truth = pd.Series(signal)
    assert combo.corr(truth) > noisy.corrwith(truth).max()


def test_combination_median_is_available_and_differs():
    f = pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 2.0], "c": [10.0, 20.0]})
    assert combine_forecasts(f, "median").tolist() == [1.0, 2.0]
    assert combine_forecasts(f, "mean").iloc[0] == pytest.approx(4.0)


def test_combination_rejects_unknown_method():
    with pytest.raises(ValueError, match="unknown method"):
        combine_forecasts(pd.DataFrame({"a": [1.0, 2.0]}), "geometric")


# --- economic value ----------------------------------------------------------


@pytest.fixture
def timing_case():
    rng = np.random.default_rng(5)
    n = 500
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    signal = pd.Series(rng.normal(0, 0.5, n), index=idx)
    actual = signal + pd.Series(rng.normal(0, 0.5, n), index=idx)
    return actual, signal, pd.Series(0.0, index=idx)


def test_economic_value_rewards_a_forecast_with_real_content(timing_case):
    actual, signal, bench = timing_case
    out = economic_value(actual, signal, bench)
    assert out["cer_gain_pct"] > 0
    assert out["sharpe_model"] > out["sharpe_benchmark"] or np.isnan(out["sharpe_benchmark"])


def test_economic_value_transaction_costs_reduce_the_gain(timing_case):
    actual, signal, bench = timing_case
    free = economic_value(actual, signal, bench, cost_bps=0)
    costly = economic_value(actual, signal, bench, cost_bps=50)
    assert costly["cer_gain_pct"] < free["cer_gain_pct"]


def test_economic_value_needs_enough_observations():
    s = pd.Series(np.zeros(30), index=pd.date_range("2020-01-01", periods=30))
    with pytest.raises(ValueError, match="at least 60"):
        economic_value(s, s, s)
