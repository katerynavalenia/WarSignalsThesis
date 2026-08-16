"""Unit tests for :mod:`src.models.garch`.

Covers the GARCH-X (`GARCHXForecaster`) predict path, which previously had
a bug where `.forecast()` was called without the required `x=` exogenous
path for ARX-mean models. `arch` raises a `TypeError` in that case, which
was silently swallowed by a broad `except Exception` and replaced with a
constant fallback forecast of `1.0` — making all three GARCH-X variants
(GARCH / GJR-GARCH / EGARCH) produce byte-identical output regardless of
their (correctly, differently) fitted volatility dynamics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models.garch import GARCHForecaster, GARCHXForecaster


def _make_series(n: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    y = pd.Series(rng.standard_normal(n) * 1.5)
    X = pd.DataFrame(
        {"f1": rng.standard_normal(n), "f2": rng.standard_normal(n)}
    )
    return y, X


class TestGARCHXVariantsDiffer:
    """The three GARCH-X variants must NOT produce identical forecasts."""

    def test_h1_forecasts_differ_across_variants(self):
        y, X = _make_series()
        preds = {}
        for variant in ("GARCH", "GJR_GARCH", "EGARCH"):
            m = GARCHXForecaster(
                variant=variant, p=1, q=1, dist="t", rescale=True,
                fallback=True,
            )
            m.fit(y.iloc[:400], X_exog=X.iloc[:400])
            pred = m.predict(horizon=1, X_exog_horizon=X.iloc[400:401])
            preds[variant] = float(pred[0])
            # Must not have silently fallen back to the constant-1.0 path.
            assert m.result_ is not None
            assert pred[0] != pytest.approx(1.0, abs=1e-9)

        values = list(preds.values())
        assert len(set(np.round(values, 8))) == len(values), (
            f"GARCH-X variants produced identical forecasts: {preds}"
        )

    def test_predict_does_not_silently_fallback_when_fitted(self):
        """`predict()` should use the real `arch` forecast, not the
        exception-fallback constant, whenever the model fit succeeded and
        an `X_exog_horizon` is supplied."""
        y, X = _make_series(seed=1)
        m = GARCHXForecaster(variant="GARCH", p=1, q=1, dist="t")
        m.fit(y.iloc[:400], X_exog=X.iloc[:400])
        assert m.result_ is not None
        pred = m.predict(horizon=1, X_exog_horizon=X.iloc[400:401])
        assert np.isfinite(pred).all()
        assert pred[0] != 1.0

    def test_multistep_garch_and_gjr_use_exog_path(self):
        """h > 1 forecasts for GARCH / GJR-GARCH (which support analytic
        multi-step forecasts in `arch`) should also respect the exog path
        and not collapse to the constant fallback."""
        y, X = _make_series(seed=2)
        for variant in ("GARCH", "GJR_GARCH"):
            m = GARCHXForecaster(variant=variant, p=1, q=1, dist="t")
            m.fit(y.iloc[:400], X_exog=X.iloc[:400])
            pred = m.predict(horizon=3, X_exog_horizon=X.iloc[400:403])
            assert len(pred) == 3
            assert not np.allclose(pred, 1.0)


class TestGARCHXNoExogMatchesPlainGARCH:
    """With no exogenous regressors, GARCH-X should behave like GARCH."""

    def test_no_exog_predict_runs(self):
        y, _ = _make_series(seed=3)
        m = GARCHXForecaster(variant="GARCH", p=1, q=1, dist="t")
        m.fit(y.iloc[:400], X_exog=None)
        pred = m.predict(horizon=1, X_exog_horizon=None)
        assert np.isfinite(pred).all()


class TestPlainGARCHVariantsDiffer:
    """Sanity check: the non-X path already differs correctly (regression
    guard so a future change can't silently break this too)."""

    def test_h1_forecasts_differ_across_variants(self):
        y, _ = _make_series(seed=4)
        preds = {}
        for variant in ("GARCH", "GJR_GARCH", "EGARCH"):
            m = GARCHForecaster(variant=variant, p=1, q=1, dist="t")
            m.fit(y.iloc[:400])
            pred = m.predict(horizon=1)
            preds[variant] = float(pred[0])
        values = list(preds.values())
        assert len(set(np.round(values, 8))) == len(values), (
            f"Plain GARCH variants produced identical forecasts: {preds}"
        )
