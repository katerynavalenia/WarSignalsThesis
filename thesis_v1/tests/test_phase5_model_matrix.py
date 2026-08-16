"""Tests for ``src.features.build_model_matrix`` (Phase 5D)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.build_model_matrix import (
    CALENDAR_PASSTHROUGH_COLS,
    INFO_SET_PATTERNS,
    PRIMARY_TARGET,
    ROBUSTNESS_TARGETS,
    _collect_n_next_trading_indices,
    _next_trading_day_index,
    _shift_to_n_trading_day_sum,
    _shift_to_n_trading_day_sumsq,
    _shift_to_next_trading_day,
    build_info_sets,
    build_model_matrix,
    build_targets,
    lag_features,
    make_train_test_split,
)
from src.utils.date_utils import US_FEDERAL_HOLIDAYS


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_master(
    start: str = "2024-01-01",
    n: int = 10,
    r_ita: list[float] | None = None,
    r_waerlst: list[float] | None = None,
    r_waerlst_recon: list[float] | None = None,
    r_bshieldt: list[float] | None = None,
    extra: dict | None = None,
) -> pd.DataFrame:
    """Build a minimal ``feature_matrix``-shaped DataFrame.

    Includes the real primary/robustness target sources (``r_WAERLST``,
    ``r_BSHIELDT``, ``r_ITA``; decision_log 2026-07-02) plus the demoted
    ``r_WAERLST_recon`` feature source.
    """
    dates = pd.date_range(start, periods=n, freq="D")
    if r_ita is None:
        r_ita = [0.0] * n
    if r_waerlst is None:
        r_waerlst = [0.0] * n
    if r_waerlst_recon is None:
        r_waerlst_recon = [0.0] * n
    if r_bshieldt is None:
        r_bshieldt = [0.0] * n
    df = pd.DataFrame(
        {
            "date": dates,
            "r_ITA": r_ita,
            "r_ITA_msadj": r_ita,
            "r_WAERLST": r_waerlst,
            "r_WAERLST_recon": r_waerlst_recon,
            "r_BSHIELDT": r_bshieldt,
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
    def test_primary_and_robustness_targets(self):
        df = _make_master(r_ita=[0.1] * 10, r_waerlst=[0.2] * 10, r_bshieldt=[0.3] * 10)
        targets = build_targets(df)
        assert "target_r_WAERLST_t1" in targets.columns
        assert "target_r_BSHIELDT_t1" in targets.columns
        assert "target_r_ITA_t1" in targets.columns
        # r_WAERLST_recon is demoted and must NOT get a target column.
        assert "target_r_WAERLST_recon_t1" not in targets.columns
        assert "date" in targets.columns

    def test_only_primary(self):
        df = _make_master()
        targets = build_targets(df, robustness_targets=None)
        assert "target_r_WAERLST_t1" in targets.columns
        assert "target_r_BSHIELDT_t1" not in targets.columns
        assert "target_r_ITA_t1" not in targets.columns

    def test_missing_primary_raises(self):
        df = _make_master().drop(columns=["r_WAERLST"])
        with pytest.raises(KeyError, match="r_WAERLST"):
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
        # As of the C5 fix, pre-lagged columns (e.g. ``r_ITA_lag1`` from
        # the feature matrix) are preserved as ``r_ITA_lag1`` in the
        # model matrix (= r_ITA at t-1 in calendar). The raw ``r_ITA``
        # column is dropped because it would otherwise produce a
        # duplicate ``r_ITA_lag1`` after the re-lag.
        assert "r_ITA_lag1" in lagged.columns
        # The value at t=1 should be the pre-lagged value at t=0, which
        # the test fixture sets to 0.0.
        assert lagged["r_ITA_lag1"].iloc[1] == 0.0
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
        # As of the C5 fix, the raw ``r_ITA`` is dropped (it would
        # otherwise produce a duplicate ``r_ITA_lag1`` after the
        # re-lag). The pre-lagged ``r_ITA_lag1`` is preserved.
        assert "r_ITA" not in lagged.columns
        # The secondary target source ``r_WAERLST_recon`` (raw) has no
        # pre-lagged version in the feature matrix, so lag_features
        # re-introduces it as ``r_WAERLST_recon_lag1``.
        assert "r_WAERLST_recon" not in lagged.columns
        assert "r_WAERLST_recon_lag1" in lagged.columns

    def test_excludes_raw_index_columns(self):
        df = _make_master(n=5, extra={"ITA": [100.0] * 5, "BSHIELDT": [50.0] * 5})
        lagged = lag_features(df)
        assert "ITA" not in lagged.columns
        assert "BSHIELDT" not in lagged.columns

    def test_pre_lagged_columns_preserved_with_original_name(self):
        # Regression guard for the C5 fix: pre-lagged columns are
        # preserved with their original name (not double-lagged).
        df = _make_master(n=10)
        # The fixture has r_ITA_lag1 = [0]*n. After lag_features, the
        # value at row t should be r_ITA_lag1 at row t-1 = 0.0.
        lagged = lag_features(df)
        # The pre-lagged column name is preserved.
        assert "r_ITA_lag1" in lagged.columns
        assert "r_ITA_lag2" in lagged.columns
        assert "r_ITA_lag5" in lagged.columns
        # The pre-lagged column has the value 0.0 at every row.
        assert (lagged["r_ITA_lag1"] == 0.0).all()


# ── Information sets ────────────────────────────────────────────────────────


class TestBuildInfoSets:
    def test_nesting_F_subset_of_P_subset_of_PN_subset_of_PNG(self):
        cols = {
            PRIMARY_TARGET, *ROBUSTNESS_TARGETS,
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

    def test_N_strictly_contains_F(self):
        # Regression guard for the N-set union bug fix (decision_log
        # 2026-07-02 / real_index_integration_plan §5): N must be F + news,
        # not news-only. Use lagged column names so the F include patterns
        # actually match (F's patterns are all ``*_lag1``/``*_lag2``/etc.).
        cols = {
            "r_ITA_lag1", "vol_5d_lag1", "VIX_lag1",  # F
            "n_articles_ukrainian_lag1", "tone_ukrainian_lag1",  # N-only
            "day_of_week",  # calendar passthrough (also in F)
        }
        out = build_info_sets(cols)
        assert set(out["F"]) < set(out["N"]), (
            "N must strictly contain F (N = F + news); "
            f"F={sorted(out['F'])}, N={sorted(out['N'])}"
        )
        assert "n_articles_ukrainian_lag1" in out["N"]

    def test_excludes_target_and_raw_columns(self):
        # The target columns (``target_r_WAERLST_t1``, etc.) and the raw
        # index levels (``ITA``, ``BSHIELDT``, ``WAERLST_recon``) must NOT
        # be features. ``r_WAERLST_recon`` is demoted (decision_log
        # 2026-07-02) from target to plain feature, so its lag1
        # (``r_WAERLST_recon_lag1``) is now a legitimate F-set feature (no
        # longer excluded on leakage grounds). The primary lagged return
        # ``r_ITA_lag1`` (= r_ITA at t-1) IS a valid F feature (C5 fix)
        # and must be included.
        cols = {
            PRIMARY_TARGET, *ROBUSTNESS_TARGETS,
            f"target_{PRIMARY_TARGET}_t1",
            *[f"target_{t}_t1" for t in ROBUSTNESS_TARGETS],
            "ITA", "BSHIELDT", "WAERLST_recon",
            "r_ITA_lag1", "r_WAERLST_recon_lag1",
            "r_ITA_msadj_lag1", "vol_5d_lag1", "date",
        }
        out = build_info_sets(cols)
        for c in (
            [f"target_{PRIMARY_TARGET}_t1"]
            + [f"target_{t}_t1" for t in ROBUSTNESS_TARGETS]
            + ["ITA", "BSHIELDT", "WAERLST_recon", "date"]
        ):
            assert c not in out["F"], f"{c} in F"
            assert c not in out["PNG"], f"{c} in PNG"
        # The demoted recon feature IS allowed as an F-set feature now.
        assert "r_WAERLST_recon_lag1" in out["F"]
        # r_ITA_lag1 (= r_ITA at t-1) is a valid F feature (C5 fix).
        assert "r_ITA_lag1" in out["F"]
        assert "r_ITA_msadj_lag1" in out["F"]

    def test_financial_columns_in_F(self):
        # As of the C5 fix, the model matrix preserves the feature
        # matrix's pre-lagged return columns (``r_ITA_lag1``,
        # ``r_ITA_lag2``, ``r_ITA_lag5``) without re-shifting. The F
        # include list must use the actual column names.
        cols = {"r_ITA_lag1", "r_ITA_msadj_lag1", "vol_5d_lag1",
                "vol_20d_lag1", "VIX_lag1", "d_VIX_lag1",
                "abs_r_ITA_lag1", "r_ITA_lag2", "r_ITA_lag5", "day_of_week"}
        out = build_info_sets(cols)
        for c in ("r_ITA_lag1", "vol_5d_lag1", "day_of_week", "VIX_lag1",
                  "r_ITA_msadj_lag1", "r_ITA_lag2", "r_ITA_lag5"):
            assert c in out["F"], c

    def test_attack_columns_in_P_not_F(self):
        cols = {"r_ITA_lag1", "launched_total_lag1",
                "attack_surprise_total_7d_lag1",
                "large_attack_indicator_lag1", "day_of_week"}
        out = build_info_sets(cols)
        assert "launched_total_lag1" not in out["F"]
        assert "launched_total_lag1" in out["P"]
        assert "attack_surprise_total_7d_lag1" in out["P"]

    def test_news_columns_in_N_not_F(self):
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

    def test_recon_feature_included_in_F(self):
        # Regression guard, updated for decision_log 2026-07-02:
        # ``r_WAERLST_recon`` is demoted from target to plain feature, so
        # its lag1 (``r_WAERLST_recon_lag1``) is now a legitimate F-set
        # feature (previously excluded when it was the secondary target's
        # source). The primary lagged return ``r_ITA_lag1`` remains a
        # valid F feature (C5 fix).
        cols = {"r_ITA_lag1", "r_WAERLST_recon_lag1",
                "VIX_lag1", "day_of_week"}
        out = build_info_sets(cols)
        assert "r_WAERLST_recon_lag1" in out["F"]
        # r_ITA_lag1 IS in F (C5 fix).
        assert "r_ITA_lag1" in out["F"]


# ── Build model matrix (end-to-end) ────────────────────────────────────────


class TestBuildModelMatrix:
    def test_basic_shape(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "target_r_WAERLST_t1" in mm.columns
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
        last_target = mm["target_r_WAERLST_t1"].iloc[-1]
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

    def test_robustness_targets_present(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert "target_r_BSHIELDT_t1" in mm.columns
        assert "target_r_ITA_t1" in mm.columns
        # r_WAERLST_recon is demoted — no target column, but its lag1
        # feature must still be present.
        assert "target_r_WAERLST_recon_t1" not in mm.columns
        assert "r_WAERLST_recon_lag1" in mm.columns

    def test_no_robustness_when_disabled(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df, robustness_targets=None)
        assert "target_r_BSHIELDT_t1" not in mm.columns
        assert "target_r_ITA_t1" not in mm.columns

    def test_no_leakage_target_not_in_features(self):
        """The target column should NOT appear in any information set."""
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        info_sets = mm.attrs["info_sets"]
        primary = mm.attrs["primary_target"]
        robustness = mm.attrs.get("robustness_targets") or []
        for name, cols in info_sets.items():
            assert primary not in cols, f"target in {name}!"
            for rob in robustness:
                assert rob not in cols, f"target in {name}!"


# ── Phase 6.1 — t5 and variance targets ────────────────────────────────────


class TestCollectNNextTradingIndices:
    def test_first_three_trading_days(self):
        # 2024-01-01 is a holiday (New Year's). Next trading days are
        # Jan 2 (Tue), Jan 3 (Wed), Jan 4 (Thu).
        dates = pd.DatetimeIndex([
            "2024-01-01",  # holiday
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
        ])
        assert _collect_n_next_trading_indices(dates, 0, 3) == [1, 2, 3]
        assert _collect_n_next_trading_indices(dates, 0, 5) == [1, 2, 3, 4]
        # Not enough future days → short list
        assert _collect_n_next_trading_indices(dates, 4, 1) == []


class TestShiftToNTradingDaySum:
    def test_5day_sum_uses_only_trading_days(self):
        # Mon..Fri: 5 trading days, then 2 weekend days. At Monday (index 0)
        # the next 5 trading days are Tue..Sat's → Mon, Tue, Wed, Thu, Fri
        # (indices 1..5).  Wait — Sat and Sun are in the index but are
        # non-trading, so the walk skips them.
        dates = pd.DatetimeIndex([
            "2024-01-01",  # Mon (holiday)
            "2024-01-02",  # Tue
            "2024-01-03",  # Wed
            "2024-01-04",  # Thu
            "2024-01-05",  # Fri
            "2024-01-06",  # Sat
            "2024-01-07",  # Sun
            "2024-01-08",  # Mon
        ])
        returns = pd.Series([10.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], index=dates)
        out = _shift_to_n_trading_day_sum(returns, dates, 5)
        # From Tue (i=1): next 5 trading days are Wed, Thu, Fri, Mon, Tue
        # = 2+3+4+7+(next Tuesday not in index → too short)
        # Actually, walk from Tue (1):
        #   1st: 2 (Wed)
        #   2nd: 3 (Thu)
        #   3rd: 4 (Fri)
        #   4th: 7 (Mon)   ← skips Sat, Sun
        #   5th: -1  (out of range)
        # → not enough, NaN
        assert pd.isna(out.iloc[1])
        # From Wed (i=2): next 5 trading days: Thu, Fri, Mon, Tue (next week).
        #   Thu=3, Fri=4, Mon=7, Tue=? Not in index → not enough.
        # So Wed's t5 also NaN.
        assert pd.isna(out.iloc[2])
        # The 5-day return at the start of a long-enough window equals the
        # sum of the next 5 trading-day returns. Test on a longer window.
        dates2 = pd.date_range("2024-01-02", periods=20, freq="B")  # 20 business days
        returns2 = pd.Series(
            np.arange(20, dtype=float), index=dates2
        )
        out2 = _shift_to_n_trading_day_sum(returns2, dates2, 5)
        # First valid value: at i=0, next 5 trading days = indices 1..5
        assert out2.iloc[0] == returns2.iloc[1:6].sum()
        # Last valid value: at i=14, next 5 trading days = indices 15..19
        assert out2.iloc[14] == returns2.iloc[15:20].sum()
        # At i=15, only 4 future trading days → NaN
        assert pd.isna(out2.iloc[15])

    def test_nan_in_window_means_nan_target(self):
        dates = pd.date_range("2024-01-02", periods=20, freq="B")
        returns = pd.Series(np.arange(20, dtype=float), index=dates)
        returns.iloc[7] = np.nan  # break the window for i=2
        out = _shift_to_n_trading_day_sum(returns, dates, 5)
        # i=2's window includes index 7 → NaN
        assert pd.isna(out.iloc[2])


class TestShiftToNTradingDaySumsq:
    def test_1day_sumsq_is_squared_value(self):
        dates = pd.date_range("2024-01-02", periods=10, freq="B")
        returns = pd.Series([0.0, 1.0, -2.0, 3.0, 0.5, 1.5, -1.0, 2.0, 0.0, -0.5],
                            index=dates)
        out = _shift_to_n_trading_day_sumsq(returns, dates, 1)
        # At i=0, next trading day is i=1, value=1.0 → 1.0²=1.0
        assert out.iloc[0] == 1.0
        # At i=1, next trading day is i=2, value=-2.0 → 4.0
        assert out.iloc[1] == 4.0
        # Last row has no next trading day → NaN
        assert pd.isna(out.iloc[-1])

    def test_5day_sumsq_sums_squared_returns(self):
        dates = pd.date_range("2024-01-02", periods=20, freq="B")
        returns = pd.Series(
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,
             10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0],
            index=dates,
        )
        out = _shift_to_n_trading_day_sumsq(returns, dates, 5)
        # At i=0, next 5 trading-day values are 1,2,3,4,5 → sum of squares = 1+4+9+16+25=55
        assert out.iloc[0] == 55.0
        # At i=14, next 5 are 15,16,17,18,19 → 225+256+289+324+361 = 1455
        assert out.iloc[14] == 1455.0


class TestBuildT5AndVarianceTargets:
    def test_default_horizons_add_t1_and_t5(self):
        df = _make_master(n=30)
        targets = build_targets(df)
        assert "target_r_WAERLST_t1" in targets.columns
        assert "target_r_WAERLST_t5" in targets.columns
        assert "target_r_BSHIELDT_t1" in targets.columns
        assert "target_r_ITA_t1" in targets.columns

    def test_default_adds_variance_targets(self):
        df = _make_master(n=30)
        targets = build_targets(df)
        assert "target_var_r_WAERLST_t1" in targets.columns
        assert "target_var_r_WAERLST_t5" in targets.columns
        assert "target_var_r_BSHIELDT_t1" in targets.columns
        assert "target_var_r_ITA_t1" in targets.columns

    def test_add_variance_false_omits_variance(self):
        df = _make_master(n=30)
        targets = build_targets(df, add_variance=False)
        for c in targets.columns:
            assert not c.startswith("target_var_")

    def test_horizons_can_be_customised(self):
        df = _make_master(n=30)
        targets = build_targets(df, horizons=(1, 3, 5))
        for h in (1, 3, 5):
            assert f"target_r_WAERLST_t{h}" in targets.columns
            assert f"target_var_r_WAERLST_t{h}" in targets.columns
        assert "target_r_WAERLST_t2" not in targets.columns
        assert "target_r_WAERLST_t10" not in targets.columns

    def test_horizons_invalid_raises(self):
        df = _make_master(n=30)
        with pytest.raises(ValueError, match="horizons"):
            build_targets(df, horizons=())
        with pytest.raises(ValueError, match="horizons"):
            build_targets(df, horizons=(0, 1))

    def test_t5_target_is_sum_of_next_5_trading_returns(self):
        # Build a small fixture where we know the next 5 trading-day returns.
        dates = pd.date_range("2024-01-02", periods=20, freq="B")
        r_waerlst = pd.Series(np.arange(20, dtype=float), index=dates, name="r_WAERLST")
        df = _make_master(
            n=20, r_waerlst=list(r_waerlst.values)
        )
        # Override dates to business days
        df["date"] = dates
        targets = build_targets(df)
        # At i=0, the next 5 trading-day returns are r_WAERLST[1:6] = [1,2,3,4,5]
        # → sum = 15.0
        assert targets["target_r_WAERLST_t5"].iloc[0] == 15.0
        # At i=14, next 5 are r_WAERLST[15:20] = [15,16,17,18,19] → sum = 85
        assert targets["target_r_WAERLST_t5"].iloc[14] == 85.0
        # At i=15..19, not enough future trading days → NaN
        for i in (15, 16, 17, 18, 19):
            assert pd.isna(targets["target_r_WAERLST_t5"].iloc[i])

    def test_variance_t1_is_squared_next_return(self):
        dates = pd.date_range("2024-01-02", periods=10, freq="B")
        r_waerlst = pd.Series([0.0, 1.0, -2.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                          index=dates)
        df = _make_master(n=10, r_waerlst=list(r_waerlst.values))
        df["date"] = dates
        targets = build_targets(df)
        # At i=0, next trading day is i=1 → 1.0² = 1.0
        assert targets["target_var_r_WAERLST_t1"].iloc[0] == 1.0
        # At i=1, next trading day is i=2 → (-2.0)² = 4.0
        assert targets["target_var_r_WAERLST_t1"].iloc[1] == 4.0


class TestBuildModelMatrixPhase6:
    def test_model_matrix_includes_t5_and_variance_columns(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        for c in (
            "target_r_WAERLST_t1", "target_r_WAERLST_t5",
            "target_r_BSHIELDT_t1", "target_r_BSHIELDT_t5",
            "target_r_ITA_t1", "target_r_ITA_t5",
            "target_var_r_WAERLST_t1", "target_var_r_WAERLST_t5",
        ):
            assert c in mm.columns, f"missing {c}"

    def test_attrs_record_horizons_and_variance(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        assert mm.attrs["horizons"] == [1, 5]
        assert mm.attrs["add_variance_targets"] is True

    def test_variance_targets_not_in_any_info_set(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        info_sets = mm.attrs["info_sets"]
        for set_name, cols in info_sets.items():
            for c in cols:
                assert not c.startswith("target_var_"), (
                    f"variance target {c} leaked into {set_name} set!"
                )
                assert not c.startswith("target_r_"), (
                    f"return target {c} leaked into {set_name} set!"
                )

    def test_t5_disabled_when_horizons_single(self):
        df = _make_master(n=30)
        mm = build_model_matrix(df, horizons=(1,), add_variance_targets=False)
        assert "target_r_WAERLST_t1" in mm.columns
        assert "target_r_WAERLST_t5" not in mm.columns
        for c in mm.columns:
            assert not c.startswith("target_var_")

    def test_extra_variance_column_count(self):
        # With primary + 2 robustness targets × {t1, t5} × {return, variance}
        # = 3 targets × 2 horizons × 2 (return + variance) = 12 target
        # columns (decision_log 2026-07-02: 3-target hierarchy replaces the
        # old primary+secondary 2-target pattern).
        df = _make_master(n=30)
        mm = build_model_matrix(df)
        target_cols = [c for c in mm.columns if c.startswith("target_")]
        assert len(target_cols) == 12
        # Specifically:
        for c in (
            "target_r_WAERLST_t1", "target_r_WAERLST_t5",
            "target_r_BSHIELDT_t1", "target_r_BSHIELDT_t5",
            "target_r_ITA_t1", "target_r_ITA_t5",
            "target_var_r_WAERLST_t1", "target_var_r_WAERLST_t5",
            "target_var_r_BSHIELDT_t1", "target_var_r_BSHIELDT_t5",
            "target_var_r_ITA_t1", "target_var_r_ITA_t5",
        ):
            assert c in target_cols


# ── Train/test split ───────────────────────────────────────────────────────


class TestMakeTrainTestSplit:
    def _make_long_master(self, n: int = 100) -> pd.DataFrame:
        return _make_master(n=n)

    def test_default_split_75_25(self):
        df = self._make_long_master(n=100)
        mm = build_model_matrix(df)
        train_mask, test_mask, split_date = make_train_test_split(
            mm, min_train_obs=50
        )
        # Note: build_model_matrix drops rows where target is NaN; the
        # resulting length is at most n. After modeling_start filtering the
        # exact count varies — assert the ratio and chronologicality, not
        # the exact 75/25 split.
        assert train_mask.sum() > 0
        assert test_mask.sum() > 0
        assert (train_mask & test_mask).sum() == 0
        # The fraction of test rows is within 1 row of the requested 25%.
        test_frac = test_mask.sum() / len(mm)
        assert abs(test_frac - 0.25) < 0.02
        # split_date is the first date in the test set
        first_test_idx = int(np.argmax(~train_mask))
        assert split_date == mm["date"].iloc[first_test_idx]

    def test_split_is_chronological(self):
        df = self._make_long_master(n=200)
        mm = build_model_matrix(df)
        train_mask, test_mask, _ = make_train_test_split(
            mm, test_fraction=0.3, min_train_obs=100
        )
        # All train dates strictly precede all test dates
        train_max = mm.loc[train_mask, "date"].max()
        test_min = mm.loc[test_mask, "date"].min()
        assert train_max < test_min

    def test_min_train_obs_enforced(self):
        df = self._make_long_master(n=20)
        mm = build_model_matrix(df)
        with pytest.raises(ValueError, match="min_train_obs"):
            make_train_test_split(mm, test_fraction=0.25, min_train_obs=500)

    def test_invalid_test_fraction_raises(self):
        df = self._make_long_master(n=100)
        mm = build_model_matrix(df)
        with pytest.raises(ValueError, match="test_fraction"):
            make_train_test_split(mm, test_fraction=0.0, min_train_obs=10)
        with pytest.raises(ValueError, match="test_fraction"):
            make_train_test_split(mm, test_fraction=1.0, min_train_obs=10)

    def test_custom_test_fraction(self):
        df = self._make_long_master(n=200)
        mm = build_model_matrix(df)
        train_mask, test_mask, split_date = make_train_test_split(
            mm, test_fraction=0.2, min_train_obs=100
        )
        # ceil(n * 0.2) test rows where n is the actual length of mm
        expected_test = int(np.ceil(len(mm) * 0.2))
        assert test_mask.sum() == expected_test
        assert train_mask.sum() == len(mm) - expected_test
        assert split_date == mm["date"].iloc[-expected_test]

    def test_split_date_actually_appears_in_test(self):
        df = self._make_long_master(n=100)
        mm = build_model_matrix(df)
        train_mask, test_mask, split_date = make_train_test_split(
            mm, min_train_obs=50
        )
        # The split date is the first date in the test block.
        assert (mm.loc[test_mask, "date"] == split_date).any()
        # No train row equals the split date.
        assert not (mm.loc[train_mask, "date"] == split_date).any()
