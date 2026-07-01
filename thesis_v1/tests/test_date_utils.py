"""Tests for ``src.utils.date_utils``."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.utils.date_utils import (
    US_FEDERAL_HOLIDAYS,
    build_calendar_index,
    is_trading_day,
    shift_to_next_trading_day,
    standardize_date_column,
)


class TestStandardizeDateColumn:
    def test_from_named_datetime_index(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=idx)
        df.index.name = "date"
        out = standardize_date_column(df)
        assert "date" in out.columns
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert list(out["date"]) == list(idx)
        assert list(out["value"]) == [1, 2, 3, 4, 5]

    def test_from_unnamed_datetime_index(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=idx)
        # Index is intentionally unnamed
        out = standardize_date_column(df)
        assert "date" in out.columns
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert len(out) == 5

    def test_from_int_yyyymmdd_column(self):
        # news_query_group_pivot uses int YYYYMMDD — this is the critical case.
        df = pd.DataFrame(
            {
                "date": [20220929, 20220930, 20221001, 20221002],
                "value": [1, 2, 3, 4],
            }
        )
        out = standardize_date_column(df)
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert out["date"].iloc[0] == pd.Timestamp("2022-09-29")
        assert out["date"].iloc[3] == pd.Timestamp("2022-10-02")

    def test_custom_int_format(self):
        df = pd.DataFrame({"date": [220929, 220930], "value": [1, 2]})
        out = standardize_date_column(df, int_format="%y%m%d")
        assert out["date"].iloc[0] == pd.Timestamp("2022-09-29")
        assert out["date"].iloc[1] == pd.Timestamp("2022-09-30")

    def test_from_string_column(self):
        df = pd.DataFrame(
            {"date": ["2024-01-01", "2024-01-02"], "value": [1, 2]}
        )
        out = standardize_date_column(df)
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert out["date"].iloc[0] == pd.Timestamp("2024-01-01")

    def test_already_datetime_is_noop(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "value": [1, 2],
            }
        )
        out = standardize_date_column(df)
        assert pd.api.types.is_datetime64_any_dtype(out["date"])
        assert out["date"].iloc[0] == pd.Timestamp("2024-01-01")

    def test_missing_raises(self):
        df = pd.DataFrame({"value": [1, 2, 3]})
        with pytest.raises(ValueError, match="not found"):
            standardize_date_column(df)

    def test_does_not_mutate_input(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({"value": [1, 2, 3]}, index=idx)
        df.index.name = "date"
        _ = standardize_date_column(df)
        # The original df's index should still be a DatetimeIndex named "date".
        assert df.index.name == "date"
        assert isinstance(df.index, pd.DatetimeIndex)


class TestBuildCalendarIndex:
    def test_basic_length(self):
        idx = build_calendar_index("2024-01-01", "2024-01-07")
        assert len(idx) == 7
        assert idx[0] == pd.Timestamp("2024-01-01")
        assert idx[-1] == pd.Timestamp("2024-01-07")

    def test_inclusive_single_day(self):
        idx = build_calendar_index("2024-01-01", "2024-01-01")
        assert len(idx) == 1
        assert idx[0] == pd.Timestamp("2024-01-01")

    def test_one_month_has_31_days(self):
        idx = build_calendar_index("2024-01-01", "2024-01-31")
        assert len(idx) == 31

    def test_returns_datetime_index(self):
        idx = build_calendar_index("2024-01-01", "2024-01-07")
        assert isinstance(idx, pd.DatetimeIndex)

    def test_date_inputs(self):
        idx = build_calendar_index(date(2024, 1, 1), date(2024, 1, 3))
        assert len(idx) == 3

    def test_business_day_freq(self):
        idx = build_calendar_index("2024-01-01", "2024-01-31", freq="B")
        # 2024-01-01 is a US holiday, 22 business days in Jan 2024
        assert all(d.weekday() < 5 for d in idx)


class TestIsTradingDay:
    def test_monday_is_trading_day(self):
        # 2024-01-08 is a Monday (Jan 1 is a holiday)
        assert is_trading_day(date(2024, 1, 8)) is True

    def test_friday_is_trading_day(self):
        assert is_trading_day(date(2024, 1, 5)) is True

    def test_saturday_is_not(self):
        assert is_trading_day(date(2024, 1, 6)) is False

    def test_sunday_is_not(self):
        assert is_trading_day(date(2024, 1, 7)) is False

    def test_new_years_day_is_not(self):
        # 2024-01-01 is a Monday but a US federal holiday
        assert is_trading_day(date(2024, 1, 1)) is False

    def test_july_4th_is_not(self):
        assert is_trading_day(date(2024, 7, 4)) is False

    def test_christmas_is_not(self):
        assert is_trading_day(date(2024, 12, 25)) is False

    def test_holidays_none_treats_new_years_as_trading(self):
        assert is_trading_day(date(2024, 1, 1), holidays=None) is True

    def test_custom_holidays(self):
        custom = {date(2024, 1, 2)}
        assert is_trading_day(date(2024, 1, 2), holidays=custom) is False
        # A different day is unaffected
        assert is_trading_day(date(2024, 1, 3), holidays=custom) is True

    def test_accepts_timestamp(self):
        assert is_trading_day(pd.Timestamp("2024-01-01")) is False
        assert is_trading_day(pd.Timestamp("2024-01-02")) is True

    def test_accepts_string(self):
        assert is_trading_day("2024-01-01") is False
        assert is_trading_day("2024-01-02") is True


class TestShiftToNextTradingDay:
    def test_weekday_returns_same_day(self):
        d = date(2024, 1, 2)  # Tuesday, not a holiday
        assert shift_to_next_trading_day(d) == d

    def test_holiday_weekday_skips_forward(self):
        # 2024-01-01 (Mon, holiday) → 2024-01-02 (Tue)
        d = date(2024, 1, 1)
        assert shift_to_next_trading_day(d) == date(2024, 1, 2)

    def test_saturday_returns_monday(self):
        d = date(2024, 1, 6)  # Saturday
        assert shift_to_next_trading_day(d) == date(2024, 1, 8)  # Monday

    def test_sunday_returns_monday(self):
        d = date(2024, 1, 7)  # Sunday
        assert shift_to_next_trading_day(d) == date(2024, 1, 8)  # Monday

    def test_friday_returns_friday(self):
        d = date(2024, 1, 5)  # Friday, not a holiday
        assert shift_to_next_trading_day(d) == d

    def test_holiday_weekday_skips_to_next_weekday(self):
        # 2025-01-01 is a Wednesday (New Year's Day, holiday).
        # The next trading day is Thursday 2025-01-02.
        d = date(2025, 1, 1)
        assert shift_to_next_trading_day(d) == date(2025, 1, 2)

    def test_friday_returns_friday_not_shifted(self):
        # 2024-12-27 is a Friday — already a trading day, should not shift.
        d = date(2024, 12, 27)
        assert shift_to_next_trading_day(d) == date(2024, 12, 27)

    def test_accepts_string(self):
        assert shift_to_next_trading_day("2024-01-06") == date(2024, 1, 8)


class TestUSFederalHolidays:
    def test_is_a_set(self):
        assert isinstance(US_FEDERAL_HOLIDAYS, set)
        assert all(isinstance(d, date) for d in US_FEDERAL_HOLIDAYS)

    def test_covers_phase5_window(self):
        # Phase 5 modeling window spans 2022-09-29 → 2026-06-21.
        # Federal holidays that fall on a weekend are *observed* on the
        # adjacent weekday (e.g. 2022-12-25 was Sunday, so the NYSE observed
        # Christmas on Monday 2022-12-26).
        for year in (2023, 2024, 2025, 2026):
            assert date(year, 12, 25) in US_FEDERAL_HOLIDAYS
        # 2022-12-25 was Sunday → observed on Monday 2022-12-26.
        assert date(2022, 12, 26) in US_FEDERAL_HOLIDAYS
        # 2023-01-01 was Sunday → observed on Monday 2023-01-02.
        assert date(2023, 1, 2) in US_FEDERAL_HOLIDAYS
        # 2024 / 2025 / 2026 — Jan 1 falls on a weekday.
        for year in (2024, 2025, 2026):
            assert date(year, 1, 1) in US_FEDERAL_HOLIDAYS
