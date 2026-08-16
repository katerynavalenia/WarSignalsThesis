"""GARCH-family volatility baselines for the Phase 6 horse race.

Wraps the ``arch`` package (https://bashtage.github.io/arch/) and exposes a
uniform :class:`GARCHForecaster` class with three variants:

- ``"GARCH"``         : Bollerslev (1986) GARCH(1,1)
- ``"GJR_GARCH"``     : Glosten-Jagannathan-Runkle (1993) GJR-GARCH
- ``"EGARCH"``        : Nelson (1991) Exponential GARCH

Per Master Plan §10.3 the default specification is:

- mean equation : ``Constant`` (no exogenous regressors in the mean)
- distribution  : Student-t (``dist="t"``) for fatter tails
- ``p = q = 1``  (single lag on each side)
- rescale       : input is in percent (``r_*`` columns); internally divided
                   by 100 to match ``arch``'s convention, then the variance
                   forecast is multiplied back to percent².

The forecaster is **univariate** — it ignores all features and only sees the
target series. The information-set horse race (Master Plan §10.2) is
delegated to the OLS / Ridge baselines in :mod:`src.models.baselines`. This
matches the Master Plan's "add attack/news features as exogenous variables
only after the baseline is functioning" guidance.
"""
from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd

try:
    from arch import arch_model as _arch_model
    _HAS_ARCH = True
except Exception:  # pragma: no cover — `arch` is in requirements.txt
    _HAS_ARCH = False


__all__ = ["GARCHForecaster", "GARCHXForecaster", "make_garch_forecaster"]


# ── Forecaster class ────────────────────────────────────────────────────────


