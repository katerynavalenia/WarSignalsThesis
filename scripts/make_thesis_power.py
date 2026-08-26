"""Simulate Clark--West power at both out-of-sample lengths in the forecast grid.

The committed power curve was run once, on the long sample, at 60 paths per
grid point. Two things were wrong with quoting it as the thesis's power
statement. It carried a simulation standard error of about six percentage
points, which is wide enough that the headline figure was not stable to the
second digit. And it describes only three of the five forecast targets: the two
Bloomberg indices begin in 2020 and yield 686 out-of-sample days against 1,855
for the rest, so the long-sample curve says nothing about the power of the
tests run on them.

This script re-runs the simulation at both lengths and at enough paths for the
figures to be quoted, writing one row per (sample length, implanted R^2).

Run from the repository root::

    python scripts/make_thesis_power.py            # 1,000 paths per point
    python scripts/make_thesis_power.py --n-sims 200   # quicker check

Writes ``outputs/tables/thesis_power_curve.csv``.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.evaluation import simulate_power_r2_oos  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs" / "tables"

R2_GRID = (0.000, 0.002, 0.005, 0.010, 0.020)

#: The two out-of-sample lengths the forecast grid actually contains. ITA runs
#: the full span; BSHIELDT starts with the Bloomberg indices in 2020.
TARGETS = {"r_ita": "long (free-data targets)",
           "r_bshieldt": "short (Bloomberg targets)"}


def load() -> pd.DataFrame:
    perception = pd.read_parquet(INTERIM / "perception_indices.parquet").reset_index()
    perception["date"] = pd.to_datetime(perception["date"])
    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    spine["date"] = pd.to_datetime(spine["date"])
    keep = ["date", *TARGETS]
    return perception.merge(spine[keep], on="date", how="inner").set_index("date")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-sims", type=int, default=1000)
    args = ap.parse_args()

    panel = load()
    frames = []
    for target, label in TARGETS.items():
        r = panel[target].dropna()
        curve = simulate_power_r2_oos(r, r2_grid=R2_GRID, n_sims=args.n_sims)
        curve.insert(0, "sample", label)
        # Binomial standard error of each rejection rate, so the table can be
        # read with its own precision attached.
        p = curve["rejection_rate"].to_numpy(float)
        curve["se"] = np.sqrt(p * (1 - p) / args.n_sims)
        frames.append(curve)
        print(f"\n{label}: n = {len(r)}, out-of-sample {int(curve.n_oos.iloc[0])}")
        print(curve[["true_r2_oos", "rejection_rate", "se"]].round(3).to_string(index=False))

    out = pd.concat(frames, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "thesis_power_curve.csv"
    out.round(4).to_csv(dest, index=False)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
