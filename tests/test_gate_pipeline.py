"""Tests for the Gate-1/Gate-2 pipeline: episodes, ecosystems, perception indices.

Offline throughout. The ecosystem classifier is checked against the failure mode
that would silently destroy the result — Ukrainian outlets publishing in Russian
being filed as Russian media — because that error would not announce itself in
any downstream number; it would just make the two ecosystems agree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.ecosystems import (  # noqa: E402
    AGGREGATORS,
    RU_INDEPENDENT,
    RU_STATE,
    UA_REGISTER,
    build_case_sql,
)
from src.data.equities import build_basket, parse_chart  # noqa: E402
from src.features.episodes import (  # noqa: E402
    anticipation_score,
    find_episodes,
    label_episodes,
)
from src.features.perception import GATE, build_indices, validation_report  # noqa: E402


# --- ecosystem register ------------------------------------------------------


def test_registers_do_not_overlap():
    """An outlet in two ecosystems would be double-counted and silently bias both."""
    assert not (RU_STATE & RU_INDEPENDENT)
    assert not (RU_STATE & UA_REGISTER)
    assert not (RU_INDEPENDENT & UA_REGISTER)
    assert not (AGGREGATORS & (RU_STATE | RU_INDEPENDENT | UA_REGISTER))


def test_case_sql_puts_country_before_language():
    """The .ua rule must be emitted before any srclc rule.

    Ukrainian outlets publish heavily in Russian (24tv.ua: 2,595 Ukrainian and
    1,865 Russian articles in the sampled corpus). If the language branch ran
    first they would be classified as Russian media.
    """
    sql = build_case_sql()
    assert sql.index("'.ua'") < sql.index("srclc = 'rus'")
    assert sql.index("'.ru'") < sql.index("srclc = 'rus'")


def test_case_sql_excludes_aggregators_first():
    sql = build_case_sql()
    assert sql.index("AGGREGATOR") < sql.index("'.ua'")
    for domain in ("msn.com", "yahoo.com"):
        assert domain in sql


# --- episodes ----------------------------------------------------------------


@pytest.fixture
def synthetic_gpr() -> pd.DataFrame:
    """Flat risk, with one injected burst of threat and no acts."""
    n = 1200
    dates = pd.date_range("2018-01-01", periods=n, freq="B")
    rng = np.random.default_rng(3)
    act = pd.Series(100 + rng.normal(0, 5, n), index=dates)
    threat = pd.Series(100 + rng.normal(0, 5, n), index=dates)
    threat.iloc[900:1000] += 60  # the episode
    return pd.DataFrame({"date": dates, "gpr_act": act.values, "gpr_threat": threat.values})


def test_anticipation_score_is_computable_without_prices(synthetic_gpr):
    """Episode selection must not touch returns, or every later test is circular."""
    score = anticipation_score(synthetic_gpr)
    assert score.notna().sum() > 300
    assert "date" not in score.name


def test_find_episodes_recovers_an_injected_burst(synthetic_gpr):
    eps = find_episodes(anticipation_score(synthetic_gpr), threshold=0.5, min_days=20)
    assert len(eps) >= 1
    burst = synthetic_gpr["date"].iloc[930]
    assert ((eps["start"] <= burst) & (eps["end"] >= burst)).any()


def test_find_episodes_returns_empty_when_nothing_is_elevated():
    dates = pd.date_range("2018-01-01", periods=900, freq="B")
    rng = np.random.default_rng(1)
    flat = pd.DataFrame(
        {
            "date": dates,
            "gpr_act": 100 + rng.normal(0, 5, 900),
            "gpr_threat": 100 + rng.normal(0, 5, 900),
        }
    )
    eps = find_episodes(anticipation_score(flat), threshold=2.0, min_days=30)
    assert len(eps) == 0


def test_label_episodes_marks_a_containing_event():
    eps = pd.DataFrame(
        {
            "start": [pd.Timestamp("2022-01-01")],
            "end": [pd.Timestamp("2022-03-01")],
            "n_days": [42],
            "peak": [2.0],
            "mean": [1.0],
        }
    )
    out = label_episodes(eps, {"invasion": "2022-02-24"})
    assert out.loc[0, "label"] == "invasion"


# --- perception indices ------------------------------------------------------


@pytest.fixture
def daily_ecosystems() -> pd.DataFrame:
    days = pd.date_range("2021-06-01", periods=400, freq="D")
    rng = np.random.default_rng(5)
    rows = []
    for eco, base in [("WEST", 0.06), ("UA", 0.80), ("RU_STATE", 0.70),
                      ("RU_INDEP", 0.60), ("EN_GLOBAL", 0.05)]:
        for d in days:
            n_total = int(rng.integers(500, 5000))
            share = min(0.99, max(0.0, base + rng.normal(0, 0.01)))
            rows.append(
                {
                    "day": d,
                    "ecosystem": eco,
                    "n_total": n_total,
                    "n_conflict": int(n_total * share),
                    "share": share,
                    "tone_conflict": -2.0 + rng.normal(0, 0.2),
                    "tone_all": -1.0,
                }
            )
    return pd.DataFrame(rows)


def test_build_indices_is_wide_and_prefixed(daily_ecosystems):
    idx = build_indices(daily_ecosystems)
    for col in ("att_UA", "tone_UA", "vol_UA", "att_WEST"):
        assert col in idx.columns
    assert idx.index.name == "date"
    assert idx.index.is_monotonic_increasing


def test_validation_report_flags_collinear_ecosystems(daily_ecosystems):
    """Two ecosystems given identical series must fail the collinearity gate."""
    d = daily_ecosystems.copy()
    west = d[d.ecosystem == "WEST"].set_index("day")["share"]
    d.loc[d.ecosystem == "UA", "share"] = d.loc[d.ecosystem == "UA", "day"].map(west).values
    idx = build_indices(d)
    gpr = pd.Series(100.0, index=idx.index)
    _, corr, verdict = validation_report(idx, gpr)
    assert verdict["max_pairwise_corr"] > GATE["max_pairwise_corr"]
    assert not verdict["collinearity_pass"]
    assert not verdict["overall_pass"]


def test_validation_report_passes_collinearity_on_independent_series(daily_ecosystems):
    idx = build_indices(daily_ecosystems)
    gpr = pd.Series(100.0, index=idx.index)
    _, _, verdict = validation_report(idx, gpr)
    assert verdict["collinearity_pass"]


# --- equities ----------------------------------------------------------------


def test_parse_chart_rejects_empty_payload():
    with pytest.raises(ValueError, match="no result"):
        parse_chart({"chart": {"result": None, "error": "nope"}}, "XXX")


def test_build_basket_averages_constituents():
    dates = pd.date_range("2021-01-01", periods=5)
    a = pd.DataFrame({"date": dates, "adjclose": [100, 110, 110, 110, 110]})
    b = pd.DataFrame({"date": dates, "adjclose": [100, 100, 100, 100, 100]})
    out = build_basket({"A": a, "B": b})
    assert out.iloc[1] == pytest.approx(100 * np.log(1.1) / 2)
