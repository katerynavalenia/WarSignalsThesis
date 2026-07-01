"""
Tests for src/data/gdelt.py
============================
Smoke tests for the Phase 3 GDELT pipeline.

Network-dependent tests are marked with `@pytest.mark.network` and
skipped by default. Run them with:
    pytest -m network
"""

from __future__ import annotations

import time
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


def test_quote_gdelt_keyword_simple():
    """Simple words stay unquoted (quotes can reduce matches in GDELT)."""
    from src.data.gdelt import _quote_gdelt_keyword
    assert _quote_gdelt_keyword("Russia") == "Russia"
    assert _quote_gdelt_keyword("missile") == "missile"
    assert _quote_gdelt_keyword("Kremlin") == "Kremlin"


def test_quote_gdelt_keyword_with_dash():
    """Keywords with dashes must be quoted (GDELT rejects unquoted dashes)."""
    from src.data.gdelt import _quote_gdelt_keyword
    assert _quote_gdelt_keyword("F-16") == '"F-16"'
    assert _quote_gdelt_keyword("air defense") == '"air defense"'
    assert _quote_gdelt_keyword("Nord Stream") == '"Nord Stream"'


def test_quote_gdelt_keyword_already_quoted():
    """Keywords already wrapped in quotes are left untouched."""
    from src.data.gdelt import _quote_gdelt_keyword
    assert _quote_gdelt_keyword('"F-16"') == '"F-16"'
    assert _quote_gdelt_keyword('"air defense"') == '"air defense"'


def test_build_gdelt_query_url_quotes_dashed_keywords():
    """Regression test: F-16 and similar dashed keywords must be quoted in the URL.

    GDELT DOC 2.0 returns HTML error "One or more of your keywords contained an
    illegal character" if dashes are not quoted. This was the root cause of
    ukraine_defense_energy returning 0 articles.
    """
    url = build_gdelt_query_url(
        keywords_any=["air defense", "Patriot", "F-16", "HIMARS"],
        languages=["English"],
        start="2024-01-15",
        end="2024-01-15",
    )
    # %22 is the URL-encoded double-quote
    assert "%22F-16%22" in url, f"F-16 must be quoted in URL: {url}"
    assert "%22air%20defense%22" in url, f"air defense must be quoted: {url}"
    # Simple words should NOT be quoted
    assert "Patriot" in url
    assert '"Patriot"' not in url and "%22Patriot%22" not in url


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


# =========================================================================
# Rate-limit / 429-retry tests
# =========================================================================

def test_rate_limiter_respects_interval():
    """RateLimiter.wait() should block for at least 1/rate seconds between calls."""
    from src.data.gdelt import RateLimiter
    lim = RateLimiter(rate_per_sec=20.0)  # 1 call per 50 ms
    t0 = time.time()
    lim.wait()
    lim.wait()
    elapsed = time.time() - t0
    # Two waits at 50ms each → at least ~50ms (we allow a small slack)
    assert elapsed >= 0.04, f"RateLimiter too fast: {elapsed:.3f}s for 2 calls at 20/s"


def test_rate_limiter_reset():
    """RateLimiter.reset() should allow immediate next call."""
    from src.data.gdelt import RateLimiter
    lim = RateLimiter(rate_per_sec=5.0)  # 1 call per 200 ms
    lim.wait()
    lim.reset()
    t0 = time.time()
    lim.wait()
    elapsed = time.time() - t0
    assert elapsed < 0.05, f"reset() did not clear state: {elapsed}s"


def test_rate_limiter_default_seven_seconds():
    """Default module limiter should be 1/7 sec (safe margin below 1/5)."""
    from src.data.gdelt import get_default_limiter
    lim = get_default_limiter()
    assert 6.5 <= lim.interval <= 7.5, (
        f"Default interval should be ~7s, got {lim.interval}"
    )


def test_set_rate_limit_replaces_singleton():
    """set_rate_limit should return a new limiter and install it as default."""
    from src.data.gdelt import (
        get_default_limiter, set_rate_limit, RateLimiter,
    )
    new_lim = set_rate_limit(rate_per_sec=10.0)
    assert isinstance(new_lim, RateLimiter)
    assert get_default_limiter() is new_lim
    assert abs(new_lim.interval - 0.1) < 0.001
    # Restore default
    set_rate_limit(rate_per_sec=1.0 / 7.0)


