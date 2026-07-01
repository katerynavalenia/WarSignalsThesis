"""Tests for ``src.features.news_features``."""
import numpy as np
import pandas as pd
import pytest

from src.features.news_features import (
    ROLLING_WINDOWS,
    SOURCE_GROUPS,
    Z_WINDOW,
    add_news_features,
)


def _master_with_news(articles_per_group: dict, n_days: int = 60) -> pd.DataFrame:
    """Build a minimal master with `n_articles_<group>` and `tone_<group>`."""
    n = n_days
    df = {
        "date": pd.date_range("2023-01-01", periods=n, freq="D"),
    }
    totals = np.zeros(n, dtype=float)
    for g in SOURCE_GROUPS:
        c = np.array(articles_per_group.get(g, [0.0] * n), dtype=float)
        df[f"n_articles_{g}"] = c
        totals += c
        df[f"tone_{g}"] = np.linspace(-5.0, 5.0, n)  # tones
    df["n_articles_total"] = totals
    # Also include narrative gaps (optional, but tested)
    df["narrative_gap_ua_west"] = df["tone_ukrainian"] - df["tone_western"]
    df["narrative_gap_ru_west"] = df["tone_russian"] - df["tone_western"]
    df["narrative_gap_ua_ru"] = df["tone_ukrainian"] - df["tone_russian"]
    # n_tone_* (used by Phase 3, just for compatibility)
    for g in SOURCE_GROUPS:
        df[f"n_tone_{g}"] = df[f"n_articles_{g}"]
    return pd.DataFrame(df)


class TestAddNewsFeatures:
    def test_share_columns_present(self):
        master = _master_with_news({"ukrainian": [10.0] * 60, "western": [90.0] * 60})
        out = add_news_features(master)
        for g in SOURCE_GROUPS:
            assert f"n_{g}_share" in out.columns
            assert f"n_{g}_log" in out.columns
            assert f"n_{g}_z30" in out.columns

    def test_share_sums_to_one_per_row(self):
        master = _master_with_news(
            {"ukrainian": [10.0] * 60, "russian": [5.0] * 60, "western": [80.0] * 60, "other": [5.0] * 60}
        )
        out = add_news_features(master)
        share_sum = (
            out["n_ukrainian_share"] + out["n_russian_share"] + out["n_western_share"] + out["n_other_share"]
        )
        # Each row should sum to ~1.0
        for v in share_sum:
            if not pd.isna(v):
                assert v == pytest.approx(1.0, abs=1e-9)

    def test_share_bounded_zero_to_one(self):
        master = _master_with_news({"ukrainian": [10.0] * 60, "western": [90.0] * 60})
        out = add_news_features(master)
        for g in SOURCE_GROUPS:
            for v in out[f"n_{g}_share"].dropna():
                assert 0.0 <= v <= 1.0

    def test_share_nan_when_total_zero(self):
        # All zeros for the first 5 days
        master = _master_with_news(
            {"ukrainian": [0.0] * 5 + [10.0] * 55, "western": [0.0] * 5 + [90.0] * 55}
        )
        out = add_news_features(master)
        # Days 0..4: total=0 → shares are NaN
        for i in range(5):
            assert pd.isna(out["n_ukrainian_share"].iloc[i])
        # Day 5: total=100 → 10/100 = 0.1
        assert out["n_ukrainian_share"].iloc[5] == pytest.approx(0.1)

    def test_log_normalization(self):
        master = _master_with_news({"ukrainian": [10.0, 100.0, 1000.0] + [10.0] * 57})
        out = add_news_features(master)
        # log1p(0) = 0, log1p(10) ≈ 2.4
        assert out["n_ukrainian_log"].iloc[0] == pytest.approx(np.log1p(10.0))
        assert out["n_ukrainian_log"].iloc[1] == pytest.approx(np.log1p(100.0))
        assert out["n_ukrainian_log"].iloc[2] == pytest.approx(np.log1p(1000.0))

    def test_z30_uses_past_30_obs(self):
        # 60 days of constant 100 → z30 = 0 (after warm-up)
        master = _master_with_news({"ukrainian": [100.0] * 60})
        out = add_news_features(master)
        # First 29 are NaN (min_periods=30, t < 29)
        for i in range(29):
            assert pd.isna(out["n_ukrainian_z30"].iloc[i])
        # t=29: std=0 → NaN
        assert pd.isna(out["n_ukrainian_z30"].iloc[29])
        # Wait, std of constant = 0 → we replace 0 with NaN → z = NaN
        # So the test should expect NaN for constant series, not 0
        for i in range(30, 60):
            assert pd.isna(out["n_ukrainian_z30"].iloc[i])

    def test_z30_nonzero_with_variation(self):
        # Build a varying series
        values = [10.0 + i for i in range(60)]  # 10, 11, ..., 69
        master = _master_with_news({"ukrainian": values})
        out = add_news_features(master)
        # At t=30, z = (40 - mean([10..39])) / std([10..39])
        # mean([10..39]) = 24.5, std = ~8.66
        # z = (40 - 24.5) / 8.66 ≈ 1.79
        z = out["n_ukrainian_z30"].iloc[30]
        assert not pd.isna(z)
        assert z > 0  # 40 is above the mean

    def test_tone_lag1_and_lag3(self):
        master = _master_with_news({"ukrainian": [10.0] * 60})
        out = add_news_features(master)
        # tone_ukrainian is linspace(-5, 5, 60)
        assert pd.isna(out["tone_ukrainian_lag1"].iloc[0])
        # t=1: lag1 of tone at t=0 = -5.0
        assert out["tone_ukrainian_lag1"].iloc[1] == pytest.approx(out["tone_ukrainian"].iloc[0])
        # lag3
        assert pd.isna(out["tone_ukrainian_lag3"].iloc[0])
        assert pd.isna(out["tone_ukrainian_lag3"].iloc[2])
        assert out["tone_ukrainian_lag3"].iloc[3] == pytest.approx(out["tone_ukrainian"].iloc[0])

    def test_total_lags(self):
        master = _master_with_news({"ukrainian": [10.0] * 60, "western": [20.0] * 60})
        out = add_news_features(master)
        assert "n_articles_total_lag1" in out.columns
        assert "n_articles_total_lag3" in out.columns
        for w in ROLLING_WINDOWS:
            assert f"n_articles_total_{w}d_rolling_mean" in out.columns
        # Check lag1
        assert pd.isna(out["n_articles_total_lag1"].iloc[0])
        assert out["n_articles_total_lag1"].iloc[1] == pytest.approx(30.0)

    def test_narrative_gap_lag1(self):
        master = _master_with_news({"ukrainian": [10.0] * 60})
        out = add_news_features(master)
        assert "narrative_gap_ua_west_lag1" in out.columns
        # First row should be NaN (no past)
        assert pd.isna(out["narrative_gap_ua_west_lag1"].iloc[0])
        # t=1: should equal the gap at t=0
        expected = master["narrative_gap_ua_west"].iloc[0]
        assert out["narrative_gap_ua_west_lag1"].iloc[1] == pytest.approx(expected)

    def test_does_not_mutate_input(self):
        master = _master_with_news({"ukrainian": [10.0] * 60, "western": [20.0] * 60})
        original_cols = list(master.columns)
        _ = add_news_features(master)
        assert list(master.columns) == original_cols
