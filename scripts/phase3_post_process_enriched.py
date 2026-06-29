#!/usr/bin/env python3
"""
Phase 3 Post-Processing Pipeline — ENRICHED VERSION (Colab-safe)
================================================================
Processes enriched GKG parquets (with TONE, COUNTRIES, PERSONS, ORGS, THEMES)
through 5 stages:
  1. Load + URL-based deduplication
  2. Domain→country mapping (data-driven from COUNTRIES field)
  3. Hybrid source-group classification (domain + country + TLD)
  4. Daily aggregation with tone averages
  5. Summary statistics + manual precision audit sample

Memory-safe: processes classification in chunks to avoid OOM on machines
with <16 GB RAM (e.g., Colab free tier with 12.7 GB).

Input:  <data-dir>/raw_enriched/raw_*.parquet
Output: <output-dir>/
          - gdelt_articles_dedup_enriched.parquet
          - gdelt_articles_classified_enriched.parquet
          - news_daily_enriched.parquet + news_daily_enriched.csv
          - domain_to_country.csv
          - manual_precision_audit_enriched.csv

Run from project root:
    python scripts/phase3_post_process_enriched.py
    python scripts/phase3_post_process_enriched.py --data-dir /content/drive/MyDrive/WarSignalsThesis_Data/data/raw_enriched --output-dir /content/drive/MyDrive/WarSignalsThesis_Data/data/processed/news --chunk-size 1000000
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd


# ── Retry helper for Drive reads ──────────────────────────────────────────────
# Colab's Drive mount occasionally throws OSError: [Errno 107] Transport endpoint
# is not connected on the first read of a file (especially when reading through a
# symlink to a Drive path). DriveFS then re-establishes the connection, so a
# short retry almost always succeeds.
def _read_parquet_retry(path: Path, max_attempts: int = 5, base_delay: float = 2.0) -> pd.DataFrame:
    """Read a parquet file with retry on transient Drive/OS errors."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pd.read_parquet(path)
        except OSError as e:
            last_err = e
            errno = e.errno if hasattr(e, "errno") else None
            # Errno 107 = transport endpoint not connected; Errno 5 = input/output err
            transient = errno in (5, 107) or "Transport endpoint" in str(e)
            if not transient or attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  ⚠ Read failed for {path.name} (errno={errno}), retry {attempt}/{max_attempts-1} in {delay:.0f}s")
            time.sleep(delay)
    raise last_err  # unreachable, but keeps type-checkers happy

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.gdelt import (
    classify_source_enhanced,
    classify_all_articles_enhanced,
    manual_precision_audit,
    _load_source_groups,
    _load_country_groups,
)


def parse_args():
    """Parse command-line arguments for flexible path configuration."""
    parser = argparse.ArgumentParser(
        description="Phase 3 enriched GKG post-processing pipeline (Colab-safe, chunked)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing raw_*.parquet files. Defaults to local project's raw_enriched/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for processed files. Defaults to data/processed/news/.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1_000_000,
        help="Number of rows per classification chunk (default: 1M, lower for low-RAM machines).",
    )
    return parser.parse_args()


# ── Paths ────────────────────────────────────────────────────────────────────
ARGS = parse_args()
RAW_DIR = ARGS.data_dir or (PROJECT_ROOT / "data" / "news_colab_sim" / "war_signals_phase3" / "raw_enriched")
OUT_DIR = ARGS.output_dir or (PROJECT_ROOT / "data" / "processed" / "news")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = ARGS.chunk_size

DEDUP_FILE = OUT_DIR / "gdelt_articles_dedup_enriched.parquet"
CLASS_FILE = OUT_DIR / "gdelt_articles_classified_enriched.parquet"
DAILY_PARQUET = OUT_DIR / "news_daily_enriched.parquet"
DAILY_CSV = OUT_DIR / "news_daily_enriched.csv"
DOMAIN_COUNTRY_FILE = OUT_DIR / "domain_to_country.csv"
AUDIT_FILE = OUT_DIR / "manual_precision_audit_enriched.csv"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Load + Dedup
# ═══════════════════════════════════════════════════════════════════════════════