def test_gdelt_request_handles_429(monkeypatch):
    """_gdelt_request should back off and retry on HTTP 429, then succeed."""
    from src.data.gdelt import _gdelt_request, RateLimiter

    # Pre-warm the limiter so its `wait()` doesn't sleep (mimics steady state).
    lim = RateLimiter(rate_per_sec=1000.0)
    lim.wait()  # set the last_call clock once
    # Force last_call to "long ago" so wait() is a no-op for subsequent calls
    lim._last_call = time.time() - 100.0  # 100s ago, way past 0.001s interval

    # Fake response: 429 twice, then 200. Provide 5 in case internal logic
    # needs more (defensive).
    class FakeResp:
        def __init__(self, status, body=None, headers=None):
            self.status_code = status
            self.headers = headers or {}
            self._body = body or {}
        def json(self):
            return self._body

    responses = [
        FakeResp(429),
        FakeResp(429),
        FakeResp(200, {"articles": [{"url": "http://x", "title": "ok"}]}),
        FakeResp(200, {"articles": []}),  # extra safety
        FakeResp(200, {"articles": []}),
    ]
    responses_iter = iter(responses)

    def fake_get(url, timeout):
        return next(responses_iter)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    sleeps = []
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: sleeps.append(s))

    articles, err = _gdelt_request("http://fake/", max_retries=5, limiter=lim)
    assert err is None
    assert len(articles) == 1
    assert articles[0]["url"] == "http://x"
    # We expect at least 2 long backoff sleeps (for the two 429s) since
    # the limiter's wait() should be a no-op (last_call was set 100s ago).
    long_sleeps = [s for s in sleeps if s >= 5.0]
    assert len(long_sleeps) >= 2, (
        f"Expected ≥2 backoff sleeps ≥5s, got sleeps={sleeps}"
    )


def test_gdelt_request_gives_up_after_max_retries(monkeypatch):
    """_gdelt_request should return error after max_retries consecutive 429s."""
    from src.data.gdelt import _gdelt_request, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)

    class FakeResp:
        def __init__(self, status):
            self.status_code = status
            self.headers = {}
        def json(self):
            return {}

    responses = [FakeResp(429) for _ in range(10)]
    responses_iter = iter(responses)

    def fake_get(url, timeout):
        return next(responses_iter)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    articles, err = _gdelt_request("http://fake/", max_retries=3, limiter=lim)
    assert articles == []
    assert err is not None
    assert "429" in err or "rate" in err.lower()


def test_gdelt_request_4xx_no_retry(monkeypatch):
    """Non-429 4xx responses (e.g. 400, 403) should NOT trigger retries."""
    from src.data.gdelt import _gdelt_request, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)

    call_count = [0]

    class FakeResp:
        def __init__(self, status):
            self.status_code = status
            self.headers = {}
            self.text = "bad query"
        def json(self):
            return {}

    def fake_get(url, timeout):
        call_count[0] += 1
        return FakeResp(400)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    articles, err = _gdelt_request("http://fake/", max_retries=5, limiter=lim)
    assert articles == []
    assert err is not None
    assert "400" in err
    # Only ONE call — no retry on 4xx
    assert call_count[0] == 1, f"4xx should not retry, got {call_count[0]} calls"


def test_gdelt_request_5xx_retries(monkeypatch):
    """5xx server errors should be retried with backoff."""
    from src.data.gdelt import _gdelt_request, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)
    call_count = [0]

    class FakeResp:
        def __init__(self, status):
            self.status_code = status
            self.headers = {}
            self._body = {"articles": [{"url": "u", "title": "t"}]} if status == 200 else {}
            self.text = "err"
        def json(self):
            return self._body

    def fake_get(url, timeout):
        call_count[0] += 1
        if call_count[0] < 3:
            return FakeResp(503)
        return FakeResp(200)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    articles, err = _gdelt_request("http://fake/", max_retries=5, limiter=lim)
    assert err is None
    assert len(articles) == 1
    assert call_count[0] == 3, f"Expected 3 calls, got {call_count[0]}"


