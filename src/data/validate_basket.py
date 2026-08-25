"""Does a free-data defence basket reproduce the Bloomberg index?

The long sample needs equity data back to 2015, but the Bloomberg files start in
2020. Any substitute — an ETF, a hand-built basket of listed defence names — is
a *different portfolio*, not the same index served by a different vendor. So the
question is never "is it identical" (it cannot be) but "is it close enough that
the thesis's conclusions do not depend on which one is used".

This module answers that on the 2020–2026 overlap, against criteria fixed in
advance so the test cannot be talked into passing after the fact. See
``docs/v3/equity_validation.md`` for why each threshold is where it is.

The precedent that motivates the design: v1 reconstructed WAERLST and BSHIELDT
from constituents. ``r_BSHIELDT_recon`` matched the real series' standard
deviation almost exactly (1.4983 vs 1.4462) and was still rejected, because its
*correlation* with the real series was far too low. Matching moments is not
evidence of matching series, so nothing here is scored on moments alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

#: Fixed before seeing any comparison. Do not loosen to make a basket pass.
THRESHOLDS = {
    "return_corr_min": 0.95,      # daily log returns
    "vol_corr_min": 0.90,         # 20-day realized volatility
    "beta_low": 0.85,
    "beta_high": 1.15,
    "r2_min": 0.90,
    "tracking_error_max": 0.50,   # std of the daily return difference, pp/day
}


@dataclass
class BasketValidation:
    """Outcome of comparing a candidate series against a Bloomberg index."""

    name: str
    n_overlap: int
    return_corr: float
    vol_corr: float
    beta: float
    r2: float
    tracking_error: float
    mean_diff: float
    std_ratio: float
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_row(self) -> dict:
        return {
            "series": self.name,
            "n_overlap": self.n_overlap,
            "return_corr": round(self.return_corr, 4),
            "vol_corr": round(self.vol_corr, 4),
            "beta": round(self.beta, 4),
            "r2": round(self.r2, 4),
            "tracking_error": round(self.tracking_error, 4),
            "mean_diff": round(self.mean_diff, 4),
            "std_ratio": round(self.std_ratio, 4),
            "passed": self.passed,
            "failures": "; ".join(self.failures),
        }


def realized_vol(returns: pd.Series, window: int = 20) -> pd.Series:
    """Rolling standard deviation of returns.

    ``closed="left"`` so the value at ``t`` uses information strictly before
    ``t`` — the same backward-looking convention as v1's ``rolling_compute``.
    """
    return returns.rolling(window, min_periods=window, closed="left").std()


def validate_basket(
    candidate: pd.Series,
    bloomberg: pd.Series,
    name: str = "candidate",
    thresholds: dict | None = None,
) -> BasketValidation:
    """Compare a candidate daily return series against a Bloomberg one.

    Both arguments are daily returns in percent, indexed by date. Only dates
    present in both are used: a candidate that trades on days the index does not
    (or vice versa) is compared on the intersection, and ``n_overlap`` records
    how much was actually available.
    """
    th = {**THRESHOLDS, **(thresholds or {})}

    joined = pd.concat(
        [candidate.rename("cand"), bloomberg.rename("bbg")], axis=1, join="inner"
    ).dropna()
    if len(joined) < 60:
        raise ValueError(
            f"only {len(joined)} overlapping observations; need at least 60 "
            "for the comparison to mean anything"
        )

    c, b = joined["cand"], joined["bbg"]
    ret_corr = float(c.corr(b))

    vols = pd.concat([realized_vol(c), realized_vol(b)], axis=1).dropna()
    vol_corr = float(vols.iloc[:, 0].corr(vols.iloc[:, 1])) if len(vols) > 30 else np.nan

    # Candidate regressed on the index: beta near 1 with high R² is the
    # substitutability claim stated as a regression.
    beta, alpha = np.polyfit(b.to_numpy(), c.to_numpy(), 1)
    resid = c.to_numpy() - (alpha + beta * b.to_numpy())
    ss_res, ss_tot = float((resid**2).sum()), float(((c - c.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

    diff = c - b
    result = BasketValidation(
        name=name,
        n_overlap=len(joined),
        return_corr=ret_corr,
        vol_corr=vol_corr,
        beta=float(beta),
        r2=float(r2),
        tracking_error=float(diff.std()),
        mean_diff=float(diff.mean()),
        std_ratio=float(c.std() / b.std()) if b.std() > 0 else np.nan,
    )

    f = result.failures
    if ret_corr < th["return_corr_min"]:
        f.append(f"return corr {ret_corr:.3f} < {th['return_corr_min']}")
    if not np.isnan(vol_corr) and vol_corr < th["vol_corr_min"]:
        f.append(f"vol corr {vol_corr:.3f} < {th['vol_corr_min']}")
    if not (th["beta_low"] <= beta <= th["beta_high"]):
        f.append(f"beta {beta:.3f} outside [{th['beta_low']}, {th['beta_high']}]")
    if not np.isnan(r2) and r2 < th["r2_min"]:
        f.append(f"R² {r2:.3f} < {th['r2_min']}")
    if result.tracking_error > th["tracking_error_max"]:
        f.append(
            f"tracking error {result.tracking_error:.3f} > {th['tracking_error_max']}"
        )
    return result


def validation_table(results: list[BasketValidation]) -> pd.DataFrame:
    """Collect several validations into one reportable table."""
    return pd.DataFrame([r.to_row() for r in results])
