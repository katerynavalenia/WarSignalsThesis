"""The threat-vs-act horse race, estimated per war regime.

This module exists to settle two questions that decide the shape of the thesis,
and it encodes the answers as defaults rather than leaving them to each caller.

**Changes, not levels.** v2's headline (``docs/v2/research_plan.md`` §6.4 —
GPR_THREAT raises European defence volatility, p<0.001) was estimated on
*standardized levels*. GPR levels are strongly persistent (AR(1) ≈ 0.6–0.7)
while daily volatility is not (AR(1) ≈ 0.17), which is the textbook setting for
persistence-driven significance. The same specification in first differences
gives nothing. :func:`channel_race` therefore differences by default, and
``use_changes=False`` is provided only so the fragility can be *shown* rather
than argued about.

**The regime is the unit of analysis.** Pooling the sample hides the result.
The threat channel is significant only in the 2021 build-up; it is absent
before it, during the invasion, and throughout the attrition window that made
up the whole of the v1 sample. :func:`race_by_regime` and
:func:`interacted_race` are the two ways of showing that, and they should agree.

Standard errors are Newey–West/HAC throughout — the regressors are persistent
and the residuals of a daily financial regression are not i.i.d.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

#: Newey-West lag truncation. Five trading days = one week, the horizon over
#: which a news shock plausibly stays in the residual.
DEFAULT_MAXLAGS = 5

#: Volatility dependent variables take |market return| as their control; signed
#: return dependent variables take the signed market return. Getting this wrong
#: silently mis-specifies the control.
_VOL_PREFIXES = ("vol_", "rv")


def zscore(s: pd.Series) -> pd.Series:
    """Standardize so coefficients are comparable across channels and regimes."""
    sd = s.std()
    if not np.isfinite(sd) or sd == 0:
        raise ValueError(f"cannot standardize '{s.name}': zero or undefined variance")
    return (s - s.mean()) / sd


def is_volatility_target(dv: str) -> bool:
    """True if ``dv`` names a volatility proxy rather than a signed return."""
    return dv.startswith(_VOL_PREFIXES)


def hac_ols(
    y: pd.Series, X: pd.DataFrame, maxlags: int = DEFAULT_MAXLAGS
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """OLS with a constant and Newey–West standard errors."""
    return sm.OLS(y, sm.add_constant(X), missing="drop").fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags}
    )


def _channel_frame(
    frame: pd.DataFrame,
    dv: str,
    act: str,
    threat: str,
    controls: list[str],
    use_changes: bool,
) -> tuple[pd.Series, pd.DataFrame]:
    needed = [dv, act, threat, *controls]
    s = frame.dropna(subset=[c for c in needed if c in frame]).copy()

    a = s[act].diff() if use_changes else s[act]
    t = s[threat].diff() if use_changes else s[threat]
    design = pd.DataFrame({"act": a, "threat": t}, index=s.index).dropna()

    for c in controls:
        col = s.loc[design.index, c]
        if c.startswith("r_") and is_volatility_target(dv):
            col = col.abs()
        design[c] = zscore(col) if not c.startswith("r_") else col

    design = design.dropna()
    design["act"] = zscore(design["act"])
    design["threat"] = zscore(design["threat"])
    return s.loc[design.index, dv], design


def channel_race(
    frame: pd.DataFrame,
    dv: str,
    act: str = "gpr_act",
    threat: str = "gpr_threat",
    controls: list[str] | None = None,
    use_changes: bool = True,
    maxlags: int = DEFAULT_MAXLAGS,
    min_obs: int = 40,
) -> dict | None:
    """Race the realized (act) channel against the expectations (threat) one.

    Returns ``None`` when fewer than ``min_obs`` usable rows remain, so a caller
    can sweep short windows without special-casing each one.
    """
    controls = ["r_mkt", "lvix"] if controls is None else controls
    y, X = _channel_frame(frame, dv, act, threat, controls, use_changes)
    if len(y) < min_obs:
        return None
    m = hac_ols(y, X, maxlags=maxlags)
    return {
        "n": int(m.nobs),
        "act": m.params["act"],
        "p_act": m.pvalues["act"],
        "threat": m.params["threat"],
        "p_threat": m.pvalues["threat"],
        "r2": m.rsquared,
    }


def race_by_regime(
    frame: pd.DataFrame,
    dv: str,
    regime_col: str = "regime",
    **kwargs,
) -> pd.DataFrame:
    """Run :func:`channel_race` separately on each regime, plus the pooled sample.

    Separate regressions rather than interactions: every coefficient, including
    the controls, is free to differ across regimes. :func:`interacted_race`
    imposes common controls, and the two agreeing is the robustness check.
    """
    rows = []
    for regime, sub in frame.groupby(regime_col, observed=True):
        res = channel_race(sub, dv, **kwargs)
        if res is not None:
            rows.append({"sample": str(regime), **res})
    pooled = channel_race(frame, dv, **kwargs)
    if pooled is not None:
        rows.append({"sample": "pooled", **pooled})
    return pd.DataFrame(rows)


def interacted_race(
    frame: pd.DataFrame,
    dv: str,
    act: str = "gpr_act",
    threat: str = "gpr_threat",
    controls: list[str] | None = None,
    regime_col: str = "regime",
    use_changes: bool = True,
    maxlags: int = DEFAULT_MAXLAGS,
) -> pd.DataFrame:
    """One regression with both channels interacted with every regime dummy.

    Estimated on the pooled sample with common controls and one standardization,
    so the regime coefficients are directly comparable to each other — which the
    separate per-regime regressions of :func:`race_by_regime` are not.
    """
    controls = ["r_mkt", "lvix"] if controls is None else controls
    y, X = _channel_frame(frame, dv, act, threat, controls, use_changes)
    regimes = frame.loc[X.index, regime_col].astype(str)

    labels = list(dict.fromkeys(regimes))
    design = X.drop(columns=["act", "threat"]).copy()
    for i, r in enumerate(labels):
        d = (regimes == r).astype(float)
        design[f"act_{r}"] = X["act"] * d
        design[f"threat_{r}"] = X["threat"] * d
        if i:  # first regime is the omitted intercept category
            design[f"is_{r}"] = d

    m = hac_ols(y, design, maxlags=maxlags)
    return pd.DataFrame(
        [
            {
                "regime": r,
                "n": int((regimes == r).sum()),
                "act": m.params[f"act_{r}"],
                "p_act": m.pvalues[f"act_{r}"],
                "threat": m.params[f"threat_{r}"],
                "p_threat": m.pvalues[f"threat_{r}"],
            }
            for r in labels
        ]
    )
