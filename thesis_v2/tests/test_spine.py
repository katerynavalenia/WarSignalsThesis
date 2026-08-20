"""Tests for the Phase 1 spine: GPR/FRED parsing and the regime calendar.

All tests are offline — the parsing functions are split from the fetching
functions precisely so the suite never touches the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.sources import parse_fred_frame, parse_gpr_frame  # noqa: E402
from src.features.calendar import (  # noqa: E402
    ATTRITION_START,
    BUILDUP_START,
    INVASION_DATE,
    REGIMES,
    SAMPLE_START,
    assign_regime,
    build_calendar,
)


@pytest.fixture
def gpr_raw() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DAY": [20220223, 20220224, 20220225],
            "GPRD": [431.0, 370.7, 515.9],
            "GPRD_ACT": [183.5, 189.5, 162.4],
            "GPRD_THREAT": [692.7, 545.4, 797.8],
            "N10D": [1, 2, 3],
        }
    )


class TestParseGpr:
    def test_parses_integer_yyyymmdd_dates(self, gpr_raw):
        out = parse_gpr_frame(gpr_raw)
        assert out["date"].tolist() == [
            pd.Timestamp("2022-02-23"),
            pd.Timestamp("2022-02-24"),
            pd.Timestamp("2022-02-25"),
        ]
        assert out["date"].dtype == "datetime64[ns]"

    def test_calendar_dates_are_nanosecond_resolution(self):
        # v1's processed tables are datetime64[ns]; pandas 3 would otherwise
        # produce datetime64[us] and silently break the merges.
        assert build_calendar("2015-02-18", "2015-03-01")["date"].dtype == "datetime64[ns]"

    def test_date_is_the_first_column(self, gpr_raw):
        # Repo-wide convention: `date` is a regular first column, never the index.
        assert list(parse_gpr_frame(gpr_raw).columns)[0] == "date"

    def test_keeps_only_the_three_index_columns(self, gpr_raw):
        assert set(parse_gpr_frame(gpr_raw).columns) == {
            "date", "gpr", "gpr_act", "gpr_threat"
        }

    def test_sorts_by_date(self, gpr_raw):
        out = parse_gpr_frame(gpr_raw.iloc[::-1].reset_index(drop=True))
        assert out["date"].is_monotonic_increasing

    def test_rejects_a_file_missing_columns(self, gpr_raw):
        with pytest.raises(ValueError, match="missing expected columns"):
            parse_gpr_frame(gpr_raw.drop(columns=["GPRD_THREAT"]))

    def test_rejects_duplicate_dates(self, gpr_raw):
        dupe = pd.concat([gpr_raw, gpr_raw.iloc[[0]]], ignore_index=True)
        with pytest.raises(ValueError, match="duplicate dates"):
            parse_gpr_frame(dupe)


class TestParseFred:
    def test_parses_values_and_index(self):
        frame = pd.DataFrame(
            {"observation_date": ["2015-01-02", "2015-01-05"], "VIXCLS": ["17.79", "19.92"]}
        )
        s = parse_fred_frame(frame, "VIXCLS")
        assert s.name == "vix"
        assert s.index.name == "date"
        assert s.iloc[0] == pytest.approx(17.79)

    def test_missing_marker_becomes_nan_not_a_dropped_row(self):
        # FRED writes "." on holidays. Losing the row would silently shorten
        # the sample; NaN keeps the calendar intact.
        frame = pd.DataFrame(
            {"observation_date": ["2015-01-01", "2015-01-02"], "VIXCLS": [".", "17.79"]}
        )
        s = parse_fred_frame(frame, "VIXCLS")
        assert len(s) == 2
        assert pd.isna(s.iloc[0])

    def test_handles_legacy_date_header(self):
        frame = pd.DataFrame({"DATE": ["2015-01-02"], "DGS10": ["2.12"]})
        assert parse_fred_frame(frame, "DGS10").iloc[0] == pytest.approx(2.12)


class TestRegimeCalendar:
    @pytest.mark.parametrize(
        "date,expected",
        [
            ("2015-06-01", "pre_war"),
            ("2021-10-31", "pre_war"),
            ("2021-11-01", "buildup"),
            ("2022-02-23", "buildup"),
            ("2022-02-24", "invasion"),
            ("2022-09-28", "invasion"),
            ("2022-09-29", "attrition"),
            ("2026-06-30", "attrition"),
        ],
    )
    def test_boundaries_are_inclusive_on_the_start_date(self, date, expected):
        assert assign_regime(pd.Series([pd.Timestamp(date)]))[0] == expected

    def test_every_regime_is_populated(self):
        cal = build_calendar()
        assert set(cal["regime"].unique()) == set(REGIMES)

    def test_attrition_matches_the_v1_sample_start(self):
        # The v1 window began the day the air-attack data began. Keeping the
        # boundary here makes "the v1 sample" a subsettable regime.
        assert ATTRITION_START == pd.Timestamp("2022-09-29")

    def test_event_time_is_two_sided(self):
        # v1's days_since_invasion was one-sided and became a pure trend.
        cal = build_calendar()
        assert cal["days_since_invasion"].min() < 0 < cal["days_since_invasion"].max()
        on_the_day = cal.loc[cal["date"] == INVASION_DATE, "days_since_invasion"]
        assert on_the_day.iloc[0] == 0

    def test_calendar_covers_every_day_with_no_gaps(self):
        cal = build_calendar("2015-02-18", "2015-03-31")
        assert len(cal) == 42
        assert cal["date"].diff().dropna().eq(pd.Timedelta(days=1)).all()

    def test_starts_at_the_gdelt_translingual_boundary(self):
        assert SAMPLE_START == pd.Timestamp("2015-02-18")
        assert build_calendar()["date"].min() == SAMPLE_START

    def test_regime_dummies_sum_to_one(self):
        cal = build_calendar()
        assert cal[[f"regime_{r}" for r in REGIMES]].sum(axis=1).eq(1).all()

    def test_buildup_precedes_invasion_precedes_attrition(self):
        assert BUILDUP_START < INVASION_DATE < ATTRITION_START
