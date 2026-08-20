"""Building the perception indices, and the battery that decides if they are real.

Two series per ecosystem per day:

``attention``
    the share of that ecosystem's own daily output that is conflict-related.
    A share, never a raw count — GDELT's source coverage drifts by a factor of
    two-and-a-half across the sample, which would otherwise appear as a trend in
    every ecosystem at once (``research_plan_v3.md`` §5.4).
``tone``
    mean GKG tone of the conflict articles. Negative is more negative coverage.

The gate in :func:`validation_report` is the point of the module. v1's
validation could not detect v1's own error because it checked the classifier
against a proxy built from the same flawed signal, so these checks are
deliberately *external*: agreement with a published index nobody here
constructed, behaviour on dates chosen in advance, and mutual independence.

Thresholds are fixed in :data:`GATE` before any of them were computed. They are
not to be loosened to make a build pass; if the build fails them the honest move
is to fix the measurement or stop.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Fixed in advance. See docs/v3/gate1_validation.md.
GATE = {
    "west_gpr_corr_min": 0.40,      # |rho|, changes, WEST attention vs published GPR
    "max_pairwise_corr": 0.70,      # changes; above this the ecosystems are not distinct
    "min_daily_articles": 50,       # per ecosystem, median; below this daily is too thin
    "invasion_zscore_min": 2.0,     # attention must visibly spike on 2022-02-24
}

CORE = ("UA", "RU_STATE", "RU_INDEP", "WEST", "EN_GLOBAL")


def build_indices(daily: pd.DataFrame, ecosystems: tuple[str, ...] = CORE) -> pd.DataFrame:
    """Pivot the per-(day, ecosystem) table into wide daily index series."""
    d = daily[daily["ecosystem"].isin(ecosystems)].copy()
    d["day"] = pd.to_datetime(d["day"]).astype("datetime64[ns]")

    att = d.pivot(index="day", columns="ecosystem", values="share")
    tone = d.pivot(index="day", columns="ecosystem", values="tone_conflict")
    vol = d.pivot(index="day", columns="ecosystem", values="n_conflict")

    out = pd.concat(
        [
            att.add_prefix("att_"),
            tone.add_prefix("tone_"),
            vol.add_prefix("vol_"),
        ],
        axis=1,
    ).sort_index()
    out.index.name = "date"
    return out


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def validation_report(
    indices: pd.DataFrame,
    gpr: pd.Series,
    ecosystems: tuple[str, ...] = CORE,
    invasion: str = "2022-02-24",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run the Gate-1 battery. Returns (per-ecosystem table, correlation matrix, verdict)."""
    rows = []
    dgpr = gpr.diff()

    for e in ecosystems:
        att = indices.get(f"att_{e}")
        vol = indices.get(f"vol_{e}")
        if att is None:
            continue
        joined = pd.concat([att.diff().rename("a"), dgpr.rename("g")], axis=1).dropna()
        corr_gpr = float(joined["a"].corr(joined["g"])) if len(joined) > 60 else np.nan

        spike = np.nan
        if invasion in indices.index.astype(str):
            z = zscore(att.dropna())
            spike = float(z.get(pd.Timestamp(invasion), np.nan))

        rows.append(
            {
                "ecosystem": e,
                "median_daily_articles": float(vol.median()) if vol is not None else np.nan,
                "corr_with_gpr": corr_gpr,
                "invasion_z": spike,
                "mean_tone": float(indices[f"tone_{e}"].mean()),
            }
        )

    table = pd.DataFrame(rows)

    att_cols = [f"att_{e}" for e in ecosystems if f"att_{e}" in indices]
    corr = indices[att_cols].diff().corr()

    off = corr.where(~np.eye(len(corr), dtype=bool))
    max_pair = float(np.nanmax(np.abs(off.values)))

    west = table.loc[table.ecosystem == "WEST", "corr_with_gpr"]
    verdict = {
        "west_gpr_corr": float(west.iloc[0]) if len(west) else np.nan,
        "west_gpr_pass": bool(len(west) and abs(west.iloc[0]) >= GATE["west_gpr_corr_min"]),
        "max_pairwise_corr": max_pair,
        "collinearity_pass": bool(max_pair <= GATE["max_pairwise_corr"]),
        "volume_pass": bool((table["median_daily_articles"] >= GATE["min_daily_articles"]).all()),
        "invasion_pass": bool(
            table["invasion_z"].dropna().ge(GATE["invasion_zscore_min"]).any()
        ),
    }
    verdict["overall_pass"] = all(
        verdict[k] for k in ("west_gpr_pass", "collinearity_pass", "volume_pass", "invasion_pass")
    )
    return table, corr, verdict
