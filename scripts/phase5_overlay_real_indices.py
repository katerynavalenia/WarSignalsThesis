#!/usr/bin/env python3
"""Phase 5 rebuild — overlay real Bloomberg WAERLST/BSHIELDT onto daily_master.

Per decision_log 2026-07-02 ("Target hierarchy restructured around real
Bloomberg WAERLST/BSHIELDT series"), the real single-index Bloomberg series
(``data/raw/bloomberg/WAERLST Index.xlsx``, ``BSHIELDT Index.xlsx``) replace
the noisy mcap-weighted reconstruction as the basis for the primary
(``r_WAERLST``) and European-robustness (``r_BSHIELDT``) targets.

The original raw Bloomberg constituent files and the market-benchmark file
(``indexes.xlsx``, source of SPX/SXXP/VIX/Brent/EURUSD/MSCI_World) are not
available locally or on the project's Google Drive (only the merged
``daily_master.parquet`` has those control columns already computed).
Rather than fabricate or re-derive that data, this script reuses the
already-computed control columns cached in ``daily_master.parquet`` and
overlays the new real WAERLST/BSHIELDT series on top, via
:func:`src.data.financial.overlay_real_indices`.

Usage
-----
    python scripts/phase5_overlay_real_indices.py [--paths-yaml CONFIG]

Produces (overwrites in place; run phase5_build_master.py's backup step
first if you need to preserve the prior version)
--------
    data/processed/daily_master.parquet     (real WAERLST/BSHIELDT overlaid)
    data/processed/feature_matrix.parquet   (financial/attack/news features)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.data.financial import overlay_real_indices
from src.features.attack_features import add_attack_features
from src.features.calendar_features import add_calendar_features
from src.features.financial_features import add_financial_features
from src.features.merge import load_paths_config
from src.features.news_features import add_news_features

WAERLST_XLSX = Path("data/raw/bloomberg/WAERLST Index.xlsx")
BSHIELDT_XLSX = Path("data/raw/bloomberg/BSHIELDT Index.xlsx")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths-yaml", default="config/paths.yaml")
    args = parser.parse_args()

    paths = load_paths_config(args.paths_yaml)
    master_path = Path(paths["processed_files"]["daily_master"])
    feat_path = Path(paths["processed_files"]["feature_matrix"])

    print("Phase 5 rebuild — overlay real WAERLST/BSHIELDT")
    print("=" * 60)

    print(f"Loading {master_path} ...")
    master = pd.read_parquet(master_path)
    print(f"  before: {master.shape}  cols(sample): "
          f"{[c for c in master.columns if c in ('ITA','BSHIELDT','WAERLST_recon','r_BSHIELDT')]}")

    print(f"Overlaying real indices from {WAERLST_XLSX.name} / {BSHIELDT_XLSX.name} ...")
    master_idx = master.set_index("date")
    overlaid = overlay_real_indices(master_idx, WAERLST_XLSX, BSHIELDT_XLSX)
    overlaid = overlaid.reset_index()

    new_cols = [c for c in overlaid.columns if c not in master.columns]
    renamed_cols = [c for c in overlaid.columns if c.endswith("_recon") and c not in master.columns]
    print(f"  after:  {overlaid.shape}")
    print(f"  new columns ({len(new_cols)}): {sorted(new_cols)}")

    print(f"Writing {master_path} ...")
    overlaid.to_parquet(master_path, index=False)

    # ── Phase 5C — rebuild feature_matrix.parquet ──────────────────────
    print("\nRebuilding feature_matrix.parquet ...")
    feat = overlaid.copy()
    feat = add_financial_features(feat)
    print(f"  + financial:  {feat.shape}")
    feat = add_attack_features(feat)
    print(f"  + attack:     {feat.shape}")
    feat = add_news_features(feat)
    print(f"  + news:       {feat.shape}")
    feat = add_calendar_features(feat)
    print(f"  + calendar:   {feat.shape}")

    print(f"Writing {feat_path} ...")
    feat.to_parquet(feat_path, index=False)

    # Sanity: confirm new required F-set columns exist and have coverage
    # in the modeling window (2022-09-29+, per the news-gated common sample).
    print("\nFeature coverage in modeling window (2022-09-29+):")
    win = feat[feat["date"] >= "2022-09-29"]
    for col in (
        "r_WAERLST", "r_BSHIELDT", "r_WAERLST_recon",
        "r_WAERLST_lag1" if "r_WAERLST_lag1" in feat.columns else "vol_5d",
        "logvol_WAERLST", "logvol_BSHIELDT",
    ):
        if col in feat.columns:
            nn = win[col].notna().sum()
            print(f"  {col:24s}  {nn:5d} non-null / {len(win)} ({100*nn/len(win):.1f}%)")
        else:
            print(f"  {col:24s}  MISSING")

    print("\nPhase 5 real-index overlay complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
