#!/usr/bin/env python3
"""Phase 5E — Generate the model-matrix data dictionary.

Usage
-----
    python scripts/phase5_data_dictionary.py [--paths-yaml CONFIG]

Produces
--------
    data/processed/data_dictionary.csv
    docs/data_dictionary.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

# Allow running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.build_model_matrix import (
    CALENDAR_PASSTHROUGH_COLS,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    build_model_matrix,
)
from src.features.merge import load_paths_config


# ── Column-level metadata ──────────────────────────────────────────────────


def _classify(name: str) -> tuple[str, str, str]:
    """Return ``(group, unit, available_at)`` for a model-matrix column.

    The metadata is hand-curated for the well-known columns. Unknown columns
    are classified as "derived" with a generic description so the dictionary
    is still useful.
    """
    if name in CALENDAR_PASSTHROUGH_COLS:
        return "calendar", "binary/categorical", "market open on day t"
    if name == "date":
        return "structural", "date", "n/a"
    if name == f"target_{PRIMARY_TARGET}_t1":
        return "target", "percent (%)", "market close on next trading day"
    if name == f"target_{SECONDARY_TARGET}_t1":
        return "target", "percent (%)", "market close on next trading day"
    if name.startswith("target_"):
        return "target", "percent (%)", "market close on next trading day"
    if name.startswith("r_") and name.endswith("_lag1"):
        return "financial", "percent (%)", "market close on day t-1"
    if name.endswith("_msadj_lag1"):
        return "financial", "percent (%)", "market close on day t-1 (ms-adj)"
    if name.endswith("_lag2") or name.endswith("_lag5"):
        return "financial", "percent (%)", "market close on day t-2 or t-5"
    if name.startswith("vol_") or name == "abs_r_ITA_lag1":
        return "financial", "percent (%) std", "market close on day t-1"
    if name.startswith("VIX") or name.startswith("d_VIX"):
        return "financial", "index level / change", "market close on day t-1"
    if name.startswith("launched_") or name.startswith("destroyed_"):
        return "attack", "count", "end of day t-1 (UAF daily report)"
    if name.startswith("attack_surprise_") or name == "penetrations_estimated_lag1":
        return "attack", "count (surprise)", "end of day t-1"
    if name in ("interception_rate_lag1", "weapon_diversity_lag1",
                 "war_intensity_lag1", "large_attack_indicator_lag1",
                 "n_attack_events_lag1", "n_records_lag1"):
        return "attack", "ratio / count", "end of day t-1"
    if name.endswith("_share_lag1") or name.endswith("_log_lag1") or name.endswith("_z30_lag1"):
        return "news", "ratio / log / z-score", "end of day t-1"
    if name.startswith("n_articles_") and name.endswith("_lag1"):
        return "news", "count", "end of day t-1"
    if name.startswith("tone_") and (name.endswith("_lag1") or name.endswith("_lag3")):
        return "news", "GDELT tone (unitless)", "end of day t-1"
    if name.endswith("_rolling") or name.endswith("_rolling_mean"):
        return "rolling", "rolling mean (past-only)", "end of day t-1"
    if name.startswith("narrative_gap_") and name.endswith("_lag1"):
        return "news", "tone difference", "end of day t-1"
    if name.startswith("n_ukrainian_russian_attack_direct_lag1") or \
       name.startswith("n_western_russian_attack_direct_lag1") or \
       name.startswith("n_other_russian_attack_direct_lag1") or \
       name.startswith("n_russian_russian_attack_direct_lag1"):
        return "news", "count (per-query × per-group)", "end of day t-1"
    if name.endswith("_lag1"):
        return "derived", "lagged (shifted by 1 day)", "end of day t-1"
    return "derived", "engineered", "see Phase 5C feature modules"


# Column-level description table (in addition to the auto-generated group/unit).
DESCRIPTIONS: dict[str, str] = {
    "date": "Calendar day.",
    "is_weekend": "1 if Saturday or Sunday.",
    "is_holiday": "1 if US federal market holiday (observed).",
    "day_of_week": "0=Mon, ..., 6=Sun.",
    "day_of_month": "1..31.",
    "month": "1..12.",
    "quarter": "1..4.",
    "is_month_start": "1 if first calendar day of the month.",
    "is_month_end": "1 if last calendar day of the month.",
    "is_quarter_end": "1 if last calendar day of the quarter.",
    "days_since_invasion": "Days since 2022-02-24 (clamped at 0 pre-invasion).",
    "vix_low": "1 if VIX < 15 on day t-1.",
    "vix_normal": "1 if 15 ≤ VIX < 25 on day t-1.",
    "vix_high": "1 if 25 ≤ VIX < 35 on day t-1.",
    "vix_crisis": "1 if VIX ≥ 35 on day t-1.",
    "waerlst_missing": "1 if WAERLST reconstruction is NaN on day t-1.",
    f"target_{PRIMARY_TARGET}_t1": (
        "PRIMARY TARGET — ITA ETF return on the next trading day after t "
        "(per §9 weekend rule, Friday close → Monday return)."
    ),
    f"target_{SECONDARY_TARGET}_t1": (
        "SECONDARY TARGET — Bloomberg WAERLST reconstruction return on the next "
        "trading day after t. Used for robustness (decision_log 2026-06-28)."
    ),
    "r_ITA_lag1": "ITA ETF return on day t-1 (one trading day lag).",
    "r_ITA_msadj_lag1": "ITA return minus MSCI World return (market-adjusted).",
    "r_BSHIELDT_lag1": "European defense index (reconstructed) return on t-1.",
    "r_BSHIELDT_msadj_lag1": "BSHIELDT return minus STXE 600 return (ms-adj).",
    "VIX_lag1": "VIX level on day t-1.",
    "d_VIX_lag1": "VIX daily change on day t-1.",
    "vol_5d_lag1": "5-day rolling std of ITA returns (sample, ddof=1) on t-1.",
    "vol_20d_lag1": "20-day rolling std of ITA returns on t-1.",
    "abs_r_ITA_lag1": "Absolute value of r_ITA on t-1 (realized-variance proxy).",
    "r_ITA_lag2": "ITA return 2 trading days back.",
    "r_ITA_lag5": "ITA return 5 trading days back.",
    "launched_total_lag1": "Total weapons launched across all categories on t-1.",
    "launched_uav_lag1": "Shahed-type UAVs launched on t-1.",
    "launched_cruise_missile_lag1": "Cruise missiles launched on t-1.",
    "launched_ballistic_missile_lag1": "Ballistic missiles launched on t-1.",
    "destroyed_total_lag1": "Total weapons intercepted/destroyed on t-1.",
    "interception_rate_lag1": "destroyed_total / launched_total on t-1.",
    "weapon_diversity_lag1": "1 − HHI of weapon-category shares on t-1.",
    "war_intensity_lag1": "log(1 + launched_total) on t-1.",
    "attack_uav_share_lag1": "launched_uav / launched_total on t-1.",
    "attack_cruise_share_lag1": "launched_cruise / launched_total on t-1.",
    "attack_ballistic_share_lag1": "launched_ballistic / launched_total on t-1.",
    "penetrations_estimated_lag1": "launched_total − destroyed_total on t-1.",
    "launched_total_lag3": "Total weapons launched 3 calendar days back.",
    "launched_total_7d_rolling": "7-day rolling mean of launched_total (past-only).",
    "launched_total_30d_rolling": "30-day rolling mean of launched_total.",
    "large_attack_indicator_lag1": "1 if launched_total > 90th percentile (full-sample).",
    "attack_surprise_total_7d_lag1": "launched_total − mean(launched_total[t-7, t)).",
    "attack_surprise_total_30d_lag1": "30-day window surprise of total.",
    "attack_surprise_total_90d_lag1": "90-day window surprise of total.",
    "n_articles_ukrainian_lag1": "Day-t-1 article count for Ukrainian-language news.",
    "n_articles_total_lag1": "Day-t-1 total article count across all groups.",
    "n_articles_total_7d_rolling_mean": "7-day rolling mean of total articles.",
    "n_ukrainian_share_lag1": "Ukrainian share of total articles on t-1.",
    "n_ukrainian_z30_lag1": "30-day rolling z-score of Ukrainian articles.",
    "n_ukrainian_russian_attack_direct_lag1": "Per-query × per-group count.",
    "tone_ukrainian_lag1": "GDELT tone of Ukrainian articles on t-1.",
    "narrative_gap_ua_west_lag1": "tone_ukrainian − tone_western on t-1.",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml",
        default="config/paths.yaml",
        help="Path to the local paths config (default: config/paths.yaml).",
    )
    args = parser.parse_args()

    print("Phase 5E — Generating data dictionary")
    print("=" * 60)

    paths = load_paths_config(args.paths_yaml)
    feat_path = Path(paths["processed_files"]["feature_matrix"])
    mm_path = Path(paths["processed_files"]["model_matrix"])
    dict_csv = Path(paths["processed_files"]["data_dictionary"])
    dict_md = Path("docs/data_dictionary.md")

    if not mm_path.exists():
        print(f"ERROR: {mm_path} not found. Run phase5_build_model_matrix.py first.")
        return 1

    print(f"Loading {feat_path} …")
    feat = pd.read_parquet(feat_path)
    print(f"  feature_matrix: {feat.shape}")

    print("Building model matrix (in-memory) …")
    mm = build_model_matrix(feat)

    # Build the data dictionary table.
    rows = []
    for col in mm.columns:
        if col in ("date",):
            group, unit, avail = "structural", "date", "n/a"
        elif col.startswith("target_"):
            group, unit, avail = (
                "target", "percent (%)", "market close on next trading day"
            )
        else:
            group, unit, avail = _classify(col)
        desc = DESCRIPTIONS.get(
            col,
            f"Phase 5 engineered feature (see {feat_path.name})."
        )
        # Per-column NaN and dtype for documentation.
        nn = int(mm[col].notna().sum()) if col != "date" else len(mm)
        dtype = str(mm[col].dtype) if col != "date" else "datetime64[ns]"
        rows.append({
            "column": col,
            "group": group,
            "dtype": dtype,
            "unit": unit,
            "available_at": avail,
            "non_null_in_modeling_window": nn,
            "description": desc,
        })

    dict_df = pd.DataFrame(rows)
    dict_csv.parent.mkdir(parents=True, exist_ok=True)
    dict_df.to_csv(dict_csv, index=False)
    print(f"\nWriting {dict_csv} ({len(dict_df)} rows) …")

    # Generate the markdown data dictionary (curated from CSV).
    with open(dict_md, "w") as f:
        f.write("# Model-matrix data dictionary\n\n")
        f.write("Auto-generated by `scripts/phase5_data_dictionary.py`. ")
        f.write("Source: `data/processed/feature_matrix.parquet` → ")
        f.write("`data/processed/model_matrix.parquet`.\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total columns: **{len(dict_df)}**\n")
        for g, n in dict_df["group"].value_counts().items():
            f.write(f"- {g}: **{n}**\n")
        f.write(f"- Modeling-window rows: **{len(mm)}** ")
        f.write(f"({mm['date'].min().date()} → {mm['date'].max().date()})\n\n")
        f.write("## Per-column metadata\n\n")
        f.write("| Column | Group | Dtype | Unit | Available at | Non-null | Description |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(
                f"| `{r['column']}` | {r['group']} | {r['dtype']} | "
                f"{r['unit']} | {r['available_at']} | "
                f"{r['non_null_in_modeling_window']} | {r['description']} |\n"
            )
    print(f"Writing {dict_md} …")

    print("\nPhase 5E data dictionary complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
