#!/usr/bin/env python3
"""Phase 3 — close-out orchestrator.

Runs the remaining Phase 3 deliverables that were not produced by
``scripts/phase3_post_process_enriched.py``:

  1+2. Fix the ``date`` index on the daily aggregate and add the
        narrative-gap columns + per-group tone sample sizes.
  3.    Build the per-query × source-group pivot (16 columns, daily).
  4.    Run the automated precision check (replaces manual labelling).
  5.    Refresh the sensitivity report on the full 46-month data.

Run from the project root:

    python scripts/phase3_close_gaps.py
    python scripts/phase3_close_gaps.py --skip-pivot
    python scripts/phase3_close_gaps.py --skip-precision --skip-sensitivity
    python scripts/phase3_close_gaps.py --dry-run

The script intentionally has zero Colab / rclone / Drive dependencies —
all input data lives on local disk.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data.gdelt_postprocess import (
    add_narrative_gap,
    auto_precision_check,
    build_query_group_pivot,
    fix_date_index,
    load_articles_columns,
    refresh_sensitivity_report,
    write_auto_precision_report,
)

ARTICLES_PATH = PROJECT_ROOT / "data/processed/news/gdelt_articles_classified_enriched.parquet"
DAILY_PATH    = PROJECT_ROOT / "data/processed/news/news_daily_enriched.parquet"
DAILY_CSV     = PROJECT_ROOT / "data/processed/news/news_daily_enriched.csv"
PIVOT_PATH    = PROJECT_ROOT / "data/processed/news/news_query_group_pivot.parquet"
PIVOT_CSV     = PROJECT_ROOT / "data/processed/news/news_query_group_pivot.csv"
PRECISION_PATH = PROJECT_ROOT / "data/processed/news/auto_precision_report.md"
SENSITIVITY_PATH = PROJECT_ROOT / "data/processed/news/sensitivity_report.md"
DOMAIN_PATH   = PROJECT_ROOT / "data/processed/news/domain_to_country.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-pivot", action="store_true")
    p.add_argument("--skip-precision", action="store_true")
    p.add_argument("--skip-sensitivity", action="store_true")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and exit without writing any files.",
    )
    return p.parse_args()


def _mem_gb(df: pd.DataFrame) -> float:
    return float(df.memory_usage(deep=True).sum()) / (1024 ** 3)


def step_1_2_fix_daily(args: argparse.Namespace) -> None:
    """Fix date index, add narrative-gap columns, overwrite daily files."""
    print("\n[1+2] Fixing date index and adding narrative-gap columns")
    daily = pd.read_parquet(DAILY_PATH)
    print(f"  loaded {daily.shape}, RAM ~{_mem_gb(daily):.2f} GB")
    daily = fix_date_index(daily)
    daily = add_narrative_gap(daily)
    new_cols = [c for c in daily.columns if c.startswith("narrative_gap_") or c.startswith("n_tone_")]
    print(f"  new columns ({len(new_cols)}): {new_cols}")
    if args.dry_run:
        print("  [dry-run] would overwrite", DAILY_PATH, "and", DAILY_CSV)
        return
    daily.to_parquet(DAILY_PATH, index=False)
    daily.to_csv(DAILY_CSV, index=False)
    print(f"  wrote {DAILY_PATH.name} and {DAILY_CSV.name}")


def step_3_pivot(args: argparse.Namespace) -> None:
    """Build per-query × source-group daily pivot."""
    print("\n[3] Building query × group pivot")
    articles = load_articles_columns(
        ARTICLES_PATH, ["date", "query_name", "source_group"]
    )
    print(f"  RAM ~{_mem_gb(articles):.2f} GB")
    pivot = build_query_group_pivot(articles)
    print(f"  pivot shape: {pivot.shape}")
    if args.dry_run:
        print("  [dry-run] would write", PIVOT_PATH, "and", PIVOT_CSV)
        del articles
        gc.collect()
        return
    pivot.to_parquet(PIVOT_PATH, index=False)
    pivot.to_csv(PIVOT_CSV, index=False)
    print(f"  wrote {PIVOT_PATH.name} and {PIVOT_CSV.name}")
    del articles
    gc.collect()


def step_4_precision(args: argparse.Namespace) -> None:
    """Automated precision check using high-confidence domain→country map."""
    print("\n[4] Running automated precision check")
    articles = load_articles_columns(
        ARTICLES_PATH, ["domain", "source_group", "classification_method"]
    )
    print(f"  RAM ~{_mem_gb(articles):.2f} GB")
    domain_country = pd.read_csv(DOMAIN_PATH)
    print(f"  domain→country map: {len(domain_country):,} domains")
    report = auto_precision_check(articles, domain_country)
    print(
        f"  high-confidence domains: {report['n_domains_kept']:,} "
        f"({report['n_articles_kept']:,} articles)"
    )
    print(
        f"  overall precision: {report['overall']['precision']:.3f} "
        f"({report['overall']['n_correct']:,} / {report['overall']['n']:,})"
    )
    if args.dry_run:
        print("  [dry-run] would write", PRECISION_PATH)
        del articles
        gc.collect()
        return
    write_auto_precision_report(report, PRECISION_PATH)
    print(f"  wrote {PRECISION_PATH.name}")
    del articles
    gc.collect()


def step_5_sensitivity(args: argparse.Namespace) -> None:
    """Refresh sensitivity report on full 46-month data."""
    print("\n[5] Refreshing sensitivity report")
    # Need the countries column for the country_only strategy.
    articles = load_articles_columns(
        ARTICLES_PATH,
        ["domain", "source_group", "classification_method", "countries"],
    )
    print(f"  RAM ~{_mem_gb(articles):.2f} GB")
    if args.dry_run:
        print("  [dry-run] would write", SENSITIVITY_PATH)
        del articles
        gc.collect()
        return
    refresh_sensitivity_report(articles, SENSITIVITY_PATH)
    print(f"  wrote {SENSITIVITY_PATH.name}")


def main() -> int:
    args = parse_args()
    print("Phase 3 — close-out orchestrator")
    print(f"  project root: {PROJECT_ROOT}")
    print(
        f"  flags: dry_run={args.dry_run} skip_pivot={args.skip_pivot} "
        f"skip_precision={args.skip_precision} "
        f"skip_sensitivity={args.skip_sensitivity}"
    )
    t_start = time.time()

    step_1_2_fix_daily(args)
    if not args.skip_pivot:
        step_3_pivot(args)
    if not args.skip_precision:
        step_4_precision(args)
    if not args.skip_sensitivity:
        step_5_sensitivity(args)

    print(f"\nDone in {time.time() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