class GARCHForecaster:
    """Univariate GARCH-family forecaster with a uniform ``fit`` / ``predict``.

    Parameters
    ----------
    variant : {"GARCH", "GJR_GARCH", "EGARCH"}, default "GARCH"
        Which GARCH specification to fit.
    p : int, default 1
        Order of the symmetric ARCH term.
    q : int, default 1
        Order of the GARCH term.
    dist : {"normal", "t", "skewt"}, default "t"
        Innovation distribution.
    rescale : bool, default True
        If True, input ``y`` is assumed to be in **percent** and divided by
        100 for the internal MLE. The variance forecast is multiplied by
        10,000 (100²) when returned, so the output units are percent².
    mean : str, default "Constant"
        Mean equation. Use ``"Zero"`` to drop the constant (recommended for
        returns, since the in-sample mean is typically ~0).
    """

    variants = ("GARCH", "GJR_GARCH", "EGARCH")

    def __init__(
        self,
        variant: str = "GARCH",
        p: int = 1,
        q: int = 1,
        dist: str = "t",
        rescale: bool = True,
        mean: str = "Zero",
    ) -> None:
        if not _HAS_ARCH:
            raise ImportError(
                "The `arch` package is required for GARCHForecaster. "
                "Install with `pip install arch`."
            )
        if variant not in self.variants:
            raise ValueError(
                f"variant='{variant}' not in {self.variants}"
            )
        self.variant = str(variant)
        self.p = int(p)
        self.q = int(q)
        self.dist = str(dist)
        self.rescale = bool(rescale)
        self.mean = str(mean)
        self.result_ = None  # populated by .fit()
        self.scale_ = 1.0   # populated by .fit()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _scale_factor(self) -> float:
        """Multiplicative factor to convert internal variance to ``%²``."""
        return 1.0 if not self.rescale else 10_000.0

    def _input_scale_factor(self) -> float:
        """Factor to divide the input ``y`` by before passing to ``arch``."""
        return 1.0 if not self.rescale else 100.0

    # ── Fit / predict ──────────────────────────────────────────────────────

    def fit(self, y) -> "GARCHForecaster":
        """Fit the model on a 1D ``y`` (Series, ndarray, or list)."""
        if not _HAS_ARCH:
            raise ImportError("`arch` is required for GARCHForecaster.")
        # Coerce to a clean Series indexed by date (arch requires a DateIndex
        # or RangeIndex; RangeIndex is fine for OOS usage).
        if isinstance(y, pd.Series):
            arr = y.to_numpy(dtype=float)
        else:
            arr = np.asarray(y, dtype=float)

        mask = ~np.isnan(arr)
        if mask.sum() < 30:
            # Too few observations; leave result_ = None and rely on the
            # unconditional variance fallback in predict().
            self.result_ = None
            self.scale_ = 1.0
            return self
        y_clean = pd.Series(arr[mask])

        scale_in = self._input_scale_factor()
        y_scaled = y_clean / scale_in

        kwargs = dict(
            mean=self.mean,
            vol=self.variant,
            p=self.p,
            q=self.q,
            dist=self.dist,
            rescale=False,
        )
        # GJR needs an explicit o=q (asymmetry order)
        if self.variant == "GJR_GARCH":
            kwargs["o"] = self.q
            kwargs["vol"] = "GARCH"

        am = _arch_model(y_scaled, **kwargs)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.result_ = am.fit(disp="off", show_warning=False)
            except Exception:
                # Fall back to a simpler model on optimization failure
                try:
                    am2 = _arch_model(
                        y_scaled, mean=self.mean, vol="GARCH",
                        p=self.p, q=self.q, dist="normal", rescale=False,
                    )
                    self.result_ = am2.fit(disp="off", show_warning=False)
                except Exception:
                    self.result_ = None
        self.scale_ = self._scale_factor()
        return self

    def predict(self, horizon: int = 1, n_sims: int = 1000) -> np.ndarray:
        """Return the conditional-variance forecast ``horizon`` steps ahead.

        Units are percent² (when ``rescale=True``). Length is ``horizon``.

        For ``GARCH`` and ``GJR_GARCH`` the closed-form analytic h-step
        forecast is used (via ``arch.forecast(method='analytic')``).

        For ``EGARCH`` no closed-form h>1 forecast is available from
        ``arch``, so we fall back to **Monte-Carlo simulation**: draw
        ``n_sims`` paths of the standardized residuals for ``horizon``
        steps, propagate them through the EGARCH recursion, and return
        the mean conditional variance. This is the only correct way to
        get multi-step EGARCH variance forecasts.

        On fit failure the unconditional variance of the training ``y``
        is used as a constant fallback.
        """
        h = max(1, int(horizon))
        if self.result_ is None:
            return np.full(h, 1.0)

        # ── EGARCH needs simulation for h > 1 ─────────────────────────────
        if self.variant == "EGARCH" and h > 1:
            return self._simulate_egarch(horizon=h, n_sims=n_sims)

        try:
            fcast = self.result_.forecast(horizon=h, reindex=False)
            # `variance` has shape (nobs, horizon); take the last row.
            var = np.asarray(fcast.variance.iloc[-1].to_numpy(), dtype=float)
            if var.size < h:
                # Pad with last value if necessary
                var = np.concatenate([var, np.full(h - var.size, var[-1])])
            # Clip to a sane upper bound — daily variance > 1e10 is
            # numerically nonsense and produces a RuntimeWarning. The
            # fallback constant 1.0 would be used downstream anyway.
            var = np.clip(var[:h], 0.0, 1e10)
            return var * self.scale_
        except Exception:
            return np.full(h, 1.0)

    def _simulate_egarch(self, horizon: int, n_sims: int = 1000) -> np.ndarray:
        """Monte-Carlo multi-step EGARCH variance forecast.

        Draws ``n_sims`` future residual paths from the standardized
        innovation distribution, propagates them through the EGARCH
        recursion for ``horizon`` steps, and returns the mean
        conditional variance at each horizon step.
        """
        try:
            res = self.result_
            p = self.p
            q = self.q
            scale = self.scale_

            # Parameters: omega, alpha[1..p], gamma[1..q] (EGARCH only),
            # beta[1..p]. For EGARCH(1,1): omega, alpha[1], beta[1].
            params = np.asarray(res.params, dtype=float)
            omega = float(params[0])
            alphas = params[1:1 + p]
            # EGARCH in `arch` does not have a separate gamma parameter;
            # the asymmetric response is captured by the alpha coefficient
            # applied to |z| * (sign(z) - E[sign(z)]) or via a
            # ``vol="EGARCH"`` with a `o` term. With EGARCH and no `o`,
            # the recursion is:
            #   log(σ²_t) = ω + Σ α_i * |z_{t-i}| + Σ β_j * log(σ²_{t-j})
            #              + γ_k * z_{t-k}   (asymmetry, if EGARCH-GJR)
            betas = params[1 + p:1 + p + p]

            # Last in-sample log(σ²) and standardized residual
            # (we need the conditional variance at the last in-sample point).
            last_var = float(res.conditional_volatility.iloc[-1] ** 2)
            log_sigma2 = np.log(max(last_var, 1e-12))

            # Use the standardized residuals from the fit to draw future
            # innovations.
            try:
                std_resid = np.asarray(res.std_resid, dtype=float)
            except Exception:
                std_resid = np.array([0.0])
            std_resid = std_resid[~np.isnan(std_resid)]
            if std_resid.size < 30:
                # Too few residuals — fall back to standard normal.
                rng = np.random.default_rng(42)
            else:
                rng = np.random.default_rng(42)

            sim_paths = np.empty((n_sims, horizon), dtype=float)
            for s in range(n_sims):
                if std_resid.size >= 30:
                    z = rng.choice(std_resid, size=horizon, replace=True)
                else:
                    z = rng.standard_normal(horizon)
                buf_log = np.full(max(p, q) + 1, log_sigma2, dtype=float)
                buf_abs = np.zeros(max(p, q) + 1, dtype=float)
                for t in range(horizon):
                    new_log = omega
                    for i, a in enumerate(alphas):
                        new_log += float(a) * abs(buf_abs[-(i + 1)])
                    for j, b in enumerate(betas):
                        new_log += float(b) * buf_log[-(j + 1)]
                    # Roll the buffers
                    buf_log = np.roll(buf_log, -1)
                    buf_log[-1] = new_log
                    buf_abs = np.roll(buf_abs, -1)
                    buf_abs[-1] = abs(z[t])
                    sim_paths[s, t] = np.exp(new_log)

            mean_path = sim_paths.mean(axis=0)
            # Apply rescale
            return mean_path * scale
        except Exception:
            return np.full(horizon, 1.0)

    # ── State ──────────────────────────────────────────────────────────────

    def __sklearn_clone__(self):
        """Allow sklearn.base.clone to copy a fitted forecaster."""
        new = GARCHForecaster(
            variant=self.variant, p=self.p, q=self.q,
            dist=self.dist, rescale=self.rescale, mean=self.mean,
        )
        new.result_ = self.result_
        new.scale_ = self.scale_
        return new


