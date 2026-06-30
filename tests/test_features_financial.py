"""Tests for ``src.features.financial_features``."""
import numpy as np
import pandas as pd
import pytest

from src.features.financial_features import add_financial_features


def _master_with_returns(returns: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    """Build a minimal master DataFrame with a daily `r_ITA` series."""
    n = len(returns)
    dates = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "ITA": np.arange(100.0, 100.0 + n),
            "r_ITA": returns,
            "VIX": [20.0] * n,
        }
    )


class TestAddFinancialFeatures:
    def test_vol_5d_uses_past_5_obs(self):
        # Constant returns: std = 0 → expected 0
        master = _master_with_returns([1.0] * 30)
        out = add_financial_features(master)
        # First 4 are NaN (need 5 past values, t=0..4 is < 5)
        assert pd.isna(out["vol_5d"].iloc[0])
        assert pd.isna(out["vol_5d"].iloc[3])
        # t=4: 4 past values < min_periods=5 → NaN
        assert pd.isna(out["vol_5d"].iloc[4])
        # t=5: 5 past values, constant → 0
        assert out["vol_5d"].iloc[5] == pytest.approx(0.0)

    def test_vol_5d_varies_with_data(self):
        # Build a series where the rolling std is non-zero
        r = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        master = _master_with_returns(r * 5)  # 50 obs
        out = add_financial_features(master)
        # At t=5: window uses r[0..5) = r[0..4] = [1,-1,1,-1,1] → std = 1.0
        assert out["vol_5d"].iloc[5] == pytest.approx(np.std([1, -1, 1, -1, 1], ddof=1))
        # And it's non-zero
        assert out["vol_5d"].iloc[5] > 0

    def test_vol_5d_min_periods_5(self):
        master = _master_with_returns([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        out = add_financial_features(master)
        # First 5 values: NaN (need 5 past obs, t=0..4 is < 5)
        for i in range(5):
            assert pd.isna(out["vol_5d"].iloc[i])
        # t=5: 5 past values → valid
        assert not pd.isna(out["vol_5d"].iloc[5])

    def test_vol_20d_min_periods_20(self):
        master = _master_with_returns([1.0] * 30)
        out = add_financial_features(master)
        # First 19 are NaN (need 20 past obs, t=0..19 is < 20)
        for i in range(19):
            assert pd.isna(out["vol_20d"].iloc[i])
        # t=19: 19 past values < min_periods=20 → NaN
        assert pd.isna(out["vol_20d"].iloc[19])
        # t=20 is the 21st row (0-indexed) → 20 past obs available
        assert not pd.isna(out["vol_20d"].iloc[20])

    def test_abs_r_ita(self):
        master = _master_with_returns([1.0, -2.0, 3.0, -4.0, 0.0])
        out = add_financial_features(master)
        assert list(out["abs_r_ITA"]) == [1.0, 2.0, 3.0, 4.0, 0.0]

    def test_r_ita_lag1(self):
        master = _master_with_returns([1.0, 2.0, 3.0, 4.0, 5.0])
        out = add_financial_features(master)
        assert pd.isna(out["r_ITA_lag1"].iloc[0])
        assert out["r_ITA_lag1"].iloc[1] == 1.0
        assert out["r_ITA_lag1"].iloc[4] == 4.0

    def test_r_ita_lag2(self):
        master = _master_with_returns([1.0, 2.0, 3.0, 4.0, 5.0])
        out = add_financial_features(master)
        assert pd.isna(out["r_ITA_lag2"].iloc[0])
        assert pd.isna(out["r_ITA_lag2"].iloc[1])
        assert out["r_ITA_lag2"].iloc[2] == 1.0
        assert out["r_ITA_lag2"].iloc[4] == 3.0

    def test_r_ita_lag5(self):
        master = _master_with_returns([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        out = add_financial_features(master)
        # First 5 are NaN
        for i in range(5):
            assert pd.isna(out["r_ITA_lag5"].iloc[i])
        assert out["r_ITA_lag5"].iloc[5] == 1.0

    def test_does_not_mutate_input(self):
        master = _master_with_returns([1.0, 2.0, 3.0])
        original_cols = list(master.columns)
        _ = add_financial_features(master)
        assert list(master.columns) == original_cols

    def test_handles_nan_in_returns(self):
        master = _master_with_returns([1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0])
        out = add_financial_features(master)
        # Output should still be computed (with NaN propagation)
        assert "vol_5d" in out.columns
        # The lag should be NaN where the source is NaN
        assert pd.isna(out["r_ITA_lag1"].iloc[2])  # lag of NaN

    def test_missing_r_ita_raises(self):
        # No r_ITA column
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "ITA": [1.0] * 5})
        with pytest.raises(KeyError):
            add_financial_features(df)
