#!/usr/bin/env python3
"""
Phase 3 Post-Processing Pipeline
=================================
Processes raw GKG bulk-download parquets through 4 stages:
  1. Load + URL-based deduplication
  2. Source-group classification
  3. Daily aggregation
  4. Summary statistics + manual precision audit sample

Input:  data/news_colab_sim/war_signals_phase3/raw/raw_*.parquet (184 files)
Output: data/processed/news/
          - gdelt_articles_dedup.parquet
          - gdelt_articles_classified.parquet
          - news_daily.parquet + news_daily.csv
          - manual_precision_audit.csv

Run from project root:
    python scripts/phase3_post_process.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path so `src.data.gdelt` is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.gdelt import classify_all_articles, build_news_daily, manual_precision_audit

# ── Paths ────────────────────────────────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "data" / "news_colab_sim" / "war_signals_phase3" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "news"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEDUP_FILE = OUT_DIR / "gdelt_articles_dedup.parquet"
CLASS_FILE = OUT_DIR / "gdelt_articles_classified.parquet"
DAILY_PARQUET = OUT_DIR / "news_daily.parquet"
DAILY_CSV = OUT_DIR / "news_daily.csv"
AUDIT_FILE = OUT_DIR / "manual_precision_audit.csv"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Load + Dedup
# ═══════════════════════════════════════════════════════════════════════════════

def stage1_load_and_dedup() -> pd.DataFrame:
    """Load all raw parquets, dedup by URL across all queries/months."""
    print("=" * 70)
    print("STAGE 1: LOAD + DEDUPLICATION")
    print("=" * 70)
    t0 = time.time()

    files = sorted(RAW_DIR.glob("raw_*.parquet"))
    print(f"Found {len(files)} raw parquet files in {RAW_DIR}")

    if not files:
        raise FileNotFoundError(f"No raw_*.parquet files found in {RAW_DIR}")

    # Load each file, tagging with query_name from filename
    # Filename pattern: raw_{query_name}_{YYYY-MM}.parquet
    dfs = []
    per_query_raw: dict[str, int] = {}
    for f in files:
        df = pd.read_parquet(f)
        if df.empty:
            continue
        # Extract query name: strip "raw_" prefix and "_YYYY-MM" suffix
        stem = f.stem  # e.g. "raw_russian_attack_direct_2022-09"
        parts = stem.split("_")
        # query name is everything between first "raw" and last date part
        # e.g. ["raw", "russian", "attack", "direct", "2022-09"]
        query_name = "_".join(parts[1:-1])
        df = df.copy()
        df["query_name"] = query_name
        per_query_raw[query_name] = per_query_raw.get(query_name, 0) + len(df)
        dfs.append(df)

    raw = pd.concat(dfs, ignore_index=True)
    total_raw = len(raw)
    unique_urls = raw["url"].nunique()

    print(f"\nTotal articles loaded: {total_raw:,}")
    print(f"Unique URLs:           {unique_urls:,}")
    print(f"\nPer-query raw counts:")
    for qname, cnt in sorted(per_query_raw.items()):
        print(f"  {qname:30s}  {cnt:>10,}")

    # Dedup by URL (keep first occurrence)
    deduped = raw.drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    n_removed = total_raw - len(deduped)
    pct_kept = len(deduped) / total_raw * 100 if total_raw > 0 else 0
    pct_removed = n_removed / total_raw * 100 if total_raw > 0 else 0

    print(f"\nDedup results:")
    print(f"  Before:  {total_raw:,}")
    print(f"  After:   {len(deduped):,}")
    print(f"  Removed: {n_removed:,} ({pct_removed:.1f}%)")
    print(f"  Kept:    {pct_kept:.1f}%")
    print(f"  Wall time: {(time.time() - t0):.1f}s")

    # Save
    deduped.to_parquet(DEDUP_FILE, index=False)
    size_mb = DEDUP_FILE.stat().st_size / 1024 / 1024
    print(f"\n✓ Saved {DEDUP_FILE} ({size_mb:.1f} MB)")

    return deduped


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Classification
# ═══════════════════════════════════════════════════════════════════════════════

def stage2_classify(df: pd.DataFrame) -> pd.DataFrame:
    """Add source_group column using config/source_groups.yaml."""
    print("\n" + "=" * 70)
    print("STAGE 2: CLASSIFICATION")
    print("=" * 70)
    t0 = time.time()

    print(f"Loaded {len(df):,} articles for classification")

    # Classify using existing function (reads config/source_groups.yaml)
    classified = classify_all_articles(df, domain_col="domain")

    print(f"\nSource group distribution:")
    vc = classified["source_group"].value_counts()
    for group, count in vc.items():
        pct = count / len(classified) * 100
        print(f"  {group:15s}  {count:>10,}  ({pct:5.1f}%)")

    print(f"  Wall time: {(time.time() - t0):.1f}s")

    # Save
    classified.to_parquet(CLASS_FILE, index=False)
    size_mb = CLASS_FILE.stat().st_size / 1024 / 1024
    print(f"\n✓ Saved {CLASS_FILE} ({size_mb:.1f} MB)")

    return classified


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3: Daily Aggregation
# ═══════════════════════════════════════════════════════════════════════════════

def stage3_daily_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to daily counts per source_group."""
    print("\n" + "=" * 70)
    print("STAGE 3: DAILY AGGREGATION")
    print("=" * 70)
    t0 = time.time()

    print(f"Loaded {len(df):,} classified articles")

    # Parse date column — GKG dates are stored as strings like "20220929" or "20220929T140000Z"
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    n_bad_dates = df["date"].isna().sum()
    if n_bad_dates > 0:
        print(f"  WARNING: {n_bad_dates:,} rows with unparseable dates — dropping")
    df = df.dropna(subset=["date"])
    # Normalize to midnight
    df["date"] = df["date"].dt.normalize()

    print(f"  Articles with valid dates: {len(df):,}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    # Build daily aggregates
    daily = build_news_daily(
        df,
        date_col="date",
        group_col="source_group",
        out_path=DAILY_PARQUET,
    )

    # Also save CSV (build_news_daily saves both when out_path is given)
    daily.to_csv(DAILY_CSV)

    n_days = len(daily)
    days_with_articles = (daily["n_articles_total"] > 0).sum()

    print(f"\nDaily aggregate shape: {daily.shape}")
    print(f"  Total days:          {n_days}")
    print(f"  Days with articles:  {days_with_articles}")
    print(f"  Total articles:      {daily['n_articles_total'].sum():,}")
    print(f"  Mean articles/day:   {daily['n_articles_total'].mean():.1f}")
    print(f"  Max articles/day:    {daily['n_articles_total'].max():,}")
    print(f"  Wall time: {(time.time() - t0):.1f}s")

    print(f"\n✓ Saved {DAILY_PARQUET}")
    print(f"✓ Saved {DAILY_CSV}")

    return daily


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 4: Summary + Audit
# ═══════════════════════════════════════════════════════════════════════════════

def stage4_summary(classified: pd.DataFrame, daily: pd.DataFrame) -> None:
    """Print final summary and generate precision audit sample."""
    print("\n" + "=" * 70)
    print("STAGE 4: SUMMARY + PRECISION AUDIT")
    print("=" * 70)

    # ── Overall stats ──
    print(f"\nTotal articles (after dedup): {len(classified):,}")
    classified["date"] = pd.to_datetime(classified["date"], errors="coerce")
    valid = classified.dropna(subset=["date"])
    if not valid.empty:
        print(f"Date range: {valid['date'].min().date()} → {valid['date'].max().date()}")
        n_days_span = (valid["date"].max() - valid["date"].min()).days + 1
        print(f"Day span:   {n_days_span} days")

    # ── Source group counts ──
    print(f"\nSource groups:")
    vc = classified["source_group"].value_counts()
    for group, count in vc.items():
        pct = count / len(classified) * 100
        print(f"  {group:15s}  {count:>10,}  ({pct:5.1f}%)")

    # ── Top domains per group ──
    for group in ["ukrainian", "russian", "western", "other"]:
        sub = classified[classified["source_group"] == group]
        if sub.empty:
            continue
        print(f"\nTop 10 domains ({group}):")
        top = sub["domain"].value_counts().head(10)
        for domain, cnt in top.items():
            print(f"  {domain:40s}  {cnt:>8,}")

    # ── Daily aggregate summary ──
    print(f"\nDaily aggregate:")
    print(f"  Shape: {daily.shape[0]} days × {daily.shape[1]} columns")
    print(f"  Columns: {list(daily.columns)}")
    print(f"  Total articles: {daily['n_articles_total'].sum():,}")
    print(f"  Days with ≥1 article: {(daily['n_articles_total'] > 0).sum()}")
    if daily["n_articles_total"].sum() > 0:
        print(f"\n  Daily stats:")
        print(daily["n_articles_total"].describe().round(1).to_string())

    # ── Per-query breakdown ──
    if "query_name" in classified.columns:
        print(f"\nPer-query article counts (after dedup):")
        qvc = classified["query_name"].value_counts()
        for qname, cnt in qvc.items():
            print(f"  {qname:30s}  {cnt:>10,}")

    # ── Manual precision audit ──
    print(f"\nGenerating manual precision audit sample...")
    audit = manual_precision_audit(classified, n_per_group=25, seed=42)
    audit.to_csv(AUDIT_FILE, index=False)
    print(f"✓ Saved {AUDIT_FILE}")
    print(f"  {len(audit)} articles to label (25 per group × 4 groups)")
    print(f"  Open the CSV and fill in the 'relevant' column (1 or 0)")

    # ── Final file listing ──
    print(f"\n{'=' * 70}")
    print("OUTPUT FILES:")
    print(f"{'=' * 70}")
    for f in sorted(OUT_DIR.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name:45s}  {size_mb:8.1f} MB")
    print(f"\n{'=' * 70}")
    print("PHASE 3 POST-PROCESSING COMPLETE")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    print(f"Phase 3 Post-Processing Pipeline")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw data dir: {RAW_DIR}")
    print(f"Output dir:   {OUT_DIR}")
    print()

    # Stage 1
    deduped = stage1_load_and_dedup()

    # Stage 2
    classified = stage2_classify(deduped)

    # Stage 3
    daily = stage3_daily_aggregate(classified)

    # Stage 4
    stage4_summary(classified, daily)

    total_min = (time.time() - t_start) / 60
    print(f"\nTotal wall time: {total_min:.1f} minutes")


if __name__ == "__main__":
    main()
