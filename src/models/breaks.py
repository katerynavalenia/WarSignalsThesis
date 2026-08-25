"""Structural break tests — supervisor comment #2.

The review asked what happens around February 2022. Chapter 5 answers it with
plots and with pre/post means, but a reader is entitled to a test rather than a
description, and the response to the review promised two.

**Chow** tests a break at a date named in advance. Here that date is 24 February
2022, chosen by the event rather than by the data, which is what makes the test
honest: a break test at a date picked by looking for the largest break is not a
test at all.

**Bai–Perron** asks the complementary question — where the largest break is, given
that nobody told the procedure. If the answer lands on the invasion without being
pointed at it, that is considerably stronger evidence than a Chow test at a date
the analyst supplied. The implementation here is the single-break case (a
supremum-Wald / Quandt-Andrews scan over candidate dates with 15% trimming),
which is what a one-event design needs; the general multiple-break dynamic
program is not implemented and is not required for the claim being made.

The supremum statistic does not have a standard F distribution, because the
maximum over many candidate dates is not a single draw. The p-value here is
therefore obtained by bootstrap under the null of no break, which is slower than
reading a table but does not require one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class BreakResult:
    statistic: float
    pvalue: float
    break_date: pd.Timestamp | None
    n: int
    note: str = ""

    def __str__(self) -> str:
        d = self.break_date.date() if self.break_date is not None else "given"
        return f"F={self.statistic:.3f}, p={self.pvalue:.4f}, break={d}, n={self.n}"


def _ssr(y: np.ndarray, X: np.ndarray) -> float:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return float(resid @ resid)


def _design(x: pd.DataFrame | pd.Series | None, n: int) -> np.ndarray:
    if x is None:
        return np.ones((n, 1))
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    return np.column_stack([np.ones(len(arr)), arr])


def chow_test(
    y: pd.Series, break_date: str | pd.Timestamp, x: pd.DataFrame | pd.Series | None = None
) -> BreakResult:
    """Chow test for a break at a **pre-specified** date.

    With ``x=None`` this tests a break in the mean, which is the relevant form
    for a tone or attention series. Supplying ``x`` tests a break in a
    regression relationship instead.
    """
    frame = pd.concat([y.rename("y")] + ([x] if x is not None else []), axis=1).dropna()
    if len(frame) < 20:
        raise ValueError(f"need at least 20 observations, got {len(frame)}")
    cut = pd.Timestamp(break_date)
    pre, post = frame.index < cut, frame.index >= cut
    if pre.sum() < 10 or post.sum() < 10:
        raise ValueError("each side of the break needs at least 10 observations")

    yv = frame["y"].to_numpy(dtype=float)
    xv = frame.drop(columns="y") if x is not None else None
    Xf = _design(xv, len(frame))
    k = Xf.shape[1]

    ssr_pooled = _ssr(yv, Xf)
    ssr_split = _ssr(yv[pre], Xf[pre]) + _ssr(yv[post], Xf[post])
    df_denom = len(frame) - 2 * k
    if df_denom <= 0 or ssr_split <= 0:
        raise ValueError("too few observations for the split regression")

    f = ((ssr_pooled - ssr_split) / k) / (ssr_split / df_denom)
    p = 1 - stats.f.cdf(f, k, df_denom)
    return BreakResult(float(f), float(p), cut, len(frame),
                       "break date fixed in advance")


def supremum_break(
    y: pd.Series,
    x: pd.DataFrame | pd.Series | None = None,
    trim: float = 0.15,
    n_boot: int = 500,
    seed: int = 0,
) -> BreakResult:
    """Locate the single most likely break without being told where to look.

    Scans every candidate date in the interior ``1 - 2*trim`` of the sample,
    takes the largest Chow statistic, and bootstraps its distribution under the
    null of no break by resampling residuals of the pooled model.

    Returns the argmax date and its bootstrap p-value.
    """
    frame = pd.concat([y.rename("y")] + ([x] if x is not None else []), axis=1).dropna()
    n = len(frame)
    if n < 60:
        raise ValueError(f"need at least 60 observations to scan, got {n}")

    yv = frame["y"].to_numpy(dtype=float)
    xv = frame.drop(columns="y") if x is not None else None
    Xf = _design(xv, n)
    k = Xf.shape[1]
    lo, hi = int(n * trim), int(n * (1 - trim))

    # For the intercept-only case the split SSR has a closed form in cumulative
    # sums, so the whole scan is O(n) rather than O(n) regressions, and the
    # bootstrap becomes feasible instead of taking hours. The general case falls
    # back to refitting, which is only used when a regressor is supplied.
    mean_only = k == 1
    cuts = np.arange(lo, hi)

    def scan(vals: np.ndarray) -> tuple[float, int]:
        ssr_pooled = _ssr(vals, Xf)
        if mean_only:
            c1 = np.cumsum(vals)
            c2 = np.cumsum(vals ** 2)
            tot1, tot2 = c1[-1], c2[-1]
            n_pre = cuts.astype(float)
            n_post = n - n_pre
            ssr_pre = c2[cuts - 1] - (c1[cuts - 1] ** 2) / n_pre
            ssr_post = (tot2 - c2[cuts - 1]) - ((tot1 - c1[cuts - 1]) ** 2) / n_post
            split = ssr_pre + ssr_post
        else:
            split = np.array([_ssr(vals[:i], Xf[:i]) + _ssr(vals[i:], Xf[i:])
                              for i in cuts])
        with np.errstate(divide="ignore", invalid="ignore"):
            f = ((ssr_pooled - split) / k) / (split / (n - 2 * k))
        f = np.where(np.isfinite(f) & (split > 0), f, -np.inf)
        j = int(np.argmax(f))
        return float(f[j]), int(cuts[j])

    stat, idx = scan(yv)

    beta, *_ = np.linalg.lstsq(Xf, yv, rcond=None)
    fitted, resid = Xf @ beta, yv - Xf @ beta
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(n_boot):
        boot, _ = scan(fitted + rng.choice(resid, size=n, replace=True))
        exceed += boot >= stat
    return BreakResult(float(stat), float(exceed / n_boot), frame.index[idx], n,
                       f"argmax over {hi-lo} candidate dates, {n_boot} bootstrap draws")
