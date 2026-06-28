"""
src/data/gdelt.py
==================

GDELT DOC 2.0 article extraction, classification, deduplication, and
daily aggregation for the War Signals thesis.

This module is importable from both local and Google Colab environments.

Functions
---------
build_gdelt_query_url()          -- Build a GDELT DOC 2.0 ArtList URL
fetch_gdelt_window()             -- Fetch articles for a date window (one query, one range)
fetch_gdelt_full()               -- Fetch all queries for the full date range, resumable
classify_source()                -- Look up source group by domain
classify_all_articles()          -- Add source_group + language to a DataFrame
detect_language()                -- langdetect wrapper (with fallback)
dedupe_articles()                -- MinHash + LSH dedup on titles
build_news_daily()               -- Daily aggregation by source group
manual_precision_audit()         -- Sample N random articles for hand-labeling

Designed to run on Google Colab Pro High-RAM. See docs/colab_03_setup.md.

Audit: docs/phase3_gdelt_audit.md
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode, quote_plus

import numpy as np
import pandas as pd
import requests
import yaml

warnings.filterwarnings("ignore")

# Default paths
DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_OUTPUT_DIR = Path("data/interim/news")

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"


# =========================================================================
# Query building
# =========================================================================

def _flatten_keywords(per_lang) -> list[str]:
    """Flatten a per-language keyword dict into a single list.

    Accepts: dict[lang] -> list[str], or a flat list[str], or None.
    """
    out: list[str] = []
    if not per_lang:
        return out
    if isinstance(per_lang, list):
        return list(per_lang)
    if isinstance(per_lang, dict):
        for lang, words in per_lang.items():
            if isinstance(words, list):
                out.extend(words)
            elif isinstance(words, str):
                out.append(words)
    return out


def build_gdelt_query_url(
    keywords_any: list[str] | None = None,
    keywords_weapon_any: list[str] | None = None,
    languages: list[str] | None = None,
    themes: list[str] | None = None,
    start: str = "",
    end: str = "",
    max_records: int = 250,
    mode: str = "artlist",
    sort: str = "datedesc",
) -> str:
    """Build a GDELT DOC 2.0 ArtList URL.

    Parameters
    ----------
    keywords_any : list of str
        Country/actor keywords (OR).
    keywords_weapon_any : list of str
        Weapon/attack keywords (OR).
    languages : list of str
        GDELT language names (e.g. "English", "Russian").
    themes : list of str
        GDELT GNS theme codes (e.g. "TERROR", "MILITARY_OPERATION").
    start, end : str
        "YYYY-MM-DD HH:MM:SS" — start/end of the date window.
    max_records : int
        Max 250 per GDELT.
    mode : str
        "artlist" for article list (Phase 3 default), or "timelinevol" for counts.
    sort : str
        "datedesc" for newest first, "dateasc" for oldest first.
    """
    parts: list[str] = []
    if keywords_any:
        parts.append("(" + " OR ".join(keywords_any) + ")")
    if keywords_weapon_any:
        parts.append("(" + " OR ".join(keywords_weapon_any) + ")")
    query = " AND ".join(parts) if parts else "*"

    # Build the URL manually so we use %20 (not +) for spaces in datetimes
    # (GDELT is strict about this).
    from urllib.parse import quote
    params = {
        "query": query,
        "mode": mode,
        "format": "json",
        "maxrecords": str(max_records),
        "sort": sort,
    }
    if languages:
        params["sourcelang"] = ",".join(languages)
    if themes:
        params["theme"] = ",".join(themes)
    if start:
        params["startdatetime"] = start
    if end:
        params["enddatetime"] = end

    qs = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
    return f"{GDELT_BASE}?{qs}"


# =========================================================================
# API client
# =========================================================================

def _gdelt_request(url: str, max_retries: int = 5, backoff: float = 2.0,
                   timeout: int = 60) -> tuple[list[dict[str, Any]], str | None]:
    """Make a GDELT request with retry logic. Returns (article_list, error_msg)."""
    last_error = None
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    last_error = "JSON decode error"
                    time.sleep(backoff)
                    continue
                if isinstance(data, dict) and "articles" in data:
                    return data["articles"], None
                if isinstance(data, list):
                    return data, None
                if isinstance(data, dict):
                    return [data], None
                return [], None
            elif r.status_code == 429:
                # Rate-limited; back off aggressively
                wait = backoff * (attempt + 1) * 2  # 4, 8, 16, 32, 64 sec
                last_error = f"429 (rate limited, slept {wait}s)"
                time.sleep(wait)
            else:
                last_error = f"HTTP {r.status_code}"
                time.sleep(backoff * (attempt + 1))
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_error = f"Request error: {e}"
            time.sleep(backoff * (attempt + 1))
    return [], last_error


def fetch_gdelt_window(
    query: dict[str, Any],
    start: str,
    end: str,
    api_sleep: float = 5.0,  # GDELT public API: 1 request per 5 seconds
    max_records: int = 250,
    max_retries: int = 5,
) -> list[dict[str, Any]]:
    """Fetch all articles matching `query` for a single date window.

    Note: GDELT ArtList returns max 250 articles per call. For larger
    windows, we paginate using startdatetime.

    Parameters
    ----------
    query : dict
        One entry from config/gdelt_queries.yaml's `queries` list.
    start, end : str
        "YYYY-MM-DD" (no time) — the date window.
    """
    keywords_any = _flatten_keywords(query.get("keywords_any", {}))
    keywords_weapon_any = _flatten_keywords(query.get("keywords_weapon_any", {}))
    languages = query.get("languages", [])
    themes = query.get("themes", [])

    out: list[dict[str, Any]] = []
    # Convert date to GDELT datetime strings
    start_dt = f"{start} 00:00:00"
    end_dt = f"{end} 23:59:59"

    # GDELT artlist max is 250 per call. For long windows we may need pagination.
    url = build_gdelt_query_url(
        keywords_any=keywords_any,
        keywords_weapon_any=keywords_weapon_any,
        languages=languages,
        themes=themes,
        start=start_dt,
        end=end_dt,
        max_records=max_records,
        mode="artlist",
        sort="datedesc",
    )
    articles, err = _gdelt_request(url, max_retries=max_retries)
    if err:
        print(f"    [WARN] {err}")
    out.extend(articles)
    time.sleep(api_sleep)

    return out


# =========================================================================
# Source classification
# =========================================================================

def _load_source_groups(path: str | Path = DEFAULT_CONFIG_DIR / "source_groups.yaml"
                        ) -> dict[str, dict]:
    """Load source_groups.yaml. Returns a {group: {description, domains}} dict."""
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg["groups"]


def _build_domain_index(groups: dict[str, dict]) -> dict[str, str]:
    """Build a flat {domain: group_name} index. Excludes 'other' catch-all."""
    idx: dict[str, str] = {}
    for g_name, g_data in groups.items():
        if g_name == "other":
            continue
        for d in g_data.get("domains", []):
            idx[d.lower()] = g_name
    return idx


def classify_source(domain: str | None,
                    groups: dict[str, dict] | None = None) -> str:
    """Look up source group by domain. Returns one of {ukrainian, russian, western, other}."""
    if domain is None or (isinstance(domain, float) and np.isnan(domain)):
        return "other"
    d = str(domain).lower().strip()
    if not d:
        return "other"
    if groups is None:
        groups = _load_source_groups()
    idx = _build_domain_index(groups)
    # Strip leading "www." if present
    d_clean = d[4:] if d.startswith("www.") else d
    return idx.get(d_clean, idx.get(d, "other"))


def classify_all_articles(
    df: pd.DataFrame,
    domain_col: str = "domain",
    groups: dict[str, dict] | None = None,
) -> pd.DataFrame:
    """Add a `source_group` column to a DataFrame of articles."""
    if groups is None:
        groups = _load_source_groups()
    out = df.copy()
    out["source_group"] = out[domain_col].apply(lambda d: classify_source(d, groups))
    return out


# =========================================================================
# Language detection
# =========================================================================

def detect_language(text: str | None, fallback: str = "Unknown") -> str:
    """Detect language of a short text. Falls back gracefully."""
    if not text or not isinstance(text, str) or len(text.strip()) < 10:
        return fallback
    try:
        from langdetect import detect
        lang_code = detect(text)
        # Map ISO 639-1 codes to GDELT names
        MAPPING = {
            "en": "English",
            "ru": "Russian",
            "uk": "Ukrainian",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "pl": "Polish",
            "nl": "Dutch",
            "pt": "Portuguese",
        }
        return MAPPING.get(lang_code, lang_code)
    except Exception:
        return fallback


# =========================================================================
# Deduplication
# =========================================================================

def _shingle(s: str, n: int = 5) -> set[str]:
    """Character n-gram shingles of a string."""
    s = s.lower().strip()
    if len(s) < n:
        return {s}
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def dedupe_articles(
    df: pd.DataFrame,
    title_col: str = "title",
    num_perm: int = 128,
    shingle_size: int = 5,
    threshold: float = 0.7,
    min_title_len: int = 20,
) -> pd.DataFrame:
    """Deduplicate articles using MinHash + LSH on titles.

    Returns the deduplicated DataFrame (one row per cluster, keeping
    the first occurrence in document order).
    """
    if df.empty:
        return df
    titles = df[title_col].fillna("").astype(str)
    keep_mask = np.ones(len(df), dtype=bool)

    long_enough = titles.str.len() >= min_title_len
    if not long_enough.any():
        return df

    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    hashes: dict[int, MinHash] = {}
    for idx in np.where(long_enough)[0]:
        t = titles.iloc[idx]
        shingles = _shingle(t, n=shingle_size)
        if not shingles:
            continue
        m = MinHash(num_perm=num_perm)
        for s in shingles:
            m.update(s.encode("utf-8"))
        lsh.insert(idx, m)
        hashes[idx] = m

    # Process in document order. For each index, look up similar indices
    # in LSH. If any earlier index is still kept, mark this as duplicate.
    # If any later index is similar, it will be marked duplicate when we
    # reach it (since this kept index is "earlier" relative to it).
    indices = sorted(hashes.keys())
    for idx in indices:
        if not keep_mask[idx]:
            continue
        m = hashes[idx]
        results = lsh.query(m)
        for r in results:
            if r != idx and r < idx and keep_mask[r]:
                # Earlier similar index is still kept; mark this as duplicate
                keep_mask[idx] = False
                break

    return df[keep_mask].reset_index(drop=True)


# =========================================================================
# Daily aggregation
# =========================================================================

def build_news_daily(
    df: pd.DataFrame,
    date_col: str = "date",
    group_col: str = "source_group",
    out_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build the daily news aggregates table.

    Output columns per (date, source_group):
      - n_articles: article count
    Plus a row for total per day.
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    # Count per (date, group)
    grp = (
        df.groupby([df[date_col].dt.normalize(), group_col])
        .size()
        .unstack(fill_value=0)
    )
    grp.columns = [f"n_articles_{c}" for c in grp.columns]
    grp["n_articles_total"] = grp.sum(axis=1)
    grp = grp.sort_index()
    grp.index.name = "date"

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        grp.to_parquet(out_path)
        grp.to_csv(out_path.with_suffix(".csv"))

    return grp


# =========================================================================
# Full pipeline (used in Colab notebook)
# =========================================================================

def fetch_gdelt_full(
    queries_path: str | Path = DEFAULT_CONFIG_DIR / "gdelt_queries.yaml",
    start: str = "2022-09-29",
    end: str = "2026-06-21",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    window: str = "month",
    api_sleep: float = 5.0,  # GDELT public API: 1 request per 5 seconds
    max_records: int = 250,
    max_retries: int = 5,
) -> pd.DataFrame:
    """Fetch all articles for all queries in monthly windows.

    Saves per-(query, month) parquet files for resumability.

    Returns the combined DataFrame.
    """
    with open(queries_path) as f:
        cfg = yaml.safe_load(f)
    queries = cfg["queries"]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    months = pd.date_range(start, end, freq="MS").strftime("%Y-%m").tolist()
    months.append(end[:7])

    for q in queries:
        for m in months:
            # Skip if already done
            out_file = output_dir / f"raw_{q['name']}_{m}.parquet"
            if out_file.exists():
                df_existing = pd.read_parquet(out_file)
                if not df_existing.empty:
                    print(f"  [SKIP] {q['name']} {m}: {len(df_existing)} articles cached")
                    all_records.extend(df_existing.to_dict("records"))
                    continue
            # Build window
            month_start = pd.Timestamp(m).date()
            month_end = (pd.Timestamp(m) + pd.offsets.MonthEnd(0)).date()
            if pd.Timestamp(month_start) < pd.Timestamp(start):
                month_start = pd.Timestamp(start).date()
            if pd.Timestamp(month_end) > pd.Timestamp(end):
                month_end = pd.Timestamp(end).date()
            print(f"  [FETCH] {q['name']} {month_start} → {month_end}", end=" ... ", flush=True)
            try:
                articles = fetch_gdelt_window(
                    q,
                    start=month_start.isoformat(),
                    end=month_end.isoformat(),
                    api_sleep=api_sleep,
                    max_records=max_records,
                    max_retries=max_retries,
                )
                # Save per-window (always save a marker, even if empty)
                pd.DataFrame(articles).to_parquet(out_file)
                all_records.extend(articles)
                print(f"{len(articles)} articles")
            except Exception as e:
                print(f"ERROR: {e}")
                # Still save an empty marker so we don't re-try on resume
                try:
                    pd.DataFrame().to_parquet(out_file)
                except Exception:
                    pass
                continue

    if not all_records:
        return pd.DataFrame()
    return pd.DataFrame(all_records)


# =========================================================================
# Manual precision audit
# =========================================================================

def manual_precision_audit(
    df: pd.DataFrame,
    n_per_group: int = 25,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample articles for manual precision audit.

    Returns a DataFrame with sampled articles + columns to fill in:
    - relevant: 1 if article is about Russian attacks on Ukraine, else 0
    - notes: free text
    """
    if df.empty or "source_group" not in df.columns:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    rows = []
    for group in ["ukrainian", "russian", "western", "other"]:
        sub = df[df["source_group"] == group]
        if sub.empty:
            continue
        idx = rng.choice(sub.index, size=min(n_per_group, len(sub)), replace=False)
        for i in idx:
            r = sub.loc[i]
            rows.append({
                "date": r.get("date"),
                "title": r.get("title"),
                "url": r.get("url"),
                "domain": r.get("domain"),
                "language": r.get("language"),
                "source_group": group,
                "relevant": "",  # to be filled in manually
                "notes": "",
            })
    return pd.DataFrame(rows)


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--smoke-test", action="store_true",
                   help="Run a 1-day smoke test")
    p.add_argument("--start", default="2024-01-15")
    p.add_argument("--end", default="2024-01-15")
    args = p.parse_args()

    if args.smoke_test:
        # Use the first query for smoke testing
        with open(DEFAULT_CONFIG_DIR / "gdelt_queries.yaml") as f:
            cfg = yaml.safe_load(f)
        q = cfg["queries"][0]
        print(f"=== Smoke test: 1 day, query '{q['name']}' ===")
        articles = fetch_gdelt_window(q, args.start, args.end, api_sleep=0.6)
        print(f"Retrieved {len(articles)} articles")
        if articles:
            print("\nSample article:")
            print(json.dumps(articles[0], indent=2, default=str))
        # Classify
        df = pd.DataFrame(articles)
        df = classify_all_articles(df)
        print(f"\nSource groups: {df['source_group'].value_counts().to_dict()}")
        if not df.empty:
            # Daily aggregation
            daily = build_news_daily(df)
            print(f"\nDaily aggregate:\n{daily.to_string()}")
