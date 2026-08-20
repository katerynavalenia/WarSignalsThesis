"""Finding anticipation episodes: periods of threat without commensurate acts.

The threat-vs-act preview (``docs/v3/gpr_regime_preview.md``) found the response
of defence equities to threat shocks is confined to the 2021 build-up — 83
trading days — and absent everywhere else, including the whole of the v1 sample.
That is a real result and a power problem: one episode cannot carry a thesis,
and asking four correlated media ecosystems to separate within 83 days is asking
too much.

The fix is more episodes of the same kind. The Russia–Ukraine build-up is one
instance of a general phenomenon — geopolitical risk that is *anticipated* but
not yet *realized* — and the 2015–2026 sample contains others.

**Episodes are defined from GPR alone, never from returns.** If the search used
equity data it would find windows where the effect exists by construction, and
any subsequent test would be circular. The score below can be computed without
ever loading a price series, and that is deliberate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def anticipation_score(
    frame: pd.DataFrame,
    act: str = "gpr_act",
    threat: str = "gpr_threat",
    window: int = 750,
    smooth: int = 21,
) -> pd.Series:
    """How much more anticipated than realized geopolitical risk is, per day.

    Both channels are standardized on a trailing ``window`` (about three trading
    years) rather than the full sample, so the score is computable in real time
    and carries no look-ahead. The difference of the two z-scores is then
    smoothed over ``smooth`` days: a single day of elevated threat is noise, a
    sustained divergence is an episode.
    """
    out = frame.sort_values("date").set_index("date")
    z = {}
    for col in (act, threat):
        s = out[col].astype(float)
        mu = s.rolling(window, min_periods=250).mean()
        sd = s.rolling(window, min_periods=250).std()
        z[col] = (s - mu) / sd.replace(0.0, np.nan)
    score = (z[threat] - z[act]).rolling(smooth, min_periods=smooth).mean()
    return score.rename("anticipation")


def find_episodes(
    score: pd.Series,
    threshold: float = 0.5,
    min_days: int = 30,
    merge_gap: int = 21,
) -> pd.DataFrame:
    """Contiguous runs where the anticipation score stays above ``threshold``.

    Runs separated by less than ``merge_gap`` days are merged — a brief dip
    below the line mid-episode is noise, not the end of one.

    Returns ``start, end, n_days, peak, mean`` sorted by start date.
    """
    s = score.dropna()
    above = s > threshold
    if not above.any():
        return pd.DataFrame(columns=["start", "end", "n_days", "peak", "mean"])

    groups = (above != above.shift()).cumsum()
    runs = [
        (g.index[0], g.index[-1])
        for _, g in s.groupby(groups)
        if above.loc[g.index].iloc[0]
    ]

    merged: list[list[pd.Timestamp]] = []
    for start, end in runs:
        if merged and (start - merged[-1][1]).days <= merge_gap:
            merged[-1][1] = end
        else:
            merged.append([start, end])

    rows = []
    for start, end in merged:
        seg = s.loc[start:end]
        if len(seg) < min_days:
            continue
        rows.append(
            {
                "start": start,
                "end": end,
                "n_days": len(seg),
                "peak": float(seg.max()),
                "mean": float(seg.mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def label_episodes(episodes: pd.DataFrame, known: dict[str, str]) -> pd.DataFrame:
    """Attach a human label to any episode whose window contains a known date.

    Face validity matters here: an episode list that does not recover the events
    a reader already knows about is measuring something else.
    """
    out = episodes.copy()
    out["label"] = ""
    for name, day in known.items():
        d = pd.Timestamp(day)
        hit = (out["start"] <= d) & (out["end"] >= d)
        out.loc[hit, "label"] = out.loc[hit, "label"].str.cat(
            pd.Series([name] * int(hit.sum()), index=out.index[hit]), sep="; "
        ).str.strip("; ")
    return out


#: Dates a correctly built anticipation index should sit near. Chosen as events
#: whose *anticipation* was public before the act, which is the phenomenon being
#: measured — not simply large geopolitical events.
KNOWN_EVENTS = {
    "Russia buildup / invasion": "2022-02-01",
    "Crimea aftermath / Minsk II": "2015-02-12",
    "North Korea ICBM crisis": "2017-08-10",
    "Soleimani strike": "2020-01-03",
    "Russia spring buildup": "2021-04-15",
    "Israel-Iran exchange": "2024-04-14",
}
