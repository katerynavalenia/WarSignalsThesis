"""Tests for ``src.features.merge`` — Phase 5B daily-master builder."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.features.merge import (
    build_daily_master,
    load_attack,
    load_financial,
    load_news_enriched,
    load_news_pivot,
    load_paths_config,
)
from src.utils.date_utils import standardize_date_column


# ── Synthetic fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def fin():
    """5 trading days of financial data (M–F)."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    df = pd.DataFrame(
        {
            "date": dates,
            "ITA": [100.0, 101.0, 102.0, 103.0, 104.0],
            "r_ITA": [0.0, 1.0, 1.0, 1.0, 1.0],
            "r_WAERLST_recon": [0.5, 0.6, np.nan, 0.8, 0.9],  # one NaN to test the flag
            "VIX": [15.0, 16.0, 17.0, 18.0, 19.0],
        }
    )
    return df


@pytest.fixture
def atk():
    """3 attack days, with one gap day (2024-01-04 has no attack)."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-05"])
    df = pd.DataFrame(
        {
            "date": dates,
            "launched_total": [10, 20, 30, 50],
            "destroyed_total": [8, 18, 25, 45],
        }
    )
    return df


@pytest.fixture
def nws():
    """3 news days."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    df = pd.DataFrame(
        {
            "date": dates,
            "n_articles_total": [100, 200, 300],
            "tone_ukrainian": [-2.0, -3.0, -1.0],
        }
    )
    return df


@pytest.fixture
def pvt():
    """News query×group pivot with int YYYYMMDD dates (the bug case).
    Standardized like the production loader would do.
    """
    df = pd.DataFrame(
        {
            "date": [20240101, 20240102, 20240103],
            "n_ukrainian_russian_attack_direct": [5, 10, 15],
            "n_western_russian_attack_direct": [50, 60, 70],
        }
    )
    return standardize_date_column(df, int_format="%Y%m%d")


# ── Tests ───────────────────────────────────────────────────────────────────


