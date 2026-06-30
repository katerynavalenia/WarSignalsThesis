"""Tests for ``src.features.calendar_features``."""
import numpy as np
import pandas as pd
import pytest

from src.features.calendar_features import (
    INVASION_DATE,
    VIX_THRESHOLDS,
    add_calendar_features,
)


def _minimal_master(dates, vix=None):
    df = {"date": pd.to_datetime(dates)}
    if vix is not None:
        df["VIX"] = vix
    return pd.DataFrame(df)


class TestAddCalendarFeatures:
    def test_day_of_week_monday_is_zero(self):
        master = _minimal_master(["2024-01-01"])  # Monday
        out = add_calendar_features(master)
        assert out["day_of_week"].iloc[0] == 0

    def test_day_of_week_sunday_is_six(self):
        master = _minimal_master(["2024-01-07"])  # Sunday
        out = add_calendar_features(master)
        assert out["day_of_week"].iloc[0] == 6

    def test_day_of_month(self):
        master = _minimal_master(["2024-01-15", "2024-02-29", "2024-12-31"])
        out = add_calendar_features(master)
        assert list(out["day_of_month"]) == [15, 29, 31]

    def test_month(self):
        master = _minimal_master(["2024-01-15", "2024-06-15", "2024-12-15"])
        out = add_calendar_features(master)
        assert list(out["month"]) == [1, 6, 12]

    def test_quarter(self):
        master = _minimal_master(["2024-01-15", "2024-04-15", "2024-07-15", "2024-10-15"])
        out = add_calendar_features(master)
        assert list(out["quarter"]) == [1, 2, 3, 4]

    def test_is_month_start(self):
        master = _minimal_master(["2024-01-01", "2024-01-02", "2024-02-01"])
        out = add_calendar_features(master)
        assert list(out["is_month_start"]) == [1, 0, 1]

    def test_is_month_end(self):
        # 2024 is a leap year, so Feb 29 is month-end (Feb 28 is not).
        master = _minimal_master(["2024-01-31", "2024-02-28", "2024-02-29", "2024-03-31"])
        out = add_calendar_features(master)
        assert list(out["is_month_end"]) == [1, 0, 1, 1]
        # 2023 (non-leap) — Feb 28 IS month-end.
        master23 = _minimal_master(["2023-01-31", "2023-02-28", "2023-03-31"])
        out23 = add_calendar_features(master23)
        assert list(out23["is_month_end"]) == [1, 1, 1]

    def test_is_quarter_end(self):
        master = _minimal_master(["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31", "2024-01-31"])
        out = add_calendar_features(master)
        assert list(out["is_quarter_end"]) == [1, 1, 1, 1, 0]

    def test_days_since_invasion_positive_after(self):
        master = _minimal_master(["2022-02-24", "2022-03-01", "2023-02-24"])
        out = add_calendar_features(master)
        # On the invasion date itself → 0
        assert out["days_since_invasion"].iloc[0] == 0
        # 5 days after → 5
        assert out["days_since_invasion"].iloc[1] == 5
        # 1 year after → 365
        assert out["days_since_invasion"].iloc[2] == 365

    def test_days_since_invasion_clamped_pre_invasion(self):
        # Pre-invasion dates should be clamped to 0, not negative.
        master = _minimal_master(["2020-01-01", "2021-06-15", "2022-02-23"])
        out = add_calendar_features(master)
        assert out["days_since_invasion"].iloc[0] == 0
        assert out["days_since_invasion"].iloc[1] == 0
        assert out["days_since_invasion"].iloc[2] == 0

    def test_vix_regime_dummies(self):
        lo, mid, hi = VIX_THRESHOLDS
        vix = [lo - 1, (lo + mid) / 2, (mid + hi) / 2, hi + 5]
        master = _minimal_master(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"], vix=vix)
        out = add_calendar_features(master)
        assert list(out["vix_low"]) == [1, 0, 0, 0]
        assert list(out["vix_normal"]) == [0, 1, 0, 0]
        assert list(out["vix_high"]) == [0, 0, 1, 0]
        assert list(out["vix_crisis"]) == [0, 0, 0, 1]

    def test_vix_dummies_skipped_when_no_vix_column(self):
        master = _minimal_master(["2024-01-01"])
        out = add_calendar_features(master)
        # No VIX → no dummies
        assert "vix_low" not in out.columns
        assert "vix_normal" not in out.columns
        # But other calendar features should be present
        assert "day_of_week" in out.columns

    def test_does_not_mutate_input(self):
        master = _minimal_master(["2024-01-01", "2024-01-02"])
        original_cols = list(master.columns)
        _ = add_calendar_features(master)
        assert list(master.columns) == original_cols

    def test_invasion_date_constant(self):
        assert INVASION_DATE == "2022-02-24"
