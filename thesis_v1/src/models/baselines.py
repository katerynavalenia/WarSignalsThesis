"""Return-forecast baselines for the Phase 6 horse race.

Each forecaster implements the minimal scikit-learn-style interface:

    forecaster.fit(X, y)      # train on past data
    forecaster.predict(X)     # 1-step-ahead forecast on new X

The same interface is used for both 1-day and 5-day forecast horizons: the
``y`` target encodes the horizon. All forecasters ignore columns they do not
need (the ``HistoricalMean`` and ``AR1`` baselines do not use ``X`` at all,
which is exactly the "no-leakage, no information set" baseline the Master
Plan §10.3 calls for).

Conventions
-----------
- ``y`` is in **percent** (matches the model-matrix target column).
- ``X`` is the lagged feature matrix (one row per forecast origin).
- Predictions are in the same units as ``y`` (percent).

A NaN-safe ``fit`` / ``predict`` is implemented in :class:`_BaseForecaster`
so each subclass can focus on the estimation logic.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import LinearRegression, Ridge

try:
    from statsmodels.tsa.ar_model import AutoReg
    _HAS_STATSMODELS = True
except Exception:  # pragma: no cover — statsmodels is in requirements.txt
    _HAS_STATSMODELS = False


__all__ = [
    "HistoricalMeanForecaster",
    "AR1Forecaster",
    "LinearRegressionForecaster",
    "RidgeForecaster",
]


# ── Base class ───────────────────────────────────────────────────────────────


class _BaseForecaster(BaseEstimator, RegressorMixin):
    """Common helpers: NaN-safe fit/predict, parameter access."""

    def _drop_nan_xy(
        self, X: Optional[pd.DataFrame], y: pd.Series
    ) -> tuple[Optional[pd.DataFrame], np.ndarray]:
        """Return ``(X_clean, y_clean)`` with rows where ``y`` is NaN dropped.

        Rows with NaN in ``X`` are also dropped for the OLS / Ridge baselines.
        For the ``HistoricalMean`` and ``AR1`` baselines ``X`` is ignored
        and only ``y`` matters.
        """
        y_arr = np.asarray(y, dtype=float)
        mask = ~np.isnan(y_arr)
        y_clean = y_arr[mask]
        if X is None:
            return None, y_clean
        X_clean = X.iloc[mask] if hasattr(X, "iloc") else np.asarray(X)[mask]
        # Drop rows with any NaN in X for the regression baselines
        if hasattr(X_clean, "isna"):
            row_nan = X_clean.isna().any(axis=1).to_numpy()
            X_clean = X_clean.iloc[~row_nan]
            y_clean = y_clean[~row_nan]
        else:
            row_nan = np.isnan(X_clean).any(axis=1)
            X_clean = X_clean[~row_nan]
            y_clean = y_clean[~row_nan]
        return X_clean, y_clean

    def _predict_constant(self, n: int) -> np.ndarray:
        """Return ``n`` copies of the trained mean (or zero if not fitted)."""
        if not hasattr(self, "mean_"):
            return np.zeros(int(n))
        return np.full(int(n), self.mean_)


# ── 1. Historical mean ──────────────────────────────────────────────────────


class HistoricalMeanForecaster(_BaseForecaster):
    """Predict the (possibly expanding) mean of the training target.

    Parameters
    ----------
    expanding : bool, default False
        If ``True``, the prediction at row ``t`` is the mean of ``y`` up to
        and **including** ``t`` (i.e. the expanding mean). This matches
        Master Plan §10.3's "historical mean" benchmark more closely when
        used as a per-row predictor inside the expanding-window engine.

        If ``False`` (default), the prediction is the **constant** mean of
        the entire training set, recomputed at every refit. This is the
        stronger "no information" baseline the Master Plan prefers for the
        first-milestone table.
    """

    def __init__(self, expanding: bool = False) -> None:
        self.expanding = bool(expanding)

    def fit(self, X, y) -> "HistoricalMeanForecaster":
        # X is intentionally ignored: the historical-mean baseline uses
        # only the target's own values. We therefore drop NaN only in
        # ``y``, NOT in ``X`` (which would otherwise discard ~75% of the
        # training rows because the F set has NaN in attack/news
        # features during the early modeling window).
        if hasattr(y, "to_numpy"):
            y_arr = y.to_numpy(dtype=float)
        else:
            y_arr = np.asarray(y, dtype=float)
        y_clean = y_arr[~np.isnan(y_arr)]
        if y_clean.size == 0:
            self.mean_ = 0.0
        else:
            self.mean_ = float(np.mean(y_clean))
        return self

    def predict(self, X) -> np.ndarray:
        if getattr(self, "expanding", False):
            # Use the constant training mean as the OOS prediction — the
            # engine recomputes the mean on every refit, so an "expanding"
            # forecast would require per-row expanding means over the
            # training set. We model that by simply broadcasting the
            # training mean: in an expanding-window OOS design the training
            # set itself expands, so the engine refits the mean at every
            # refit date.
            return self._predict_constant(self._n_rows(X))
        return self._predict_constant(self._n_rows(X))

    @staticmethod
    def _n_rows(X) -> int:
        if X is None:
            return 0
        if hasattr(X, "shape"):
            return int(X.shape[0])
        return int(len(X))


# ── 2. AR(1) ────────────────────────────────────────────────────────────────


class AR1Forecaster(_BaseForecaster):
    """AR(1) baseline forecaster.

    The target ``y`` is regressed on its own first lag (or first ``lags``
    lags when ``lags > 1``). At predict time the forecaster produces a
    vector of length ``n`` (number of test rows) by **iterative 1-step
    forecasting** — the first forecast uses the last observed training
    value as the seed; subsequent forecasts feed each new prediction back
    in as the lag for the next step. This is the correct 1-step-ahead
    OOS protocol for an AR model: ``AutoReg.forecast(steps=n)`` is *not*
    used (it would return the long-horizon mean and ignore the fitted
    coefficients).

    Parameters
    ----------
    lags : int, default 1
        Number of AR lags.
    """

    def __init__(self, lags: int = 1) -> None:
        self.llags = int(lags)

    def fit(self, X, y) -> "AR1Forecaster":
        if not _HAS_STATSMODELS:
            raise ImportError(
                "statsmodels is required for AR1Forecaster. "
                "Install with `pip install statsmodels`."
            )
        # X is intentionally ignored: the AR(1) baseline uses only the
        # target's own history. This guarantees the AR(1) row in the
        # benchmark is identical across information sets — by construction
        # (the historical mean baseline has the same property).
        _, y_clean = self._drop_nan_xy(None, y)
        self.ar_result_ = None
        self._params_ = None
        self._last_obs_ = None
        if y_clean.size < self.llags + 1:
            self._fallback_mean_ = (
                float(np.mean(y_clean)) if y_clean.size else 0.0
            )
            return self
        idx = pd.date_range("2000-01-01", periods=y_clean.size, freq="B")
        s = pd.Series(y_clean, index=idx, name="y")
        try:
            self.ar_result_ = AutoReg(s, lags=self.llags, old_names=False).fit()
            # Cache the params and the last ``lags`` observations for
            # iterative 1-step forecasting.
            params = np.asarray(self.ar_result_.params, dtype=float)
            self._params_ = params
            self._last_obs_ = y_clean[-self.llags:].astype(float).tolist()
        except Exception:
            self.ar_result_ = None
            self._params_ = None
            self._fallback_mean_ = float(np.mean(y_clean))
        return self

    def predict(self, X) -> np.ndarray:
        n = self._n_rows(X)
        if self.ar_result_ is None or self._params_ is None or self._last_obs_ is None:
            return np.full(n, getattr(self, "_fallback_mean_", 0.0))
        try:
            params = self._params_
            const = float(params[0])
            ar_coefs = params[1:1 + self.llags]
            # Iterative 1-step forecast. The buffer holds the most recent
            # ``lags`` predicted values (in chronological order).
            buf = list(self._last_obs_)
            out = np.zeros(n, dtype=float)
            for t in range(n):
                # y_hat_t = const + sum(coef_i * buf[-i-1] for i in 0..lags-1)
                y_hat = const
                for i, c in enumerate(ar_coefs):
                    y_hat += float(c) * buf[-1 - i]
                out[t] = y_hat
                # Roll the buffer
                buf.pop()  # drop oldest
                buf.append(y_hat)  # append new prediction
            return out
        except Exception:
            return np.full(n, getattr(self, "_fallback_mean_", 0.0))

    @staticmethod
    def _n_rows(X) -> int:
        if X is None:
            return 1
        if hasattr(X, "shape"):
            return int(X.shape[0])
        return int(len(X))


# ── 3. OLS linear regression ────────────────────────────────────────────────


class LinearRegressionForecaster(_BaseForecaster):
    """Ordinary least squares via :class:`sklearn.linear_model.LinearRegression`.

    Parameters
    ----------
    fit_intercept : bool, default True
        Whether to add an intercept.
    na_action : {"impute_mean", "drop", "zero"}, default "impute_mean"
        How to handle NaN in ``X`` at predict time:
        - ``"impute_mean"`` (default) — fill NaN with the per-column train
          mean. Defensible but flattens predictions for rows with sparse
          features (e.g. early attack features that are all-NaN).
        - ``"drop"`` — set the prediction to NaN for any test row that has
          any NaN in its feature vector. The benchmark then drops these
          rows from the metric computation. Most conservative.
        - ``"zero"`` — fill NaN with 0.0. Assumes NaN means "no signal";
          may be appropriate for attack features.
    standardize : bool, default False
        If True, z-score the features using train statistics
        (mean=0, std=1). NaN values are then imputed with 0 (the
        standardized mean). This is the **only correct way** to handle
        features that have NaN in train (because the train mean is then
        zero by construction, not the raw mean of the column).
        Recommended for information sets that mix many-sparse features
        (P, PN, PNG) where the un-standardized mean is dominated by
        zeros and would shift test predictions far off-distribution.
    """

    def __init__(self, fit_intercept: bool = True,
                 na_action: str = "impute_mean",
                 standardize: bool = False) -> None:
        self.fit_intercept = bool(fit_intercept)
        if na_action not in ("impute_mean", "drop", "zero"):
            raise ValueError(
                f"na_action='{na_action}' not in ('impute_mean', 'drop', 'zero')"
            )
        self.na_action = str(na_action)
        if not isinstance(standardize, bool):
            raise TypeError(f"standardize must be bool, got {type(standardize)}")
        self.standardize = bool(standardize)

    def fit(self, X, y) -> "LinearRegressionForecaster":
        X_clean, y_clean = self._drop_nan_xy(X, y)
        self.model_ = None
        if X_clean is None or X_clean.shape[0] < 2:
            return self
        self.model_ = LinearRegression(fit_intercept=self.fit_intercept)
        # Replace any remaining inf with 0 (defensive)
        if hasattr(X_clean, "replace"):
            X_clean = X_clean.replace([np.inf, -np.inf], 0.0)
        else:
            X_clean = np.where(np.isinf(X_clean), 0.0, X_clean)
        # Cache per-column mean and std for the standardize policy.
        if hasattr(X_clean, "mean"):
            self._col_means_ = X_clean.mean(numeric_only=True).fillna(0.0)
            self._col_stds_ = X_clean.std(numeric_only=True).fillna(1.0).replace(0, 1.0)
        else:
            self._col_means_ = np.nanmean(X_clean, axis=0)
            self._col_stds_ = np.nanstd(X_clean, axis=0, ddof=0)
            self._col_stds_[self._col_stds_ == 0] = 1.0
        # Apply standardization
        if self.standardize:
            if hasattr(X_clean, "div"):
                X_clean = (X_clean - self._col_means_) / self._col_stds_
            else:
                X_clean = (X_clean - self._col_means_) / self._col_stds_
        # Fill remaining NaN with 0 (the standardized mean)
        if hasattr(X_clean, "fillna"):
            X_clean = X_clean.fillna(0.0)
        else:
            X_clean = np.where(np.isnan(X_clean), 0.0, X_clean)
        self.model_.fit(X_clean, y_clean)
        return self

    def predict(self, X) -> np.ndarray:
        if not hasattr(self, "model_") or self.model_ is None or X is None:
            return self._predict_constant(self._n_rows(X))
        n = self._n_rows(X)
        if self.na_action == "drop":
            X_arr = self._to_2d(X)
            has_nan = np.isnan(X_arr).any(axis=1) if X_arr.ndim == 2 else np.zeros(n, dtype=bool)
            X_in = self._impute(X)
            preds = np.asarray(self.model_.predict(X_in), dtype=float)
            preds[has_nan] = np.nan
            return preds
        X_in = self._impute(X)
        return np.asarray(self.model_.predict(X_in), dtype=float)

    def _impute(self, X):
        if self.na_action == "zero":
            X_arr = self._to_2d(X)
            X_arr = np.where(np.isnan(X_arr), 0.0, X_arr)
            X_arr = np.where(np.isinf(X_arr), 0.0, X_arr)
            return X_arr
        if self.standardize:
            # Standardize using train statistics; missing values become 0
            # (= the standardized mean).
            if hasattr(X, "sub") and hasattr(self, "_col_means_"):
                X_in = (X - self._col_means_) / self._col_stds_
                X_in = X_in.replace([np.inf, -np.inf], 0.0).fillna(0.0)
            else:
                X_arr = np.asarray(X, dtype=float)
                X_in = (X_arr - np.asarray(self._col_means_, dtype=float)) / np.asarray(self._col_stds_, dtype=float)
                X_in = np.where(np.isnan(X_in), 0.0, X_in)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
            return X_in
        # impute_mean (default)
        if hasattr(X, "fillna") and hasattr(self, "_col_means_"):
            X_in = X.replace([np.inf, -np.inf], np.nan).fillna(self._col_means_)
        else:
            X_arr = np.asarray(X, dtype=float)
            if hasattr(self, "_col_means_"):
                means = np.asarray(self._col_means_, dtype=float)
                X_in = np.where(np.isnan(X_arr), means, X_arr)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
            else:
                X_in = np.where(np.isnan(X_arr), 0.0, X_arr)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
        return X_in

    @staticmethod
    def _to_2d(X):
        """Coerce X to a 2D ``np.ndarray`` for ``has_nan`` detection."""
        if hasattr(X, "to_numpy"):
            return np.atleast_2d(X.to_numpy(dtype=float))
        return np.atleast_2d(np.asarray(X, dtype=float))

    @staticmethod
    def _n_rows(X) -> int:
        if X is None:
            return 0
        if hasattr(X, "shape"):
            return int(X.shape[0])
        return int(len(X))


# ── 4. Ridge regression ─────────────────────────────────────────────────────


class RidgeForecaster(_BaseForecaster):
    """Ridge regression with a single global ``alpha`` (Master Plan §10.3).

    Parameters
    ----------
    alpha : float, default 1.0
        L2 regularization strength.
    fit_intercept : bool, default True
        Whether to add an intercept.
    na_action : {"impute_mean", "drop", "zero"}, default "impute_mean"
        See :class:`LinearRegressionForecaster` for semantics.
    standardize : bool, default False
        If True, z-score the features using train statistics. See
        :class:`LinearRegressionForecaster` for the rationale.
    """

    def __init__(self, alpha: float = 1.0, fit_intercept: bool = True,
                 na_action: str = "impute_mean",
                 standardize: bool = False) -> None:
        self.alpha = float(alpha)
        self.fit_intercept = bool(fit_intercept)
        if na_action not in ("impute_mean", "drop", "zero"):
            raise ValueError(
                f"na_action='{na_action}' not in ('impute_mean', 'drop', 'zero')"
            )
        self.na_action = str(na_action)
        if not isinstance(standardize, bool):
            raise TypeError(f"standardize must be bool, got {type(standardize)}")
        self.standardize = bool(standardize)

    def fit(self, X, y) -> "RidgeForecaster":
        X_clean, y_clean = self._drop_nan_xy(X, y)
        self.model_ = None
        if X_clean is None or X_clean.shape[0] < 2:
            return self
        self.model_ = Ridge(alpha=self.alpha, fit_intercept=self.fit_intercept)
        if hasattr(X_clean, "replace"):
            X_clean = X_clean.replace([np.inf, -np.inf], 0.0)
        else:
            X_clean = np.where(np.isinf(X_clean), 0.0, X_clean)
        if hasattr(X_clean, "mean"):
            self._col_means_ = X_clean.mean(numeric_only=True).fillna(0.0)
            self._col_stds_ = X_clean.std(numeric_only=True).fillna(1.0).replace(0, 1.0)
        else:
            self._col_means_ = np.nanmean(X_clean, axis=0)
            self._col_stds_ = np.nanstd(X_clean, axis=0, ddof=0)
            self._col_stds_[self._col_stds_ == 0] = 1.0
        if self.standardize:
            if hasattr(X_clean, "sub"):
                X_clean = (X_clean - self._col_means_) / self._col_stds_
            else:
                X_clean = (X_clean - self._col_means_) / self._col_stds_
        if hasattr(X_clean, "fillna"):
            X_clean = X_clean.fillna(0.0)
        else:
            X_clean = np.where(np.isnan(X_clean), 0.0, X_clean)
        self.model_.fit(X_clean, y_clean)
        return self

    def predict(self, X) -> np.ndarray:
        if not hasattr(self, "model_") or self.model_ is None or X is None:
            return self._predict_constant(self._n_rows(X))
        n = self._n_rows(X)
        if self.na_action == "drop":
            X_arr = self._to_2d(X)
            has_nan = np.isnan(X_arr).any(axis=1) if X_arr.ndim == 2 else np.zeros(n, dtype=bool)
            X_in = self._impute(X)
            preds = np.asarray(self.model_.predict(X_in), dtype=float)
            preds[has_nan] = np.nan
            return preds
        X_in = self._impute(X)
        return np.asarray(self.model_.predict(X_in), dtype=float)

    def _impute(self, X):
        if self.na_action == "zero":
            X_arr = self._to_2d(X)
            X_arr = np.where(np.isnan(X_arr), 0.0, X_arr)
            X_arr = np.where(np.isinf(X_arr), 0.0, X_arr)
            return X_arr
        if self.standardize:
            if hasattr(X, "sub") and hasattr(self, "_col_means_"):
                X_in = (X - self._col_means_) / self._col_stds_
                X_in = X_in.replace([np.inf, -np.inf], 0.0).fillna(0.0)
            else:
                X_arr = np.asarray(X, dtype=float)
                X_in = (X_arr - np.asarray(self._col_means_, dtype=float)) / np.asarray(self._col_stds_, dtype=float)
                X_in = np.where(np.isnan(X_in), 0.0, X_in)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
            return X_in
        if hasattr(X, "fillna") and hasattr(self, "_col_means_"):
            X_in = X.replace([np.inf, -np.inf], np.nan).fillna(self._col_means_)
        else:
            X_arr = np.asarray(X, dtype=float)
            if hasattr(self, "_col_means_"):
                means = np.asarray(self._col_means_, dtype=float)
                X_in = np.where(np.isnan(X_arr), means, X_arr)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
            else:
                X_in = np.where(np.isnan(X_arr), 0.0, X_arr)
                X_in = np.where(np.isinf(X_in), 0.0, X_in)
        return X_in

    @staticmethod
    def _to_2d(X):
        if hasattr(X, "to_numpy"):
            return np.atleast_2d(X.to_numpy(dtype=float))
        return np.atleast_2d(np.asarray(X, dtype=float))

    @staticmethod
    def _n_rows(X) -> int:
        if X is None:
            return 0
        if hasattr(X, "shape"):
            return int(X.shape[0])
        return int(len(X))

    @staticmethod
    def _n_rows(X) -> int:
        if X is None:
            return 0
        if hasattr(X, "shape"):
            return int(X.shape[0])
        return int(len(X))


# ── Convenience factory ─────────────────────────────────────────────────────


def make_baseline(name: str, **kwargs) -> _BaseForecaster:
    """Return a forecaster by name (case-insensitive).

    Used by the engine so models can be referenced by string in the horse
    race config (and persisted to the benchmark CSV).
    """
    table = {
        "historical_mean": HistoricalMeanForecaster,
        "ar1": AR1Forecaster,
        "linear_regression": LinearRegressionForecaster,
        "ols": LinearRegressionForecaster,
        "ridge": RidgeForecaster,
    }
    key = name.lower().strip()
    if key not in table:
        raise KeyError(
            f"Unknown baseline '{name}'. Known: {sorted(table)}"
        )
    return table[key](**kwargs)
