"""Tests for the physical air-attack layer and its three-period reading.

The whole module exists because "no record" means different things in different
periods, so that is what these tests pin down. Offline: they read the committed
attack tables, never the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.attacks import (  # noqa: E402
    INVASION_START,
    PUBLISHED_INVARIANTS,
    UAF_REPORTING_START,
    load_attack_panel,
    period_of,
    verify_invariants,
)

ATTACK_DIR = Path("data/interim/attacks")


@pytest.fixture(scope="module")
def spine_dates() -> pd.Series:
    return pd.read_parquet("data/interim/spine_full.parquet")["date"]


@pytest.fixture(scope="module")
def panel(spine_dates) -> pd.DataFrame:
    return load_attack_panel(spine_dates)


class TestPublishedInvariants:
    """The copy in this repo must be the data the approved thesis was written on.

    These three numbers are printed in the approved PDF. They are the only
    provenance check available, because the raw Ukrainian Air Force export and
    the code that processed it are both gone.
    """

    def test_copy_reconciles_to_the_approved_thesis(self):
        dm = pd.read_parquet(ATTACK_DIR / "daily_master.parquet")
        for name, (found, published) in verify_invariants(dm).items():
            assert found == published, f"{name}: copy {found}, approved {published}"

    def test_the_invariants_are_the_published_ones(self):
        """Guards against someone 'fixing' a failure by editing the target."""
        assert PUBLISHED_INVARIANTS == {
            "market_info_dates": 809,
            "weapons_launched": 102396,
            "weapons_destroyed": 76126,
        }


class TestThreePeriods:
    def test_pre_war_is_zero_not_missing(self, panel):
        """No mass air campaign existed, so zero is the substantive answer."""
        pre = panel[panel.date < INVASION_START]
        assert len(pre) > 1500
        assert not pre.attack_unobserved.any()
        assert (pre["launched_total_lag1"] == 0).all()
        assert pre["launched_total_lag1"].notna().all()

    def test_invasion_window_is_missing_not_zero(self, panel):
        """The attacks happened; the tallies did not exist yet. Coding these
        zero would assert no air attacks during the invasion of Ukraine."""
        inv = panel[(panel.date >= INVASION_START)
                    & (panel.date < UAF_REPORTING_START)]
        assert len(inv) > 100
        assert inv.attack_unobserved.all()
        assert inv["launched_total_lag1"].isna().all()
        assert (inv["launched_total_lag1"] == 0).sum() == 0

    def test_measured_window_has_no_missing_features(self, panel):
        """Days inside the reporting era with no published wave are real zeros."""
        mea = panel[panel.date >= UAF_REPORTING_START]
        assert len(mea) > 800
        assert not mea.attack_unobserved.any()
        assert mea["launched_total_lag1"].notna().all()
        assert (mea["launched_total_lag1"] > 0).sum() > 400

    def test_every_row_belongs_to_exactly_one_period(self, panel):
        counts = period_of(panel.date).value_counts()
        assert set(counts.index) == {"pre-war", "invasion", "measured"}
        assert counts.sum() == len(panel)

    def test_unobserved_flag_matches_the_invasion_window_exactly(self, panel):
        expected = ((panel.date >= INVASION_START)
                    & (panel.date < UAF_REPORTING_START))
        assert (panel.attack_unobserved == expected).all()

    def test_missingness_occurs_only_where_flagged(self, panel):
        """No feature may be NaN outside the invasion window. A stray NaN would
        silently drop rows from any physical specification."""
        feats = [c for c in panel.columns
                 if c not in ("date", "attack_unobserved")]
        stray = panel.loc[~panel.attack_unobserved, feats].isna().sum().sum()
        assert stray == 0, f"{stray} unflagged missing values"


class TestFeatureBlock:
    def test_carries_the_approved_physical_features(self, panel):
        feats = [c for c in panel.columns
                 if c not in ("date", "attack_unobserved")]
        assert len(feats) == 41
        for expected in ("launched_total_lag1", "interception_rate_lag1",
                         "weapon_diversity_lag1", "large_attack_indicator_lag1",
                         "attack_surprise_total_30d_lag1"):
            assert expected in feats

    def test_news_features_are_not_in_the_physical_block(self, panel):
        """`n_articles_*` and `*_direct` count articles *about* attacks. They are
        narrative evidence; putting them in P would place news on both sides of
        the comparison the thesis exists to make."""
        feats = [c for c in panel.columns]
        assert not [c for c in feats if "n_articles" in c]
        assert not [c for c in feats if c.endswith("_direct_lag1")]

    def test_every_feature_is_lagged(self, panel):
        """The market-information-date rule against look-ahead lives in the lag.
        An unlagged physical feature would leak same-day information."""
        feats = [c for c in panel.columns
                 if c not in ("date", "attack_unobserved")]
        assert all("_lag" in c or "_rolling" in c for c in feats), \
            [c for c in feats if "_lag" not in c and "_rolling" not in c]

    def test_panel_aligns_to_the_supplied_calendar(self, panel, spine_dates):
        assert len(panel) == spine_dates.nunique()
        assert panel.date.is_monotonic_increasing
        assert not panel.date.duplicated().any()
