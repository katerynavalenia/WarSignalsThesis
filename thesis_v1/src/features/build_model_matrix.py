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

Per decision_log 2026-07-02 (target hierarchy restructure), the primary
target is the **real Bloomberg WAERLST index** (`r_WAERLST`; the literal
thesis-title outcome). Two robustness targets are carried alongside it:
the **real Bloomberg BSHIELDT index** (`r_BSHIELDT`, European/war-exposed)
and the **ITA ETF proxy** (`r_ITA`, US robustness, yfinance). The old
mcap-weighted reconstruction (`r_WAERLST_recon`) is demoted from target to
lagged **feature** only (`r_WAERLST_recon_lag1`), since the real WAERLST
series now exists and is far cleaner.
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

# Primary financial target: real Bloomberg WAERLST index (decision_log 2026-07-02).
PRIMARY_TARGET = "r_WAERLST"
# Robustness targets: real Bloomberg BSHIELDT (European, war-exposed) and the
# ITA ETF proxy (US robustness, yfinance). Order matters only for defaults.
ROBUSTNESS_TARGETS = ("r_BSHIELDT", "r_ITA")
# Full target tuple used as the default everywhere a 3-target set is needed.
TARGET_COLS = (PRIMARY_TARGET,) + ROBUSTNESS_TARGETS
# NOTE: r_WAERLST_recon is intentionally NOT a target anymore (demoted,
# decision_log 2026-07-02). It is retained as a lagged *feature*
# (``r_WAERLST_recon_lag1``) in the F info set.


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


def _collect_n_next_trading_indices(
    dates: pd.DatetimeIndex,
    start: int,
    n: int,
) -> list:
    """Return the list of the next ``n`` trading-day indices after ``dates[start]``.

    Stops early (returns a shorter list) if the index runs out before ``n``
    future trading days are available.
    """
    out = []
    cursor = start
    for _ in range(n):
        cursor = _next_trading_day_index(dates, cursor)
        if cursor == -1:
            break
        out.append(cursor)
    return out


def _shift_to_n_trading_day_sum(
    series: pd.Series,
    dates: pd.DatetimeIndex,
    n: int,
) -> pd.Series:
    """Sum of the next ``n`` trading-day values of ``series`` (§9 weekend rule).

    For each calendar day ``t``, the value is ``Σ series[t+1..t+n]`` where
    ``t+1, ..., t+n`` are the next ``n`` trading days. Rows with fewer than
    ``n`` future trading days or with any NaN in the window are left NaN.
    """
    out = pd.Series(np.nan, index=series.index, name=series.name)
    n_rows = len(dates)
    for i in range(n_rows):
        idxs = _collect_n_next_trading_indices(dates, i, n)
        if len(idxs) < n:
            continue
        vals = series.iloc[idxs]
        if vals.isna().any():
            continue
        out.iloc[i] = float(vals.sum())
    return out


def _shift_to_n_trading_day_sumsq(
    series: pd.Series,
    dates: pd.DatetimeIndex,
    n: int,
) -> pd.Series:
    """Sum of squares of the next ``n`` trading-day values (realized variance).

    For ``n == 1`` this is the per-day squared return (RV proxy for the next
    trading day). For ``n > 1`` it is the sum of squared daily returns over
    the next ``n`` trading days, used as the QLIKE-compatible realized
    variance target for multi-day GARCH forecasts.
    """
    out = pd.Series(np.nan, index=series.index, name=series.name)
    n_rows = len(dates)
    for i in range(n_rows):
        idxs = _collect_n_next_trading_indices(dates, i, n)
        if len(idxs) < n:
            continue
        vals = series.iloc[idxs]
        if vals.isna().any():
            continue
        out.iloc[i] = float((vals ** 2).sum())
    return out