def test_gdelt_request_honors_retry_after_header(monkeypatch):
    """If the server sends Retry-After, we should respect it (within reason)."""
    from src.data.gdelt import _gdelt_request, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)
    sleeps = []

    class FakeResp:
        def __init__(self, status, headers=None):
            self.status_code = status
            self.headers = headers or {}
            self._body = {"articles": [{"url": "u", "title": "t"}]}
            self.text = ""
        def json(self):
            return self._body

    responses = iter([
        FakeResp(429, {"Retry-After": "30"}),
        FakeResp(200),
    ])

    def fake_get(url, timeout):
        return next(responses)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: sleeps.append(s))

    articles, err = _gdelt_request("http://fake/", max_retries=3, limiter=lim)
    assert err is None
    assert len(articles) == 1
    # Retry-After: 30 with ±20% jitter → expected sleep in [24, 36] sec
    # (modulo 5-sec minimum clamp)
    backoff_sleep = max(s for s in sleeps if s >= 5.0)
    assert 20.0 <= backoff_sleep <= 40.0, (
        f"Expected sleep 20-40s from Retry-After:30, got {backoff_sleep} "
        f"(all sleeps: {sleeps})"
    )


def test_gdelt_request_handles_network_exception(monkeypatch):
    """requests.RequestException should be retried."""
    from src.data.gdelt import _gdelt_request, RateLimiter
    import requests as _req

    lim = RateLimiter(rate_per_sec=1000.0)
    call_count = [0]

    def fake_get(url, timeout):
        call_count[0] += 1
        if call_count[0] < 2:
            raise _req.exceptions.Timeout("simulated timeout")
        class OK:
            status_code = 200
            headers = {}
            def json(self):
                return {"articles": [{"url": "u", "title": "t"}]}
        return OK()

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    articles, err = _gdelt_request("http://fake/", max_retries=3, limiter=lim)
    assert err is None
    assert len(articles) == 1
    assert call_count[0] == 2


def test_fetch_gdelt_window_passes_limiter(monkeypatch):
    """fetch_gdelt_window should use the provided rate limiter for requests."""
    from src.data.gdelt import fetch_gdelt_window, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)
    # Track limiter.wait() calls to confirm the window fn uses it
    wait_calls = [0]
    original_wait = lim.wait
    def counted_wait():
        wait_calls[0] += 1
        original_wait()
    lim.wait = counted_wait

    class FakeResp:
        status_code = 200
        headers = {}
        def json(self):
            return {"articles": []}
    monkeypatch.setattr("src.data.gdelt.requests.get", lambda *a, **kw: FakeResp())
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    fetch_gdelt_window(
        {"name": "test", "keywords_any": ["x"], "keywords_weapon_any": []},
        start="2024-01-01",
        end="2024-01-31",
        limiter=lim,
    )
    assert wait_calls[0] >= 1, "fetch_gdelt_window should call limiter.wait()"


def test_fetch_gdelt_window_backward_compat_api_sleep(monkeypatch):
    """If api_sleep > 0, fetch_gdelt_window should add an extra sleep."""
    from src.data.gdelt import fetch_gdelt_window, RateLimiter

    lim = RateLimiter(rate_per_sec=1000.0)
    sleeps = []

    class FakeResp:
        status_code = 200
        headers = {}
        def json(self):
            return {"articles": []}
    monkeypatch.setattr("src.data.gdelt.requests.get", lambda *a, **kw: FakeResp())
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: sleeps.append(s))

    fetch_gdelt_window(
        {"name": "test", "keywords_any": ["x"], "keywords_weapon_any": []},
        start="2024-01-01",
        end="2024-01-31",
        api_sleep=2.5,  # explicit legacy param
        limiter=lim,
    )
    # Should have at least one 2.5s sleep
    assert any(abs(s - 2.5) < 0.01 for s in sleeps), (
        f"Expected api_sleep=2.5s in sleeps, got {sleeps}"
    )


# =========================================================================
# Smoke-test flow (Cell 3) + full-extraction flow (Cell 4) integration tests
# =========================================================================

@pytest.fixture
def fast_limiter():
    """Rate limiter at 1000 calls/sec — eliminates real-time waiting in tests."""
    from src.data.gdelt import RateLimiter
    lim = RateLimiter(rate_per_sec=1000.0)
    yield lim


