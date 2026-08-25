"""The war-regime calendar.

v1 collapsed the whole conflict into one scalar, ``days_since_invasion``, which
is why every war indicator ended up collinear with it: on a sample that starts
in September 2022 a monotone trend and a war indicator are close to the same
variable. With the sample extended back to 2015 the conflict has genuine
*phases*, and the phase is what carries information.

The four regimes, and why each earns a boundary:

``pre_war``
    2015-02-18 → 2021-10-31. Post-Crimea frozen conflict. Establishes what the
    normal relationship between war news and defence equities looks like.
``buildup``
    2021-11-01 → 2022-02-23. Troop concentration and public intelligence
    warnings, with almost no realized fighting — as close to *pure threat
    without acts* as this conflict offers, and therefore the sharpest available
    setting for the threat-vs-act question.
``invasion``
    2022-02-24 → 2022-09-28. The invasion and the defence-sector re-rating.
    Entirely outside the v1 sample; the single largest identifying event.
``attrition``
    2022-09-29 onward. The v1 sample, and the only window with air-attack data.
"""

from __future__ import annotations

import pandas as pd

#: GDELT's translingual archive begins here; it bounds the whole study.
SAMPLE_START = pd.Timestamp("2015-02-18")

BUILDUP_START = pd.Timestamp("2021-11-01")
INVASION_DATE = pd.Timestamp("2022-02-24")
ATTRITION_START = pd.Timestamp("2022-09-29")

REGIMES = ("pre_war", "buildup", "invasion", "attrition")


def assign_regime(dates: pd.Series | pd.DatetimeIndex) -> pd.Series:
    """Label each date with its war regime.

    Dates before :data:`SAMPLE_START` are labelled ``pre_war`` as well — the
    boundary is a data-availability limit, not an economic one, so callers
    filter on date rather than relying on the label to exclude them.
    """
    d = pd.to_datetime(pd.Series(dates).reset_index(drop=True)).astype("datetime64[ns]")
    out = pd.Series("pre_war", index=d.index, dtype="object")
    out[d >= BUILDUP_START] = "buildup"
    out[d >= INVASION_DATE] = "invasion"
    out[d >= ATTRITION_START] = "attrition"
    return pd.Categorical(out, categories=list(REGIMES), ordered=True)


def build_calendar(start: str | pd.Timestamp = SAMPLE_START,
                   end: str | pd.Timestamp = "2026-06-30") -> pd.DataFrame:
    """A calendar-day spine with regime labels and event-time counters.

    Calendar days rather than trading days, because the news indices are
    defined every day and the weekend rule (Friday news predicts Monday) needs
    weekend rows to survive the merge. Trading-day filtering happens later,
    when the equity panel is attached.

    Columns: ``date``, ``regime``, ``days_since_invasion`` (negative before the
    invasion, so it is a genuine two-sided event-time axis rather than v1's
    one-sided trend), ``is_weekend``, ``year``, and one dummy per regime.
    """
    dates = pd.date_range(
        pd.Timestamp(start), pd.Timestamp(end), freq="D", unit="ns"
    )
    cal = pd.DataFrame({"date": dates})
    cal["regime"] = assign_regime(cal["date"])
    cal["days_since_invasion"] = (cal["date"] - INVASION_DATE).dt.days
    cal["is_weekend"] = cal["date"].dt.dayofweek >= 5
    cal["year"] = cal["date"].dt.year
    for r in REGIMES:
        cal[f"regime_{r}"] = (cal["regime"] == r).astype("int8")
    return cal