def build_targets(
    feature_matrix: pd.DataFrame,
    primary_target: str = PRIMARY_TARGET,
    robustness_targets: Iterable[str] = ROBUSTNESS_TARGETS,
    horizons: Iterable[int] = (1, 5),
    add_variance: bool = True,
) -> pd.DataFrame:
    """Construct next-trading-day return target(s) and (optionally) variance targets.

    Per the §9 weekend rule, a calendar day ``t`` has a target equal to the
    return of the **next trading day** (so Sat/Sun/Mon all point to Monday's
    return). The target at the last calendar day in the index is NaN.

    ``primary_target`` (default ``r_WAERLST``) plus any names in
    ``robustness_targets`` (default ``("r_BSHIELDT", "r_ITA")``) each get a
    target column. Pass ``robustness_targets=()`` (or ``None``) to build only
    the primary target.

    For each horizon ``h`` in ``horizons``, adds the column
    ``target_{name}_t{h}`` (cumulative log return over the next ``h`` trading
    days for ``h > 1``). If ``add_variance=True`` (default) also adds
    ``target_var_{name}_t{h}`` (sum of squared daily returns over the same
    window — the QLIKE-compatible realized-variance target for GARCH).
    """
    out = pd.DataFrame({"date": feature_matrix["date"]})
    dates = pd.DatetimeIndex(feature_matrix["date"])
    horizons = sorted(set(int(h) for h in horizons))
    if not horizons or any(h < 1 for h in horizons):
        raise ValueError(f"horizons must be a non-empty iterable of positive ints, got {horizons}")

    def _add_target(name: str, source_col: str) -> None:
        if source_col not in feature_matrix.columns:
            raise KeyError(
                f"target='{name}' (column '{source_col}') not in feature_matrix. "
                f"Available: {[c for c in feature_matrix.columns if c.startswith('r_')]}"
            )
        src = feature_matrix[source_col]
        for h in horizons:
            if h == 1:
                out[f"target_{name}_t1"] = _shift_to_next_trading_day(src, dates)
            else:
                out[f"target_{name}_t{h}"] = _shift_to_n_trading_day_sum(src, dates, h)
            if add_variance:
                out[f"target_var_{name}_t{h}"] = _shift_to_n_trading_day_sumsq(src, dates, h)

    _add_target(primary_target, primary_target)
    for name in (robustness_targets or ()):
        _add_target(name, name)

    return out


# ── Lag structure ───────────────────────────────────────────────────────────


def _is_passthrough(col: str) -> bool:
    """Return True if ``col`` is a calendar/structural feature known at market open."""
    if col in CALENDAR_PASSTHROUGH_COLS:
        return True
    if col.startswith("is_") and len(col) < 30:
        return True
    return False


def _is_pre_lagged(col: str) -> bool:
    """Return True if the column name encodes an explicit lag.

    A column like ``r_ITA_lag1``, ``r_ITA_lag2``, ``r_ITA_lag5`` is a
    *pre-lagged* return from the feature matrix. Re-shifting it inside
    :func:`lag_features` would double the lag (r_ITA at t-1 in the
    feature matrix → r_ITA at t-2 in the model matrix). This method
    detects such columns by their ``_lagN`` suffix.
    """
    import re
    return bool(re.search(r"_lag\d+$", col))


