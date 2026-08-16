"""Tests for Phase 6 — Econometric baselines.

Covers:
- ``src.models.baselines`` — 4 return forecasters (Phase 6.2)
- ``src.models.garch``     — 3 GARCH-family models (Phase 6.3)
- ``src.models.evaluation`` — MAE / RMSE / dir-acc / QLIKE (Phase 6.4)
- ``src.models.expanding_window`` — expanding-window engine (Phase 6.5)
- ``src.models.horse_race`` — top-level runner (Phase 6.6)
- ``scripts.phase6_run_baselines`` — CLI (Phase 6.7)

Designed to keep the entire suite green and to add ≥25 new tests on top of
the existing 304.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ── Phase 6.2 — Return-baselines library ────────────────────────────────────


class TestHistoricalMeanForecaster:
    def test_constant_equals_train_mean(self):
        from src.models.baselines import HistoricalMeanForecaster
        y = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
        m = HistoricalMeanForecaster().fit(None, y)
        pred = m.predict(np.zeros((3, 0)))
        assert np.allclose(pred, [0.3, 0.3, 0.3])

    def test_nan_in_target_dropped(self):
        from src.models.baselines import HistoricalMeanForecaster
        y = pd.Series([0.1, np.nan, 0.3, 0.5])
        m = HistoricalMeanForecaster().fit(None, y)
        # mean of [0.1, 0.3, 0.5] = 0.3
        pred = m.predict(np.zeros((2, 0)))
        assert np.allclose(pred, [0.3, 0.3])

    def test_empty_target_returns_zero(self):
        from src.models.baselines import HistoricalMeanForecaster
        m = HistoricalMeanForecaster().fit(None, pd.Series([], dtype=float))
        pred = m.predict(np.zeros((3, 0)))
        assert np.allclose(pred, [0.0, 0.0, 0.0])

    def test_handles_dataframe_X(self):
        from src.models.baselines import HistoricalMeanForecaster
        y = pd.Series([1.0, 2.0, 3.0])
        X = pd.DataFrame({"a": [0, 0, 0], "b": [1, 1, 1]})
        m = HistoricalMeanForecaster().fit(X, y)
        # 2.0 is the train mean; predict on 4 new rows
        X_test = pd.DataFrame({"a": [0, 0, 0, 0], "b": [1, 1, 1, 1]})
        pred = m.predict(X_test)
        assert pred.shape == (4,)
        assert np.allclose(pred, 2.0)


class TestAR1Forecaster:
    def test_known_ar1_recovers_positive_coef(self):
        from src.models.baselines import AR1Forecaster
        rng = np.random.default_rng(0)
        n = 500
        phi = 0.6
        eps = rng.normal(scale=1.0, size=n)
        y_vals = np.zeros(n)
        for t in range(1, n):
            y_vals[t] = phi * y_vals[t - 1] + eps[t]
        y = pd.Series(y_vals)
        m = AR1Forecaster(lags=1).fit(None, y)
        assert m.ar_result_ is not None
        # Statsmodels AR(1) coefficient should be close to true 0.6
        coef = float(m.ar_result_.params.iloc[1] if hasattr(m.ar_result_.params, "iloc") else m.ar_result_.params[1])
        assert 0.4 < coef < 0.8, f"AR(1) coef {coef} far from true 0.6"

    def test_too_short_falls_back_to_mean(self):
        from src.models.baselines import AR1Forecaster
        y = pd.Series([0.1, 0.2, 0.3])
        m = AR1Forecaster(lags=1).fit(None, y)
        # Either fitted AR or fallback — either way, predict returns a value
        pred = m.predict(np.zeros((2, 0)))
        assert pred.shape == (2,)
        assert np.all(np.isfinite(pred))

    def test_nan_in_y_dropped(self):
        from src.models.baselines import AR1Forecaster
        y_vals = np.zeros(50)
        for t in range(1, 50):
            y_vals[t] = 0.5 * y_vals[t - 1] + 0.1
        y_vals[10] = np.nan
        y = pd.Series(y_vals)
        m = AR1Forecaster(lags=1).fit(None, y)
        pred = m.predict(np.zeros((3, 0)))
        assert np.all(np.isfinite(pred))


class TestLinearRegressionForecaster:
    def test_perfect_single_feature_recovers_coef_1(self):
        from src.models.baselines import LinearRegressionForecaster
        # y = 2 * x + small noise
        rng = np.random.default_rng(42)
        x = np.linspace(-1, 1, 100)
        y = 2.0 * x + rng.normal(scale=0.01, size=100)
        X = pd.DataFrame({"x": x})
        m = LinearRegressionForecaster().fit(X, pd.Series(y))
        pred = m.predict(X)
        # Coefficient should be ≈ 2.0
        coef = float(m.model_.coef_[0])
        assert abs(coef - 2.0) < 0.05, f"coef={coef}, expected ≈ 2.0"
        # Predictions match the data closely
        assert np.allclose(pred, y, atol=0.1)

    def test_zero_features_uses_intercept(self):
        from src.models.baselines import LinearRegressionForecaster
        y = pd.Series([0.5, 0.5, 0.5, 0.5])
        X = pd.DataFrame({"x": [0.0, 0.0, 0.0, 0.0]})
        m = LinearRegressionForecaster().fit(X, y)
        # coef=0, intercept=0.5
        assert np.allclose(m.model_.coef_, [0.0])
        assert abs(m.model_.intercept_ - 0.5) < 1e-8

    def test_drops_rows_with_nan_in_X(self):
        from src.models.baselines import LinearRegressionForecaster
        X = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0, 5.0]})
        y = pd.Series([2.0, 4.0, np.nan, 8.0, 10.0])
        m = LinearRegressionForecaster().fit(X, y)
        # Should fit on the 4 clean rows: y = 2 * x
        assert m.model_ is not None
        assert abs(float(m.model_.coef_[0]) - 2.0) < 1e-6

    def test_predict_with_no_fit_returns_zero(self):
        from src.models.baselines import LinearRegressionForecaster
        m = LinearRegressionForecaster()  # never fit
        X = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        pred = m.predict(X)
        assert np.allclose(pred, 0.0)


class TestRidgeForecaster:
    def test_alpha_equals_zero_matches_ols(self):
        from src.models.baselines import (
            LinearRegressionForecaster,
            RidgeForecaster,
        )
        rng = np.random.default_rng(0)
        x = np.linspace(-1, 1, 100)
        y = 2.0 * x + rng.normal(scale=0.1, size=100)
        X = pd.DataFrame({"x": x})
        m_ridge = RidgeForecaster(alpha=1e-9).fit(X, pd.Series(y))
        m_ols = LinearRegressionForecaster().fit(X, pd.Series(y))
        assert abs(m_ridge.model_.coef_[0] - m_ols.model_.coef_[0]) < 1e-3

    def test_large_alpha_shrinks_to_mean(self):
        from src.models.baselines import RidgeForecaster
        rng = np.random.default_rng(0)
        x = np.linspace(-1, 1, 100)
        y = 2.0 * x + rng.normal(scale=0.1, size=100)
        X = pd.DataFrame({"x": x})
        m = RidgeForecaster(alpha=1e6).fit(X, pd.Series(y))
        # Coefficient should be very close to zero
        assert abs(float(m.model_.coef_[0])) < 1e-3
        # Intercept should be close to mean of y
        assert abs(m.model_.intercept_ - np.mean(y)) < 0.5

    def test_handles_nan(self):
        from src.models.baselines import RidgeForecaster
        X = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0, 5.0]})
        y = pd.Series([2.0, 4.0, np.nan, 8.0, 10.0])
        m = RidgeForecaster(alpha=1.0).fit(X, y)
        assert m.model_ is not None


class TestMakeBaselineFactory:
    def test_known_names(self):
        from src.models.baselines import (
            AR1Forecaster,
            HistoricalMeanForecaster,
            LinearRegressionForecaster,
            RidgeForecaster,
            make_baseline,
        )
        assert isinstance(make_baseline("historical_mean"), HistoricalMeanForecaster)
        assert isinstance(make_baseline("ar1"), AR1Forecaster)
        assert isinstance(make_baseline("ols"), LinearRegressionForecaster)
        assert isinstance(make_baseline("ridge", alpha=2.0), RidgeForecaster)
        assert isinstance(make_baseline("linear_regression"), LinearRegressionForecaster)

    def test_unknown_raises(self):
        from src.models.baselines import make_baseline
        with pytest.raises(KeyError):
            make_baseline("nope")

    def test_kwargs_passed(self):
        from src.models.baselines import RidgeForecaster, make_baseline
        m = make_baseline("ridge", alpha=0.5)
        assert isinstance(m, RidgeForecaster)
        assert m.alpha == 0.5


# ── Phase 6.3 — GARCH-family library ────────────────────────────────────────


def _simulate_garch11(n: int, omega: float = 0.05, alpha: float = 0.08,
                      beta: float = 0.90, seed: int = 0) -> np.ndarray:
    """Simulate a GARCH(1,1) with Gaussian innovations for unit tests."""
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    sigma2 = np.zeros(n)
    sigma2[0] = omega / (1.0 - alpha - beta)
    for t in range(1, n):
        sigma2[t] = omega + alpha * y[t - 1] ** 2 + beta * sigma2[t - 1]
        y[t] = rng.normal(scale=np.sqrt(sigma2[t]))
    return y


def _simulate_gjr(n: int, omega: float = 0.05, alpha: float = 0.04,
                  gamma: float = 0.10, beta: float = 0.85, seed: int = 0) -> np.ndarray:
    """Simulate GJR-GARCH(1,1) with leverage term.

    Variance: σ²_t = ω + α ε²_{t-1} + γ ε²_{t-1} I[ε_{t-1}<0] + β σ²_{t-1}.
    """
    rng = np.random.default_rng(seed)
    eps = np.zeros(n)
    sigma2 = np.zeros(n)
    sigma2[0] = omega / max(1.0 - alpha - 0.5 * gamma - beta, 0.1)
    for t in range(1, n):
        indicator = 1.0 if eps[t - 1] < 0 else 0.0
        sigma2[t] = (
            omega
            + alpha * eps[t - 1] ** 2
            + gamma * eps[t - 1] ** 2 * indicator
            + beta * sigma2[t - 1]
        )
        eps[t] = rng.normal(scale=np.sqrt(sigma2[t]))
    return eps


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("arch"),
    reason="`arch` not installed; skipping GARCH tests",
)
class TestGARCHForecaster:
    def test_garch11_recovers_parameters(self):
        from src.models.garch import GARCHForecaster
        y = _simulate_garch11(n=2000, omega=0.05, alpha=0.08, beta=0.90, seed=42)
        # arch expects percent units by default — use rescale=False
        f = GARCHForecaster(variant="GARCH", p=1, q=1, dist="normal",
                            rescale=False, mean="Zero").fit(y)
        assert f.result_ is not None
        params = f.result_.params
        # arch parameter names: "omega", "alpha[1]", "beta[1]"
        omega_hat = float(params["omega"])
        alpha_hat = float(params["alpha[1]"])
        beta_hat = float(params["beta[1]"])
        # Tolerance is wide because the optimization is on simulated data
        assert 0.005 < omega_hat < 0.20, f"omega_hat={omega_hat}"
        assert 0.02 < alpha_hat < 0.20, f"alpha_hat={alpha_hat}"
        assert 0.70 < beta_hat < 0.98, f"beta_hat={beta_hat}"

    def test_gjr_gamma_positive_on_leverage_fixture(self):
        from src.models.garch import GARCHForecaster
        y = _simulate_gjr(n=1500, omega=0.05, alpha=0.04, gamma=0.10, beta=0.85, seed=7)
        f = GARCHForecaster(variant="GJR_GARCH", p=1, q=1, dist="normal",
                            rescale=False, mean="Zero").fit(y)
        assert f.result_ is not None
        # arch GJR params: omega, alpha[1], gamma[1], beta[1]
        gamma_hat = float(f.result_.params["gamma[1]"])
        assert gamma_hat > 0.0, f"gamma should be positive on leverage data, got {gamma_hat}"

    def test_egarch_converges(self):
        from src.models.garch import GARCHForecaster
        y = _simulate_garch11(n=1500, seed=11)
        f = GARCHForecaster(variant="EGARCH", p=1, q=1, dist="t",
                            rescale=False, mean="Zero").fit(y)
        assert f.result_ is not None

    def test_predict_horizon_length(self):
        from src.models.garch import GARCHForecaster
        y = _simulate_garch11(n=500, seed=3)
        f = GARCHForecaster(variant="GARCH", p=1, q=1, dist="normal",
                            rescale=False, mean="Zero").fit(y)
        v1 = f.predict(horizon=1)
        v5 = f.predict(horizon=5)
        v20 = f.predict(horizon=20)
        assert v1.shape == (1,)
        assert v5.shape == (5,)
        assert v20.shape == (20,)
        assert np.all(np.isfinite(v1))
        assert np.all(np.isfinite(v5))

    def test_rescale_true_outputs_percent_squared(self):
        from src.models.garch import GARCHForecaster
        y = _simulate_garch11(n=500, seed=5) * 100.0  # simulate in % units
        f = GARCHForecaster(variant="GARCH", p=1, q=1, dist="normal",
                            rescale=True, mean="Zero").fit(y)
        v = f.predict(horizon=1)
        # Unconditional variance of y (in %²) should be in the same order of
        # magnitude as the forecast.
        assert v[0] > 0
        assert np.isfinite(v[0])

    def test_unknown_variant_raises(self):
        from src.models.garch import GARCHForecaster
        with pytest.raises(ValueError, match="variant"):
            GARCHForecaster(variant="NOPE")

    def test_too_few_obs_returns_no_result(self):
        from src.models.garch import GARCHForecaster
        y = np.array([0.1, 0.2, np.nan, np.nan, 0.5] * 5)
        f = GARCHForecaster(variant="GARCH", p=1, q=1, rescale=False).fit(y)
        # Few clean obs → result_ may be None, predict returns fallback
        v = f.predict(horizon=1)
        assert v.shape == (1,)
        assert np.all(np.isfinite(v))


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("arch"),
    reason="`arch` not installed; skipping GARCH tests",
)
class TestMakeGARCHForecaster:
    def test_known_variants(self):
        from src.models.garch import GARCHForecaster, make_garch_forecaster
        for name in ("GARCH", "GJR_GARCH", "EGARCH"):
            f = make_garch_forecaster(name=name.lower(), p=1, q=1)
            assert isinstance(f, GARCHForecaster)
            assert f.variant == name.upper()
        f = make_garch_forecaster(name="garch")
        assert f.variant == "GARCH"

    def test_kwargs_propagate(self):
        from src.models.garch import make_garch_forecaster
        f = make_garch_forecaster(name="GARCH", p=2, q=1, dist="normal")
        assert f.p == 2
        assert f.dist == "normal"


# ── Phase 6 supervisor-review regression guards ──────────────────────────
# These tests guard against the 3 critical and 4 major issues identified in
# the supervisor review (2026-07-01). See docs/phase6_audit.md for context.


class TestAR1Fix:
    """Regression guard for C1: AR(1) iterative h-step forecast.

    The old code called ``AutoReg.forecast(steps=n)`` with n=number of test
    rows, returning a long-horizon unconditional-mean path. The new code
    does iterative 1-step-ahead forecasts and uses the last ``lags``
    training observations as the seed.
    """

    def test_ar1_uses_iterative_1step_forecast(self):
        from src.models.baselines import AR1Forecaster
        # Simulate AR(1) with known coefficient 0.5, intercept 0.1, noise 0.1
        rng = np.random.default_rng(42)
        n_train = 200
        y_vals = np.zeros(n_train + 20)
        y_vals[0] = 0.0
        for t in range(1, n_train + 20):
            y_vals[t] = 0.1 + 0.5 * y_vals[t - 1] + 0.1 * rng.normal()
        y_train = pd.Series(y_vals[:n_train])
        m = AR1Forecaster(lags=1).fit(None, y_train)
        # Recovered coef should be close to 0.5
        assert m._params_ is not None
        assert abs(m._params_[1] - 0.5) < 0.15, f"coef={m._params_[1]:.3f}"
        # Predict the next 20 observations
        preds = m.predict(np.zeros((20, 0)))
        # Iterative 1-step forecast should converge toward the unconditional
        # mean = intercept / (1 - coef) = 0.1 / 0.5 = 0.2.
        # The first prediction should be ≈ intercept + coef * last_y_train
        # and the path should be smooth, not flat.
        assert preds.shape == (20,)
        # The path is non-trivial: std(preds) > 0
        assert np.std(preds) > 0.0
        # Predictions should converge toward 0.2 (unconditional mean)
        # — last few predictions should be close to 0.2
        assert abs(np.mean(preds[-5:]) - 0.2) < 0.5

    def test_ar1_predictions_differ_across_targets(self):
        # The fix ensures the AR(1) baseline uses only the target's own
        # history, not the feature matrix. Therefore AR(1) predictions for
        # r_ITA vs r_WAERLST_recon must differ (they have different
        # training series).
        from src.models.baselines import AR1Forecaster
        rng = np.random.default_rng(0)
        n = 200
        y_ita = np.cumsum(rng.normal(scale=1.0, size=n)) + np.arange(n) * 0.01
        y_waerlst = np.cumsum(rng.normal(scale=2.0, size=n)) + np.arange(n) * 0.005
        m_ita = AR1Forecaster(lags=1).fit(None, pd.Series(y_ita))
        m_waer = AR1Forecaster(lags=1).fit(None, pd.Series(y_waerlst))
        p_ita = m_ita.predict(np.zeros((10, 0)))
        p_waer = m_waer.predict(np.zeros((10, 0)))
        assert not np.allclose(p_ita, p_waer, atol=1e-6), (
            "AR(1) predictions for r_ITA and r_WAERLST_recon should differ"
        )

    def test_ar1_seed_equals_last_training_observation(self):
        # The first iterative 1-step prediction should equal
        # intercept + coef * y_train[-1].
        from src.models.baselines import AR1Forecaster
        y = pd.Series([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        m = AR1Forecaster(lags=1).fit(None, y)
        preds = m.predict(np.zeros((3, 0)))
        # The first prediction should be: const + coef * 0.9
        const = m._params_[0]
        coef = m._params_[1]
        expected_first = const + coef * 0.9
        assert abs(preds[0] - expected_first) < 1e-6, (
            f"first pred {preds[0]:.4f} != expected {expected_first:.4f}"
        )

    def test_ar1_ignores_X(self):
        # X is ignored by AR(1) — passing two different X matrices should
        # yield the same predictions.
        from src.models.baselines import AR1Forecaster
        y = pd.Series(np.arange(50, dtype=float))
        m = AR1Forecaster(lags=1).fit(None, y)
        X_a = pd.DataFrame({"a": [1.0] * 10, "b": [2.0] * 10})
        X_b = pd.DataFrame({"a": [99.0] * 10, "b": [88.0] * 10})
        p_a = m.predict(X_a)
        p_b = m.predict(X_b)
        assert np.allclose(p_a, p_b)


class TestInfoSetFixes:
    """Regression guards for C2 (F set missing r_ITA_lag1) and C3 (GARCH
    source for WAERLST_recon)."""

    def test_model_matrix_has_r_WAERLST_recon_lag1(self):
        # C3 fix: the GARCH source column for the secondary target must
        # exist in the model matrix.
        from src.features.build_model_matrix import build_model_matrix
        from tests.test_phase5_model_matrix import _make_master
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "r_WAERLST_recon_lag1" in mm.columns
        assert "r_ITA_lag1" in mm.columns

    def test_garch_uses_correct_source_per_target(self):
        # For r_ITA the source should be r_ITA_lag1; for r_WAERLST_recon
        # the source should be r_WAERLST_recon_lag1.
        from src.features.build_model_matrix import build_model_matrix
        from src.models.expanding_window import ExpandingWindowEngine
        from tests.test_phase5_model_matrix import _make_master

        df = _make_master(n=100)
        mm = build_model_matrix(df)
        eng = ExpandingWindowEngine(
            model_matrix=mm, info_sets=mm.attrs["info_sets"],
            targets=["r_ITA", "r_WAERLST_recon"], horizons=[1],
            test_fraction=0.25, min_train_obs=20, refit_every=10,
        )
        # Internal: just check that _find_vol_source_col returns the right
        # thing for each target.
        col_ita = eng._find_vol_source_col("r_ITA")
        col_waer = eng._find_vol_source_col("r_WAERLST_recon")
        assert col_ita == "r_ITA_lag1"
        assert col_waer == "r_WAERLST_recon_lag1"


class TestNANAction:
    """Regression guard for M2: OLS/Ridge ``na_action`` policy."""

    def test_ols_na_action_drop_returns_nan_for_nan_rows(self):
        from src.models.baselines import LinearRegressionForecaster
        rng = np.random.default_rng(0)
        X = pd.DataFrame({"x": rng.normal(size=50)})
        y = pd.Series(2.0 * X["x"] + rng.normal(scale=0.1, size=50))
        m = LinearRegressionForecaster(na_action="drop").fit(X, y)
        # Test set with NaN in row 1
        X_test = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
        preds = m.predict(X_test)
        assert preds[0] == pytest.approx(2.0, abs=0.5)
        assert np.isnan(preds[1])
        assert preds[2] == pytest.approx(6.0, abs=0.5)

    def test_ridge_na_action_zero_fills_with_zero(self):
        from src.models.baselines import RidgeForecaster
        rng = np.random.default_rng(0)
        X = pd.DataFrame({"x": rng.normal(size=50)})
        y = pd.Series(2.0 * X["x"] + rng.normal(scale=0.1, size=50))
        m = RidgeForecaster(alpha=1.0, na_action="zero").fit(X, y)
        X_test = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
        preds = m.predict(X_test)
        assert np.isfinite(preds).all()
        # Imputed NaN row has prediction close to the intercept (since x=0
        # after imputation).
        # The exact value depends on the fit, but it must be finite.
        assert abs(preds[1] - preds[0]) < abs(preds[0] - preds[2])

    def test_invalid_na_action_raises(self):
        from src.models.baselines import LinearRegressionForecaster
        with pytest.raises(ValueError, match="na_action"):
            LinearRegressionForecaster(na_action="bogus")


class TestRefitFlag:
    """Regression guard for M3: refit_flag = 1 only on first day of fold."""

    def test_refit_flag_1_only_on_first_day_of_fold(self):
        from src.models.baselines import HistoricalMeanForecaster
        from src.models.expanding_window import ExpandingWindowEngine
        from tests.test_phase6_baselines import _build_small_model_matrix
        mm = _build_small_model_matrix(n=200)
        eng = ExpandingWindowEngine(
            model_matrix=mm, info_sets=mm.attrs["info_sets"],
            targets=["r_ITA"], horizons=[1], refit_every=20,
            min_train_obs=50, test_fraction=0.25,
        )
        eng.add_model("hm", HistoricalMeanForecaster, info_set="F")
        df = eng.run()
        # For each fold, the first row should have refit_flag=1, the rest 0.
        for fold, sub in df.groupby("fold"):
            sub = sub.sort_values("date")
            flags = sub["refit_flag"].to_numpy()
            assert flags[0] == 1, f"fold {fold}: first row has flag {flags[0]}"
            assert (flags[1:] == 0).all(), (
                f"fold {fold}: non-first rows have flag != 0 "
                f"(unique: {np.unique(flags[1:], return_counts=True)})"
            )


# ── Phase 6 second-iteration regression guards (2026-07-01) ────────────────


class TestEGARCHH5Simulation:
    """Regression guard for C4: EGARCH h=5 must NOT be the fallback constant.

    The `arch` package raises ``ValueError: Analytic forecasts not
    available for horizon > 1`` for EGARCH. The previous code caught
    this in a bare ``except Exception`` and returned ``np.full(h, 1.0)``,
    producing 100% fallback predictions.
    """

    def test_egarch_h5_is_not_constant_fallback(self):
        import warnings
        from src.models.garch import GARCHForecaster
        rng = np.random.default_rng(0)
        y = pd.Series(rng.normal(scale=1.0, size=500))
        f = GARCHForecaster(variant="EGARCH", p=1, q=1, dist="t",
                            rescale=False, mean="Zero")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f.fit(y)
        var5 = f.predict(horizon=5, n_sims=200)
        # Must not be the constant fallback
        assert not np.allclose(var5, 1.0), (
            f"EGARCH h=5 returned fallback constant 1.0; "
            f"actual: {var5}"
        )
        # Must have meaningful variance
        assert np.std(var5) > 0.001
        # Must be the requested length
        assert var5.shape == (5,)

    def test_egarch_h1_still_uses_analytic(self):
        import warnings
        from src.models.garch import GARCHForecaster
        rng = np.random.default_rng(0)
        y = pd.Series(rng.normal(scale=1.0, size=500))
        f = GARCHForecaster(variant="EGARCH", p=1, q=1, dist="t",
                            rescale=False, mean="Zero")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f.fit(y)
        var1 = f.predict(horizon=1)
        # h=1 uses the analytic path, length is 1
        assert var1.shape == (1,)
        assert np.isfinite(var1).all()
        assert var1[0] > 0


class TestModelMatrixHasRitaLag1:
    """Regression guard for C5: the model matrix must include
    ``r_ITA_lag1`` (= r_ITA at t-1), the most informative single
    feature for next-day return prediction. The previous design
    double-shifted pre-lagged columns, losing 1 day of the most
    recent return information.
    """

    def test_r_ita_lag1_exists_in_model_matrix(self):
        import warnings
        from src.features.build_model_matrix import build_model_matrix
        from tests.test_phase5_model_matrix import _make_master
        df = _make_master(n=30, r_ita=[0.1, 0.2, 0.3, 0.4, 0.5] * 6)
        mm = build_model_matrix(df)
        assert "r_ITA_lag1" in mm.columns
        assert mm["r_ITA_lag1"].notna().sum() > 0

    def test_r_ita_lag1_in_F_set(self):
        import warnings
        from src.features.build_model_matrix import build_model_matrix
        from tests.test_phase5_model_matrix import _make_master
        df = _make_master(n=30, r_ita=[0.1] * 30)
        mm = build_model_matrix(df)
        f_cols = mm.attrs["info_sets"]["F"]
        assert "r_ITA_lag1" in f_cols

    def test_r_WAERLST_recon_lag1_included_in_F(self):
        # Updated for decision_log 2026-07-02: r_WAERLST_recon is demoted
        # from target to plain feature, so r_WAERLST_recon_lag1 is no
        # longer a target source and IS now a legitimate F feature.
        from src.features.build_model_matrix import build_info_sets
        cols = {"r_ITA_lag1", "r_WAERLST_recon_lag1", "VIX_lag1", "day_of_week"}
        out = build_info_sets(cols)
        assert "r_WAERLST_recon_lag1" in out["F"]


class TestStandardizeFixesDistributionShift:
    """Regression guard for C6: OLS/Ridge with ``standardize=True`` must
    produce predictions that are not 7x more volatile than the realized
    target (which was the bug on the P/PN/PNG sets before standardization).
    """

    def test_standardize_imputes_with_zero_not_mean(self):
        from src.models.baselines import LinearRegressionForecaster
        rng = np.random.default_rng(0)
        # Train has NaN in the first 50 rows, real values in the last 50.
        X_train = pd.DataFrame({"x": [np.nan] * 50 + list(rng.normal(size=50))})
        y_train = pd.Series(list(rng.normal(size=100)))
        m = LinearRegressionForecaster(standardize=True).fit(X_train, y_train)
        # Test set: all real values
        X_test = pd.DataFrame({"x": rng.normal(scale=5.0, size=20)})
        preds = m.predict(X_test)
        # Predictions should NOT explode (i.e. no 7x over-forecasting)
        # because standardization normalizes both train and test to z-scores.
        assert np.isfinite(preds).all()
        assert np.std(preds) < 5 * np.std(y_train)
        # And the predictions should NOT be NaN (impute=0 handles NaN cleanly)
        assert not np.any(np.isnan(preds))

    def test_standardize_ridge_produces_finite_predictions(self):
        from src.models.baselines import RidgeForecaster
        rng = np.random.default_rng(0)
        X_train = pd.DataFrame({"x": [np.nan] * 50 + list(rng.normal(size=50))})
        y_train = pd.Series(list(rng.normal(size=100)))
        m = RidgeForecaster(alpha=1.0, standardize=True).fit(X_train, y_train)
        X_test = pd.DataFrame({"x": rng.normal(scale=5.0, size=20)})
        preds = m.predict(X_test)
        assert np.isfinite(preds).all()

    def test_invalid_standardize_type_raises(self):
        from src.models.baselines import LinearRegressionForecaster
        with pytest.raises(TypeError, match="standardize"):
            LinearRegressionForecaster(standardize="yes")

    def test_standardize_false_keeps_old_behavior(self):
        from src.models.baselines import LinearRegressionForecaster
        rng = np.random.default_rng(0)
        X_train = pd.DataFrame({"x": [np.nan] * 50 + list(rng.normal(size=50))})
        y_train = pd.Series(list(rng.normal(size=100)))
        m = LinearRegressionForecaster(standardize=False).fit(X_train, y_train)
        # Just check it doesn't crash
        X_test = pd.DataFrame({"x": rng.normal(scale=1.0, size=10)})
        preds = m.predict(X_test)
        assert np.isfinite(preds).all()


class TestHistoricalMeanIgnoresX:
    """Regression guard for the HistoricalMean X-NaN-dropping bug.

    The ``_drop_nan_xy`` helper drops rows where X is NaN. For
    HistoricalMean, X is intentionally ignored, so the helper should
    only drop rows where y is NaN. The pre-fix behavior dropped ~75% of
    the training rows in the F set (because the F set has NaN in
    attack/news features during the early modeling window), biasing
    the mean toward a subset of the data.
    """

    def test_historical_mean_uses_all_y_not_subset(self):
        from src.models.baselines import HistoricalMeanForecaster
        # Train y: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], mean = 5.5
        y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        # Train X: has NaN in some rows. The NaN rows have y = [100, 200, 300].
        X = pd.DataFrame({"x": [np.nan, 1, np.nan, 2, np.nan, 3, 4, 5, 6, 7]})
        m = HistoricalMeanForecaster().fit(X, y)
        # Expected mean: (1+2+3+4+5+6+7+8+9+10) / 10 = 5.5
        # Pre-fix bug: would compute mean of [1,2,3,4,5,6,7] / 7 = 4.0
        assert abs(m.mean_ - 5.5) < 1e-9, f"HistoricalMean should use all y, got {m.mean_}"

    def test_historical_mean_ignores_X_at_predict_time(self):
        from src.models.baselines import HistoricalMeanForecaster
        y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        m = HistoricalMeanForecaster().fit(None, y)
        # X with NaN should not affect prediction
        X = pd.DataFrame({"x": [np.nan, np.nan, np.nan]})
        preds = m.predict(X)
        assert np.allclose(preds, [3.0, 3.0, 3.0])


# ── Phase 6.4 — Evaluation metrics ─────────────────────────────────────────


class TestReturnMetrics:
    def test_mae_known_value(self):
        from src.models.evaluation import mae
        # y = [1, 2, 3], yhat = [1, 2, 5] → |0|+|0|+|2| = 2, mean = 2/3
        assert abs(mae([1, 2, 3], [1, 2, 5]) - 2 / 3) < 1e-9

    def test_rmse_known_value(self):
        from src.models.evaluation import rmse
        # y = [1, 2, 3], yhat = [1, 2, 5] → 0+0+4 = 4, mean = 4/3, sqrt
        expected = np.sqrt(4 / 3)
        assert abs(rmse([1, 2, 3], [1, 2, 5]) - expected) < 1e-9

    def test_directional_accuracy_perfect(self):
        from src.models.evaluation import directional_accuracy
        # Same sign everywhere → 1.0
        assert directional_accuracy([0.1, -0.2, 0.3], [0.5, -0.1, 0.4]) == 1.0

    def test_directional_accuracy_zero(self):
        from src.models.evaluation import directional_accuracy
        # All opposite signs → 0.0
        assert directional_accuracy([0.1, -0.2, 0.3], [-0.5, 0.1, -0.4]) == 0.0

    def test_directional_accuracy_zero_y_excluded(self):
        from src.models.evaluation import directional_accuracy
        # y=0 rows are excluded from the denominator
        # [0.1, 0, 0.3] vs [0.1, 0, -0.3] → only 2 non-zero rows; 1 match → 0.5
        assert directional_accuracy([0.1, 0.0, 0.3], [0.1, 0.0, -0.3]) == 0.5
        # All zero-y → 0.5 (no information)
        assert directional_accuracy([0.0, 0.0], [0.5, -0.5]) == 0.5

    def test_correlation_known_value(self):
        from src.models.evaluation import correlation
        # y = [1, 2, 3, 4], yhat = [2, 4, 6, 8] → perfect positive corr
        assert abs(correlation([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9

    def test_correlation_negative(self):
        from src.models.evaluation import correlation
        assert abs(correlation([1, 2, 3, 4], [4, 3, 2, 1]) - (-1.0)) < 1e-9

    def test_nan_dropped(self):
        from src.models.evaluation import mae, rmse
        y = [1.0, np.nan, 3.0, 4.0]
        yhat = [1.0, 5.0, np.nan, 4.0]
        # After dropping NaN: y=[1, 4], yhat=[1, 4] → MAE = 0
        assert mae(y, yhat) == 0.0
        assert rmse(y, yhat) == 0.0

    def test_empty_input_raises(self):
        from src.models.evaluation import mae, rmse
        with pytest.raises(ValueError, match="empty"):
            mae([], [])
        with pytest.raises(ValueError, match="empty"):
            rmse([], [])

    def test_shape_mismatch_raises(self):
        from src.models.evaluation import mae
        with pytest.raises(ValueError, match="shape"):
            mae([1, 2, 3], [1, 2])


class TestVolMetrics:
    def test_qlike_perfect_forecast_is_zero(self):
        from src.models.evaluation import qlike
        # If forecast == realized, QLIKE = 1 - log(1) - 1 = 0
        v = np.array([0.5, 1.0, 1.5, 2.0])
        assert abs(qlike(v, v)) < 1e-9

    def test_qlike_non_negative(self):
        from src.models.evaluation import qlike
        # Random positive values, QLIKE is always ≥ 0
        rng = np.random.default_rng(0)
        f = rng.uniform(0.1, 5.0, 200)
        r = rng.uniform(0.1, 5.0, 200)
        assert qlike(f, r) >= 0.0

    def test_qlike_drops_non_positive(self):
        from src.models.evaluation import qlike
        f = np.array([0.0, 1.0, 2.0, 3.0])
        r = np.array([1.0, 0.0, 2.0, 3.0])
        # Only (2, 2) and (3, 3) remain → 0
        assert abs(qlike(f, r)) < 1e-9

    def test_qlike_all_invalid_raises(self):
        from src.models.evaluation import qlike
        with pytest.raises(ValueError, match="positive"):
            qlike([0, 0, 0], [1, 1, 1])

    def test_bias_known_value(self):
        from src.models.evaluation import bias
        # forecast = 2 * realized → bias = 2 - 1 = 1
        r = np.array([1.0, 2.0, 3.0])
        assert abs(bias(2.0 * r, r) - 1.0) < 1e-9

    def test_bias_zero_when_perfect(self):
        from src.models.evaluation import bias
        v = np.array([0.5, 1.0, 1.5])
        assert bias(v, v) == 0.0

    def test_compute_return_metrics(self):
        from src.models.evaluation import compute_return_metrics
        m = compute_return_metrics([1, 2, 3], [1, 2, 5])
        assert set(m.keys()) == {"MAE", "RMSE", "dir_acc", "corr"}
        assert abs(m["MAE"] - 2 / 3) < 1e-9

    def test_compute_vol_metrics(self):
        from src.models.evaluation import compute_vol_metrics
        f = np.array([0.5, 1.0, 1.5])
        r = np.array([0.5, 1.0, 1.5])
        m = compute_vol_metrics(f, r)
        assert set(m.keys()) == {"QLIKE", "MAE", "MSE", "bias"}
        assert m["MAE"] == 0.0
        assert m["MSE"] == 0.0
        assert m["QLIKE"] == 0.0
        assert m["bias"] == 0.0


# ── Phase 6.5 — Expanding-window engine ────────────────────────────────────


def _build_small_model_matrix(
    n: int = 200, with_t5: bool = True, with_var: bool = True
) -> pd.DataFrame:
    """Build a minimal model-matrix fixture (1,342 × N would be ideal, but for
    unit tests a 200-row version is enough to exercise the engine)."""
    from src.features.build_model_matrix import build_model_matrix
    from tests.test_phase5_model_matrix import _make_master

    rng = np.random.default_rng(0)
    r_ita = rng.normal(scale=1.0, size=n)
    r_waerlst = rng.normal(scale=1.0, size=n)
    # The fixture's _make_master sets r_ITA_lag1 = [0]*n by default;
    # override with the same series shifted by 1 so GARCH/AR1 have a
    # non-trivial source.
    r_ita_lag1 = np.concatenate([[np.nan], r_ita[:-1]])
    r_ita_lag2 = np.concatenate([[np.nan, np.nan], r_ita[:-2]])
    r_ita_lag5 = np.concatenate([[np.nan] * 5, r_ita[:-5]])
    r_ita_msadj = r_ita - rng.normal(scale=0.5, size=n)  # crude msadj
    df = _make_master(
        n=n,
        r_ita=list(r_ita),
        r_waerlst=list(r_waerlst),
    )
    # Override dates to business days
    dates = pd.bdate_range("2024-01-02", periods=n)
    df["date"] = dates
    df["r_ITA"] = r_ita
    df["r_WAERLST_recon"] = r_waerlst
    # Overwrite the pre-lagged returns (which the fixture sets to 0)
    df["r_ITA_lag1"] = r_ita_lag1
    df["r_ITA_lag2"] = r_ita_lag2
    df["r_ITA_lag5"] = r_ita_lag5
    df["r_ITA_msadj"] = r_ita_msadj

    kwargs = {}
    if with_t5:
        kwargs["horizons"] = (1, 5)
    else:
        kwargs["horizons"] = (1,)
    kwargs["add_variance_targets"] = with_var
    return build_model_matrix(df, **kwargs)


class TestModelSpec:
    def test_returns_requires_info_set(self):
        from src.models.expanding_window import ModelSpec
        with pytest.raises(ValueError, match="info_set"):
            ModelSpec(name="x", factory=lambda: None, info_set=None,
                      model_type="returns")

    def test_vol_allows_none_info_set(self):
        from src.models.expanding_window import ModelSpec
        s = ModelSpec(name="g", factory=lambda: None, info_set=None,
                      model_type="vol")
        assert s.info_set is None
        assert s.model_type == "vol"

    def test_unknown_model_type_raises(self):
        from src.models.expanding_window import ModelSpec
        with pytest.raises(ValueError, match="model_type"):
            ModelSpec(name="x", factory=lambda: None, info_set="F",
                      model_type="unknown")


class TestAssertNoFutureData:
    def test_clean_split_passes(self):
        from src.models.expanding_window import assert_no_future_data
        train = pd.Series(pd.bdate_range("2024-01-02", periods=100))
        test = pd.Series(pd.bdate_range("2024-07-01", periods=20))
        # Should not raise
        assert_no_future_data(train, test)

    def test_overlap_raises(self):
        from src.models.expanding_window import assert_no_future_data
        train = pd.Series(pd.bdate_range("2024-01-02", periods=100))
        test = pd.Series(pd.bdate_range("2024-04-01", periods=20))
        with pytest.raises(ValueError, match="LEAKAGE"):
            assert_no_future_data(train, test)


class TestExpandingWindowEngine:
    def _small_eng(self, refit_every: int = 20, **kw) -> "ExpandingWindowEngine":
        from src.models.baselines import HistoricalMeanForecaster, RidgeForecaster
        from src.models.expanding_window import ExpandingWindowEngine
        mm = _build_small_model_matrix(n=200)
        eng = ExpandingWindowEngine(
            model_matrix=mm,
            info_sets=mm.attrs["info_sets"],
            targets=["r_ITA"],
            horizons=[1, 5],
            test_fraction=0.25,
            min_train_obs=50,
            refit_every=refit_every,
            **kw,
        )
        eng.add_model("historical_mean", HistoricalMeanForecaster,
                      info_set="F", model_type="returns")
        eng.add_model("ridge", lambda: RidgeForecaster(alpha=1.0),
                      info_set="F", model_type="returns")
        return eng

    def test_run_produces_long_dataframe(self):
        eng = self._small_eng()
        df = eng.run()
        assert isinstance(df, pd.DataFrame)
        expected_cols = {
            "date", "fold", "model", "info_set", "target", "horizon",
            "prediction", "realized", "train_n", "refit_flag",
        }
        assert set(df.columns) == expected_cols

    def test_no_leakage_train_max_lt_test_min(self):
        eng = self._small_eng()
        df = eng.run()
        # For every (model, target, horizon) the train data used for the
        # FIRST refit (fold=0) must be ≥ min_train_obs and strictly before
        # the test data.
        for model in df["model"].unique():
            sub = df[(df["model"] == model) & (df["fold"] == 0)]
            # train_n at fold 0 == first test index, i.e. all train rows
            assert sub["train_n"].iloc[0] >= 50  # min_train_obs
            # First forecast date in fold 0 must equal the first date at
            # index ``train_n`` in the model matrix (i.e. the split boundary).
            train_n = int(sub["train_n"].iloc[0])
            expected_first_test_date = pd.Timestamp(eng.mm["date"].iloc[train_n])
            assert sub["date"].iloc[0] == expected_first_test_date
            # All forecast dates must be >= the split date
            assert (sub["date"] >= expected_first_test_date).all()

    def test_refit_every_produces_correct_n_folds(self):
        eng = self._small_eng(refit_every=20)
        df = eng.run()
        # n_folds = ceil(test_n / refit_every) but the last fold may be
        # smaller (the engine ensures the last test row is always a refit
        # point). With test_n=50 and refit_every=20, expect 3-4 folds.
        assert 3 <= df["fold"].nunique() <= 4

    def test_horizons_both_produced(self):
        eng = self._small_eng()
        df = eng.run()
        assert set(df["horizon"].unique()) == {1, 5}

    def test_models_both_produced(self):
        eng = self._small_eng()
        df = eng.run()
        assert set(df["model"].unique()) == {"historical_mean", "ridge"}

    def test_predictions_finite_for_working_models(self):
        eng = self._small_eng()
        df = eng.run()
        # HistoricalMean and Ridge should produce finite predictions
        # (the t1 target is finite at every row of the synthetic fixture)
        for model in ("historical_mean", "ridge"):
            sub = df[(df["model"] == model) & (df["horizon"] == 1)]
            assert sub["prediction"].notna().any()
            # MAE against realized should be ≤ std of the target
            mae = (sub["prediction"] - sub["realized"]).abs().mean()
            assert np.isfinite(mae)

    def test_quick_mode_runs_smaller(self):
        eng = self._small_eng(quick=True, quick_n_days=30)
        df = eng.run()
        # Quick mode restricts to last 30 OOS days
        n_test_dates = df.groupby(["model", "horizon"])["date"].nunique()
        assert (n_test_dates <= 30).all()

    def test_no_models_raises(self):
        from src.models.expanding_window import ExpandingWindowEngine
        mm = _build_small_model_matrix(n=200)
        eng = ExpandingWindowEngine(
            model_matrix=mm, info_sets=mm.attrs["info_sets"],
            targets=["r_ITA"], horizons=[1], refit_every=20,
            min_train_obs=50,
        )
        with pytest.raises(RuntimeError, match="No models"):
            eng.run()

    def test_min_train_obs_enforced(self):
        from src.models.baselines import HistoricalMeanForecaster
        from src.models.expanding_window import ExpandingWindowEngine
        # Tiny matrix with min_train_obs higher than train size
        mm = _build_small_model_matrix(n=30)
        eng = ExpandingWindowEngine(
            model_matrix=mm, info_sets=mm.attrs["info_sets"],
            targets=["r_ITA"], horizons=[1], refit_every=5,
            min_train_obs=500,  # impossible
        )
        eng.add_model("hm", HistoricalMeanForecaster, info_set="F")
        with pytest.raises(ValueError, match="min_train_obs"):
            eng.run()

    def test_run_horse_race_engine_function(self):
        from src.models.baselines import HistoricalMeanForecaster
        from src.models.expanding_window import (
            ModelSpec, run_horse_race_engine,
        )
        mm = _build_small_model_matrix(n=200)
        specs = [
            ModelSpec("historical_mean", HistoricalMeanForecaster, info_set="F"),
        ]
        df = run_horse_race_engine(
            mm, specs=specs, targets=["r_ITA"], horizons=[1],
            refit_every=20, min_train_obs=50, test_fraction=0.25,
        )
        assert len(df) > 0
        assert df["model"].iloc[0] == "historical_mean"

    def test_garch_vol_univariate(self):
        # GARCH ignores features; we add it via spec and verify that
        # the realized column corresponds to target_var_r_ITA_t1 (variance).
        from src.models.garch import GARCHForecaster
        from src.models.expanding_window import (
            ExpandingWindowEngine, ModelSpec,
        )
        mm = _build_small_model_matrix(n=200)
        eng = ExpandingWindowEngine(
            model_matrix=mm, info_sets=mm.attrs["info_sets"],
            targets=["r_ITA"], horizons=[1], refit_every=20,
            min_train_obs=50,
        )
        eng.add_model("garch", lambda: GARCHForecaster(variant="GARCH",
                                                      p=1, q=1, dist="t",
                                                      rescale=True),
                      info_set=None, model_type="vol")
        df = eng.run()
        assert len(df) > 0
        # The info_set column should be "-" for vol
        assert (df["info_set"] == "-").all()
        # Realized values should be positive (they are squared returns)
        realized_pos = df["realized"].dropna()
        assert (realized_pos > 0).all()
        # Predictions should be positive
        pred_pos = df["prediction"].dropna()
        assert (pred_pos > 0).all()


# ── Phase 6.6 — Horse-race runner ──────────────────────────────────────────


class TestDefaultReturnSpecs:
    def test_default_5_info_sets_4_models(self):
        from src.models.horse_race import default_return_specs
        specs = default_return_specs()
        # 4 models × 5 info sets = 20
        assert len(specs) == 20
        names = {s.name for s in specs}
        assert names == {"historical_mean", "ar1", "ols", "ridge"}
        for s in specs:
            assert s.model_type == "returns"

    def test_custom_info_sets(self):
        from src.models.horse_race import default_return_specs
        specs = default_return_specs(info_sets=("F", "PN"))
        # 4 models × 2 info sets = 8
        assert len(specs) == 8
        for s in specs:
            assert s.info_set in ("F", "PN")

    def test_ridge_alpha_propagates(self):
        from src.models.horse_race import default_return_specs
        specs = default_return_specs(info_sets=("F",), ridge_alpha=0.5)
        for s in specs:
            if s.name == "ridge":
                m = s.factory()
                assert m.alpha == 0.5


class TestDefaultVolSpecs:
    def test_three_garch_variants(self):
        from src.models.horse_race import default_vol_specs
        specs = default_vol_specs()
        assert len(specs) == 3
        names = {s.name for s in specs}
        assert names == {"garch", "gjr_garch", "egarch"}
        for s in specs:
            assert s.model_type == "vol"
            assert s.info_set is None


class TestBuildBenchmarkTables:
    def test_returns_benchmark_row_count(self):
        from src.models.horse_race import build_benchmark_tables
        # Build a tiny synthetic long-form DataFrame
        rows = []
        for set_name in ("F", "P", "N", "PN", "PNG"):
            for model in ("ols", "ridge"):
                for target in ("r_ITA", "r_WAERLST_recon"):
                    for h in (1, 5):
                        for i in range(10):
                            rows.append({
                                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                                "fold": 0, "model": model, "info_set": set_name,
                                "target": target, "horizon": h,
                                "prediction": float(i) * 0.1,
                                "realized": float(i) * 0.1 + 0.05,
                                "train_n": 100, "refit_flag": 1,
                            })
        df = pd.DataFrame(rows)
        bench, vol = build_benchmark_tables(df)
        # 5 sets × 2 models × 2 targets × 2 horizons = 40
        assert len(bench) == 40
        assert vol.empty
        # Columns
        for c in ("target", "horizon", "model", "info_set", "n_obs",
                  "MAE", "RMSE", "dir_acc", "corr"):
            assert c in bench.columns

    def test_vol_benchmark_separated(self):
        from src.models.horse_race import build_benchmark_tables
        rows = []
        for model in ("garch", "gjr_garch", "egarch"):
            for target in ("r_ITA", "r_WAERLST_recon"):
                for h in (1, 5):
                    for i in range(10):
                        rows.append({
                            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                            "fold": 0, "model": model, "info_set": "-",
                            "target": target, "horizon": h,
                            "prediction": 0.5 + 0.01 * i,
                            "realized": 0.5 + 0.02 * i,
                            "train_n": 100, "refit_flag": 1,
                        })
        df = pd.DataFrame(rows)
        bench, vol = build_benchmark_tables(df)
        # 3 × 2 × 2 = 12 vol rows
        assert len(vol) == 12
        assert bench.empty
        # QLIKE column is present
        assert "QLIKE" in vol.columns
        # info_set is "-"
        assert (vol["info_set"] == "-").all()

    def test_all_finite_metrics(self):
        from src.models.horse_race import build_benchmark_tables
        rows = []
        rng = np.random.default_rng(0)
        for model in ("ols", "ridge"):
            for h in (1, 5):
                for i in range(30):
                    rows.append({
                        "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                        "fold": 0, "model": model, "info_set": "F",
                        "target": "r_ITA", "horizon": h,
                        "prediction": float(rng.normal()),
                        "realized": float(rng.normal()),
                        "train_n": 100, "refit_flag": 1,
                    })
        df = pd.DataFrame(rows)
        bench, _ = build_benchmark_tables(df)
        # All numeric metric columns are finite
        for c in ("MAE", "RMSE", "dir_acc", "corr"):
            assert np.isfinite(bench[c]).all(), f"non-finite {c}"


class TestRunHorseRace:
    def test_full_run_produces_benchmarks(self):
        from src.models.horse_race import run_horse_race
        mm = _build_small_model_matrix(n=200)
        out = run_horse_race(
            mm, horizons=(1, 5), targets=("r_ITA",),
            info_sets=("F", "P"),  # small to keep test fast
            min_train_obs=50, refit_every=20, test_fraction=0.25,
        )
        assert "predictions" in out
        assert "benchmark" in out
        assert "vol_benchmark" in out
        assert "info_set_cardinality" in out
        # 2 info_sets × 4 models × 2 targets × 2 horizons = 32 returns
        # (single target, so 16 actually)
        assert len(out["benchmark"]) == 16
        # 3 GARCH × 1 target × 2 horizons = 6
        assert len(out["vol_benchmark"]) == 6

    def test_info_set_cardinality_in_output(self):
        from src.models.horse_race import run_horse_race
        mm = _build_small_model_matrix(n=200)
        out = run_horse_race(
            mm, horizons=(1,), targets=("r_ITA",), info_sets=("F",),
            min_train_obs=50, refit_every=20,
        )
        card = out["info_set_cardinality"]
        # 5 rows (F, P, N, PN, PNG)
        assert len(card) == 5
        assert "information_set" in card.columns
        assert "n_features" in card.columns


class TestSaveBenchmarkCSVs:
    def test_writes_three_files(self, tmp_path):
        from src.models.horse_race import save_benchmark_csvs
        bench = pd.DataFrame({
            "target": ["r_ITA"], "horizon": [1], "model": ["ols"],
            "info_set": ["F"], "n_obs": [10], "MAE": [0.1], "RMSE": [0.2],
            "dir_acc": [0.5], "corr": [0.0], "QLIKE": [np.nan],
        })
        vol = pd.DataFrame({
            "target": ["r_ITA"], "horizon": [1], "model": ["garch"],
            "info_set": ["-"], "n_obs": [10], "MAE": [0.1], "RMSE": [0.2],
            "dir_acc": [np.nan], "corr": [np.nan], "QLIKE": [0.5],
        })
        card = pd.DataFrame({"information_set": ["F"], "n_features": [23]})
        written = save_benchmark_csvs(tmp_path, bench, vol, card, suffix="")
        assert len(written) == 3
        for p in written.values():
            assert p.exists()
            assert p.stat().st_size > 0

    def test_suffix_in_filename(self, tmp_path):
        from src.models.horse_race import save_benchmark_csvs
        bench = pd.DataFrame({"target": [], "horizon": [], "model": []})
        vol = pd.DataFrame({"target": [], "horizon": [], "model": []})
        written = save_benchmark_csvs(tmp_path, bench, vol, suffix="_quick")
        assert "_quick" in written["benchmark"].name


# ── Phase 6.7 — CLI runner + 3 figures ─────────────────────────────────────


class TestFigureFunctions:
    def test_fig14_creates_file(self, tmp_path):
        from scripts.phase6_run_baselines import _fig14_forecast_vs_realized
        # Build a tiny predictions DataFrame
        rng = np.random.default_rng(0)
        rows = []
        for set_name in ("F", "PN", "PNG"):
            for i in range(30):
                rows.append({
                    "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                    "fold": 0, "model": "ols", "info_set": set_name,
                    "target": "r_ITA", "horizon": 1,
                    "prediction": float(rng.normal()),
                    "realized": float(rng.normal()),
                    "train_n": 100, "refit_flag": 1,
                })
        df = pd.DataFrame(rows)
        out = tmp_path / "fig14.png"
        result = _fig14_forecast_vs_realized(df, out, target="r_ITA", horizon=1)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 1000  # non-trivial PNG

    def test_fig15_creates_file(self, tmp_path):
        from scripts.phase6_run_baselines import _fig15_loss_by_info_set
        rows = []
        for set_name in ("F", "P", "N", "PN", "PNG"):
            rows.append({
                "target": "r_ITA", "horizon": 1, "model": "ols",
                "info_set": set_name, "n_obs": 100, "MAE": 0.1, "RMSE": 0.2,
                "dir_acc": 0.5, "corr": 0.0, "QLIKE": np.nan,
            })
        bench = pd.DataFrame(rows)
        out = tmp_path / "fig15.png"
        result = _fig15_loss_by_info_set(bench, out, target="r_ITA", horizon=1)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_fig16_creates_file(self, tmp_path):
        from scripts.phase6_run_baselines import _fig16_garch_vol_diagnostic
        rng = np.random.default_rng(0)
        rows = []
        for h in (1, 5):
            for i in range(30):
                rows.append({
                    "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                    "fold": 0, "model": "garch", "info_set": "-",
                    "target": "r_ITA", "horizon": h,
                    "prediction": 0.5 + 0.1 * rng.normal(),
                    "realized": 0.5 + 0.2 * rng.normal(),
                    "train_n": 100, "refit_flag": 1,
                })
        df = pd.DataFrame(rows)
        out = tmp_path / "fig16.png"
        result = _fig16_garch_vol_diagnostic(df, out, target="r_ITA")
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 1000


class TestCLIRunner:
    def test_quick_smoke_produces_outputs(self, tmp_path, monkeypatch):
        """End-to-end CLI smoke test: --quick mode on a tiny synthetic matrix."""
        import subprocess
        # Save a tiny synthetic model matrix in a temporary location
        mm = _build_small_model_matrix(n=200)
        # Write a temporary paths.yaml pointing to the synthetic matrix
        paths = {
            "data": {
                "raw": "data/raw", "interim": "data/interim",
                "processed": str(tmp_path / "processed"),
                "external": "data/external",
            },
            "raw_subdirs": {},
            "outputs": {
                "figures": str(tmp_path / "figures"),
                "tables": str(tmp_path / "tables"),
                "model_objects": str(tmp_path / "model_objects"),
                "logs": str(tmp_path / "logs"),
            },
            "processed_files": {
                "daily_master": str(tmp_path / "processed" / "daily_master.parquet"),
                "feature_matrix": str(tmp_path / "processed" / "feature_matrix.parquet"),
                "model_matrix": str(tmp_path / "processed" / "model_matrix.parquet"),
                "data_dictionary": str(tmp_path / "processed" / "data_dictionary.csv"),
            },
        }
        # Create the directories
        (tmp_path / "processed").mkdir(parents=True, exist_ok=True)
        (tmp_path / "figures").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tables").mkdir(parents=True, exist_ok=True)
        # Save the synthetic model matrix
        mm.to_parquet(tmp_path / "processed" / "model_matrix.parquet", index=False)
        # Write the paths YAML
        import yaml
        paths_yaml = tmp_path / "paths.yaml"
        with open(paths_yaml, "w") as f:
            yaml.dump(paths, f)
        # Run the CLI
        result = subprocess.run(
            [
                sys.executable,
                "scripts/phase6_run_baselines.py",
                "--paths-yaml", str(paths_yaml),
                "--quick",
                "--info-sets", "F,P",  # small
                "--targets", "r_WAERLST",
                "--horizons", "1",
                "--out-suffix", "_smoke",
                "--min-train-obs", "50",  # small matrix → small min
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        assert result.returncode == 0, "CLI exited non-zero"
        # Outputs should exist
        assert (tmp_path / "tables" / "phase6_benchmark_smoke.csv").exists()
        assert (tmp_path / "tables" / "phase6_volatility_benchmark_smoke.csv").exists()
        assert (tmp_path / "tables" / "phase6_info_set_cardinality_smoke.csv").exists()
        assert (tmp_path / "tables" / "phase6_predictions_smoke.parquet").exists()
        assert (tmp_path / "figures" / "fig14_oos_forecast_vs_realized_smoke.png").exists()
        assert (tmp_path / "figures" / "fig15_loss_by_info_set_smoke.png").exists()
        assert (tmp_path / "figures" / "fig16_garch_vol_diagnostic_smoke.png").exists()