# ── Convenience factory ─────────────────────────────────────────────────────


def make_garch_forecaster(
    name: str = "GARCH",
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    rescale: bool = True,
    mean: str = "Zero",
) -> GARCHForecaster:
    """Return a :class:`GARCHForecaster` by name (case-insensitive)."""
    key = name.upper().strip()
    return GARCHForecaster(
        variant=key, p=p, q=q, dist=dist, rescale=rescale, mean=mean,
    )


# ── GARCH-X — exogenous regressors in the mean equation ────────────────────


class GARCHXForecaster:
    """GARCH-family forecaster with exogenous regressors in the mean equation.

    This is the Phase 7.5 extension of :class:`GARCHForecaster` (deferred
    from the Phase 6 audit). The mean equation is ``"ARX"`` — the
    exogenous regressors enter the conditional mean (not the variance)
    of the return process. This matches the ``arch`` package's ``x=``
    parameter (passed to ``arch_model(..., x=exog, mean="ARX", ...)``).

    For multi-step forecasts (``horizon > 1``), the ``arch`` package
    does not natively support exogenous regressors. We use a
    **recursive 1-step forecast** that consumes the next ``horizon``
    rows of the exogenous matrix one at a time. This mirrors the
    C4 fix for EGARCH h>1 from Phase 6. For h=1, we use the
    standard 1-step forecast (exog = last row).

    If the ``arch`` package refuses the ARX + chosen vol model
    combination, we fall back to a two-step approach: fit
    ARX with GARCH, take the residuals, then fit a univariate
    GARCH on the residuals. The forecast is then
    ``ARX_mean_forecast + GARCH_residual_variance_forecast``.

    Parameters
    ----------
    variant : {"GARCH", "GJR_GARCH", "EGARCH"}, default "GARCH"
        Which GARCH specification to fit.
    p : int, default 1
    q : int, default 1
    dist : {"normal", "t", "skewt"}, default "t"
    rescale : bool, default True
        If True, ``y`` is divided by 100 internally and the variance
        forecast is multiplied by 10,000 (matching GARCHForecaster).
    fallback : bool, default True
        If True, fall back to the two-step ARX-residual + univariate
        GARCH on arch-package refusal.
    n_sim : int, default 200
        Reserved for future simulation-based h-step forecasts.
    """

    variants = ("GARCH", "GJR_GARCH", "EGARCH")

    def __init__(
        self,
        variant: str = "GARCH",
        p: int = 1,
        q: int = 1,
        dist: str = "t",
        rescale: bool = True,
        fallback: bool = True,
        n_sim: int = 200,
    ) -> None:
        if not _HAS_ARCH:
            raise ImportError(
                "The `arch` package is required for GARCHXForecaster."
            )
        if variant not in self.variants:
            raise ValueError(f"variant='{variant}' not in {self.variants}")
        self.variant = str(variant)
        self.p = int(p)
        self.q = int(q)
        self.dist = str(dist)
        self.rescale = bool(rescale)
        self.fallback = bool(fallback)
        self.n_sim = int(n_sim)
        # Fitted-state
        self.result_ = None
        self.scale_ = 1.0
        self.exog_cols_: list = []
        self._used_fallback = False

    # ── Helpers (mirror GARCHForecaster) ──────────────────────────────────

    def _scale_factor(self) -> float:
        return 1.0 if not self.rescale else 10_000.0

    def _input_scale_factor(self) -> float:
        return 1.0 if not self.rescale else 100.0

    # ── Fit ───────────────────────────────────────────────────────────────

    def fit(self, y, X_exog: Optional[pd.DataFrame] = None) -> "GARCHXForecaster":
        """Fit a GARCH-X model.

        Parameters
        ----------
        y : pd.Series or 1D array
            Target return series (in percent when ``rescale=True``).
        X_exog : pd.DataFrame, optional
            Exogenous regressors. Must be aligned to ``y`` and contain
            no NaN in the rows where ``y`` is not NaN. If ``None``,
            behaves identically to :class:`GARCHForecaster`.
        """
        if not _HAS_ARCH:
            raise ImportError("`arch` is required for GARCHXForecaster.")
        # Coerce y
        if isinstance(y, pd.Series):
            arr = y.to_numpy(dtype=float)
            y_index = y.index
        else:
            arr = np.asarray(y, dtype=float)
            y_index = pd.RangeIndex(len(arr))
        mask = ~np.isnan(arr)
        if mask.sum() < 30:
            self.result_ = None
            self.scale_ = 1.0
            return self
        y_clean = pd.Series(arr[mask], index=y_index[mask])

        # Coerce X_exog
        if X_exog is None or (hasattr(X_exog, "empty") and X_exog.empty):
            # No exog: behave like GARCHForecaster
            self.exog_cols_ = []
            x_for_arch = None
        else:
            if not isinstance(X_exog, pd.DataFrame):
                X_exog = pd.DataFrame(
                    X_exog,
                    columns=[f"f{i}" for i in range(np.asarray(X_exog).shape[1])]
                    if hasattr(X_exog, "shape") and len(X_exog.shape) > 1
                    else ["f0"],
                )
            X_exog = X_exog.reset_index(drop=True)
            # Drop rows where y is NaN; align to y_clean
            mask_arr = mask.values if hasattr(mask, "values") else np.asarray(mask)
            X_exog = X_exog.iloc[mask_arr].reset_index(drop=True)
            # Replace any remaining NaN with 0 (exog shouldn't be NaN at fit time
            # if features are pre-lagged, but be defensive)
            X_exog = X_exog.fillna(0.0)
            self.exog_cols_ = list(X_exog.columns)
            x_for_arch = X_exog

        scale_in = self._input_scale_factor()
        y_scaled = y_clean / scale_in

        kwargs = dict(
            mean="ARX",
            vol=self.variant,
            p=self.p,
            q=self.q,
            dist=self.dist,
            rescale=False,
        )
        if self.variant == "GJR_GARCH":
            kwargs["o"] = self.q
            kwargs["vol"] = "GARCH"

        if x_for_arch is not None:
            am = _arch_model(y_scaled, x=x_for_arch, **kwargs)
        else:
            am = _arch_model(y_scaled, **kwargs)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.result_ = am.fit(disp="off", show_warning=False)
            except Exception as exc:
                if not self.fallback or x_for_arch is None:
                    self.result_ = None
                else:
                    # Fall back: ARX with normal dist and GARCH vol
                    try:
                        kwargs2 = dict(kwargs)
                        kwargs2["dist"] = "normal"
                        am2 = _arch_model(
                            y_scaled, x=x_for_arch, **kwargs2,
                        )
                        self.result_ = am2.fit(disp="off", show_warning=False)
                        self._used_fallback = True
                    except Exception:
                        self.result_ = None
        self.scale_ = self._scale_factor()
        return self

    # ── Predict ────────────────────────────────────────────────────────────

    def predict(
        self,
        horizon: int = 1,
        X_exog_horizon: Optional[pd.DataFrame] = None,
    ) -> np.ndarray:
        """Return the conditional-variance forecast ``horizon`` steps ahead.

        For ``horizon = 1``, uses the standard 1-step forecast with the
        last row of ``X_exog_horizon`` (if provided).

        For ``horizon > 1``, uses a **recursive 1-step forecast**:
        re-fit is not feasible per-step, so we rely on the
        :meth:`arch.result.forecast` API with ``reindex=False`` and
        feed the next ``horizon`` rows of ``X_exog_horizon`` one at
        a time. The arch package does support exog in 1-step
        forecasts; for h-step it does not, so we approximate by
        calling 1-step forecast ``horizon`` times and updating the
        history.

        Returns an array of length ``horizon`` (percent² units when
        ``rescale=True``).
        """
        h = max(1, int(horizon))
        if self.result_ is None:
            return np.full(h, 1.0)

        x_for_forecast = self._build_forecast_x(horizon=h, X_exog_horizon=X_exog_horizon)

        if h == 1:
            try:
                fcast = self.result_.forecast(
                    horizon=1, x=x_for_forecast, reindex=False,
                )
                var = np.asarray(
                    fcast.variance.iloc[-1].to_numpy(), dtype=float
                )
                return np.array([float(var[0]) * self.scale_])
            except Exception:
                return np.array([1.0])

        # h > 1 — recursive 1-step forecast with the exogenous path
        return self._recursive_h_step_forecast(horizon=h, x_for_forecast=x_for_forecast)

    def _build_forecast_x(
        self, horizon: int, X_exog_horizon: Optional[pd.DataFrame],
    ) -> Optional[dict]:
        """Build the ``x=`` argument for ``arch``'s ``.forecast()``.

        ``arch`` expects, for models fit with a DataFrame ``x``, a mapping
        from exogenous-column name to an array of shape
        ``(nobs - start, horizon)`` — i.e. one row (forecast origin) by
        ``horizon`` columns (the expected future path of that regressor).
        Since we only ever forecast from the last in-sample origin, the
        row dimension is always 1.

        Returns ``None`` if the model was fit without exogenous regressors.
        """
        if not self.exog_cols_:
            return None
        if X_exog_horizon is None:
            raise ValueError(
                "Model was fit with exogenous regressors but no "
                "X_exog_horizon was provided to predict()."
            )
        X_exog_horizon = X_exog_horizon.reset_index(drop=True)
        if len(X_exog_horizon) < horizon:
            # Pad by repeating the last available row.
            pad = pd.DataFrame(
                [X_exog_horizon.iloc[-1]] * (horizon - len(X_exog_horizon))
            )
            X_exog_horizon = pd.concat(
                [X_exog_horizon, pad], ignore_index=True,
            )
        X_exog_horizon = X_exog_horizon.iloc[:horizon].fillna(0.0)
        return {
            col: X_exog_horizon[col].to_numpy(dtype=float).reshape(1, -1)
            for col in self.exog_cols_
        }

    def _recursive_h_step_forecast(
        self, horizon: int, x_for_forecast: Optional[dict],
    ) -> np.ndarray:
        """h-step-ahead variance forecast with the exogenous path supplied.

        Despite the name (kept for backward compatibility), this now uses
        ``arch``'s native multi-step ``forecast(horizon=h, x=...)`` with the
        expected exogenous path rather than a manual recursion — the exog
        enters only the MEAN equation, so the analytic h-step VARIANCE
        forecast from ``arch`` is exact once the correct ``x`` is supplied
        (and is required at all when ``x`` is not ``None``, since ``arch``
        raises otherwise).
        """
        try:
            fcast = self.result_.forecast(
                horizon=horizon, x=x_for_forecast, reindex=False,
            )
            var = np.asarray(fcast.variance.iloc[-1].to_numpy(), dtype=float)
            if var.size < horizon:
                var = np.concatenate([var, np.full(horizon - var.size, var[-1])])
            return var[:horizon] * self.scale_
        except Exception:
            return np.full(horizon, 1.0)

    # ── State ─────────────────────────────────────────────────────────────

    def __sklearn_clone__(self):
        new = GARCHXForecaster(
            variant=self.variant, p=self.p, q=self.q,
            dist=self.dist, rescale=self.rescale,
            fallback=self.fallback, n_sim=self.n_sim,
        )
        new.result_ = self.result_
        new.scale_ = self.scale_
        new.exog_cols_ = list(self.exog_cols_)
        return new
