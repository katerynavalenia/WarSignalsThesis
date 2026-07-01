"""Tests for src/data/gdelt_postprocess.py (Phase 3 gap-closure library).

These tests use small in-memory DataFrames — they do not read the
4.7 GB classified-articles parquet.  An end-to-end smoke test using a
small synthetic parquet lives in ``test_end_to_end_with_tmp_parquet``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.gdelt_postprocess import (  # noqa: E402
    HIGH_CONF_ARTICLE_COUNT,
    HIGH_CONF_PRIMARY_PCT,
    SOURCE_GROUPS,
    add_narrative_gap,
    auto_precision_check,
    build_query_group_pivot,
    fix_date_index,
    write_auto_precision_report,
)


# ── fix_date_index ────────────────────────────────────────────────────────
def test_fix_date_index_moves_date_from_index_to_column():
    df = pd.DataFrame(
        {"n_articles_western": [1, 2, 3], "tone_western": [-1.0, -0.5, 0.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    df.index.name = "date"
    out = fix_date_index(df)
    assert "date" in out.columns
    assert out.index.name is None
    # 'date' should be the first column.
    assert out.columns[0] == "date"
    assert len(out) == 3


def test_fix_date_index_idempotent_when_date_already_a_column():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "n_articles_western": [10, 20],
    })
    out = fix_date_index(df)
    assert list(out.columns) == ["date", "n_articles_western"]
    assert len(out) == 2


# ── add_narrative_gap ─────────────────────────────────────────────────────
def test_add_narrative_gap_creates_three_gap_columns():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "tone_ukrainian": [-4.0, -3.0],
        "tone_russian":   [-3.5, -2.5],
        "tone_western":   [-1.0, -0.5],
    })
    out = add_narrative_gap(df)
    assert "narrative_gap_ua_west" in out.columns
    assert "narrative_gap_ru_west" in out.columns
    assert "narrative_gap_ua_ru" in out.columns
    np.testing.assert_allclose(
        out["narrative_gap_ua_west"].values, [-3.0, -2.5]
    )
    np.testing.assert_allclose(
        out["narrative_gap_ru_west"].values, [-2.5, -2.0]
    )
    np.testing.assert_allclose(
        out["narrative_gap_ua_ru"].values, [-0.5, -0.5]
    )


def test_add_narrative_gap_copies_article_counts_into_n_tone_columns():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "n_articles_ukrainian": [100, 50],
        "n_articles_russian":   [80, 40],
        "n_articles_western":   [1000, 900],
        "n_articles_other":     [50, 25],
        "n_articles_total":     [1230, 1015],
        "tone_ukrainian": [-3.0, -2.0],
        "tone_russian":   [-3.0, -2.0],
        "tone_western":   [-1.0, -1.0],
        "tone_other":     [0.0, 0.0],
    })
    out = add_narrative_gap(df)
    for g in SOURCE_GROUPS:
        n_articles = f"n_articles_{g}"
        n_tone = f"n_tone_{g}"
        assert n_tone in out.columns
        np.testing.assert_array_equal(out[n_tone].values, out[n_articles].values)


def test_add_narrative_gap_skips_missing_columns_gracefully():
    # If tone_ukrainian is missing, the gap involving it should be skipped.
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]),
        "tone_western": [-1.0],
    })
    out = add_narrative_gap(df)
    assert "narrative_gap_ua_west" not in out.columns
    assert "narrative_gap_ru_west" not in out.columns
    assert "narrative_gap_ua_ru" not in out.columns


# ── build_query_group_pivot ───────────────────────────────────────────────
def test_build_pivot_shape_is_n_days_by_16():
    n_days = 5
    rows = []
    for d in range(n_days):
        for q in ("russian_attack_direct", "ukraine_defense_energy",
                  "defense_industry_western", "energy_war"):
            for g in SOURCE_GROUPS:
                rows.append({
                    "date": pd.Timestamp(f"2024-01-{d+1:02d}"),
                    "query_name": q,
                    "source_group": g,
                })
    # Add some article counts (just integers 1..N).
    articles = pd.DataFrame(rows)
    articles["count"] = 1
    pivot = build_query_group_pivot(articles)
    assert pivot.shape == (n_days, 17)  # 16 query-group cols + date
    assert pivot.columns[0] == "date"
    # All 16 combos should be present.
    expected_cols = {
        f"n_{g}_{q}"
        for q in ("russian_attack_direct", "ukraine_defense_energy",
                  "defense_industry_western", "energy_war")
        for g in SOURCE_GROUPS
    }
    assert set(pivot.columns) == expected_cols | {"date"}


def test_build_pivot_counts_match_input():
    articles = pd.DataFrame([
        {"date": pd.Timestamp("2024-01-01"),
         "query_name": "russian_attack_direct", "source_group": "ukrainian"},
        {"date": pd.Timestamp("2024-01-01"),
         "query_name": "russian_attack_direct", "source_group": "ukrainian"},
        {"date": pd.Timestamp("2024-01-01"),
         "query_name": "russian_attack_direct", "source_group": "russian"},
        {"date": pd.Timestamp("2024-01-02"),
         "query_name": "defense_industry_western", "source_group": "western"},
    ])
    pivot = build_query_group_pivot(articles)
    assert pivot.loc[
        pivot["date"] == pd.Timestamp("2024-01-01"), "n_ukrainian_russian_attack_direct"
    ].iloc[0] == 2
    assert pivot.loc[
        pivot["date"] == pd.Timestamp("2024-01-01"), "n_russian_russian_attack_direct"
    ].iloc[0] == 1
    assert pivot.loc[
        pivot["date"] == pd.Timestamp("2024-01-02"), "n_western_defense_industry_western"
    ].iloc[0] == 1


# ── auto_precision_check ──────────────────────────────────────────────────
def _make_dc(domains_with_counts: list[tuple[str, str, int, int]]) -> pd.DataFrame:
    """Build a synthetic domain_to_country frame.

    Each tuple is (domain, primary_country, primary_count, article_count).
    """
    return pd.DataFrame(
        domains_with_counts,
        columns=["domain", "primary_country", "primary_country_count", "article_count"],
    )


def test_auto_precision_perfect_agreement_when_classifier_matches_country():
    articles = pd.DataFrame({
        "domain": ["a.com", "b.com", "c.com"],
        "source_group": ["western", "russian", "ukrainian"],
        "classification_method": ["country", "country", "country"],
    })
    # a.com → US (western), b.com → RU (russian), c.com → UA (ukrainian).
    dc = _make_dc([
        ("a.com", "US", 200, 200),   # 100 % US
        ("b.com", "RU", 200, 200),   # 100 % RU
        ("c.com", "UA", 200, 200),   # 100 % UA
    ])
    report = auto_precision_check(articles, dc)
    assert report["overall"]["precision"] == 1.0
    assert report["n_articles_kept"] == 3
    assert report["thresholds"]["article_count_min"] == HIGH_CONF_ARTICLE_COUNT
    assert report["thresholds"]["primary_pct_min"] == HIGH_CONF_PRIMARY_PCT


def test_auto_precision_drops_low_confidence_domains():
    articles = pd.DataFrame({
        "domain": ["a.com", "low.com"],
        "source_group": ["western", "western"],
        "classification_method": ["country", "country"],
    })
    dc = _make_dc([
        # High confidence: included.
        ("a.com",  "US", 200, 200),
        # Low confidence: only 50 articles AND only 60 % primary → excluded.
        ("low.com", "US",  30,  50),
    ])
    report = auto_precision_check(articles, dc)
    # Only a.com is kept.
    assert report["n_articles_kept"] == 1
    assert report["overall"]["n"] == 1


def test_auto_precision_known_groups_in_by_group():
    articles = pd.DataFrame({
        "domain": ["a.com"] * 3,
        "source_group": ["western", "russian", "ukrainian"],
        "classification_method": ["country"] * 3,
    })
    dc = _make_dc([
        ("a.com", "US", 200, 200),
    ])
    report = auto_precision_check(articles, dc)
    # expected_group is derived from "US" → western.
    # Only the article whose source_group is "western" is correct.
    assert report["overall"]["n_correct"] == 1
    assert report["overall"]["n"] == 3
    # Per-group counts: only the 'western' expected group has any articles.
    assert report["by_group"]["western"]["n"] == 3
    assert report["by_group"]["western"]["n_correct"] == 1
    assert report["by_group"]["western"]["precision"] == pytest.approx(1 / 3)


def test_auto_precision_reports_all_four_methods():
    articles = pd.DataFrame({
        "domain": ["a.com"] * 4,
        "source_group": ["western", "russian", "ukrainian", "other"],
        "classification_method": ["country", "domain", "tld", "fallback"],
    })
    dc = _make_dc([("a.com", "US", 200, 200)])
    report = auto_precision_check(articles, dc)
    for m in ("country", "domain", "tld", "fallback"):
        assert m in report["by_method"]
        assert "precision" in report["by_method"][m]
        assert "n" in report["by_method"][m]


# ── write_auto_precision_report ───────────────────────────────────────────
def test_write_auto_precision_report(tmp_path):
    report = {
        "thresholds": {"article_count_min": 100, "primary_pct_min": 0.7},
        "n_domains_kept": 10,
        "n_articles_kept": 1000,
        "by_method": {
            "country":  {"precision": 0.95, "n": 800, "n_correct": 760},
            "domain":   {"precision": 0.90, "n": 100, "n_correct":  90},
            "tld":      {"precision": 0.80, "n":  50, "n_correct":  40},
            "fallback": {"precision": 0.00, "n":  50, "n_correct":   0},
        },
        "by_group": {
            "ukrainian": {"precision": 0.91, "n": 100, "n_correct":  91},
            "russian":   {"precision": 0.93, "n": 100, "n_correct":  93},
            "western":   {"precision": 0.85, "n": 700, "n_correct": 595},
            "other":     {"precision": 0.50, "n": 100, "n_correct":  50},
        },
        "overall": {"precision": 0.85, "n": 1000, "n_correct": 850},
    }
    out = tmp_path / "report.md"
    write_auto_precision_report(report, out)
    text = out.read_text(encoding="utf-8")
    assert "Automated Precision Report" in text
    assert "country" in text
    assert "ukrainian" in text
    assert "0.950" in text  # country precision
    assert "1,000" in text  # articles kept, comma-formatted


# ── end-to-end with a small synthetic parquet (no 4.7 GB read) ───────────
def test_end_to_end_with_tmp_parquet(tmp_path, monkeypatch):
    """Simulate the orchestrator on a tiny synthetic articles parquet."""
    # Build a tiny synthetic articles frame.
    np.random.seed(0)
    n = 1000
    domains = np.random.choice(
        [f"d{i}.com" for i in range(20)] + ["ua.ua", "ru.ru"],
        size=n,
    )
    countries = np.random.choice(
        ["US", "RU", "UA", "DE", "FR", ""], size=n
    )
    # Use per-row random dates so all 3 days are present.
    day_offsets = np.random.randint(0, 3, size=n)
    articles = pd.DataFrame({
        "date": pd.to_datetime("2024-06-01") + pd.to_timedelta(
            day_offsets, unit="D"
        ),
        "domain": domains,
        "query_name": np.random.choice(
            ["russian_attack_direct", "defense_industry_western", "energy_war"],
            size=n,
        ),
        "source_group": np.random.choice(
            list(SOURCE_GROUPS), size=n
        ),
        "classification_method": np.random.choice(
            ["country", "domain", "tld", "fallback"], size=n
        ),
        "countries": countries,
        "url": [f"http://{d}/{i}" for i, d in enumerate(domains)],
    })
    articles_path = tmp_path / "articles.parquet"
    articles.to_parquet(articles_path, index=False)

    # Build a tiny daily aggregate and a tiny domain_to_country.
    daily = pd.DataFrame({
        "date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
        "n_articles_ukrainian": [5, 7, 3],
        "n_articles_russian":   [3, 4, 2],
        "n_articles_western":   [80, 90, 70],
        "n_articles_other":     [12, 10, 8],
        "n_articles_total":     [100, 111, 83],
        "tone_ukrainian":       [-3.0, -3.5, -2.8],
        "tone_russian":         [-3.0, -3.2, -2.9],
        "tone_western":         [-1.0, -0.8, -1.1],
        "tone_other":           [0.0, 0.1, -0.1],
    })
    # Set 'date' as index to mirror the actual file's quirk.
    daily_indexed = daily.set_index("date")
    daily_path = tmp_path / "daily.parquet"
    daily_indexed.to_parquet(daily_path)  # writes with date as index

    # domain_to_country with enough data for the precision filter.
    dc_rows = []
    for i, d in enumerate([f"d{i}.com" for i in range(20)] + ["ua.ua", "ru.ru"]):
        country = "US" if d.endswith(".com") else (
            "UA" if d.endswith(".ua") else "RU"
        )
        # Ensure enough articles to pass the high-confidence threshold.
        dc_rows.append((d, country, 200, 200))
    domain_path = tmp_path / "domain_to_country.csv"
    pd.DataFrame(
        dc_rows, columns=["domain", "primary_country", "primary_country_count", "article_count"]
    ).to_csv(domain_path, index=False)

    # Patch the project-level paths.
    from src.data import gdelt_postprocess as gp
    monkeypatch.setattr(gp, "ARTICLES_PATH", articles_path, raising=False)
    # Run each step manually on the tmp paths.
    from src.data.gdelt_postprocess import (
        add_narrative_gap,
        auto_precision_check,
        build_query_group_pivot,
        fix_date_index,
        load_articles_columns,
        write_auto_precision_report,
    )

    # Step 1+2
    d = pd.read_parquet(daily_path)
    d = fix_date_index(d)
    d = add_narrative_gap(d)
    assert "date" in d.columns
    assert "narrative_gap_ua_west" in d.columns
    assert "n_tone_ukrainian" in d.columns

    # Step 3
    a = load_articles_columns(articles_path, ["date", "query_name", "source_group"])
    pv = build_query_group_pivot(a)
    assert pv.shape[0] == 3
    assert pv.shape[1] == 17

    # Step 4
    a2 = load_articles_columns(
        articles_path, ["domain", "source_group", "classification_method"]
    )
    dc = pd.read_csv(domain_path)
    rep = auto_precision_check(a2, dc)
    assert rep["n_articles_kept"] > 0
    assert 0.0 <= rep["overall"]["precision"] <= 1.0

    out_md = tmp_path / "precision.md"
    write_auto_precision_report(rep, out_md)
    assert out_md.exists()
    assert "Automated Precision Report" in out_md.read_text(encoding="utf-8")
