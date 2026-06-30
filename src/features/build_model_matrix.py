"""Phase 5D — Build the model matrix from the feature matrix.

The model matrix is the final input to Phase 6 baselines and Phase 7 ML
models. It contains:

- The **target** ``target_r_<X>_t1``: next-trading-day return of the chosen
  financial outcome. Per Master Plan §9 (weekend rule): Friday close → Monday
  pre-market info predicts Monday, so the target at Saturday/Sunday uses
  Monday's return.
- **Past-lagged features**: all current-day features (vol_5d, attack
  surprise, news counts, etc.) are shifted by 1 trading day so the model
  only sees information available *before* market open on day t.
- **Same-day features** (only ones truly known before market open): calendar
  flags (``is_weekend``, ``day_of_week``, VIX regime dummies, etc.) are
  kept as-is.
- **Information-set masks** (F/P/N/PN/PNG) defining which columns belong
  to which horse-race baseline.

Per Master Plan §6.1 we keep the target on the **primary ITA ETF** (Phase 1
audit recommendation: clean yfinance proxy, ρ = 0.86 with SPX) and the
secondary on the **Bloomberg WAERLST reconstruction** (decision_log
2026-06-28). This preserves both signals so Phase 6 can compare them as
robustness.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import numpy as np
import pandas as pd

from src.utils.date_utils import is_trading_day


# Calendar-day columns that ARE known at the open of day t and do NOT need
# to be lagged. (Everything else is lagged by 1 trading day.)
CALENDAR_PASSTHROUGH_COLS = (
    "is_weekend",
    "is_holiday",
    "day_of_week",
    "day_of_month",
    "month",
    "quarter",
    "is_month_start",
    "is_month_end",
    "is_quarter_end",
    "days_since_invasion",
    "vix_low",
    "vix_normal",
    "vix_high",
    "vix_crisis",
    "waerlst_missing",
)

# Primary financial target (yfinance proxy, recommended by Phase 1 audit).
PRIMARY_TARGET = "r_ITA"
# Secondary target (Bloomberg reconstruction, per decision_log 2026-06-28).
SECONDARY_TARGET = "r_WAERLST_recon"


# ── Target construction ─────────────────────────────────────────────────────


def _next_trading_day_index(idx: pd.DatetimeIndex, start: int) -> int:
    """Return the index of the first *trading day* strictly after ``idx[start]``.

    Walks forward through ``idx`` until it finds a day that is a weekday AND
    not a US federal holiday. Returns ``-1`` if no such day exists.
    """
    n = len(idx)
    for j in range(start + 1, n):
        if is_trading_day(idx[j]):
            return j
    return -1


def _shift_to_next_trading_day(
    series: pd.Series,
    dates: pd.DatetimeIndex,
) -> pd.Series:
    """Shift ``series`` forward to the *next trading day* (the §9 weekend rule).

    For each calendar day ``t``, the value is the value of ``series`` at the
    next trading day. Non-trading days (weekend, holiday) inherit the
    target from the next trading day, so Friday close → Saturday/Sunday/Monday
    all carry Monday's return as the target.
    """
    out = pd.Series(np.nan, index=series.index, name=series.name)
    n = len(dates)
    for i in range(n):
        j = _next_trading_day_index(dates, i)
        if j == -1:
            break
        val = series.iloc[j]
        if not pd.isna(val):
            out.iloc[i] = val
    return out


def build_targets(
    feature_matrix: pd.DataFrame,
    primary_target: str = PRIMARY_TARGET,
    secondary_target: Optional[str] = SECONDARY_TARGET,
) -> pd.DataFrame:
    """Construct the next-trading-day return target(s).

    Per the §9 weekend rule, a calendar day ``t`` has a target equal to the
    return of the **next trading day** (so Sat/Sun/Mon all point to Monday's
    return). The target at the last calendar day in the index is NaN.
    """
    out = pd.DataFrame({"date": feature_matrix["date"]})
    dates = pd.DatetimeIndex(feature_matrix["date"])

    if primary_target not in feature_matrix.columns:
        raise KeyError(
            f"primary_target='{primary_target}' not in feature_matrix. "
            f"Available: {[c for c in feature_matrix.columns if c.startswith('r_')]}"
        )
    out[f"target_{primary_target}_t1"] = _shift_to_next_trading_day(
        feature_matrix[primary_target], dates
    )

    if secondary_target is not None:
        if secondary_target not in feature_matrix.columns:
            raise KeyError(
                f"secondary_target='{secondary_target}' not in feature_matrix"
            )
        out[f"target_{secondary_target}_t1"] = _shift_to_next_trading_day(
            feature_matrix[secondary_target], dates
        )

    return out


# ── Lag structure ───────────────────────────────────────────────────────────


def _is_passthrough(col: str) -> bool:
    """Return True if ``col`` is a calendar/structural feature known at market open."""
    if col in CALENDAR_PASSTHROUGH_COLS:
        return True
    if col.startswith("is_") and len(col) < 30:
        return True
    return False


def lag_features(
    feature_matrix: pd.DataFrame,
    exclude: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Lag all non-calendar features by 1 calendar day."""
    out = feature_matrix.copy()
    if exclude is None:
        exclude = (
            "date",
            "ITA",
            "BSHIELDT",
            "WAERLST_recon",
            PRIMARY_TARGET,
            SECONDARY_TARGET,
        )
    drop = (set(exclude) - {"date"}) & set(out.columns)
    if drop:
        out = out.drop(columns=list(drop))

    lag_cols = [c for c in out.columns if c != "date" and not _is_passthrough(c)]
    passthrough_cols = [c for c in out.columns if c != "date" and _is_passthrough(c)]

    lagged_dict: Dict[str, pd.Series] = {}
    for c in lag_cols:
        shifted = out[c].shift(1)
        shifted.name = c + "_lag1"
        lagged_dict[c + "_lag1"] = shifted

    passthrough = out[passthrough_cols].copy()
    date_col = out[["date"]].copy()

    new_cols: list = ["date"]
    for c in out.columns:
        if c == "date":
            continue
        if c in passthrough_cols:
            new_cols.append(c)
        elif c in lag_cols:
            new_cols.append(c + "_lag1")

    out = pd.concat(
        [date_col, passthrough, pd.DataFrame(lagged_dict, index=out.index)],
        axis=1,
    )
    return out[new_cols]


