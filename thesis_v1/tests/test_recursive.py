"""Tests for ``src.utils.recursive``."""
import numpy as np
import pandas as pd
import pytest

from src.utils.recursive import expanding_compute, rolling_compute


class TestExpandingCompute:
    def test_basic_mean_with_min_periods_1(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = expanding_compute(s, np.mean, min_periods=1)
        assert result.iloc[0] == 1.0
        assert result.iloc[1] == 1.5
        assert result.iloc[2] == 2.0
        assert result.iloc[3] == 2.5
        assert result.iloc[4] == 3.0

    def test_min_periods_creates_leading_nans(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = expanding_compute(s, np.mean, min_periods=3)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 2.0  # (1+2+3)/3
        assert result.iloc[3] == 2.5
        assert result.iloc[4] == 3.0

    def test_uses_only_past_data(self):
        # The result at index t must not see the value at index t+1.
        s = pd.Series([1.0, 100.0, 3.0])
        result = expanding_compute(s, np.max, min_periods=1)
        # At index 0, max of [1] = 1
        assert result.iloc[0] == 1.0
        # At index 1, max of [1, 100] = 100
        assert result.iloc[1] == 100.0
        # At index 2, max of [1, 100, 3] = 100
        assert result.iloc[2] == 100.0

    def test_index_preserved(self):
        s = pd.Series([1.0, 2.0, 3.0], index=["a", "b", "c"], name="x")
        result = expanding_compute(s, np.mean, min_periods=1)
        assert list(result.index) == ["a", "b", "c"]
        assert result.name == "x"

    def test_custom_function(self):
        s = pd.Series([2.0, 4.0, 6.0, 8.0])

        def sum_squares(x):
            return float(np.sum(x ** 2))

        result = expanding_compute(s, sum_squares, min_periods=1)
        assert result.iloc[0] == 4.0   # 2^2
        assert result.iloc[1] == 20.0  # 4 + 16
        assert result.iloc[2] == 56.0  # 4 + 16 + 36
        assert result.iloc[3] == 120.0

    def test_min_periods_below_1_raises(self):
        s = pd.Series([1.0, 2.0])
        with pytest.raises(ValueError, match="min_periods"):
            expanding_compute(s, np.mean, min_periods=0)


class TestRollingCompute:
    def test_basic_mean_window_3(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = rolling_compute(s, window=3, func=np.mean, min_periods=3)
        # With min_periods=3 the first valid index is t=3 (need 3 past obs).
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        # At index 3, window=[1, 2, 3] (excludes 4) → 2.0
        assert result.iloc[3] == 2.0
        # At index 4, window=[2, 3, 4] (excludes 5) → 3.0
        assert result.iloc[4] == 3.0

    def test_window_2_first_valid_at_t2(self):
        # With window=2, min_periods=2, the first valid index is t=2.
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = rolling_compute(s, window=2, func=np.mean, min_periods=2)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        # At index 2, window=[1, 2] (excludes 3) → 1.5
        assert result.iloc[2] == 1.5
        # At index 3, window=[2, 3] (excludes 4) → 2.5
        assert result.iloc[3] == 2.5
        # At index 4, window=[3, 4] (excludes 5) → 3.5
        assert result.iloc[4] == 3.5

    def test_excludes_current_value(self):
        # This is the key invariant: the current value is NOT used.
        s = pd.Series([1.0, 2.0, 3.0, 100.0, 5.0])
        result = rolling_compute(s, window=2, func=np.mean, min_periods=2)
        # At index 2: window=[1,2], excludes 3 → 1.5
        assert result.iloc[2] == 1.5
        # At index 3: window=[2,3], excludes 100 → 2.5
        assert result.iloc[3] == 2.5
        # At index 4: window=[3,100], excludes 5 → 51.5
        assert result.iloc[4] == 51.5

    def test_min_periods_creates_leading_nans(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = rolling_compute(s, window=3, func=np.mean, min_periods=3)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        assert result.iloc[3] == 2.0
        assert result.iloc[4] == 3.0

    def test_min_periods_below_window_uses_partial_window(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        # min_periods=2 with window=5 → use first 2 elements at t=2
        result = rolling_compute(s, window=5, func=np.mean, min_periods=2)
        assert pd.isna(result.iloc[0])
        # At t=1: window=[1], mean=1.0 (only 1 value available, but min_periods=2)
        # Actually, range(min_periods, n) → range(2, 5)
        # At t=2: values[0:2]=[1,2], mean=1.5
        assert result.iloc[2] == 1.5
        # At t=3: values[0:3]=[1,2,3], mean=2.0
        assert result.iloc[3] == 2.0
        # At t=4: values[0:4]=[1,2,3,4], mean=2.5
        assert result.iloc[4] == 2.5

    def test_index_preserved(self):
        s = pd.Series([1.0, 2.0, 3.0], index=["a", "b", "c"], name="x")
        result = rolling_compute(s, window=2, func=np.mean, min_periods=2)
        assert list(result.index) == ["a", "b", "c"]
        assert result.name == "x"

    def test_window_below_1_raises(self):
        s = pd.Series([1.0, 2.0])
        with pytest.raises(ValueError, match="window"):
            rolling_compute(s, window=0, func=np.mean)

    def test_min_periods_below_1_raises(self):
        s = pd.Series([1.0, 2.0])
        with pytest.raises(ValueError, match="min_periods"):
            rolling_compute(s, window=2, func=np.mean, min_periods=0)

    def test_matches_pandas_rolling_with_closed_left(self):
        # Cross-check that our implementation matches pandas' built-in rolling
        # with closed='left' for a vectorizable function.
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        our = rolling_compute(s, window=3, func=np.mean, min_periods=3)
        pandas_result = s.rolling(window=3, min_periods=3, closed="left").mean()
        pd.testing.assert_series_equal(our, pandas_result, check_names=False)