class TestBuildDailyMaster:
    def test_calendar_creates_one_row_per_day(self, fin, atk, nws, pvt):
        master = build_daily_master(
            fin, atk, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        # 5 calendar days
        assert len(master) == 5
        assert list(master["date"]) == list(pd.date_range("2024-01-01", "2024-01-05"))

    def test_calendar_start_only_uses_default(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        # Default calendar_start = 2020-01-07; but fin starts 2024-01-01 which is later.
        # Since fin's min is 2024-01-01 < default 2020-01-07, the default is used.
        # Result: starts at 2020-01-07 — but our synthetic data only covers 2024.
        # So financial/attack/news will be NaN, but the calendar should still start 2020-01-07.
        assert master["date"].min() == pd.Timestamp("2020-01-07")
        assert master["date"].max() == pd.Timestamp("2024-01-03")

    def test_int_yyyymmdd_date_is_cast(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        # The pivot's int 20240101 should appear as a datetime in the merge.
        assert pd.api.types.is_datetime64_any_dtype(master["date"])
        # The pivot column should have non-NaN values for the 3 covered days.
        for d in ("2024-01-01", "2024-01-02", "2024-01-03"):
            row = master[master["date"] == pd.Timestamp(d)].iloc[0]
            assert not pd.isna(row["n_ukrainian_russian_attack_direct"])

    def test_financial_columns_present(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        for col in ("ITA", "r_ITA", "VIX"):
            assert col in master.columns

    def test_attack_columns_present_with_nan_on_no_attack_days(self, fin, atk, nws, pvt):
        master = build_daily_master(
            fin, atk, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        # Attack column should exist
        assert "launched_total" in master.columns
        # 2024-01-04 has no attack in the fixture → NaN
        row = master[master["date"] == pd.Timestamp("2024-01-04")].iloc[0]
        assert pd.isna(row["launched_total"])
        # 2024-01-01 has an attack → 10
        row = master[master["date"] == pd.Timestamp("2024-01-01")].iloc[0]
        assert row["launched_total"] == 10

    def test_news_pivot_columns_present(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        for col in ("n_ukrainian_russian_attack_direct", "n_western_russian_attack_direct"):
            assert col in master.columns

    def test_waerlst_missing_flag(self, fin, atk, nws, pvt):
        master = build_daily_master(
            fin, atk, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        assert "waerlst_missing" in master.columns
        # Fixture: 2024-01-03 has r_WAERLST_recon=NaN → flag=1
        row = master[master["date"] == pd.Timestamp("2024-01-03")].iloc[0]
        assert row["waerlst_missing"] == 1
        # 2024-01-01 has a value → flag=0
        row = master[master["date"] == pd.Timestamp("2024-01-01")].iloc[0]
        assert row["waerlst_missing"] == 0

    def test_is_weekend_flag(self, fin, atk, nws, pvt):
        master = build_daily_master(
            fin, atk, nws, pvt, calendar_start="2024-01-05", calendar_end="2024-01-08"
        )
        # 2024-01-05 = Friday, 2024-01-06 = Saturday, 2024-01-07 = Sunday, 2024-01-08 = Monday
        assert master[master["date"] == pd.Timestamp("2024-01-05")].iloc[0]["is_weekend"] == 0
        assert master[master["date"] == pd.Timestamp("2024-01-06")].iloc[0]["is_weekend"] == 1
        assert master[master["date"] == pd.Timestamp("2024-01-07")].iloc[0]["is_weekend"] == 1
        assert master[master["date"] == pd.Timestamp("2024-01-08")].iloc[0]["is_weekend"] == 0

    def test_is_holiday_flag(self, fin, atk, nws, pvt):
        master = build_daily_master(
            fin, atk, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        # 2024-01-01 = New Year's Day (Monday, observed)
        row = master[master["date"] == pd.Timestamp("2024-01-01")].iloc[0]
        assert row["is_holiday"] == 1
        # 2024-01-02 = Tuesday, not a holiday
        row = master[master["date"] == pd.Timestamp("2024-01-02")].iloc[0]
        assert row["is_holiday"] == 0

    def test_date_is_first_column(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        assert master.columns[0] == "date"

    def test_sorted_ascending(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        assert master["date"].is_monotonic_increasing

    def test_index_is_default_range(self, fin, atk, nws, pvt):
        master = build_daily_master(fin, atk, nws, pvt, calendar_end="2024-01-03")
        # Per 2026-06-30 decision, `date` is a regular column, not the index.
        assert master.index.name is None
        assert isinstance(master.index, pd.RangeIndex)

    def test_column_collision_raises(self, fin, atk, nws, pvt):
        # Add a column to nws that collides with one in atk.
        nws_collide = nws.copy()
        nws_collide["launched_total"] = 999  # collision with atk
        with pytest.raises(ValueError, match="Column collision"):
            build_daily_master(fin, atk, nws_collide, pvt, calendar_end="2024-01-03")

    def test_duplicate_dates_in_source_deduped(self, fin, atk, nws, pvt):
        # Duplicate a row in atk
        atk_dup = pd.concat([atk, atk.iloc[[0]]], ignore_index=True)
        # Should not raise and should keep the last duplicate.
        master = build_daily_master(
            fin, atk_dup, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        assert len(master) == 5
        # The first date (2024-01-01) should have the attack value (10, from the
        # original row, since `keep="last"` is the same here).
        row = master[master["date"] == pd.Timestamp("2024-01-01")].iloc[0]
        assert row["launched_total"] == 10

    def test_waerlst_missing_handles_missing_column(self, fin, atk, nws, pvt):
        # Drop the WAERLST column from fin — flag should be all 1s.
        fin_no_waerlst = fin.drop(columns=["r_WAERLST_recon"])
        master = build_daily_master(
            fin_no_waerlst, atk, nws, pvt, calendar_start="2024-01-01", calendar_end="2024-01-05"
        )
        assert master["waerlst_missing"].sum() == 5


class TestLoadPathsConfig:
    def test_loads_default(self):
        cfg = load_paths_config()
        assert "data" in cfg
        assert "processed" in cfg["data"]
        assert "daily_master" in cfg["processed_files"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="paths config not found"):
            load_paths_config(tmp_path / "nonexistent.yaml")


class TestLoaders:
    """End-to-end loader tests using the real data files."""

    def test_load_financial(self):
        cfg = load_paths_config()
        df = load_financial(cfg)
        assert "date" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert "r_ITA" in df.columns
        assert len(df) == 1610

    def test_load_attack(self):
        cfg = load_paths_config()
        df = load_attack(cfg)
        assert "date" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert "launched_total" in df.columns
        assert len(df) == 809

    def test_load_news_enriched(self):
        cfg = load_paths_config()
        df = load_news_enriched(cfg)
        assert "date" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert "n_articles_total" in df.columns
        assert len(df) == 1342

    def test_load_news_pivot_casts_category_to_datetime(self):
        """The pivot's `date` is category-of-strings in YYYYMMDD; loader
        must cast it to datetime64[ns]."""
        cfg = load_paths_config()
        df = load_news_pivot(cfg)
        assert "date" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert len(df) == 1342
        # Spot-check: first date should be 2022-09-29.
        assert df["date"].iloc[0] == pd.Timestamp("2022-09-29")
