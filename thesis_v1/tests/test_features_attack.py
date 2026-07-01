"""Tests for ``src.features.attack_features``."""
import numpy as np
import pandas as pd
import pytest

from src.features.attack_features import (
    SURPRISE_SERIES,
    SURPRISE_WINDOWS,
    add_attack_features,
    compute_attack_surprise_ar1,
)


def _master_with_attacks(launched: list[float], start: str = "2022-10-01") -> pd.DataFrame:
    """Minimal master with attack columns. All other columns are 0/NaN."""
    n = len(launched)
    return pd.DataFrame(
        {
            "date": pd.date_range(start, periods=n, freq="D"),
            "launched_total": launched,
            "launched_uav": [l * 0.5 for l in launched],
            "launched_cruise_missile": [l * 0.2 for l in launched],
            "launched_ballistic_missile": [l * 0.1 for l in launched],
            "launched_recon_uav": [0.0] * n,
            "launched_loitering_munition": [0.0] * n,
            "launched_guided_bomb": [0.0] * n,
            "launched_other": [l * 0.2 for l in launched],
            "destroyed_total": [l * 0.8 for l in launched],
        }
    )


class TestAddAttackFeatures:
    def test_uav_share_matches_definition(self):
        master = _master_with_attacks([100.0, 50.0, 0.0])
        out = add_attack_features(master)
        # 50% of total is uav (per fixture)
        assert out["attack_uav_share"].iloc[0] == pytest.approx(0.5)
        assert out["attack_cruise_share"].iloc[0] == pytest.approx(0.2)
        assert out["attack_ballistic_share"].iloc[0] == pytest.approx(0.1)
        # Zero total → NaN share
        assert pd.isna(out["attack_uav_share"].iloc[2])

    def test_penetrations_estimated(self):
        master = _master_with_attacks([100.0, 50.0])
        out = add_attack_features(master)
        # launched - destroyed = launched * 0.2
        assert out["penetrations_estimated"].iloc[0] == pytest.approx(20.0)
        assert out["penetrations_estimated"].iloc[1] == pytest.approx(10.0)

    def test_surprise_columns_exist(self):
        master = _master_with_attacks([10.0] * 100)
        out = add_attack_features(master)
        for s in SURPRISE_SERIES:
            short = s.replace("launched_", "")
            for w in SURPRISE_WINDOWS:
                col = f"attack_surprise_{short}_{w}d"
                assert col in out.columns, f"missing {col}"
        # Plus penetrations
        for w in SURPRISE_WINDOWS:
            assert f"attack_surprise_penetrations_{w}d" in out.columns

    def test_surprise_uses_only_past(self):
        # Series with a known step: first 7 are 10, then 100.
        # (Use 7 tens so the window values[0:7] = [10]*7 → mean 10.)
        master = _master_with_attacks([10.0] * 7 + [100.0] * 9)
        out = add_attack_features(master)
        # 7-day window: at t=7, uses [t-7, t) = [0..6] = [10,10,10,10,10,10,10]
        # mean = 10, actual = 100, surprise = 100 - 10 = 90
        assert out["attack_surprise_total_7d"].iloc[7] == pytest.approx(90.0)
        # First 7 values are NaN (min_periods=7, t < 7)
        for i in range(7):
            assert pd.isna(out["attack_surprise_total_7d"].iloc[i])

    def test_surprise_zero_when_constant(self):
        master = _master_with_attacks([10.0] * 50)
        out = add_attack_features(master)
        # Surprise = actual - mean = 10 - 10 = 0 (everywhere valid)
        for i in range(7, 50):
            assert out["attack_surprise_total_7d"].iloc[i] == pytest.approx(0.0)

    def test_surprise_30d_window(self):
        master = _master_with_attacks([10.0] * 60)
        out = add_attack_features(master)
        # First 30 are NaN (need 30 past obs); t=30 is first valid
        for i in range(30):
            assert pd.isna(out["attack_surprise_total_30d"].iloc[i])
        assert out["attack_surprise_total_30d"].iloc[30] == pytest.approx(0.0)

    def test_surprise_90d_window(self):
        master = _master_with_attacks([10.0] * 120)
        out = add_attack_features(master)
        for i in range(90):
            assert pd.isna(out["attack_surprise_total_90d"].iloc[i])
        assert out["attack_surprise_total_90d"].iloc[90] == pytest.approx(0.0)

    def test_large_attack_indicator(self):
        # Build a series with a clear 90th-percentile threshold
        # All 10 except one outlier of 100
        values = [10.0] * 19 + [100.0]
        master = _master_with_attacks(values)
        out = add_attack_features(master)
        # 90th percentile of 20 values (19 tens + 100) → ~10 (the 90th percentile is the 18th smallest)
        # Actually, with 19 values of 10 and 1 of 100, the 90th percentile ≈ 10 + 0.1*(100-10)*9 ≈ ...
        # Let's just check that the max is flagged
        assert out["large_attack_indicator"].iloc[19] == 1
        # And at least some non-max values are not flagged
        assert out["large_attack_indicator"].iloc[0] == 0

    def test_lags(self):
        master = _master_with_attacks([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        out = add_attack_features(master)
        # launched_total_lag1: shift by 1
        assert pd.isna(out["launched_total_lag1"].iloc[0])
        assert out["launched_total_lag1"].iloc[1] == 10.0
        assert out["launched_total_lag1"].iloc[5] == 50.0
        # launched_total_lag3: shift by 3
        assert pd.isna(out["launched_total_lag3"].iloc[0])
        assert pd.isna(out["launched_total_lag3"].iloc[2])
        assert out["launched_total_lag3"].iloc[3] == 10.0
        # 7d_rolling: needs 7 past obs → all NaN for n=6
        for i in range(6):
            assert pd.isna(out["launched_total_7d_rolling"].iloc[i])

    def test_does_not_mutate_input(self):
        master = _master_with_attacks([10.0, 20.0, 30.0])
        original_cols = list(master.columns)
        _ = add_attack_features(master)
        assert list(master.columns) == original_cols

    def test_handles_all_zero_attacks(self):
        # A day with zero attacks → safe_total is NaN → shares are NaN
        master = _master_with_attacks([0.0, 0.0, 10.0])
        out = add_attack_features(master)
        # Day 0 and 1 have launched_total=0 → shares are NaN
        assert pd.isna(out["attack_uav_share"].iloc[0])
        assert pd.isna(out["attack_uav_share"].iloc[1])
        # Day 2 has 10 → 5/10 = 0.5
        assert out["attack_uav_share"].iloc[2] == pytest.approx(0.5)


class TestAR1Hook:
    def test_returns_float(self):
        s = pd.Series(np.random.RandomState(42).normal(10, 2, 200).clip(min=0))
        result = compute_attack_surprise_ar1(s, min_train=180)
        assert isinstance(result, float)
        assert not np.isnan(result)
        # Should be roughly in the same range as the input
        assert 0 < result < 30

    def test_returns_nan_for_short_series(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result = compute_attack_surprise_ar1(s, min_train=180)
        assert np.isnan(result)

    def test_returns_nan_for_all_nan(self):
        s = pd.Series([np.nan] * 200)
        result = compute_attack_surprise_ar1(s, min_train=180)
        assert np.isnan(result)

    def test_drops_nan_internally(self):
        # NaN at start should be dropped
        s = pd.Series([np.nan] * 50 + list(np.random.RandomState(0).normal(10, 2, 200).clip(min=0)))
        result = compute_attack_surprise_ar1(s, min_train=180)
        assert not np.isnan(result)

    def test_min_train_respected(self):
        # 200 obs, min_train=300 → should return NaN
        s = pd.Series([1.0] * 200)
        result = compute_attack_surprise_ar1(s, min_train=300)
        assert np.isnan(result)
