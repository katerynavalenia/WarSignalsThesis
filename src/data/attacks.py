"""The physical air-attack layer, and the three periods it has to be read in.

The approved design is a comparison — *Physical Air-Attack Intensity versus
Multilingual News Narratives* — and this module supplies the physical half. It
measures Russian air attacks on Ukraine: weapons launched and destroyed by
category, interception rate, weapon diversity, composition shares, large-attack
indicators, and surprise measures comparing recent intensity against rolling
7-, 30- and 90-day expectations.

**The data begins when the Ukrainian Air Force began publishing, not when the
attacks began.** That distinction governs everything here. The source is the
UAF's daily tallies, and they start on 29 September 2022. Reading the absence of
a record before that date as an absence of attacks is right for one period and
badly wrong for another, so the sample is cut into three:

``pre-war`` — 18 February 2015 to 23 February 2022
    Zero, and the zero is *substantive rather than observed*. No Russian mass
    air campaign against Ukrainian cities existed in this period; the Donbas
    conflict was fought with artillery and ground forces. Every physical
    variable is therefore set to 0.0, which is also what each formula returns on
    an all-zero history: no weapons, no composition, no surprise against a
    rolling mean of nothing. This is a modelling assumption and is stated as one
    wherever the results are reported.

``invasion`` — 24 February 2022 to 28 September 2022
    **Unobserved, and emphatically not zero.** This window contains the cruise
    missile campaign against Kyiv, Vinnytsia, Kremenchuk and Odesa. The UAF had
    not yet begun publishing daily counts, so the attacks happened and were not
    tallied in this format. Coding them zero would assert that no air attacks
    occurred during the invasion of Ukraine — and it would do so precisely
    across the February-2022 defence-equity re-rating, teaching any model that
    attack intensity was nil exactly when defence equities repriced hardest.
    That is not a gap; it is a bias pointing toward the null the thesis tests.
    These rows carry ``attack_unobserved = True`` and NaN features, and no
    specification containing physical variables may train on them.

``measured`` — 29 September 2022 onward
    Observed. Days inside this window with no published wave are genuine zeros
    and are filled as such; only 809 of 931 trading days carry a UAF record.

The 41 physical features are taken from the approved design's own model matrix
rather than re-derived, so the measured window reproduces the published
construction exactly, lags included. The alternative — recomputing the surprise
and share measures from the raw counts — would risk a silent divergence from the
figures the supervisor has already read.

The approved thesis's own attack sample began 29 September 2022, so excluding
the invasion window costs nothing relative to what was approved; it matches that
coverage rather than falling short of it.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ATTACK_DIR = Path("data/interim/attacks")

#: The day the Ukrainian Air Force began publishing daily attack tallies. Not
#: the day attacks began — that is the whole point of this module.
UAF_REPORTING_START = pd.Timestamp("2022-09-29")

#: The full-scale invasion. Between this date and :data:`UAF_REPORTING_START`
#: there were substantial air attacks and no systematic public count of them.
INVASION_START = pd.Timestamp("2022-02-24")

#: Invariants published in the approved thesis. Any copy of the data that does
#: not reproduce these is not the data the thesis was written on.
PUBLISHED_INVARIANTS = {
    "market_info_dates": 809,
    "weapons_launched": 102396,
    "weapons_destroyed": 76126,
}


def _physical_columns(matrix: pd.DataFrame) -> list[str]:
    """The approved design's physical block.

    Selected by name against the published feature list. ``n_articles`` and
    ``_direct`` columns are excluded deliberately: they count *articles about*
    attacks, which is narrative evidence and belongs to the N block. Mixing them
    into P would put news features on both sides of the comparison the thesis
    exists to make.
    """
    keys = ("launch", "destroy", "intercept", "weapon", "attack")
    return [
        c for c in matrix.columns
        if any(k in c.lower() for k in keys)
        and "n_articles" not in c
        and "_direct" not in c
    ]


def verify_invariants(daily_master: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """Reconcile a copy of the attack data against the approved thesis.

    Returns ``{name: (found, published)}``. The caller decides what to do about
    a mismatch; this function does not raise, because a diagnostic that hides
    the numbers is useless when the numbers are what you need to see.
    """
    recorded = daily_master[daily_master["launched_total"].notna()]
    found = {
        "market_info_dates": int(len(recorded)),
        "weapons_launched": int(daily_master["launched_total"].sum()),
        "weapons_destroyed": int(daily_master["destroyed_total"].sum()),
    }
    return {k: (found[k], PUBLISHED_INVARIANTS[k]) for k in PUBLISHED_INVARIANTS}


def load_attack_panel(
    dates: pd.Series | pd.DatetimeIndex,
    attack_dir: Path = ATTACK_DIR,
) -> pd.DataFrame:
    """Physical features on the supplied trading-day calendar, period by period.

    ``dates`` is the calendar to align to — normally the equity spine's trading
    days, so the panel joins straight onto it. Returns one row per date with the
    41 physical features plus ``attack_unobserved``, which is True exactly on the
    invasion window and is the column every downstream guard checks.
    """
    idx = pd.DatetimeIndex(pd.Series(dates).sort_values().unique(), name="date")
    matrix = pd.read_parquet(attack_dir / "model_matrix.parquet")
    matrix["date"] = pd.to_datetime(matrix["date"])
    features = _physical_columns(matrix)

    out = pd.DataFrame(index=idx, columns=features, dtype="float64")

    # Measured window: the approved construction, taken as published. Cast to
    # float first -- the large-attack indicator arrives as a nullable Int8, and
    # a nullable integer will not assign into a float frame.
    measured = (
        matrix.set_index("date")[features]
        .apply(pd.to_numeric, errors="coerce")
        .astype("float64")
        .reindex(idx)
    )
    in_measured = idx >= UAF_REPORTING_START
    out.loc[in_measured, features] = measured.loc[in_measured, features]

    # A trading day inside the measured window with no published wave is a
    # genuine zero -- the UAF reported nothing because nothing was launched.
    out.loc[in_measured] = out.loc[in_measured].fillna(0.0)

    # Pre-war: substantively zero, as argued in the module docstring.
    out.loc[idx < INVASION_START, features] = 0.0

    # Invasion window: left NaN. Assigning anything here would be an invention.
    unobserved = (idx >= INVASION_START) & (idx < UAF_REPORTING_START)
    out.loc[unobserved, features] = float("nan")

    out["attack_unobserved"] = unobserved
    return out.reset_index()


def period_of(dates: pd.Series | pd.DatetimeIndex) -> pd.Series:
    """Label each date ``pre-war``, ``invasion`` or ``measured``.

    Reported alongside results so a reader can see how much of any estimate
    rests on assumed zeros rather than counted weapons.
    """
    d = pd.DatetimeIndex(dates)
    out = pd.Series("measured", index=range(len(d)), dtype="object")
    out[d < UAF_REPORTING_START] = "invasion"
    out[d < INVASION_START] = "pre-war"
    return out