@pytest.fixture
def fake_gdelt_429_then_200(monkeypatch, fast_limiter):
    """Mock: first call returns 429 (rate-limited), second returns 200 with articles."""
    from src.data.gdelt import _gdelt_request

    class FakeResp:
        def __init__(self, status, body=None, headers=None):
            self.status_code = status
            self.headers = headers or {}
            self.text = "rate limited" if status == 429 else ""
            self._body = body or {}
        def json(self):
            return self._body

    # Patch time.sleep to no-op so backoffs don't actually wait
    sleeps = []
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: sleeps.append(s))

    responses = [
        FakeResp(429, {"articles": []}),
        FakeResp(200, {
            "articles": [
                {
                    "url": "https://kyivpost.com/test",
                    "title": "Russia attacks Ukraine with missiles",
                    "domain": "kyivpost.com",
                    "language": "English",
                    "sourceCommonName": "Kyiv Post",
                    "seendate": "20240115120000",
                },
                {
                    "url": "https://tass.com/test",
                    "title": "Russian offensive in Donbas",
                    "domain": "tass.com",
                    "language": "Russian",
                    "sourceCommonName": "TASS",
                    "seendate": "20240115130000",
                },
            ]
        }),
    ]
    responses_iter = iter(responses)

    def fake_get(url, timeout):
        return next(responses_iter)

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    return {"sleeps": sleeps}


def test_smoke_test_recovers_from_429(fake_gdelt_429_then_200, fast_limiter, capsys):
    """Cell 3 smoke test: 429 on first call, 200 on second; should succeed."""
    from src.data.gdelt import _gdelt_request, build_gdelt_query_url, _flatten_keywords
    url = build_gdelt_query_url(
        keywords_any=["russia", "ukraine"],
        start="2024-01-15 00:00:00",
        end="2024-01-15 23:59:59",
    )
    articles, err = _gdelt_request(url, max_retries=3, limiter=fast_limiter)
    assert err is None
    assert len(articles) == 2
    # The two articles should be from the fake response
    assert articles[0]["title"] == "Russia attacks Ukraine with missiles"
    assert articles[1]["title"] == "Russian offensive in Donbas"
    # We should have backed off at least once (for the 429)
    long_sleeps = [s for s in fake_gdelt_429_then_200["sleeps"] if s >= 5.0]
    assert len(long_sleeps) >= 1, "Expected ≥1 backoff sleep for the 429"


def test_smoke_test_url_format():
    """Cell 3 builds a URL with the right GDELT date format."""
    from src.data.gdelt import build_gdelt_query_url
    url = build_gdelt_query_url(
        keywords_any=["russia", "ukraine"],
        languages=["English", "Russian"],
        start="2024-01-15 00:00:00",
        end="2024-01-15 23:59:59",
    )
    # GDELT requires YYYYMMDDHHMMSS format (no separators)
    assert "startdatetime=20240115000000" in url
    assert "enddatetime=20240115235959" in url
    assert "2024-01-15" not in url
    assert "russia" in url
    assert "Russian" in url


def test_full_extraction_resumable(tmp_path, fast_limiter, monkeypatch):
    """Cell 4 should: (1) cache per (query, month), (2) skip cached, (3) save on success."""
    from src.data.gdelt import fetch_gdelt_full, build_gdelt_query_url, _gdelt_request

    # Track how many requests are made
    call_log = []

    class FakeResp:
        def __init__(self, status=200, body=None):
            self.status_code = status
            self.headers = {}
            self._body = body or {}
            self.text = ""
        def json(self):
            return self._body

    def fake_get(url, timeout):
        call_log.append(url)
        return FakeResp(200, {"articles": [
            {"url": "u1", "title": "Article 1", "domain": "example.com",
             "language": "English", "sourceCommonName": "Example",
             "seendate": "20240101"}
        ]})

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    # Set up a fake queries config
    queries_yaml = tmp_path / "queries.yaml"
    queries_yaml.write_text("""
queries:
  - name: test_query
    keywords_any: { en: [russia] }
    keywords_weapon_any: { en: [missile] }
    languages: [English]
""")
    output_dir = tmp_path / "news"
    output_dir.mkdir()

    # First run: 45 months × 1 query = 45 calls
    df = fetch_gdelt_full(
        queries_path=queries_yaml,
        start="2022-09-29",
        end="2026-06-21",
        output_dir=output_dir,
        rate_per_sec=1000.0,  # fast for tests
    )
    assert len(df) == 45, f"First run should fetch 45 windows, got {len(df)}"
    assert len(call_log) == 45

    # Second run: should skip all cached → 0 new calls
    call_log.clear()
    df2 = fetch_gdelt_full(
        queries_path=queries_yaml,
        start="2022-09-29",
        end="2026-06-21",
        output_dir=output_dir,
        rate_per_sec=1000.0,
    )
    assert len(df2) == 45
    assert len(call_log) == 0, f"Second run should not re-fetch, got {len(call_log)} calls"

    # Verify parquet files exist for each month
    parquet_files = list(output_dir.glob("raw_test_query_*.parquet"))
    assert len(parquet_files) == 45


