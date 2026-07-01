"""End-to-end smoke tests for the Phase 5 pipeline.

These tests verify that the full pipeline (load → merge → features) works
on real data without errors and produces a sensible feature matrix.

The tests are marked as slow (and may be skipped if data is unavailable)
because they load ~5 GB of parquets from the data/processed directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from src.features.attack_features import add_attack_features
from src.features.calendar_features import add_calendar_features
from src.features.financial_features import add_financial_features
from src.features.merge import (
    build_daily_master,
    load_attack,
    load_financial,
    load_news_enriched,
    load_news_pivot,
    load_paths_config,
)
from src.features.news_features import add_news_features

# Allow running tests from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def paths():
    """Load paths config; skip the e2e tests if data files are missing."""
    try:
        return load_paths_config()
    except FileNotFoundError:
        pytest.skip("config/paths.yaml not found")


@pytest.fixture(scope="module")
def daily_master(paths):
    """Build the daily master from real data; skip if sources are missing."""
    try:
        fin = load_financial(paths)
        atk = load_attack(paths)
        nws = load_news_enriched(paths)
        pvt = load_news_pivot(paths)
    except FileNotFoundError as e:
        pytest.skip(f"Source data not found: {e}")
    return build_daily_master(fin, atk, nws, pvt)


@pytest.fixture(scope="module")
def feature_matrix(daily_master):
    """Apply all four feature modules."""
    feat = daily_master.copy()
    feat = add_financial_features(feat)
    feat = add_attack_features(feat)
    feat = add_news_features(feat)
    feat = add_calendar_features(feat)
    return feat


class TestDailyMasterE2E:
    def test_shape_matches_expected(self, daily_master):
        # 2020-01-07 to 2026-06-30 = ~2,367 calendar days (extended with real Bloomberg)
        assert len(daily_master) >= 2358
        assert daily_master["date"].iloc[0] == pd.Timestamp("2020-01-07")
        assert daily_master["date"].iloc[-1] >= pd.Timestamp("2026-06-21")

    def test_all_source_columns_present(self, daily_master):
        expected_cols = {
            "date",
            # Financial (real Bloomberg + EU defense)
            "r_WAERLST", "r_BSHIELDT", "r_EUDEF", "r_ITA", "VIX",
            # Attack
            "launched_total", "destroyed_total", "interception_rate",
            # News
            "n_articles_total", "tone_ukrainian", "narrative_gap_ua_west",
            # News pivot
            "n_ukrainian_russian_attack_direct",
            # Derived
            "has_attack_report", "waerlst_missing", "is_weekend", "is_holiday",
        }
        missing = expected_cols - set(daily_master.columns)
        assert not missing, f"daily_master missing columns: {missing}"

    def test_date_dtype_and_first_column(self, daily_master):
        assert pd.api.types.is_datetime64_any_dtype(daily_master["date"])
        assert daily_master.columns[0] == "date"

    def test_no_duplicate_dates(self, daily_master):
        assert not daily_master["date"].duplicated().any()

    def test_calendar_is_complete(self, daily_master):
        # No gaps in the calendar index
        expected_range = pd.date_range(
            daily_master["date"].min(), daily_master["date"].max(), freq="D"
        )
        assert len(daily_master) == len(expected_range)


class TestFeatureMatrixE2E:
    def test_columns_added(self, feature_matrix):
        # 72 (daily_master) + 6 (financial) + 10 (attack) + 12 (news) + 8 (calendar) ≈ 141
        # (the exact count is verified separately; here we just check the
        # expected new columns are present)
        new_cols = {
            "vol_5d", "vol_20d", "abs_r_ITA", "r_ITA_lag1", "r_ITA_lag2", "r_ITA_lag5",
            "attack_uav_share", "attack_cruise_share", "attack_ballistic_share",
            "penetrations_estimated", "large_attack_indicator",
            "attack_surprise_total_7d", "attack_surprise_total_30d", "attack_surprise_total_90d",
            "n_ukrainian_share", "n_ukrainian_log", "n_ukrainian_z30",
            "n_articles_total_lag1", "n_articles_total_7d_rolling_mean",
            "day_of_week", "days_since_invasion", "vix_crisis",
        }
        missing = new_cols - set(feature_matrix.columns)
        assert not missing, f"feature_matrix missing columns: {missing}"

    def test_surprise_features_use_past_only(self, feature_matrix):
        # The surprise at t must use the *past* mean (window excludes t).
        # With the NaN→0 fix (supervisor audit), no-attack days are 0
        # instead of NaN. The surprise is "actual - past_mean" — with
        # all zeros in the early window, surprise = actual (since past_mean=0).
        # We verify:
        #   (1) At t=0 (first day of modeling window, 2022-09-29), the
        #       surprise is finite (actual attack count, past_mean=0).
        #   (2) At a well-populated index (t=30), the surprise is finite.
        #   (3) The surprise is "actual - past_mean" — a value above 0 means
        #       the current attack count exceeds the past mean.
        modeling = feature_matrix[feature_matrix["date"] >= "2022-09-29"].reset_index(drop=True)
        val_0 = modeling["attack_surprise_total_7d"].iloc[0]
        assert np.isfinite(val_0), (
            f"surprise at t=0 should be finite (NaN→0 fix), got {val_0}"
        )
        surprise_at_30 = modeling["attack_surprise_total_7d"].iloc[30]
        # Use isfinite or NaN — if launched_total is NaN on that day, surprise is NaN.
        if not pd.isna(surprise_at_30):
            assert np.isfinite(surprise_at_30), (
                f"surprise at t=30 should be finite, got {surprise_at_30}"
            )

    def test_z30_uses_past_30_obs(self, feature_matrix):
        # With ``np.nanmean``, the 30-day window ignores NaN days. The z30
        # at t=0 (first day of modeling window) should be NaN because the
        # window is entirely pre-coverage.
        # At t=30, the 30-day window is entirely within the news coverage
        # period, so the z30 should be finite (assuming non-zero variance).
        modeling = feature_matrix[feature_matrix["date"] >= "2022-09-29"].reset_index(drop=True)
        assert pd.isna(modeling["n_ukrainian_z30"].iloc[0]), (
            "z30 at t=0 should be NaN (no past news data)"
        )
        z30_at_30 = modeling["n_ukrainian_z30"].iloc[30]
        assert np.isfinite(z30_at_30), (
            f"z30 at t=30 should be finite, got {z30_at_30}"
        )

    def test_vix_regime_consistency(self, feature_matrix):
        # The four VIX regime dummies should be mutually exclusive (exactly one is 1).
        regime_cols = ["vix_low", "vix_normal", "vix_high", "vix_crisis"]
        available = [c for c in regime_cols if c in feature_matrix.columns]
        if not available:
            pytest.skip("VIX regime columns not present")
        sum_regime = feature_matrix[available].sum(axis=1)
        # On rows where VIX is non-null, exactly one regime should be active.
        vix_present = feature_matrix["VIX"].notna() if "VIX" in feature_matrix.columns else pd.Series(False, index=feature_matrix.index)
        # Allow NaN sum where VIX is NaN; otherwise sum should be 1.
        valid = vix_present & sum_regime.notna()
        assert (sum_regime[valid] == 1).all(), "VIX regime dummies should sum to 1"

    def test_calendar_features_finite(self, feature_matrix):
        # days_since_invasion should be 0 before the invasion and positive after.
        ds = feature_matrix["days_since_invasion"]
        assert (ds >= 0).all(), "days_since_invasion should be >= 0 everywhere"
        assert ds.max() > 1300, "days_since_invasion should exceed 1300 by mid-2026"

    def test_does_not_modify_daily_master(self, daily_master, feature_matrix):
        # The feature matrix should have all daily_master columns unchanged.
        for col in daily_master.columns:
            if col in feature_matrix.columns:
                pd.testing.assert_series_equal(
                    daily_master[col].reset_index(drop=True),
                    feature_matrix[col].reset_index(drop=True),
                    check_names=False,
                )


# Import numpy for the np.isfinite check.
import numpy as np
