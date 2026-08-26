"""Correlations among the war indicators, over the full sample.

The physical and narrative layers are treated throughout as two distinct sources
of information about the same war. Whether they are in fact distinct is an
empirical question, and this answers it before any forecasting is attempted: if
attack intensity and media attention moved together, comparing them would be
comparing one signal with itself.

Correlations are in levels and over the whole span on which each pair is
observed, so they describe the indicators as series rather than the daily
innovations the forecasting design uses.

    python scripts/run_indicator_correlations.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.attacks import load_attack_panel  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

LABELS = {
    "attack": "Attack intensity",
    "att_UA": "Ukrainian attention",
    "att_RU_STATE": "Russian state attention",
    "att_RU_INDEP": "Russian independent attention",
    "att_WEST": "Western attention",
    "tone_UA": "Ukrainian tone",
    "tone_RU_STATE": "Russian state tone",
    "tone_WEST": "Western tone",
    "gpr": "Geopolitical risk index",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(INTERIM / "perception_indices.parquet")
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    atk = load_attack_panel(spine.reset_index()["date"]).set_index("date")

    frame = pd.DataFrame({
        "attack": np.log1p(atk["launched_total_lag1"]),
        **{c: idx[c] for c in LABELS if c in idx.columns},
        "gpr": spine["gpr"],
    })
    frame = frame.rename(columns=LABELS)
    corr = frame.corr()

    corr.to_csv(args.out_dir / "indicator_correlations.csv")
    print(f"complete rows: {len(frame.dropna())}\n")
    print(corr.round(2).to_string())

    off = corr.where(~np.eye(len(corr), dtype=bool))
    print(f"\n  strongest pair : {off.stack().idxmax()} at {off.stack().max():.2f}")
    print(f"  weakest pair   : {off.abs().stack().idxmin()} at "
          f"{off.stack()[off.abs().stack().idxmin()]:.2f}")
    cross = corr.loc["Attack intensity",
                     [c for c in corr.columns if "attention" in c or "tone" in c]]
    print(f"\n  attack intensity against the narrative indicators: "
          f"{cross.abs().min():.2f} to {cross.abs().max():.2f} in absolute value")
    print(f"\nwrote {args.out_dir / 'indicator_correlations.csv'}")


if __name__ == "__main__":
    main()