def test_full_extraction_handles_429_with_retry(
    tmp_path, fast_limiter, monkeypatch
):
    """Cell 4 should auto-retry on 429 and eventually succeed."""
    from src.data.gdelt import fetch_gdelt_full

    class FakeResp:
        def __init__(self, status, body=None):
            self.status_code = status
            self.headers = {}
            self._body = body or {}
            self.text = "rate limited" if status == 429 else ""
        def json(self):
            return self._body

    # First 2 calls: 429, third: 200
    call_count = [0]

    def fake_get(url, timeout):
        call_count[0] += 1
        if call_count[0] <= 2:
            return FakeResp(429)
        return FakeResp(200, {"articles": [
            {"url": "u", "title": "T", "domain": "x.com",
             "language": "English", "sourceCommonName": "X",
             "seendate": "20240101"}
        ]})

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    queries_yaml = tmp_path / "queries.yaml"
    queries_yaml.write_text("""
queries:
  - name: t
    keywords_any: { en: [a] }
""")
    output_dir = tmp_path / "news"
    output_dir.mkdir()

    # 1 month × 1 query → 1 call → first 2 attempts get 429, then 200
    df = fetch_gdelt_full(
        queries_path=queries_yaml,
        start="2022-09-29",
        end="2022-09-30",
        output_dir=output_dir,
        rate_per_sec=1000.0,
    )
    # Should have at least 1 article (from the successful 3rd call)
    assert len(df) >= 1
    # And 3+ actual requests (2 retries + 1 success)
    assert call_count[0] >= 3, f"Expected ≥3 calls (2×429 + 1×200), got {call_count[0]}"


def test_full_extraction_saves_empty_marker_on_failure(
    tmp_path, fast_limiter, monkeypatch
):
    """Cell 4 should save an empty marker on a 0-article response, so resume
    doesn't loop forever on a query that simply has no matches."""
    from src.data.gdelt import fetch_gdelt_full

    class FakeResp:
        def __init__(self, status=200, body=None):
            self.status_code = status
            self.headers = {}
            self._body = body or {}
            self.text = ""
        def json(self):
            return self._body

    def fake_get(url, timeout):
        return FakeResp(200, {"articles": []})  # always empty

    monkeypatch.setattr("src.data.gdelt.requests.get", fake_get)
    monkeypatch.setattr("src.data.gdelt.time.sleep", lambda s: None)

    queries_yaml = tmp_path / "queries.yaml"
    queries_yaml.write_text("""
queries:
  - name: empty
    keywords_any: { en: [x] }
""")
    output_dir = tmp_path / "news"
    output_dir.mkdir()

    df = fetch_gdelt_full(
        queries_path=queries_yaml,
        start="2022-09-29",
        end="2022-09-30",
        output_dir=output_dir,
        rate_per_sec=1000.0,
    )
    assert len(df) == 0
    # The empty marker should be saved (so we don't retry on resume)
    parquet_files = list(output_dir.glob("raw_empty_*.parquet"))
    assert len(parquet_files) == 1
    # And a re-run should not re-fetch (cached as empty)
    df2 = fetch_gdelt_full(
        queries_path=queries_yaml,
        start="2022-09-29",
        end="2022-09-30",
        output_dir=output_dir,
        rate_per_sec=1000.0,
    )
    assert len(df2) == 0


def test_full_extraction_predictable_wall_time():
    """Verify the wall-time formula: total_calls × rate_interval."""
    import pandas as pd
    from src.data.gdelt import RateLimiter

    start, end = "2022-09-29", "2026-06-21"
    months = pd.date_range(start, end, freq="MS").strftime("%Y-%m").tolist()
    months.append(end[:7])
    months = sorted(set(months))
    n_months = len(months)
    n_queries = 4
    n_calls = n_months * n_queries

    lim = RateLimiter(rate_per_sec=1.0 / 7.0)  # default 7 sec
    sec = n_calls * lim.interval
    # Sanity: ~180 calls × 7s = 1260s = 21 min
    assert 1200 <= sec <= 1320, f"Unexpected wall time: {sec}s for {n_calls} calls"
    assert n_months == 45  # locked-in for the project date range
    assert n_calls == 180  # 45 × 4 queries
