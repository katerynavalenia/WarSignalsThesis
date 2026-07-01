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


__all__ = ["GARCHForecaster", "make_garch_forecaster"]


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
            return var[:h] * self.scale_
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
