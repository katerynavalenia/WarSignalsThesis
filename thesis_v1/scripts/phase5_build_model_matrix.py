#!/usr/bin/env python3
"""Phase 5D — Build the model matrix from the feature matrix.

Usage
-----
    python scripts/phase5_build_model_matrix.py [--paths-yaml CONFIG]

Produces
--------
    data/processed/model_matrix.parquet
    outputs/tables/info_set_cardinality.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.build_model_matrix import build_model_matrix
from src.features.merge import load_paths_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-yaml",
        default="config/paths.yaml",
        help="Path to the local paths config (default: config/paths.yaml).",
    )
    args = parser.parse_args()

    print("Phase 5D — Building model_matrix.parquet")
    print("=" * 60)

    paths = load_paths_config(args.paths_yaml)

    feat_path = Path(paths["processed_files"]["feature_matrix"])
    if not feat_path.exists():
        print(f"ERROR: {feat_path} not found. Run phase5_build_master.py first.")
        return 1

    out_path = Path(paths["processed_files"]["model_matrix"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading {feat_path} …")
    feat = pd.read_parquet(feat_path)
    print(f"  feature_matrix: {feat.shape}")

    print("Building model matrix …")
    mm = build_model_matrix(feat)

    print(f"  model_matrix: {mm.shape}  ({mm['date'].min().date()} → {mm['date'].max().date()})")
    print(f"  primary target column:      {mm.attrs.get('primary_target')}")
    print(f"  robustness target columns: {mm.attrs.get('robustness_targets')}")

    print(f"\nWriting {out_path} …")
    mm.to_parquet(out_path, index=False)

    # ── Information-set cardinality table ──────────────────────────────────
    info_sets = mm.attrs.get("info_sets", {})
    rows = []
    for name, cols in info_sets.items():
        rows.append({"information_set": name, "n_features": len(cols)})
    card = pd.DataFrame(rows)

    table_path = Path(paths["outputs"]["tables"]) / "info_set_cardinality.csv"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    card.to_csv(table_path, index=False)
    print(f"\nWriting {table_path} …")
    print(card.to_string(index=False))

    # ── Quick summary ─────────────────────────────────────────────────────
    primary = mm.attrs["primary_target"]
    print(f"\nTarget '{primary}':")
    print(f"  non-null: {mm[primary].notna().sum()} / {len(mm)}")
    print(f"  mean:    {mm[primary].mean():.4f}")
    print(f"  std:     {mm[primary].std():.4f}")
    print(f"  min/max: {mm[primary].min():.4f} / {mm[primary].max():.4f}")

    print("\nPhase 5D complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