def lag_features(
    feature_matrix: pd.DataFrame,
    exclude: Optional[Iterable[str]] = None,
    keep_target_sources: bool = True,
    skip_pre_lagged: bool = True,
) -> pd.DataFrame:
    """Lag all non-calendar features by 1 calendar day.

    Parameters
    ----------
    feature_matrix : pd.DataFrame
        The feature matrix from Phase 5E.
    exclude : iterable of str, optional
        Column names to drop entirely (raw index levels like ``ITA``,
        ``BSHIELDT``, ``WAERLST_recon``).
    keep_target_sources : bool, default True
        If True, the target source columns (``r_WAERLST``, ``r_BSHIELDT``,
        ``r_ITA``) plus the demoted ``r_WAERLST_recon`` feature source are
        kept in the model matrix as lagged columns (``r_WAERLST_lag1``,
        ``r_WAERLST_recon_lag1``, …). These are used by GARCH-family models
        as the source time series; the actual target sources are excluded
        from the F/P/N/PN/PNG information sets by :func:`build_info_sets`
        (see ``_BASE_EXCLUDE_PREFIXES``); ``r_WAERLST_recon_lag1`` is a
        legitimate F-set feature (no longer a target source).
    skip_pre_lagged : bool, default True
        If True, columns whose name encodes an explicit lag
        (``r_ITA_lag1``, ``r_ITA_lag2``, …) are **not re-shifted**.
        This prevents the double-lag bug where ``r_ITA_lag1`` (= r_ITA at
        t-1 in the feature matrix) becomes ``r_ITA_lag1_lag1`` (= r_ITA
        at t-2 in the model matrix) — losing 1 day of the most recent
        return information.

        The resulting column name preserves the original name
        (``r_ITA_lag1`` stays as ``r_ITA_lag1`` in the model matrix).
    """
    out = feature_matrix.copy()
    if exclude is None:
        exclude = (
            "date",
            "ITA",
            "BSHIELDT",
            "WAERLST_recon",
        )
    drop = (set(exclude) - {"date"}) & set(out.columns)
    if drop:
        out = out.drop(columns=list(drop))

    # If keep_target_sources is False, drop the target source columns so
    # they are not even available in the model matrix.
    if not keep_target_sources:
        for c in TARGET_COLS:
            if c in out.columns:
                out = out.drop(columns=[c])

    # Detect and resolve the pre-lagged / re-lagged naming conflict.
    # The feature matrix has BOTH a raw column (e.g. ``r_ITA``) and a
    # pre-lagged version of the same column (``r_ITA_lag1``,
    # representing r_ITA at t-1 in the feature matrix's coordinate
    # system). After ``lag_features`` runs, the raw column gets
    # re-lagged to ``r_ITA_lag1`` (= r_ITA at t-1 in the model matrix's
    # coordinate system). If we also keep the pre-lagged column with
    # its original name, we have a duplicate column.
    #
    # Resolution: when ``skip_pre_lagged=True`` we DROP the raw
    # column (e.g. ``r_ITA``) — the pre-lagged ``r_ITA_lag1`` is
    # preserved as-is and represents the same information (r_ITA at
    # t-1 in the model matrix). For the secondary target, the feature
    # matrix has ``r_WAERLST_recon`` (raw) but no pre-lagged version
    # — we re-introduce it as ``r_WAERLST_recon_lag1`` for GARCH/AR1
    # use.
    if skip_pre_lagged:
        # Drop raw columns whose pre-lagged form is also in the matrix
        # (avoids the duplicate ``r_ITA_lag1`` from re-lagging ``r_ITA``).
        pre_lagged_bases = set()
        for c in list(out.columns):
            if _is_pre_lagged(c) and c.endswith("_lag1"):
                base = c[: -len("_lag1")]
                pre_lagged_bases.add(base)
        if pre_lagged_bases:
            cols_to_drop = [
                c for c in pre_lagged_bases
                if c in out.columns and not _is_pre_lagged(c)
            ]
            if cols_to_drop:
                out = out.drop(columns=cols_to_drop)

        # ``r_WAERLST_recon`` (demoted from target to feature, decision_log
        # 2026-07-02) has no pre-lagged version in the feature matrix — its
        # raw column would otherwise just be dropped, losing the signal.
        # Re-introduce it as ``r_WAERLST_recon_lag1`` so it stays available
        # as a legitimate F-set feature (and for any GARCH/AR1 use).
        _RECON_FEATURE = "r_WAERLST_recon"
        if keep_target_sources and _RECON_FEATURE in out.columns \
                and not _is_pre_lagged(_RECON_FEATURE):
            # Already dropped above
            pass
        elif keep_target_sources and _RECON_FEATURE not in out.columns:
            # Not in the feature matrix at all — nothing to do.
            pass

        # Now ensure the recon source column exists as ``_lag1`` in the
        # model matrix. The primary/robustness target sources
        # (``r_WAERLST_lag1``, ``r_BSHIELDT_lag1``, ``r_ITA_lag1``) are
        # already there via the normal re-lag path (or pre-lagged
        # carryover for r_ITA). ``r_WAERLST_recon_lag1`` is the lag-1 of
        # the raw recon column — re-introduce it from the original
        # feature matrix below (before the re-lag block was applied).
        if keep_target_sources and _RECON_FEATURE in feature_matrix.columns \
                and _RECON_FEATURE not in out.columns:
            # The raw column was dropped above; re-introduce its lag-1
            # version. Use the original feature_matrix (not ``out``)
            # because ``out`` has already been modified.
            recon_lag1 = feature_matrix[_RECON_FEATURE].shift(1)
            recon_lag1.name = _RECON_FEATURE + "_lag1"
            out[_RECON_FEATURE + "_lag1"] = recon_lag1

    lag_cols = [
        c for c in out.columns
        if c != "date"
        and not _is_passthrough(c)
        and not (skip_pre_lagged and _is_pre_lagged(c))
    ]
    passthrough_cols = [c for c in out.columns if c != "date" and _is_passthrough(c)]
    pre_lagged_cols = [
        c for c in out.columns
        if c != "date" and skip_pre_lagged and _is_pre_lagged(c)
    ]

    lagged_dict: Dict[str, pd.Series] = {}
    for c in lag_cols:
        shifted = out[c].shift(1)
        shifted.name = c + "_lag1"
        lagged_dict[c + "_lag1"] = shifted

    passthrough = out[passthrough_cols].copy()
    date_col = out[["date"]].copy()
    pre_lagged = out[pre_lagged_cols].copy() if pre_lagged_cols else None

    # Build the new column list in original order with dedup.
    seen: set = set()
    new_cols: list = ["date"]
    for c in out.columns:
        if c == "date":
            continue
        if c in passthrough_cols:
            if c not in seen:
                new_cols.append(c)
                seen.add(c)
        elif c in lag_cols:
            new_name = c + "_lag1"
            if new_name not in seen:
                new_cols.append(new_name)
                seen.add(new_name)
        elif c in pre_lagged_cols:
            if c not in seen:
                new_cols.append(c)
                seen.add(c)

    pieces = [date_col, passthrough]
    if pre_lagged is not None:
        pieces.append(pre_lagged)
    pieces.append(pd.DataFrame(lagged_dict, index=out.index))

    out = pd.concat(pieces, axis=1)
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
        # Financial baseline. As of the C5 fix, the model matrix preserves
        # the feature matrix's pre-lagged column names (``r_ITA_lag1``,
        # not ``r_ITA_lag1_lag1``) because :func:`lag_features` no longer
        # re-shifts pre-lagged columns. This means the F set now contains
        # r_ITA at t-1, t-2, t-5 (the most informative lags for next-day
        # return prediction). Per decision_log 2026-07-02, the real
        # WAERLST/BSHIELDT series (and their volume-derived liquidity
        # features) are added alongside the existing r_ITA/r_BSHIELDT
        # (reconstruction-era) robustness features.
        "include": (
            # Returns (r_ITA at t-1, t-2, t-5 from the feature matrix
            # carry-over).
            "r_ITA_lag1", "r_ITA_msadj_lag1",
            "r_ITA_lag2", "r_ITA_lag5",
            "r_BSHIELDT_lag1", "r_BSHIELDT_msadj_lag1",
            # Real Bloomberg WAERLST (primary target source, lagged) and
            # BSHIELDT lags/abs — added per decision_log 2026-07-02.
            "r_WAERLST_lag1", "r_WAERLST_lag2", "r_WAERLST_lag5",
            "abs_r_WAERLST_lag1",
            # Demoted reconstruction, kept as a lagged feature only
            # (decision_log 2026-07-02) — no longer a target source, so no
            # leakage concern.
            "r_WAERLST_recon_lag1",
            # Volatility and market controls
            "VIX_lag1", "d_VIX_lag1",
            "vol_5d_lag1", "vol_20d_lag1",
            "abs_r_ITA_lag1",
            # Volume-derived liquidity features (WAERLST/BSHIELDT), from
            # ``compute_index_returns_and_volume`` in src/data/financial.py.
            "logvol_WAERLST_lag1", "vol_z30_WAERLST_lag1", "dvol_WAERLST_lag1",
            "logvol_BSHIELDT_lag1", "vol_z30_BSHIELDT_lag1", "dvol_BSHIELDT_lag1",
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
    # Always exclude raw (same-day, un-lagged) index levels + the date
    # column. Exclude any ``target_*`` column (returns and variance) so
    # they can never be picked as features — that would be leakage (the
    # lagged version of the *same* target series is fine as a feature;
    # only the contemporaneous/undelayed level is excluded here).
    #
    # Per decision_log 2026-07-02, ``r_WAERLST_recon`` is demoted from a
    # modeling target to a plain lagged feature (``r_WAERLST_recon_lag1``).
    # It is therefore NOT a target source anymore and must NOT be excluded
    # on leakage grounds — the previous version of this function excluded
    # it because it used to be the secondary target's source column. The
    # actual (current) target sources are the primary/robustness targets
    # themselves (``r_WAERLST``, ``r_BSHIELDT``, ``r_ITA``); their lag1
    # versions (``r_WAERLST_lag1``, etc.) are legitimate predictive
    # features (they encode t-1 information, not t or t+1), so they need
    # no exclusion either.
    base_excludes = {
        "date",
        "ITA",
        "BSHIELDT",
        "WAERLST_recon",
    } | {c for c in cols if c.startswith("target_")}

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

    # Force nesting: F ⊂ P, F ⊂ N, F ⊂ P ⊂ PN, N ⊂ PN, PN ⊂ PNG.
    # N was previously left as "news-only" (F was never unioned in), which
    # made N != "F + news" as documented, and coincidentally made N and F
    # near-identical in cardinality by construction (docs/phase7_audit.md
    # §1.5). Fixed here (decision_log 2026-07-02 / real_index_integration
    # plan §5): N must be F + news, matching the P/PN/PNG pattern. PN is
    # F + P + N (attacks + news together), so it must also absorb N's
    # news-only columns, not just its own per-query×group additions.
    out["P"] = sorted(set(out["F"]) | set(out["P"]))
    out["N"] = sorted(set(out["F"]) | set(out["N"]))
    out["PN"] = sorted(set(out["P"]) | set(out["N"]) | set(out["PN"]))
    out["PNG"] = sorted(set(out["PN"]) | set(out["PNG"]))

    for name in out:
        out[name] = [c for c in out[name] if c not in base_excludes]

    return out


# ── Build the model matrix ──────────────────────────────────────────────────


DEFAULT_MODELING_START = "2022-09-29"


def make_train_test_split(
    mm: pd.DataFrame,
    test_fraction: float = 0.25,
    min_train_obs: int = 500,
) -> tuple:
    """Chronological train/test split for the model matrix.

    Parameters
    ----------
    mm : pd.DataFrame
        The model matrix, in chronological order by ``date``.
    test_fraction : float, default 0.25
        Fraction of rows to reserve for the test set (the last
        ``ceil(n * test_fraction)`` rows after chronological ordering).
    min_train_obs : int, default 500
        Minimum number of training observations required; raises
        :class:`ValueError` otherwise.

    Returns
    -------
    train_mask, test_mask, split_date : (np.ndarray, np.ndarray, pd.Timestamp)
        Boolean masks of the same length as ``mm`` and the date of the first
        test row.
    """
    n = len(mm)
    if not 0.0 < test_fraction < 1.0:
        raise ValueError(f"test_fraction must be in (0, 1), got {test_fraction}")
    n_test = int(np.ceil(n * test_fraction))
    n_train = n - n_test
    if n_train < min_train_obs:
        raise ValueError(
            f"Train set would have {n_train} obs < min_train_obs={min_train_obs}. "
            f"Either reduce test_fraction, lower min_train_obs, or extend the "
            f"modeling window. (n={n}, test_fraction={test_fraction})"
        )
    train_mask = np.zeros(n, dtype=bool)
    test_mask = np.zeros(n, dtype=bool)
    train_mask[:n_train] = True
    test_mask[n_train:] = True
    split_date = mm["date"].iloc[n_train]
    return train_mask, test_mask, pd.Timestamp(split_date)


def build_model_matrix(
    feature_matrix: pd.DataFrame,
    modeling_start: Union[str, pd.Timestamp] = DEFAULT_MODELING_START,
    modeling_end: Optional[Union[str, pd.Timestamp]] = None,
    primary_target: str = PRIMARY_TARGET,
    robustness_targets: Iterable[str] = ROBUSTNESS_TARGETS,
    info_set_patterns: Optional[Dict[str, Dict[str, Iterable[str]]]] = None,
    horizons: Iterable[int] = (1, 5),
    add_variance_targets: bool = True,
) -> pd.DataFrame:
    """Assemble the final model matrix from the feature matrix.

    For each (target, horizon) pair this adds ``target_{name}_t{h}`` columns
    (cumulative log returns over the next ``h`` trading days, weekend-rule
    aligned). When ``add_variance_targets`` is True (default) it also adds
    ``target_var_{name}_t{h}`` (sum of squared daily returns — the realized
    variance target for GARCH). ``primary_target`` defaults to ``r_WAERLST``
    (real Bloomberg index) and ``robustness_targets`` to
    ``("r_BSHIELDT", "r_ITA")`` per decision_log 2026-07-02.
    """
    # 1. Build targets (t1 + t5 + var).
    targets = build_targets(
        feature_matrix,
        primary_target=primary_target,
        robustness_targets=robustness_targets,
        horizons=horizons,
        add_variance=add_variance_targets,
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

    # 5. Drop rows where the primary target is NaN (last rows in window).
    primary_col = f"target_{primary_target}_t1"
    mm = mm.dropna(subset=[primary_col]).reset_index(drop=True)

    # 6. Build the information-set column masks.
    info_sets = build_info_sets(mm.columns, info_set_patterns=info_set_patterns)
    mm.attrs["info_sets"] = info_sets
    mm.attrs["primary_target"] = primary_col
    mm.attrs["robustness_targets"] = [
        f"target_{name}_t1" for name in (robustness_targets or ())
    ]
    mm.attrs["modeling_start"] = str(mm["date"].min())
    mm.attrs["modeling_end"] = str(mm["date"].max())
    mm.attrs["horizons"] = sorted(set(int(h) for h in horizons))
    mm.attrs["add_variance_targets"] = bool(add_variance_targets)

    return mm
