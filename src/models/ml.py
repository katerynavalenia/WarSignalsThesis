"""XGBoost forecaster for the Phase 7 horse race.

This module wraps ``xgboost.XGBRegressor`` in the scikit-learn-style
``fit`` / ``predict`` interface that the Phase 6 expanding-window engine
expects (see :mod:`src.models.baselines` for the base contract).

Key design choices (Master Plan §10.4):

- **NaN handling is delegated to XGBoost natively** — XGBoost's
  ``sparse_split`` learns the optimal "missing → branch" at each split.
  We do NOT impute / standardize (contrast with OLS / Ridge which require
  ``standardize=True`` to handle the distribution shift between train
  and test in the P/PN/PNG info sets).
- **Early stopping on a held-out tail of the training data** — a fixed
  ``val_fraction`` of the most recent train rows is used as the
  validation set; this mirrors the "fit within training fold only" rule
  from Master Plan §11.
- **Shallow trees, conservative learning rate, early stopping** — the
  Master Plan §10.4 default recipe; the TS-CV grid search in
  :mod:`src.models.ml_tuning` tunes this further on a held-out CV set.

The class is intentionally minimal: a thin wrapper that handles the
``fit`` / ``predict`` interface, NaN delegation, early stopping, and
scikit-learn ``clone`` compatibility. All the heavy lifting is done by
``xgboost``.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin

try:
    import xgboost as _xgb
    _HAS_XGB = True
except Exception:  # pragma: no cover — xgboost is in requirements.txt
    _HAS_XGB = False

from src.models.baselines import _BaseForecaster


__all__ = ["XGBoostForecaster"]


class XGBoostForecaster(_BaseForecaster):
    """XGBoost regressor with early stopping, scikit-learn-style interface.

    Parameters
    ----------
    max_depth : int, default 5
        Maximum tree depth (Master Plan §10.4: shallow trees).
    learning_rate : float, default 0.05
        Step size shrinkage (Master Plan §10.4: conservative).
    n_estimators : int, default 500
        Maximum number of boosting rounds. Actual number is determined
        by early stopping.
    min_child_weight : int, default 5
        Minimum sum of instance weight (Hessian) needed in a child.
    reg_alpha : float, default 0.0
        L1 regularization term on weights.
    reg_lambda : float, default 1.0
        L2 regularization term on weights.
    subsample : float, default 0.8
        Subsample ratio of the training instances per boosting round.
    colsample_bytree : float, default 0.8
        Subsample ratio of columns when constructing each tree.
    early_stopping_rounds : int, default 50
        Stop training if validation score does not improve for this many
        rounds. If ``None``, no early stopping.
    val_fraction : float, default 0.15
        Fraction of the most-recent training rows held out as the
        validation set for early stopping. Must be in (0, 1).
    objective : str, default "reg:squarederror"
        XGBoost objective function. ``"reg:squarederror"`` for point
        forecasting; ``"reg:absoluteerror"`` for MAE-direct.
    eval_metric : str, default "mae"
        Metric monitored for early stopping. ``"mae"`` matches the
        Phase 6 evaluation metric.
    random_state : int, default 42
        Random seed for reproducibility.
    n_jobs : int, default 1
        Number of parallel threads. Default 1 to keep the expanding
        window engine deterministic.

    Attributes
    ----------
    model_ : xgboost.XGBRegressor
        The fitted XGBoost model.
    best_iteration_ : int
        Best iteration found by early stopping (0 if no early stopping).
    best_score_ : float
        Best validation score (in the eval_metric scale).
    n_features_in_ : int
        Number of features seen at fit time.
    feature_names_ : list of str
        Feature names (the columns of the train DataFrame).
    """

    def __init__(
        self,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        n_estimators: int = 500,
        min_child_weight: int = 5,
        reg_alpha: float = 0.0,
        reg_lambda: float = 1.0,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        early_stopping_rounds: int = 50,
        val_fraction: float = 0.15,
        objective: str = "reg:squarederror",
        eval_metric: str = "mae",
        random_state: int = 42,
        n_jobs: int = 1,
    ) -> None:
        if not _HAS_XGB:
            raise ImportError(
                "The `xgboost` package is required for XGBoostForecaster. "
                "Install with `pip install xgboost`."
            )
        if not 0.0 < val_fraction < 1.0:
            raise ValueError(
                f"val_fraction must be in (0, 1), got {val_fraction!r}"
            )
        self.max_depth = int(max_depth)
        self.learning_rate = float(learning_rate)
        self.n_estimators = int(n_estimators)
        self.min_child_weight = int(min_child_weight)
        self.reg_alpha = float(reg_alpha)
        self.reg_lambda = float(reg_lambda)
        self.subsample = float(subsample)
        self.colsample_bytree = float(colsample_bytree)
        self.early_stopping_rounds = (
            int(early_stopping_rounds) if early_stopping_rounds is not None
            else None
        )
        self.val_fraction = float(val_fraction)
        self.objective = str(objective)
        self.eval_metric = str(eval_metric)
        self.random_state = int(random_state)
        self.n_jobs = int(n_jobs)
        # Fitted-state attributes (set in fit())
        self.model_: Optional[_xgb.XGBRegressor] = None
        self.best_iteration_: int = 0
        self.best_score_: float = np.nan
        self.n_features_in_: int = 0
        self.feature_names_: list = []

    # ── Fit ───────────────────────────────────────────────────────────────

    def fit(self, X, y) -> "XGBoostForecaster":
        """Fit the XGBoost model.

        Parameters
        ----------
        X : pd.DataFrame or None
            Lagged feature matrix. If ``None``, an empty matrix is used
            (this matches the HistoricalMean / AR1 pattern but is unusual
            for a tree model — for a real run, pass a feature matrix).
        y : pd.Series
            Target vector in percent. Rows with NaN in ``y`` are dropped;
            rows with NaN in ``X`` are passed to XGBoost (which handles
            them natively).
        """
        # NaN-safe clean (drops rows where y is NaN; keeps X NaNs for XGBoost)
        X_clean, y_clean = self._drop_nan_y_only(X, y)

        # Coerce to DataFrame so the rest of the path is type-uniform
        if X_clean is not None and not isinstance(X_clean, pd.DataFrame):
            X_clean = pd.DataFrame(
                np.asarray(X_clean),
                columns=[f"f{i}" for i in range(np.asarray(X_clean).shape[1])]
                if hasattr(X_clean, "shape") and len(X_clean.shape) > 1
                else ["f0"],
            )

        # Handle the (rare) degenerate case
        if len(y_clean) < 10:
            # Not enough rows to fit; leave model_ as None
            self.model_ = None
            self.best_iteration_ = 0
            self.best_score_ = np.nan
            self.n_features_in_ = 0
            self.feature_names_ = []
            return self

        # Train/val split for early stopping
        n = len(y_clean)
        n_val = max(1, int(round(n * self.val_fraction)))
        n_train = n - n_val

        # If features are missing, build a constant 1-column frame
        # (allows the model to still train on a simple bias term).
        if X_clean is None or (
            hasattr(X_clean, "shape") and X_clean.shape[1] == 0
        ):
            X_full = pd.DataFrame(
                {"_const": np.ones(n)},
                index=getattr(y_clean, "index", None) if hasattr(y_clean, "index") else None,
            )
        else:
            X_full = X_clean.reset_index(drop=True)

        X_train = X_full.iloc[:n_train]
        X_val = X_full.iloc[n_train:]
        y_train = (
            y_clean.iloc[:n_train]
            if hasattr(y_clean, "iloc")
            else np.asarray(y_clean)[:n_train]
        )
        y_val = (
            y_clean.iloc[n_train:]
            if hasattr(y_clean, "iloc")
            else np.asarray(y_clean)[n_train:]
        )

        # Build the XGBoost model
        esr = self.early_stopping_rounds
        # XGBoost 2.x: early_stopping_rounds passed in constructor; in 3.x
        # deprecated. We pass it conditionally for forward compat.
        kwargs = dict(
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            n_estimators=self.n_estimators,
            min_child_weight=self.min_child_weight,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            objective=self.objective,
            eval_metric=self.eval_metric,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            tree_method="hist",
        )
        try:
            model = _xgb.XGBRegressor(
                early_stopping_rounds=esr,
                **kwargs,
            )
        except TypeError:
            # Older XGBoost versions may not accept the kwarg in constructor
            model = _xgb.XGBRegressor(**kwargs)

        try:
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)] if esr is not None else None,
                verbose=False,
            )
        except Exception as exc:  # pragma: no cover — defensive
            # On any fit failure, leave model_ as None; the engine will
            # fall back to NaN predictions for this fold.
            self.model_ = None
            self.best_iteration_ = 0
            self.best_score_ = np.nan
            self.n_features_in_ = int(X_full.shape[1])
            self.feature_names_ = list(X_full.columns)
            return self

        self.model_ = model
        self.n_features_in_ = int(X_full.shape[1])
        self.feature_names_ = list(X_full.columns)
        # best_iteration_ may not exist on older XGBoost; guard.
        self.best_iteration_ = int(
            getattr(model, "best_iteration_", 0) or 0
        )
        self.best_score_ = float(getattr(model, "best_score_", np.nan) or np.nan)
        return self

    # ── Predict ────────────────────────────────────────────────────────────

    def predict(self, X) -> np.ndarray:
        """1-step-ahead point forecast for each row in ``X``.

        Parameters
        ----------
        X : pd.DataFrame or None
            Feature matrix for the forecast period. Must have the same
            columns as the X passed to fit(). If ``None``, returns the
            training mean broadcast to the requested length.

        Returns
        -------
        np.ndarray
            1-D array of length ``len(X)`` (or 0 if X is None) of point
            forecasts, in the same units as the training target (percent).
        """
        if self.model_ is None:
            # Fallback: return zeros (or training mean if we have it)
            if hasattr(self, "mean_") and self.mean_ is not None:
                return np.full(_n_rows(X), float(self.mean_))
            return np.zeros(_n_rows(X))

        if X is None or (
            hasattr(X, "shape") and X.shape[0] == 0
        ):
            return np.zeros(0)

        # If we trained with a constant frame (no real features), and the
        # test set has different columns, build a matching constant frame.
        if not hasattr(X, "columns"):
            X = pd.DataFrame(X)
        if list(X.columns) != self.feature_names_:
            # Try to align; if the test set has only a subset, build a
            # zero-filled frame with the train columns.
            X_aligned = pd.DataFrame(
                {c: X[c] if c in X.columns else np.zeros(len(X))
                 for c in self.feature_names_},
                index=X.index,
            )
        else:
            X_aligned = X.reset_index(drop=True)

        try:
            preds = self.model_.predict(
                X_aligned,
                iteration_range=(0, (self.best_iteration_ or 0) + 1),
            )
        except TypeError:
            # Older XGBoost without iteration_range kwarg
            preds = self.model_.predict(X_aligned)
        except Exception:  # pragma: no cover — defensive
            return np.full(len(X_aligned), np.nan)
        return np.asarray(preds, dtype=float)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _drop_nan_y_only(
        self, X: Optional[pd.DataFrame], y: pd.Series
    ) -> tuple:
        """Drop rows where ``y`` is NaN; keep ``X`` as-is (XGBoost
        handles X NaN natively)."""
        y_arr = np.asarray(y, dtype=float)
        mask = ~np.isnan(y_arr)
        y_clean = (
            y.iloc[mask] if hasattr(y, "iloc")
            else y_arr[mask]
        )
        if X is None:
            return None, np.asarray(y_clean, dtype=float)
        if hasattr(X, "iloc"):
            X_clean = X.iloc[mask].reset_index(drop=True)
        else:
            X_clean = np.asarray(X)[mask]
        y_arr2 = np.asarray(y_clean, dtype=float)
        return X_clean, y_arr2


def _n_rows(X) -> int:
    """Return the number of rows in X, or 0 if X is None."""
    if X is None:
        return 0
    if hasattr(X, "shape"):
        return int(X.shape[0])
    try:
        return int(len(X))
    except Exception:
        return 0
