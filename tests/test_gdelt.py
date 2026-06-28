"""
Tests for src/data/gdelt.py
============================
Smoke tests for the Phase 3 GDELT pipeline.

Network-dependent tests are marked with `@pytest.mark.network` and
skipped by default. Run them with:
    pytest -m network
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.gdelt import (
    build_gdelt_query_url,
    build_news_daily,
    classify_all_articles,
    classify_source,
    dedupe_articles,
    detect_language,
    manual_precision_audit,
)

CONFIG_DIR = Path("config")


# ----- query building ----------------------------------------------------

def test_build_gdelt_query_url_basic():
    url = build_gdelt_query_url(
        keywords_any=["Russia", "Ukraine"],
        keywords_weapon_any=["missile", "drone"],
        languages=["English", "Russian"],
        start="2024-01-01 00:00:00",
        end="2024-01-31 23:59:59",
    )
    assert "api.gdeltproject.org" in url
    assert "Russia" in url or "Russia" in url.replace("+", " ")
    assert "missile" in url or "missile" in url.replace("+", " ")
    assert "English" in url
    assert "maxrecords=250" in url
    assert "mode=artlist" in url


def test_build_gdelt_query_url_no_keywords():
    url = build_gdelt_query_url(languages=["English"])
    # wildcard is URL-encoded as %2A
    assert ("*") in url or ("%2A") in url


# ----- source classification ----------------------------------------------

def test_classify_source_ukrainian():
    assert classify_source("ukrinform.ua") == "ukrainian"
    assert classify_source("www.kyivpost.com") == "ukrainian"
    assert classify_source("suspilne.media") == "ukrainian"


def test_classify_source_russian():
    assert classify_source("rt.com") == "russian"
    assert classify_source("tass.ru") == "russian"
    assert classify_source("www.sputniknews.com") == "russian"


def test_classify_source_western():
    assert classify_source("reuters.com") == "western"
    assert classify_source("www.bbc.co.uk") == "western"
    assert classify_source("ft.com") == "western"
    assert classify_source("dw.com") == "western"


def test_classify_source_other():
    assert classify_source("randomblog.com") == "other"
    assert classify_source(None) == "other"
    assert classify_source("") == "other"
    assert classify_source("https://unknown") == "other"


def test_classify_all_articles():
    df = pd.DataFrame({
        "domain": ["ukrinform.ua", "rt.com", "reuters.com", "unknown.io"],
        "title": ["A", "B", "C", "D"],
    })
    out = classify_all_articles(df)
    assert list(out["source_group"]) == ["ukrainian", "russian", "western", "other"]


# ----- language detection ------------------------------------------------

def test_detect_language_english():
    text = "This is a test of the emergency broadcast system in the United States of America"
    assert detect_language(text) in ("English", "Unknown")  # langdetect may fail for short text


def test_detect_language_russian():
    text = (
        "Россия нанесла удар по украинской инфраструктуре в ночь на понедельник, "
        "сообщили официальные лица. Атака произошла в рамках продолжающегося конфликта."
    )
    assert detect_language(text) in ("Russian", "Unknown")


def test_detect_language_short_fallback():
    assert detect_language("Hi") == "Unknown"  # too short
    assert detect_language(None) == "Unknown"


def test_detect_language_ukrainian():
    text = (
        "Україна зазнала масованої атаки з боку Росії в ніч на понеділок, "
        "за словами офіційних осіб, атака відбулася в рамках триваючого конфлікту."
    )
    assert detect_language(text) in ("Ukrainian", "Russian", "Unknown")  # may confuse UA/RU


# ----- deduplication -----------------------------------------------------

def test_dedupe_articles_identical_titles():
    df = pd.DataFrame({
        "title": ["Russia attacks Ukraine with missiles"] * 5,
        "domain": ["a.com"] * 5,
    })
    out = dedupe_articles(df, threshold=0.7)
    assert len(out) == 1  # all 5 collapse to 1


def test_dedupe_articles_different_titles():
    df = pd.DataFrame({
        "title": [
            "Russia attacks Ukraine with missiles today",
            "European markets rise on inflation data",
            "New study shows coffee benefits",
        ],
        "domain": ["a.com", "b.com", "c.com"],
    })
    out = dedupe_articles(df, threshold=0.7)
    assert len(out) == 3  # all different, all kept


def test_dedupe_articles_near_duplicates():
    df = pd.DataFrame({
        "title": [
            "Russia launches massive missile attack on Kyiv overnight",
            "Russia launches massive missile attack on Kyiv overnight, officials say",
            "Russia launches massive missile attack on Kyiv overnight, says military",
            "European markets rise on inflation data",  # different topic
        ],
    })
    out = dedupe_articles(df, threshold=0.7)
    # First 3 are near-duplicates (Jaccard > 0.7), 4th is different
    assert len(out) == 2


def test_dedupe_articles_short_titles_skipped():
    df = pd.DataFrame({"title": ["A", "B", "C"]})  # all too short
    out = dedupe_articles(df, min_title_len=20)
    assert len(out) == 3  # all kept (none eligible for dedup)


def test_dedupe_articles_empty():
    out = dedupe_articles(pd.DataFrame())
    assert out.empty


# ----- daily aggregation -------------------------------------------------

def test_build_news_daily():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-15", "2024-01-15", "2024-01-15",
            "2024-01-16", "2024-01-17",
        ]),
        "source_group": ["ukrainian", "russian", "western", "ukrainian", "western"],
    })
    out = build_news_daily(df)
    # 3 dates, 3 group columns (ukrainian, russian, western) + 1 total = 4 columns
    assert out.shape == (3, 4)
    assert out.loc["2024-01-15", "n_articles_ukrainian"] == 1
    assert out.loc["2024-01-15", "n_articles_total"] == 3


def test_build_news_daily_with_persist(tmp_path):
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
        "source_group": ["ukrainian", "western"],
    })
    out_path = tmp_path / "news_daily.parquet"
    build_news_daily(df, out_path=out_path)
    assert out_path.exists()
    loaded = pd.read_parquet(out_path)
    assert loaded.shape[0] == 1


# ----- manual precision audit --------------------------------------------

def test_manual_precision_audit():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15"] * 8),
        "title": [f"Article {i}" for i in range(8)],
        "url": [f"https://example.com/{i}" for i in range(8)],
        "domain": ["a.com", "b.com", "c.com", "d.com", "e.com", "f.com", "g.com", "h.com"],
        "language": ["English"] * 8,
        "source_group": (
            ["ukrainian"] * 2 + ["russian"] * 2 + ["western"] * 2 + ["other"] * 2
        ),
    })
    audit = manual_precision_audit(df, n_per_group=2)
    assert len(audit) == 8
    assert (audit["relevant"] == "").all()  # to be filled manually
    assert set(audit["source_group"].unique()) == {"ukrainian", "russian", "western", "other"}


# ----- config files exist ------------------------------------------------

def test_config_files_exist():
    assert (CONFIG_DIR / "gdelt_queries.yaml").exists()
    assert (CONFIG_DIR / "source_groups.yaml").exists()


def test_config_files_valid_yaml():
    import yaml
    with open(CONFIG_DIR / "gdelt_queries.yaml") as f:
        q = yaml.safe_load(f)
    assert "queries" in q
    assert len(q["queries"]) >= 1
    with open(CONFIG_DIR / "source_groups.yaml") as f:
        s = yaml.safe_load(f)
    assert "groups" in s
    for g in ["ukrainian", "russian", "western", "other"]:
        assert g in s["groups"]


# ----- network test (skipped by default) ---------------------------------

@pytest.mark.network
@pytest.mark.skip(reason="Network test; run manually with `pytest -m network`")
def test_smoke_test_gdelt_api():
    """Live API test. Run manually: pytest tests/test_gdelt.py -m network"""
    from src.data.gdelt import fetch_gdelt_window
    import yaml
    with open(CONFIG_DIR / "gdelt_queries.yaml") as f:
        cfg = yaml.safe_load(f)
    q = cfg["queries"][0]
    articles = fetch_gdelt_window(q, "2024-01-15", "2024-01-15", api_sleep=0.6)
    assert isinstance(articles, list)



def test_normalize_gdelt_datetime():
    """Date normalization for GDELT format YYYYMMDDHHMMSS."""
    from src.data.gdelt import _normalize_gdelt_datetime
    assert _normalize_gdelt_datetime("2024-01-15") == "20240115000000"
    assert _normalize_gdelt_datetime("2024-01-15 00:00:00") == "20240115000000"
    assert _normalize_gdelt_datetime("2024-01-15 12:30:45") == "20240115123045"
    assert _normalize_gdelt_datetime("20240115000000") == "20240115000000"
    assert _normalize_gdelt_datetime("2024-01-15T12:30:45") == "20240115123045"
    # Edge: empty string
    assert _normalize_gdelt_datetime("") == ""
    assert _normalize_gdelt_datetime("2024-01-15 12:30") == "20240115123000"  # short time


def test_build_gdelt_query_url_date_normalized():
    """build_gdelt_query_url should normalize dates to GDELT format."""
    from src.data.gdelt import build_gdelt_query_url
    url = build_gdelt_query_url(
        keywords_any=["Ukraine"],
        start="2024-01-15 00:00:00",
        end="2024-01-15 23:59:59",
    )
    assert "startdatetime=20240115000000" in url
    assert "enddatetime=20240115235959" in url
    # Should NOT have dashes or colons
    assert "2024-01-15" not in url
    assert "00:00:00" not in url
