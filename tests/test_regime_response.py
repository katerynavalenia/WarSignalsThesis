"""Tests for the Bloomberg loader and the threat-vs-act estimator.

All offline: the workbook parser is fed a hand-built frame shaped like a real
Bloomberg export, and the estimator is fed synthetic series with a known
coefficient, so the suite never needs the gitignored xlsx files or the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.bloomberg import (  # noqa: E402
    add_return_features,
    parse_index_workbook,
)
from src.models.regime_response import (  # noqa: E402
    channel_race,
    interacted_race,
    is_volatility_target,
    race_by_regime,
    zscore,
)


@pytest.fixture
def workbook() -> pd.DataFrame:
    """A Bloomberg export: metadata rows, a header row, then newest-first data."""
    return pd.DataFrame(
        [
            ["Security", "BSHIELDT Index", None],
            ["Start Date", "2020-01-01 00:00:00", None],
            ["End Date", "2020-01-06 00:00:00", None],
            ["Period", "D", None],
            ["Currency", "EUR", None],
            [None, None, None],
            ["Date", "PX_LAST", "PX_VOLUME"],
            ["2020-01-06 00:00:00", 1591.00, 52004533],
            ["2020-01-03 00:00:00", 1589.48, 27367530],
            ["2020-01-02 00:00:00", 1588.09, 32087392],
        ]
    )


def test_parse_index_workbook_sorts_ascending(workbook: pd.DataFrame) -> None:
    out = parse_index_workbook(workbook)
    assert list(out.columns) == ["date", "px", "volume"]
    assert out["date"].is_monotonic_increasing
    assert out["date"].dtype == "datetime64[ns]"
    assert out.loc[0, "px"] == pytest.approx(1588.09)
    assert len(out) == 3


def test_parse_index_workbook_drops_metadata_rows(workbook: pd.DataFrame) -> None:
    out = parse_index_workbook(workbook)
    assert out["date"].min() == pd.Timestamp("2020-01-02")
    assert out["px"].notna().all()


def test_parse_index_workbook_rejects_missing_header(workbook: pd.DataFrame) -> None:
    broken = workbook.drop(index=6)
    with pytest.raises(ValueError, match="Date"):
        parse_index_workbook(broken)


def test_parse_index_workbook_rejects_duplicate_dates(workbook: pd.DataFrame) -> None:
    dupe = pd.concat([workbook, workbook.iloc[[7]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        parse_index_workbook(dupe)


def test_add_return_features_shapes() -> None:
    px = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=10), "bshieldt": 100.0})
    px.loc[5, "bshieldt"] = 110.0
    out = add_return_features(px, columns=["bshieldt"], rv_window=3)
    assert {"r_bshieldt", "vol_bshieldt", "rv3_bshieldt"} <= set(out.columns)
    assert pd.isna(out.loc[0, "r_bshieldt"])  # no return on the first day
    assert (out["vol_bshieldt"].dropna() >= 0).all()
    assert out.loc[5, "r_bshieldt"] == pytest.approx(100 * np.log(1.10))


def test_zscore_rejects_constant_series() -> None:
    with pytest.raises(ValueError, match="variance"):
        zscore(pd.Series([2.0, 2.0, 2.0], name="flat"))


def test_is_volatility_target() -> None:
    assert is_volatility_target("vol_bshieldt")
    assert is_volatility_target("rv5_waerlst")
    assert not is_volatility_target("r_bshieldt")


@pytest.fixture
def synthetic() -> pd.DataFrame:
    """A panel where the threat channel has a known effect and act has none."""
    rng = np.random.default_rng(0)
    n = 400
    idx = pd.date_range("2021-01-01", periods=n, freq="B")
    act = pd.Series(rng.normal(size=n).cumsum() + 100, index=idx)
    threat = pd.Series(rng.normal(size=n).cumsum() + 100, index=idx)
    r_mkt = pd.Series(rng.normal(scale=1.0, size=n), index=idx)
    y = 0.8 * threat.diff().fillna(0) + 0.5 * r_mkt + rng.normal(scale=0.2, size=n)
    return pd.DataFrame(
        {
            "gpr_act": act,
            "gpr_threat": threat,
            "r_mkt": r_mkt,
            "lvix": pd.Series(rng.normal(size=n), index=idx),
            "r_target": y,
            "regime": ["buildup"] * (n // 2) + ["attrition"] * (n - n // 2),
        },
        index=idx,
    )


def test_channel_race_recovers_the_planted_channel(synthetic: pd.DataFrame) -> None:
    res = channel_race(synthetic, "r_target")
    assert res is not None
    assert res["p_threat"] < 0.01
    assert res["threat"] > 0
    assert res["p_act"] > 0.05  # nothing was planted on the act channel


def test_channel_race_returns_none_when_too_short(synthetic: pd.DataFrame) -> None:
    assert channel_race(synthetic.head(10), "r_target") is None


def test_levels_and_changes_disagree_on_persistent_regressors(
    synthetic: pd.DataFrame,
) -> None:
    """The transform matters: random walks in levels manufacture significance."""
    rng = np.random.default_rng(7)
    noise = synthetic.copy()
    noise["r_target"] = rng.normal(size=len(noise))  # unrelated to either channel
    in_changes = channel_race(noise, "r_target", use_changes=True)
    in_levels = channel_race(noise, "r_target", use_changes=False)
    assert in_changes["p_threat"] > 0.05
    # The levels fit attributes variance the changes fit does not.
    assert in_levels["r2"] > in_changes["r2"]


def test_race_by_regime_covers_every_regime_plus_pooled(
    synthetic: pd.DataFrame,
) -> None:
    out = race_by_regime(synthetic, "r_target")
    assert set(out["sample"]) == {"buildup", "attrition", "pooled"}
    assert (out["n"] > 0).all()


def test_interacted_race_reports_one_row_per_regime(synthetic: pd.DataFrame) -> None:
    out = interacted_race(synthetic, "r_target")
    assert set(out["regime"]) == {"buildup", "attrition"}
    assert out["p_threat"].notna().all()
