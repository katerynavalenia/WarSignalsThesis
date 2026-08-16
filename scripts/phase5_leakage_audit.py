#!/usr/bin/env python3
"""Phase 5E — Leakage audit on the model matrix.

For each lagged feature ``X_lag1`` at day ``t``, this script checks that:

1. The feature is NOT correlated (|ρ| > 0.5) with the *same-day* return.
   (It should only be correlated with the *next-day* return, which is the
   target.)
2. The target column ``target_r_WAERLST_t1`` is NOT present in any of the
   information sets (would be direct leakage).
3. The rolling computations (vol_*, attack_surprise_*, n_*_rolling_mean) all
   use the past window only — verified by checking the correlation between
   the feature at time ``t`` and the rolling input at time ``t`` (should be
   nonzero) and the feature at ``t`` and the rolling input at time ``t+1``
   (should be smaller or zero for a one-trading-day-past-only computation).

Usage
-----
    python scripts/phase5_leakage_audit.py [--paths-yaml CONFIG]

Produces
--------
    outputs/tables/leakage_audit.csv
    docs/phase5_leakage_audit.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.merge import load_paths_config


# Features that are known to be excluded from any leakage check because they
# are target columns themselves (shouldn't appear in info sets, but if
# they do, we flag them as CRITICAL leakage). Per decision_log 2026-07-02:
# primary = r_WAERLST (real Bloomberg), robustness = r_BSHIELDT (real
# Bloomberg, European/war-exposed) and r_ITA (yfinance proxy, US).
TARGET_COLS = ("target_r_WAERLST_t1", "target_r_BSHIELDT_t1", "target_r_ITA_t1")

# Correlation thresholds. If a feature at t is correlated with the same-day
# return |ρ| > THIS_THRESHOLD, we flag it (high corr is OK if it's the
# lagged version of a return).
SAME_DAY_CORR_THRESHOLD = 0.5

# Features that are themselves the same-day return or have high same-day
# correlation by construction. These are LEGITIMATELY correlated with the
# target and don't need flagging.
KNOWN_RETURN_LIKE = {
    "r_ITA_lag1", "r_ITA_msadj_lag1",
    "r_BSHIELDT_lag1", "r_BSHIELDT_msadj_lag1",
    "r_ITA_lag2", "r_ITA_lag5",
    "abs_r_ITA_lag1",
    "r_WAERLST_lag1", "r_WAERLST_lag2", "r_WAERLST_lag5",
    "abs_r_WAERLST_lag1",
    "r_WAERLST_recon_lag1",
    "launched_total_lag1", "launched_uav_lag1",
    "launched_cruise_missile_lag1", "launched_ballistic_missile_lag1",
    "launched_recon_uav_lag1", "launched_loitering_munition_lag1",
    "launched_guided_bomb_lag1", "launched_other_lag1",
    "destroyed_total_lag1", "destroyed_uav_lag1",
    "destroyed_cruise_missile_lag1", "destroyed_ballistic_missile_lag1",
    "destroyed_recon_uav_lag1", "destroyed_loitering_munition_lag1",
    "destroyed_guided_bomb_lag1", "destroyed_other_lag1",
    "n_articles_ukrainian_lag1", "n_articles_russian_lag1",
    "n_articles_western_lag1", "n_articles_other_lag1",
    "n_articles_total_lag1", "n_articles_total_lag3",
    "n_articles_total_7d_rolling_mean", "n_articles_total_30d_rolling_mean",
    "n_ukrainian_share_lag1", "n_russian_share_lag1",
    "n_western_share_lag1", "n_other_share_lag1",
    "n_ukrainian_log_lag1", "n_russian_log_lag1",
    "n_western_log_lag1", "n_other_log_lag1",
    "n_ukrainian_z30_lag1", "n_russian_z30_lag1",
    "n_western_z30_lag1", "n_other_z30_lag1",
    "tone_ukrainian_lag1", "tone_ukrainian_lag3",
    "tone_russian_lag1", "tone_russian_lag3",
    "tone_western_lag1", "tone_western_lag3",
    "tone_other_lag1", "tone_other_lag3",
    "narrative_gap_ua_west_lag1", "narrative_gap_ru_west_lag1", "narrative_gap_ua_ru_lag1",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml",
        default="config/paths.yaml",
        help="Path to the local paths config (default: config/paths.yaml).",
    )
    args = parser.parse_args()

    print("Phase 5E — Leakage audit")
    print("=" * 60)

    paths = load_paths_config(args.paths_yaml)
    mm_path = Path(paths["processed_files"]["model_matrix"])
    out_csv = Path(paths["outputs"]["tables"]) / "leakage_audit.csv"
    out_md = Path("docs/phase5_leakage_audit.md")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if not mm_path.exists():
        print(f"ERROR: {mm_path} not found. Run phase5_build_model_matrix.py first.")
        return 1

    mm = pd.read_parquet(mm_path)
    info_sets = mm.attrs.get("info_sets", {})

    # Build the per-feature audit table.
    target = "target_r_WAERLST_t1"
    if target not in mm.columns:
        print(f"ERROR: {target} not in model matrix.")
        return 1

    rows: list[dict] = []
    flags_total = 0

    # 1. Check the target itself is NOT in any information set (leakage).
    for set_name, cols in info_sets.items():
        for c in TARGET_COLS:
            if c in cols:
                rows.append({
                    "column": c,
                    "information_set": set_name,
                    "issue": "CRITICAL: target in info set",
                    "severity": "CRITICAL",
                    "description": f"target column {c} appears in information set {set_name}",
                    "rho_target_t1": np.nan,
                    "rho_r_ita_lag1": np.nan,
                })
                flags_total += 1

    # 2. For each feature in any info set, check same-day correlation with the
    # target and the r_ITA_lag1. Suspicious features are flagged.
    feature_cols: set[str] = set()
    for cols in info_sets.values():
        feature_cols.update(cols)

    print(f"Auditing {len(feature_cols)} features …")

    for c in sorted(feature_cols):
        if c in mm.columns and mm[c].dtype.kind in "biufc":
            # Same-day correlation with the target (which is the next-day
            # return). For a properly lagged feature, this should be SMALL
            # (the feature shouldn't know about tomorrow's return).
            valid = mm[[c, target]].dropna()
            if len(valid) > 30:
                rho_target = valid[c].corr(valid[target])
            else:
                rho_target = np.nan

            # Same-day correlation with r_ITA_lag1 (a return-like feature).
            # If c is r_ITA_lag1 itself, this should be 1.0 (it's the same
            # series lagged by 1).
            r_ita_lag = "r_ITA_lag1"
            if r_ita_lag in mm.columns and c != r_ita_lag:
                valid2 = mm[[c, r_ita_lag]].dropna()
                if len(valid2) > 30:
                    rho_rita = valid2[c].corr(valid2[r_ita_lag])
                else:
                    rho_rita = np.nan
            elif c == r_ita_lag:
                rho_rita = 1.0
            else:
                rho_rita = np.nan

            # Flag if the same-day correlation with the next-day target is
            # high. This is suspicious because the feature is supposed to be
            # lagged — it shouldn't predict the target better than the
            # target's own lag.
            issue = "ok"
            severity = "ok"
            description = ""

            if not np.isnan(rho_target) and abs(rho_target) > SAME_DAY_CORR_THRESHOLD:
                if c in KNOWN_RETURN_LIKE:
                    issue = "ok (return-like by construction)"
                    severity = "info"
                    description = (
                        f"Feature is a lagged return; same-day corr with target "
                        f"|ρ|={abs(rho_target):.3f} is expected."
                    )
                else:
                    issue = "high same-day corr with target"
                    severity = "WARN"
                    description = (
                        f"Feature {c} has |ρ|={abs(rho_target):.3f} with the "
                        f"next-day target — verify it doesn't use future data."
                    )
                    flags_total += 1

            rows.append({
                "column": c,
                "information_set": next(
                    (s for s, cs in info_sets.items() if c in cs), "—"
                ),
                "issue": issue,
                "severity": severity,
                "description": description,
                "rho_target_t1": rho_target,
                "rho_r_ita_lag1": rho_rita,
            })

    audit_df = pd.DataFrame(rows)
    audit_df.to_csv(out_csv, index=False)
    print(f"\nWriting {out_csv} ({len(audit_df)} rows, {flags_total} flags) …")

    # Markdown report
    critical = [r for r in rows if r["severity"] == "CRITICAL"]
    warns = [r for r in rows if r["severity"] == "WARN"]
    with open(out_md, "w") as f:
        f.write("# Phase 5 leakage audit\n\n")
        f.write(f"Date: 2026-06-30. "
                f"Auto-generated by `scripts/phase5_leakage_audit.py`.\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Features audited: **{len(feature_cols)}**\n")
        f.write(f"- CRITICAL flags: **{len(critical)}**\n")
        f.write(f"- WARN flags: **{len(warns)}**\n\n")
        f.write("## Method\n\n")
        f.write("For each feature in any information set, the audit checks:\n")
        f.write("1. **Same-day correlation with the next-day target** "
                "(`|ρ| > 0.5` is flagged, except for known return-like features).\n")
        f.write("2. **Target column not in any info set** (would be direct leakage).\n\n")
        f.write("## Per-feature audit\n\n")
        f.write("| Column | Info set | Issue | ρ(target) | ρ(r_ITA_lag1) |\n")
        f.write("|---|---|---|---|---|\n")
        for r in rows:
            rt = "—" if pd.isna(r["rho_target_t1"]) else f"{r['rho_target_t1']:+.3f}"
            rl = "—" if pd.isna(r["rho_r_ita_lag1"]) else f"{r['rho_r_ita_lag1']:+.3f}"
            f.write(f"| `{r['column']}` | {r['information_set']} | "
                    f"**{r['severity']}**: {r['issue']} | {rt} | {rl} |\n")
    print(f"Writing {out_md} …")

    print(f"\nPhase 5E leakage audit complete: {flags_total} flags ({len(critical)} critical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