def stage1_load_and_dedup() -> pd.DataFrame:
    print("=" * 70)
    print("STAGE 1: LOAD + DEDUPLICATION (enriched)")
    print("=" * 70)
    t0 = time.time()

    files = sorted(RAW_DIR.glob("raw_*.parquet"))
    print(f"Found {len(files)} enriched parquet files in {RAW_DIR}")
    if not files:
        raise FileNotFoundError(f"No raw_*.parquet files in {RAW_DIR}")

    dfs = []
    per_query_raw: dict[str, int] = {}
    for i, f in enumerate(files, 1):
        if i % 10 == 0 or i == 1:
            print(f"  Loading file {i}/{len(files)}: {f.name}")
        df = _read_parquet_retry(f)
        if df.empty:
            continue
        stem = f.stem
        parts = stem.split("_")
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
    print(f"Columns: {list(raw.columns)}")
    print(f"\nPer-query raw counts:")
    for qname, cnt in sorted(per_query_raw.items()):
        print(f"  {qname:30s}  {cnt:>10,}")

    deduped = raw.drop_duplicates(subset=["url"], keep="first").reset_index(drop=True)
    n_removed = total_raw - len(deduped)
    pct_removed = n_removed / total_raw * 100 if total_raw > 0 else 0

    print(f"\nDedup results:")
    print(f"  Before:  {total_raw:,}")
    print(f"  After:   {len(deduped):,}")
    print(f"  Removed: {n_removed:,} ({pct_removed:.1f}%)")
    print(f"  Wall time: {(time.time() - t0):.1f}s")

    deduped.to_parquet(DEDUP_FILE, index=False)
    size_mb = DEDUP_FILE.stat().st_size / 1024 / 1024
    print(f"\n✓ Saved {DEDUP_FILE} ({size_mb:.1f} MB)")
    return deduped


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: Build domain→country mapping
# ═══════════════════════════════════════════════════════════════════════════════