# ── Information sets (horse race) ────────────────────────────────────────────


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    """Return True if ``name`` matches any of the literal column-name patterns."""
    return name in set(patterns)


# All column names below use the ``_lag1`` suffix because the model matrix
# is built by passing the feature matrix through ``lag_features`` first.
# Sets are nested: F ⊂ P ⊂ PN ⊂ PNG.
#
#   F   : financial baseline
#   P   : F + physical attacks
#   N   : F + news attention
#   PN  : F + P + N
#   PNG : F + PN + narrative-gap features

INFO_SET_PATTERNS: Dict[str, Dict[str, Iterable[str]]] = {
    "F": {
        # Financial baseline. All non-calendar columns are listed with
        # their ``_lag1`` suffix.
        "include": (
            # Returns (one-trading-day-lagged, market-adjusted, etc.)
            "r_ITA_lag1", "r_ITA_msadj_lag1",
            "r_BSHIELDT_lag1", "r_BSHIELDT_msadj_lag1",
            # Volatility and market controls
            "VIX_lag1", "d_VIX_lag1",
            "vol_5d_lag1", "vol_20d_lag1",
            "abs_r_ITA_lag1",
            # Already-lagged returns from the feature matrix
            "r_ITA_lag2", "r_ITA_lag5",
        ),
        "exclude": (),
    },
    "P": {
        # F + physical attacks. All non-calendar columns get the ``_lag1`` suffix.
        "include": (
            # Attack counts (lagged)
            "launched_total_lag1", "launched_uav_lag1",
            "launched_cruise_missile_lag1", "launched_ballistic_missile_lag1",
            "launched_recon_uav_lag1", "launched_loitering_munition_lag1",
            "launched_guided_bomb_lag1", "launched_other_lag1",
            "destroyed_total_lag1", "destroyed_uav_lag1",
            "destroyed_cruise_missile_lag1", "destroyed_ballistic_missile_lag1",
            "destroyed_recon_uav_lag1", "destroyed_loitering_munition_lag1",
            "destroyed_guided_bomb_lag1", "destroyed_other_lag1",
            # Composition and rates (lagged)
            "interception_rate_lag1", "weapon_diversity_lag1",
            "war_intensity_lag1", "n_attack_events_lag1", "n_records_lag1",
            "attack_uav_share_lag1", "attack_cruise_share_lag1",
            "attack_ballistic_share_lag1", "penetrations_estimated_lag1",
            # Pre-lagged attack features
            "launched_total_lag3",
            "launched_total_7d_rolling", "launched_total_30d_rolling",
            "large_attack_indicator_lag1",
            # Attack surprise (15 columns: 5 series × 3 windows, lagged)
            "attack_surprise_total_7d_lag1",
            "attack_surprise_total_30d_lag1",
            "attack_surprise_total_90d_lag1",
            "attack_surprise_uav_7d_lag1",
            "attack_surprise_uav_30d_lag1",
            "attack_surprise_uav_90d_lag1",
            "attack_surprise_cruise_7d_lag1",
            "attack_surprise_cruise_30d_lag1",
            "attack_surprise_cruise_90d_lag1",
            "attack_surprise_ballistic_7d_lag1",
            "attack_surprise_ballistic_30d_lag1",
            "attack_surprise_ballistic_90d_lag1",
            "attack_surprise_penetrations_7d_lag1",
            "attack_surprise_penetrations_30d_lag1",
            "attack_surprise_penetrations_90d_lag1",
        ),
        "exclude": (),
    },
    "N": {
        # F + news attention. All non-calendar columns get the ``_lag1`` suffix.
        "include": (
            # Article counts (lagged)
            "n_articles_ukrainian_lag1", "n_articles_russian_lag1",
            "n_articles_western_lag1", "n_articles_other_lag1",
            "n_articles_total_lag1", "n_articles_total_lag3",
            "n_articles_total_7d_rolling_mean",
            "n_articles_total_30d_rolling_mean",
            # Shares (lagged)
            "n_ukrainian_share_lag1", "n_russian_share_lag1",
            "n_western_share_lag1", "n_other_share_lag1",
            # Log normalizations (lagged)
            "n_ukrainian_log_lag1", "n_russian_log_lag1",
            "n_western_log_lag1", "n_other_log_lag1",
            # Z-score (lagged)
            "n_ukrainian_z30_lag1", "n_russian_z30_lag1",
            "n_western_z30_lag1", "n_other_z30_lag1",
            # Tones (lagged; current values are not available pre-market)
            "tone_ukrainian_lag1", "tone_ukrainian_lag3",
            "tone_russian_lag1", "tone_russian_lag3",
            "tone_western_lag1", "tone_western_lag3",
            "tone_other_lag1", "tone_other_lag3",
        ),
        "exclude": (),
    },
    "PN": {
        # F + P + N (built via set nesting in build_info_sets). The per-query
        # × per-group columns (e.g. n_ukrainian_russian_attack_direct_lag1)
        # are added here so PN differs from F ∪ P ∪ N in a meaningful way.
        "include": (
            # 16 per-query × per-group columns (4 queries × 4 source groups),
            # all with the _lag1 suffix.
            "n_ukrainian_russian_attack_direct_lag1",
            "n_ukrainian_ukraine_defense_energy_lag1",
            "n_ukrainian_defense_industry_western_lag1",
            "n_ukrainian_energy_war_lag1",
            "n_russian_russian_attack_direct_lag1",
            "n_russian_ukraine_defense_energy_lag1",
            "n_russian_defense_industry_western_lag1",
            "n_russian_energy_war_lag1",
            "n_western_russian_attack_direct_lag1",
            "n_western_ukraine_defense_energy_lag1",
            "n_western_defense_industry_western_lag1",
            "n_western_energy_war_lag1",
            "n_other_russian_attack_direct_lag1",
            "n_other_ukraine_defense_energy_lag1",
            "n_other_defense_industry_western_lag1",
            "n_other_energy_war_lag1",
        ),
        "exclude": (),
    },
    "PNG": {
        # F + PN + narrative-gap features. The narrative gaps are
        # differences of tone between source groups (e.g. ``tone_ukrainian -
        # tone_western``), lagged.
        "include": (
            "narrative_gap_ua_west_lag1",
            "narrative_gap_ru_west_lag1",
            "narrative_gap_ua_ru_lag1",
        ),
        "exclude": (),
    },
}


