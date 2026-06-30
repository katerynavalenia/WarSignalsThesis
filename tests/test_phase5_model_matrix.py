"""Tests for ``src.features.build_model_matrix`` (Phase 5D)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.build_model_matrix import (
    CALENDAR_PASSTHROUGH_COLS,
    INFO_SET_PATTERNS,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    _next_trading_day_index,
    _shift_to_next_trading_day,
    build_info_sets,
    build_model_matrix,
    build_targets,
    lag_features,
)
from src.utils.date_utils import US_FEDERAL_HOLIDAYS


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_master(
    start: str = "2024-01-01",
    n: int = 10,
    r_ita: list[float] | None = None,
    r_waerlst: list[float] | None = None,
    extra: dict | None = None,
) -> pd.DataFrame:
    """Build a minimal ``feature_matrix``-shaped DataFrame."""
    dates = pd.date_range(start, periods=n, freq="D")
    if r_ita is None:
        r_ita = [0.0] * n
    if r_waerlst is None:
        r_waerlst = [0.0] * n
    df = pd.DataFrame(
        {
            "date": dates,
            "r_ITA": r_ita,
            "r_ITA_msadj": r_ita,
            "r_WAERLST_recon": r_waerlst,
            "VIX": [15.0] * n,
            "d_VIX": [0.0] * n,
            "vol_5d": [1.0] * n,
            "vol_20d": [1.5] * n,
            "abs_r_ITA": [abs(r) for r in r_ita],
            "r_ITA_lag1": [0.0] * n,
            "r_ITA_lag2": [0.0] * n,
            "r_ITA_lag5": [0.0] * n,
            "is_weekend": (dates.dayofweek >= 5).astype(int),
            "is_holiday": [int(d.date() in US_FEDERAL_HOLIDAYS) for d in dates],
            "day_of_week": dates.dayofweek,
            "month": dates.month,
            "days_since_invasion": [100] * n,
            "vix_low": [0] * n,
            "vix_normal": [1] * n,
            "vix_high": [0] * n,
            "vix_crisis": [0] * n,
            "waerlst_missing": [0] * n,
        }
    )
    if extra:
        for k, v in extra.items():
            df[k] = v
    return df


# ── Target construction ─────────────────────────────────────────────────────


class TestNextTradingDayIndex:
    def test_friday_points_to_monday(self):
        dates = pd.DatetimeIndex([
            "2024-01-05",  # Fri
            "2024-01-06",  # Sat
            "2024-01-07",  # Sun
            "2024-01-08",  # Mon (no holiday)
        ])
        assert _next_trading_day_index(dates, 0) == 3
        assert _next_trading_day_index(dates, 1) == 3
        assert _next_trading_day_index(dates, 2) == 3
        assert _next_trading_day_index(dates, 3) == -1

    def test_skips_holiday(self):
        # 2024-01-01 is New Year's Day. Mon 2024-01-08 is a normal trading day.
        dates = pd.DatetimeIndex([
            "2023-12-29",  # Fri
            "2024-01-01",  # Mon (holiday)
            "2024-01-02",  # Tue
        ])
        assert _next_trading_day_index(dates, 0) == 2
        assert _next_trading_day_index(dates, 1) == 2
        assert _next_trading_day_index(dates, 2) == -1


class TestShiftToNextTradingDay:
    def test_friday_target_carries_to_weekend(self):
        # Mon Tue Wed Thu Fri — target at each day = next trading day's return.
        dates = pd.DatetimeIndex([
            "2024-01-01",  # Mon (holiday)
            "2024-01-02",  # Tue
            "2024-01-03",  # Wed
            "2024-01-04",  # Thu
            "2024-01-05",  # Fri
        ])
        returns = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        target = _shift_to_next_trading_day(returns, dates)
        # Mon 2024-01-01 is a holiday → next trading day is Tue 2024-01-02 (return 2.0).
        assert target.iloc[0] == 2.0
        # Tue → Wed (3.0)
        assert target.iloc[1] == 3.0
        # Fri → no next trading day → NaN
        assert pd.isna(target.iloc[4])

    def test_target_is_nan_at_last_calendar_day(self):
        dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
        returns = pd.Series([1.0, 2.0], index=dates)
        target = _shift_to_next_trading_day(returns, dates)
        assert target.iloc[0] == 2.0
        assert pd.isna(target.iloc[1])


class TestBuildTargets:
    def test_primary_and_secondary_targets(self):
        df = _make_master(r_ita=[0.1] * 10, r_waerlst=[0.2] * 10)
        targets = build_targets(df)
        assert "target_r_ITA_t1" in targets.columns
        assert "target_r_WAERLST_recon_t1" in targets.columns
        assert "date" in targets.columns

    def test_only_primary(self):
        df = _make_master()
        targets = build_targets(df, secondary_target=None)
        assert "target_r_ITA_t1" in targets.columns
        assert "target_r_WAERLST_recon_t1" not in targets.columns

    def test_missing_primary_raises(self):
        df = _make_master().drop(columns=["r_ITA"])
        with pytest.raises(KeyError, match="primary_target"):
            build_targets(df)


# ── Lag features ────────────────────────────────────────────────────────────


class TestIsPassthrough:
    def test_calendar_columns_pass_through(self):
        for c in CALENDAR_PASSTHROUGH_COLS:
            assert _is_passthrough_for_test(c) is True, c

    def test_financial_columns_are_lagged(self):
        for c in ("r_ITA", "vol_5d", "r_ITA_lag1", "attack_surprise_total_7d"):
            assert _is_passthrough_for_test(c) is False, c


def _is_passthrough_for_test(col: str) -> bool:
    from src.features.build_model_matrix import _is_passthrough
    return _is_passthrough(col)


class TestLagFeatures:
    def test_lags_non_calendar_columns(self):
        df = _make_master(n=5, r_ita=[1.0, 2.0, 3.0, 4.0, 5.0])
        lagged = lag_features(df)
        # r_ITA was excluded (it is the primary target). r_ITA_lag1 stays and
        # becomes r_ITA_lag1_lag1, with the value at t=1 == r_ITA_lag1[0] == 0.0.
        # (The test fixture sets r_ITA_lag1 = [0]*n in the input.)
        assert "r_ITA_lag1_lag1" in lagged.columns
        assert lagged["r_ITA_lag1_lag1"].iloc[1] == 0.0
        # Calendar passthrough keeps the same value
        assert lagged["day_of_week"].iloc[1] == df["day_of_week"].iloc[1]
        # vol_5d is lagged (value at t=1 should be vol_5d[0] == 1.0)
        assert "vol_5d_lag1" in lagged.columns
        assert lagged["vol_5d_lag1"].iloc[1] == 1.0
        # First value of a lagged column is NaN
        assert pd.isna(lagged["vol_5d_lag1"].iloc[0])

    def test_excludes_target_columns(self):
        df = _make_master()
        lagged = lag_features(df)
        assert "r_ITA" not in lagged.columns
        assert "r_WAERLST_recon" not in lagged.columns

    def test_excludes_raw_index_columns(self):
        df = _make_master(n=5, extra={"ITA": [100.0] * 5, "BSHIELDT": [50.0] * 5})
        lagged = lag_features(df)
        assert "ITA" not in lagged.columns
        assert "BSHIELDT" not in lagged.columns


# ── Information sets ────────────────────────────────────────────────────────


class TestBuildInfoSets:
    def test_nesting_F_subset_of_P_subset_of_PN_subset_of_PNG(self):
        cols = {
            PRIMARY_TARGET, SECONDARY_TARGET,
            "ITA", "BSHIELDT", "WAERLST_recon",
            "r_ITA", "vol_5d", "launched_total",
            "n_articles_total", "n_articles_ukrainian",
            "n_ukrainian_russian_attack_direct",
            "narrative_gap_ua_west",
            "day_of_week", "is_weekend",
            "date", "fake_column",
        }
        out = build_info_sets(cols)
        assert set(out["F"]).issubset(set(out["P"]))
        assert set(out["P"]).issubset(set(out["PN"]))
        assert set(out["PN"]).issubset(set(out["PNG"]))

    def test_excludes_target_and_raw_columns(self):
        # Note: r_ITA_lag1 and r_WAERLST_recon_lag1 are KEPT as
        # F-set features (they are lagged return inputs). Only the target
        # columns (target_r_ITA_t1, target_r_WAERLST_recon_t1) and
        # the raw index LEVELS (ITA, BSHIELDT, WAERLST_recon) are
        # excluded.
        cols = {
            PRIMARY_TARGET, SECONDARY_TARGET,
            f"target_{PRIMARY_TARGET}_t1",
            f"target_{SECONDARY_TARGET}_t1",
            "ITA", "BSHIELDT", "WAERLST_recon",
            "r_ITA_lag1", "r_WAERLST_recon_lag1",
            "vol_5d_lag1", "date",
        }
        out = build_info_sets(cols)
        for c in (
            f"target_{PRIMARY_TARGET}_t1",
            f"target_{SECONDARY_TARGET}_t1",
            "ITA", "BSHIELDT", "WAERLST_recon", "date",
        ):
            assert c not in out["F"]
            assert c not in out["PNG"]
        # r_ITA_lag1 should be IN the F set (it's a feature, not the target).
        assert "r_ITA_lag1" in out["F"]

    def test_financial_columns_in_F(self):
        # The patterns use the _lag1 suffix because the model matrix is lagged.
        cols = {"r_ITA_lag1", "r_ITA_msadj_lag1", "vol_5d_lag1",
                "vol_20d_lag1", "VIX_lag1", "d_VIX_lag1",
                "abs_r_ITA_lag1", "r_ITA_lag2", "day_of_week"}
        out = build_info_sets(cols)
        for c in ("r_ITA_lag1", "vol_5d_lag1", "day_of_week", "VIX_lag1"):
            assert c in out["F"], c

    def test_attack_columns_in_P_not_F(self):
        # Patterns use the _lag1 suffix because the model matrix is lagged.
        cols = {"r_ITA_lag1", "launched_total_lag1",
                "attack_surprise_total_7d_lag1",
                "large_attack_indicator_lag1", "day_of_week"}
        out = build_info_sets(cols)
        assert "launched_total_lag1" not in out["F"]
        assert "launched_total_lag1" in out["P"]
        assert "attack_surprise_total_7d_lag1" in out["P"]

    def test_news_columns_in_N_not_F(self):
        # Patterns use the _lag1 suffix because the model matrix is lagged.
        cols = {"r_ITA_lag1", "n_articles_ukrainian_lag1",
                "n_ukrainian_share_lag1", "n_ukrainian_z30_lag1",
                "n_articles_total_lag1",
                "n_ukrainian_russian_attack_direct_lag1",
                "day_of_week"}
        out = build_info_sets(cols)
        assert "n_articles_ukrainian_lag1" not in out["F"]
        assert "n_articles_ukrainian_lag1" in out["N"]
        assert "n_ukrainian_russian_attack_direct_lag1" not in out["N"]
        assert "n_ukrainian_russian_attack_direct_lag1" in out["PN"]

    def test_narrative_gaps_only_in_PNG(self):
        # Patterns use the _lag1 suffix because the model matrix is lagged.
        cols = {"r_ITA_lag1",
                "narrative_gap_ua_west_lag1",
                "narrative_gap_ru_west_lag1",
                "narrative_gap_ua_ru_lag1",
                "day_of_week"}
        out = build_info_sets(cols)
        for c in ("narrative_gap_ua_west_lag1",
                  "narrative_gap_ru_west_lag1",
                  "narrative_gap_ua_ru_lag1"):
            assert c not in out["F"]
            assert c not in out["P"]
            assert c not in out["PN"]
            assert c in out["PNG"]


# ── Build model matrix (end-to-end) ────────────────────────────────────────


class TestBuildModelMatrix:
    def test_basic_shape(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "target_r_ITA_t1" in mm.columns
        assert "date" in mm.columns
        # First 7 days are dropped (modeling_start = 2022-09-29, but our
        # synthetic data starts 2024-01-01 → 30 days).
        assert len(mm) <= 30

    def test_drops_last_row_with_nan_target(self):
        df = _make_master(n=10)
        mm = build_model_matrix(df)
        # The last row in the model matrix should have a non-NaN target
        # (the very-last day of the input has no next trading day, so it
        # should be dropped).
        last_target = mm["target_r_ITA_t1"].iloc[-1]
        assert not pd.isna(last_target)

    def test_info_sets_in_attrs(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "info_sets" in mm.attrs
        assert set(mm.attrs["info_sets"].keys()) == {"F", "P", "N", "PN", "PNG"}

    def test_modeling_window_applied(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df, modeling_start="2024-01-15",
                               modeling_end="2024-01-25")
        assert mm["date"].min() >= pd.Timestamp("2024-01-15")
        assert mm["date"].max() <= pd.Timestamp("2024-01-25")

    def test_calendar_columns_not_lagged(self):
        df = _make_master(n=30)
        # Override day_of_week with known values to test passthrough
        df["day_of_week"] = list(range(7)) * 4 + [0, 1]
        mm = build_model_matrix(df)
        # day_of_week should keep its original values (not lagged)
        assert list(mm["day_of_week"]) == list(df["day_of_week"])[:len(mm)]

    def test_secondary_target_present(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "target_r_WAERLST_recon_t1" in mm.columns

    def test_no_secondary_when_disabled(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df, secondary_target=None)
        assert "target_r_WAERLST_recon_t1" not in mm.columns

    def test_no_leakage_target_not_in_features(self):
        """The target column should NOT appear in any information set."""
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        info_sets = mm.attrs["info_sets"]
        primary = mm.attrs["primary_target"]
        secondary = mm.attrs.get("secondary_target")
        for name, cols in info_sets.items():
            assert primary not in cols, f"target in {name}!"
            if secondary:
                assert secondary not in cols, f"target in {name}!"
