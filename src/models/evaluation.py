"""Forecast-evaluation statistics — supervisor comment #4.

v1 judged out-of-sample forecasts on MAE and directional accuracy and reported
no formal test. That is not the toolkit this literature uses, and it is not
sensitive enough to detect the effect sizes it deals in: a real signal of
R²_OS = 0.5% is invisible in MAE. The two Clark–West figures quoted in the v1
audit were computed ad hoc in a session and never committed, so nothing testable
survived.

This module is that missing piece. It matters more under the null framing than
it would have under a positive one: once the thesis's answer is "nothing is
priced", the claim rests entirely on being able to say *how much* would have
been detectable. A null without a power statement is an absence of evidence;
with one it is evidence of absence. :func:`min_detectable_r2_oos` is therefore
the load-bearing function here, not an accessory to the tests.

Conventions used throughout:

* **Losses, not errors.** Functions take realized values and forecasts and form
  losses internally, so squared-versus-absolute is an explicit argument rather
  than an assumption buried in a caller.
* **Nested versus non-nested matters.** Diebold–Mariano is invalid when one
  model nests the other — the standard case of "benchmark plus a predictor" —
  because the DM statistic is not asymptotically normal there. Use
  :func:`clark_west` for nested comparisons. The distinction is enforced by
  having two functions rather than one with a flag.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


def _align(*series: pd.Series) -> list[np.ndarray]:
    """Inner-join on index, drop rows where anything is missing."""
    frame = pd.concat([s.rename(f"s{i}") for i, s in enumerate(series)], axis=1).dropna()
    if frame.empty:
        raise ValueError("no overlapping non-missing observations")
    return [frame[c].to_numpy(dtype=float) for c in frame.columns]


# --- out-of-sample fit -------------------------------------------------------


def campbell_thompson_r2_oos(
    actual: pd.Series, forecast: pd.Series, benchmark: pd.Series
) -> float:
    """Campbell–Thompson out-of-sample R², as a fraction (0.005 = 0.5%).

    ``1 - MSE(model)/MSE(benchmark)``. Negative means the model forecasts worse
    than the benchmark, which for daily return prediction is the common case and
    is not a bug. Values of 0.3–1% are publishable in this literature, which is
    precisely why MAE cannot arbitrate.
    """
    a, f, b = _align(actual, forecast, benchmark)
    sse_model = float(np.sum((a - f) ** 2))
    sse_bench = float(np.sum((a - b) ** 2))
    if sse_bench == 0:
        raise ValueError("benchmark has zero forecast error; R²_OS undefined")
    return 1.0 - sse_model / sse_bench


def mse_ratio(actual: pd.Series, forecast: pd.Series, benchmark: pd.Series) -> float:
    """MSE(model) / MSE(benchmark). Below 1 favours the model."""
    return 1.0 - campbell_thompson_r2_oos(actual, forecast, benchmark)


# --- tests of equal predictive accuracy --------------------------------------


@dataclass
class TestResult:
    statistic: float
    pvalue: float
    n: int
    note: str = ""

    def __str__(self) -> str:
        return f"stat={self.statistic:+.3f}, p={self.pvalue:.4f}, n={self.n}"


def _newey_west_var(d: np.ndarray, lags: int) -> float:
    """Long-run variance of a loss differential, Bartlett kernel."""
    d = d - d.mean()
    n = len(d)
    gamma0 = float(d @ d) / n
    total = gamma0
    for k in range(1, lags + 1):
        cov = float(d[k:] @ d[:-k]) / n
        total += 2.0 * (1.0 - k / (lags + 1.0)) * cov
    return total


def diebold_mariano(
    actual: pd.Series,
    forecast_a: pd.Series,
    forecast_b: pd.Series,
    horizon: int = 1,
    loss: str = "squared",
    small_sample: bool = True,
) -> TestResult:
    """Diebold–Mariano test of equal accuracy between two **non-nested** models.

    Positive statistic means model A has the larger loss, i.e. B forecasts
    better. Two-sided p-value.

    ``small_sample`` applies the Harvey–Leybourne–Newbold correction, which
    rescales the statistic and uses a t-distribution. It matters at the sample
    sizes this thesis works with and is on by default.

    Do **not** use this where one model nests the other — under the null the
    loss differential is degenerate and the statistic is not normal. That case
    is :func:`clark_west`.
    """
    a, fa, fb = _align(actual, forecast_a, forecast_b)
    if loss == "squared":
        d = (a - fa) ** 2 - (a - fb) ** 2
    elif loss == "absolute":
        d = np.abs(a - fa) - np.abs(a - fb)
    else:
        raise ValueError(f"unknown loss: {loss!r}")

    n = len(d)
    lags = max(horizon - 1, 0)
    var = _newey_west_var(d, lags)
    if var <= 0:
        raise ValueError("non-positive long-run variance; cannot form the statistic")

    stat = d.mean() / np.sqrt(var / n)
    note = ""
    if small_sample:
        adj = np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
        stat *= adj
        p = 2 * (1 - stats.t.cdf(abs(stat), df=n - 1))
        note = "Harvey-Leybourne-Newbold corrected"
    else:
        p = 2 * (1 - stats.norm.cdf(abs(stat)))
    return TestResult(float(stat), float(p), n, note)


def clark_west(
    actual: pd.Series,
    forecast_benchmark: pd.Series,
    forecast_model: pd.Series,
    horizon: int = 1,
) -> TestResult:
    """Clark–West test for **nested** models: benchmark vs benchmark-plus-predictor.

    Corrects the MSE comparison for the noise the larger model introduces by
    estimating parameters that are zero under the null. Without that adjustment
    the nested alternative is biased toward losing even when its predictor has
    genuine content — which is exactly how v1's information-set horse race was
    set up to fail.

    One-sided by construction: the alternative is that the larger model is
    better. Positive statistic favours the model.
    """
    a, fb, fm = _align(actual, forecast_benchmark, forecast_model)
    adjusted = (a - fb) ** 2 - ((a - fm) ** 2 - (fb - fm) ** 2)
    n = len(adjusted)
    var = _newey_west_var(adjusted, max(horizon - 1, 0))
    if var <= 0:
        raise ValueError("non-positive long-run variance; cannot form the statistic")
    stat = adjusted.mean() / np.sqrt(var / n)
    p = 1 - stats.norm.cdf(stat)
    return TestResult(float(stat), float(p), n, "one-sided; H1 = model beats benchmark")


# --- power -------------------------------------------------------------------


def min_detectable_effect_sd(
    n_oos: int,
    alpha: float = 0.05,
    power: float = 0.80,
    one_sided: bool = True,
) -> float:
    """Smallest mean adjusted-loss differential detectable, in **SD units**.

    ``(z_alpha + z_power)/sqrt(n)``. This is a standardized effect size, *not*
    an R²_OS — the two differ by the ratio of the loss differential's standard
    deviation to the benchmark's mean squared error, which depends on the data.
    Conflating them overstates the bound by an order of magnitude. For the
    quantity the thesis actually needs, use :func:`simulate_power_r2_oos`.
    """
    if n_oos < 2:
        raise ValueError("need at least two out-of-sample observations")
    z_a = stats.norm.ppf(1 - alpha) if one_sided else stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    return float((z_a + z_b) / np.sqrt(n_oos))


def simulate_power_r2_oos(
    returns: pd.Series,
    r2_grid: tuple[float, ...] = (0.000, 0.002, 0.005, 0.010, 0.020, 0.040),
    n_sims: int = 200,
    min_train: int = 250,
    alpha: float = 0.05,
    seed: int = 0,
) -> pd.DataFrame:
    """Empirical power of the Clark–West test, by simulation on the real sample.

    Analytic power formulas for Clark–West require assumptions about the
    predictor's variance ratio that are not worth defending. Simulating is both
    easier to justify and easier to check: implant a predictor that genuinely
    explains a known fraction of return variance, run the same expanding-window
    machinery the thesis uses, and count rejections.

    Returns one row per implanted R², with the rejection rate. The smallest R²
    whose rejection rate reaches 0.80 is the number to quote as the detection
    threshold; effect sizes below it cannot be ruled out by this sample.
    """
    rng = np.random.default_rng(seed)
    y = returns.dropna().to_numpy(dtype=float)
    n = len(y)
    if n <= min_train + 50:
        raise ValueError(f"need more than {min_train + 50} observations, got {n}")
    sigma = float(np.std(y))

    rows = []
    for r2 in r2_grid:
        beta = float(np.sqrt(max(r2, 0.0))) * sigma
        rejections = 0
        for _ in range(n_sims):
            x = rng.normal(size=n)
            noise = rng.normal(scale=sigma * np.sqrt(max(1.0 - r2, 1e-9)), size=n)
            y_sim = beta * x + noise

            f_bench = np.full(n, np.nan)
            f_model = np.full(n, np.nan)
            for t in range(min_train, n):
                f_bench[t] = y_sim[:t].mean()
                design = np.column_stack([np.ones(t), x[:t]])
                coef, *_ = np.linalg.lstsq(design, y_sim[:t], rcond=None)
                f_model[t] = coef[0] + coef[1] * x[t]

            sl = slice(min_train, n)
            idx = pd.RangeIndex(n)[sl]
            try:
                res = clark_west(
                    pd.Series(y_sim[sl], index=idx),
                    pd.Series(f_bench[sl], index=idx),
                    pd.Series(f_model[sl], index=idx),
                )
            except ValueError:
                continue
            rejections += res.pvalue < alpha
        rows.append({"true_r2_oos": r2, "rejection_rate": rejections / n_sims,
                     "n_oos": n - min_train, "n_sims": n_sims})
    return pd.DataFrame(rows)


# --- multiple testing --------------------------------------------------------


def benjamini_hochberg(pvalues: pd.Series, alpha: float = 0.05) -> pd.DataFrame:
    """BH false-discovery-rate control. Returns p, adjusted p and the decision."""
    from statsmodels.stats.multitest import multipletests

    clean = pvalues.dropna()
    rej, adj, _, _ = multipletests(clean.to_numpy(), alpha=alpha, method="fdr_bh")
    return pd.DataFrame(
        {"pvalue": clean, "p_adjusted": adj, "reject": rej}, index=clean.index
    ).sort_values("pvalue")


def romano_wolf(
    statistics: pd.Series,
    bootstrap_draws: np.ndarray,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Romano–Wolf step-down familywise-error control.

    Stronger than BH — it controls the probability of *any* false rejection
    rather than their expected share — and it accounts for dependence between
    tests, which matters here because the forecast grid reuses the same targets
    and overlapping windows.

    ``bootstrap_draws`` is (n_draws, n_tests) of centred statistics under the
    null, which the caller produces by resampling the loss differentials.
    """
    stats_abs = statistics.abs()
    order = stats_abs.sort_values(ascending=False).index
    draws = np.abs(np.asarray(bootstrap_draws, dtype=float))
    if draws.ndim != 2 or draws.shape[1] != len(statistics):
        raise ValueError("bootstrap_draws must be (n_draws, n_tests)")

    positions = {name: i for i, name in enumerate(statistics.index)}
    remaining = list(order)
    rows = []
    while remaining:
        cols = [positions[n] for n in remaining]
        maxima = draws[:, cols].max(axis=1)
        name = remaining[0]
        crit = float(np.quantile(maxima, 1 - alpha))
        p = float((maxima >= stats_abs[name]).mean())
        reject = stats_abs[name] > crit
        rows.append({"test": name, "statistic": float(statistics[name]),
                     "critical_value": crit, "p_rw": p, "reject": bool(reject)})
        if not reject:
            for n in remaining[1:]:
                rows.append({"test": n, "statistic": float(statistics[n]),
                             "critical_value": crit, "p_rw": np.nan, "reject": False})
            break
        remaining = remaining[1:]
    return pd.DataFrame(rows).set_index("test")