def build_info_sets(
    columns: Iterable[str],
    info_set_patterns: Optional[Dict[str, Dict[str, Iterable[str]]]] = None,
) -> Dict[str, list]:
    """Build the column lists for each information set (nested F ⊂ P ⊂ PN ⊂ PNG)."""
    if info_set_patterns is None:
        info_set_patterns = INFO_SET_PATTERNS

    cols = list(columns)
    base_excludes = {
        "date",
        "ITA",
        "BSHIELDT",
        "WAERLST_recon",
        f"target_{PRIMARY_TARGET}_t1",
        f"target_{SECONDARY_TARGET}_t1",
    }

    out: Dict[str, list] = {}
    for name in ("F", "P", "N", "PN", "PNG"):
        spec = info_set_patterns[name]
        included = [
            c for c in cols
            if _matches_any(c, spec["include"])
            and not _matches_any(c, spec.get("exclude", ()))
        ]
        if name == "F":
            for c in CALENDAR_PASSTHROUGH_COLS:
                if c in cols and c not in included:
                    included.append(c)
        out[name] = sorted(set(included))

    # Force nesting: F ⊂ P, P ⊂ PN, PN ⊂ PNG.
    out["P"] = sorted(set(out["F"]) | set(out["P"]))
    out["PN"] = sorted(set(out["P"]) | set(out["PN"]))
    out["PNG"] = sorted(set(out["PN"]) | set(out["PNG"]))

    for name in out:
        out[name] = [c for c in out[name] if c not in base_excludes]

    return out