def stage2_domain_country_mapping(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("STAGE 2: DOMAIN→COUNTRY MAPPING")
    print("=" * 70)
    t0 = time.time()

    if "countries" not in df.columns:
        print("  WARNING: 'countries' column not found — skipping")
        return df

    # For each domain, count country codes across all articles
    domain_country_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    domain_article_count: dict[str, int] = defaultdict(int)

    for _, row in df[["domain", "countries"]].iterrows():
        domain = row["domain"]
        if not domain or pd.isna(domain):
            continue
        domain_article_count[domain] += 1
        countries = str(row["countries"]) if not pd.isna(row["countries"]) else ""
        for code in countries.split(";"):
            code = code.strip().upper()
            if code and len(code) == 2 and code.isalpha():
                domain_country_counts[domain][code] += 1

    # Build mapping: for each domain, pick the most common country code
    rows = []
    for domain, art_count in domain_article_count.items():
        counts = domain_country_counts[domain]
        if counts:
            # Sort by count descending, pick most common
            top_code, top_count = max(counts.items(), key=lambda x: x[1])
            confidence = top_count / art_count
        else:
            top_code, top_count, confidence = "", 0, 0.0
        rows.append({
            "domain": domain,
            "primary_country": top_code,
            "primary_country_count": top_count,
            "article_count": art_count,
            "confidence": round(confidence, 3),
        })

    mapping = pd.DataFrame(rows).sort_values("article_count", ascending=False)
    mapping.to_csv(DOMAIN_COUNTRY_FILE, index=False)

    # Summary
    n_with_country = (mapping["primary_country"] != "").sum()
    n_total = len(mapping)
    pct_covered = n_with_country / n_total * 100 if n_total > 0 else 0

    print(f"  Unique domains:           {n_total:,}")
    print(f"  With country mapping:     {n_with_country:,} ({pct_covered:.1f}%)")
    print(f"  Without country mapping:  {n_total - n_with_country:,}")
    print(f"  Mean confidence:          {mapping.loc[mapping['primary_country'] != '', 'confidence'].mean():.3f}")
    print(f"  Wall time: {(time.time() - t0):.1f}s")

    print(f"\n  Top 20 countries by domain count:")
    top_countries = mapping[mapping["primary_country"] != ""]["primary_country"].value_counts().head(20)
    for code, cnt in top_countries.items():
        print(f"    {code}: {cnt:>6,} domains")

    print(f"\n✓ Saved {DOMAIN_COUNTRY_FILE}")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3: Hybrid Classification
# ═══════════════════════════════════════════════════════════════════════════════

def stage3_classify(df: pd.DataFrame, chunk_size: int = 2_000_000) -> pd.DataFrame:
    """Chunked classification to bound memory usage.

    Processes the deduped DataFrame in chunks of `chunk_size` rows,
    saving each classified chunk to a temporary parquet, then concatenates.
    Peak memory per chunk: ~2-3 GB (vs 8-12 GB for full apply).
    """
    print("\n" + "=" * 70)
    print("STAGE 3: HYBRID CLASSIFICATION (chunked)")
    print("=" * 70)
    t0 = time.time()

    n = len(df)
    n_chunks = (n + chunk_size - 1) // chunk_size
    print(f"Loaded {n:,} articles for classification")
    print(f"Chunk size: {chunk_size:,} ({n_chunks} chunks)")

    from src.data.gdelt import _load_source_groups, _load_country_groups
    groups = _load_source_groups()
    country_groups = _load_country_groups()

    tmp_dir = OUT_DIR / "_tmp_chunks"
    tmp_dir.mkdir(exist_ok=True)
    chunk_files = []

    for i in range(n_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, n)
        chunk = df.iloc[start:end].copy()
        t_chunk = time.time()
        print(f"  Chunk {i+1}/{n_chunks}  rows {start:,}–{end:,}  "
              f"({(time.time() - t0)/60:.1f} min elapsed)...", flush=True)
        chunk_classified = classify_all_articles_enhanced(
            chunk, groups=groups, country_groups=country_groups
        )
        chunk_file = tmp_dir / f"chunk_{i:03d}.parquet"
        chunk_classified.to_parquet(chunk_file, index=False)
        chunk_files.append(chunk_file)
        del chunk, chunk_classified
        import gc; gc.collect()
        print(f"    → done in {time.time() - t_chunk:.1f}s, saved {chunk_file.name}")

    # Concatenate all chunks
    print(f"\nConcatenating {len(chunk_files)} chunks...")
    classified = pd.concat(
        [pd.read_parquet(f) for f in chunk_files], ignore_index=True
    )
    print(f"  Concatenated: {len(classified):,} rows")

    # Cleanup temp files
    for f in chunk_files:
        f.unlink()
    tmp_dir.rmdir()
    print(f"  Cleaned up temp files")

    print(f"\nSource group distribution:")
    vc = classified["source_group"].value_counts()
    for group, count in vc.items():
        pct = count / len(classified) * 100
        print(f"  {group:15s}  {count:>10,}  ({pct:5.1f}%)")

    print(f"\nClassification method distribution:")
    mc = classified["classification_method"].value_counts()
    for method, count in mc.items():
        pct = count / len(classified) * 100
        print(f"  {method:15s}  {count:>10,}  ({pct:5.1f}%)")

    print(f"\nClassification method × source group cross-tab:")
    ct = pd.crosstab(classified["classification_method"], classified["source_group"])
    print(ct.to_string())

    print(f"  Total wall time: {(time.time() - t0)/60:.1f} min")

    classified.to_parquet(CLASS_FILE, index=False)
    size_mb = CLASS_FILE.stat().st_size / 1024 / 1024
    print(f"\n✓ Saved {CLASS_FILE} ({size_mb:.1f} MB)")
    return classified


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 4: Daily Aggregation with Tone
# ═══════════════════════════════════════════════════════════════════════════════

def stage4_daily_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("STAGE 4: DAILY AGGREGATION (with tone)")
    print("=" * 70)
    t0 = time.time()

    print(f"Loaded {len(df):,} classified articles")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    n_bad = df["date"].isna().sum()
    if n_bad > 0:
        print(f"  WARNING: {n_bad:,} rows with unparseable dates — dropping")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.normalize()

    print(f"  Articles with valid dates: {len(df):,}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    # Article counts per (date, source_group)
    counts = (
        df.groupby([df["date"], "source_group"])
        .size()
        .unstack(fill_value=0)
    )
    counts.columns = [f"n_articles_{c}" for c in counts.columns]
    counts["n_articles_total"] = counts.sum(axis=1)

    # Tone averages per (date, source_group)
    has_tone = "tone_avg" in df.columns and df["tone_avg"].notna().any()
    if has_tone:
        print(f"  Computing tone averages (tone_avg present)...")
        tone = (
            df.groupby([df["date"], "source_group"])["tone_avg"]
            .mean()
            .unstack()
        )
        tone.columns = [f"tone_{c}" for c in tone.columns]
        daily = counts.join(tone)
    else:
        print(f"  WARNING: tone_avg not present — skipping tone aggregation")
        daily = counts

    daily = daily.sort_index()
    daily.index.name = "date"

    daily.to_parquet(DAILY_PARQUET)
    daily.to_csv(DAILY_CSV)

    n_days = len(daily)
    days_with_articles = (daily["n_articles_total"] > 0).sum()
    print(f"\n  Daily aggregate shape: {daily.shape}")
    print(f"  Total days:          {n_days}")
    print(f"  Days with articles:  {days_with_articles}")
    print(f"  Total articles:      {daily['n_articles_total'].sum():,}")
    print(f"  Wall time: {(time.time() - t0):.1f}s")

    if has_tone:
        tone_cols = [c for c in daily.columns if c.startswith("tone_")]
        print(f"\n  Tone summary (mean across all days):")
        for col in tone_cols:
            mean_val = daily[col].mean()
            print(f"    {col:25s}  {mean_val:>7.2f}")

    print(f"\n✓ Saved {DAILY_PARQUET}")
    print(f"✓ Saved {DAILY_CSV}")
    return daily


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 5: Summary + Audit
# ═══════════════════════════════════════════════════════════════════════════════

def stage5_summary(classified: pd.DataFrame, daily: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print("STAGE 5: SUMMARY + PRECISION AUDIT")
    print("=" * 70)

    print(f"\nTotal articles (after dedup): {len(classified):,}")
    classified["date"] = pd.to_datetime(classified["date"], errors="coerce")
    valid = classified.dropna(subset=["date"])
    if not valid.empty:
        print(f"Date range: {valid['date'].min().date()} → {valid['date'].max().date()}")

    print(f"\nSource groups:")
    vc = classified["source_group"].value_counts()
    for group, count in vc.items():
        pct = count / len(classified) * 100
        print(f"  {group:15s}  {count:>10,}  ({pct:5.1f}%)")

    print(f"\nClassification methods:")
    mc = classified["classification_method"].value_counts()
    for method, count in mc.items():
        pct = count / len(classified) * 100
        print(f"  {method:15s}  {count:>10,}  ({pct:5.1f}%)")

    for group in ["ukrainian", "russian", "western", "other"]:
        sub = classified[classified["source_group"] == group]
        if sub.empty:
            continue
        print(f"\nTop 10 domains ({group}):")
        top = sub["domain"].value_counts().head(10)
        for domain, cnt in top.items():
            print(f"  {domain:40s}  {cnt:>8,}")

    print(f"\nDaily aggregate:")
    print(f"  Shape: {daily.shape[0]} days × {daily.shape[1]} columns")
    print(f"  Columns: {list(daily.columns)}")
    print(f"  Total articles: {daily['n_articles_total'].sum():,}")
    print(f"  Days with ≥1 article: {(daily['n_articles_total'] > 0).sum()}")

    # Per-query breakdown
    if "query_name" in classified.columns:
        print(f"\nPer-query article counts (after dedup):")
        qvc = classified["query_name"].value_counts()
        for qname, cnt in qvc.items():
            print(f"  {qname:30s}  {cnt:>10,}")

    # Manual precision audit (400 articles: 100 per group)
    print(f"\nGenerating manual precision audit sample (100 per group)...")
    audit = manual_precision_audit(classified, n_per_group=100, seed=42)
    audit.to_csv(AUDIT_FILE, index=False)
    print(f"✓ Saved {AUDIT_FILE}")
    print(f"  {len(audit)} articles to label ({len(audit) // 4} per group × 4 groups)")

    # Final file listing
    print(f"\n{'=' * 70}")
    print("OUTPUT FILES:")
    print(f"{'=' * 70}")
    for f in sorted(OUT_DIR.iterdir()):
        if f.is_file() and "enriched" in f.name or "domain_to_country" in f.name:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name:50s}  {size_mb:8.1f} MB")

    print(f"\n{'=' * 70}")
    print("PHASE 3 ENRICHED POST-PROCESSING COMPLETE")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    print(f"Phase 3 Enriched Post-Processing Pipeline (Colab-safe, chunked)")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw data dir: {RAW_DIR}")
    print(f"Output dir:   {OUT_DIR}")
    print(f"Chunk size:   {CHUNK_SIZE:,} rows")
    print()

    deduped = stage1_load_and_dedup()
    stage2_domain_country_mapping(deduped)
    classified = stage3_classify(deduped, chunk_size=CHUNK_SIZE)
    daily = stage4_daily_aggregate(classified)
    stage5_summary(classified, daily)

    total_min = (time.time() - t_start) / 60
    print(f"\nTotal wall time: {total_min:.1f} minutes")


if __name__ == "__main__":
    main()