# ── Build the model matrix ──────────────────────────────────────────────────


DEFAULT_MODELING_START = "2022-09-29"


def build_model_matrix(
    feature_matrix: pd.DataFrame,
    modeling_start: Union[str, pd.Timestamp] = DEFAULT_MODELING_START,
    modeling_end: Optional[Union[str, pd.Timestamp]] = None,
    primary_target: str = PRIMARY_TARGET,
    secondary_target: Optional[str] = SECONDARY_TARGET,
    info_set_patterns: Optional[Dict[str, Dict[str, Iterable[str]]]] = None,
) -> pd.DataFrame:
    """Assemble the final model matrix from the feature matrix."""
    # 1. Build targets.
    targets = build_targets(
        feature_matrix,
        primary_target=primary_target,
        secondary_target=secondary_target,
    )

    # 2. Lag features (past-only).
    lagged = lag_features(feature_matrix)

    # 3. Restrict to the modeling window.
    mask = lagged["date"] >= pd.Timestamp(modeling_start)
    if modeling_end is not None:
        mask &= lagged["date"] <= pd.Timestamp(modeling_end)
    lagged = lagged.loc[mask].reset_index(drop=True)
    targets = targets.loc[mask].reset_index(drop=True)

    # 4. Merge targets with lagged features.
    mm = lagged.merge(targets, on="date", how="left")

    # 5. Drop rows where the primary target is NaN.
    primary_col = f"target_{primary_target}_t1"
    mm = mm.dropna(subset=[primary_col]).reset_index(drop=True)

    # 6. Build the information-set column masks.
    info_sets = build_info_sets(mm.columns, info_set_patterns=info_set_patterns)
    mm.attrs["info_sets"] = info_sets
    mm.attrs["primary_target"] = primary_col
    if secondary_target is not None:
        mm.attrs["secondary_target"] = f"target_{secondary_target}_t1"
    mm.attrs["modeling_start"] = str(mm["date"].min())
    mm.attrs["modeling_end"] = str(mm["date"].max())

    return mm
