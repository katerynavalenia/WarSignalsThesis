"""Build the correlation table reported in the thesis descriptive section.

The committed ``indicator_correlations.csv`` is a levels matrix on the
attack subsample and carries no EN_GLOBAL column and no equity returns, so it
cannot support the claim the descriptive section needs to make: that the five
media ecosystems are distinct populations, and that none of them is strongly
correlated with defence returns unconditionally.

This script writes that table instead. Everything is in **daily first
differences**, which is the transform used in every regression in the thesis
(levels carry a common war-regime trend that the financial controls already
absorb).

Run from the repository root::

    python scripts/make_thesis_correlations.py

Writes ``outputs/tables/thesis_correlations.csv``.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs" / "tables"

# Ecosystems in the order they are reported in the thesis: local blocks first,
# then the two Western-facing ones, so the block structure is visible.
ECOSYSTEMS = ["UA", "RU_STATE", "RU_INDEP", "WEST", "EN_GLOBAL"]

LABEL = {
    "UA": "Ukrainian",
    "RU_STATE": "Russian state",
    "RU_INDEP": "Russian indep.",
    "WEST": "Western",
    "EN_GLOBAL": "Native-English",
}


def load_panel() -> pd.DataFrame:
    """Perception indices and financial series on one daily index, differenced."""
    perception = pd.read_parquet(INTERIM / "perception_indices.parquet")
    # perception_indices is stored with `date` as the index; the repository
    # convention is a regular column, so restore it before merging.
    perception = perception.reset_index().rename(columns={"index": "date"})
    perception["date"] = pd.to_datetime(perception["date"])

    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    spine["date"] = pd.to_datetime(spine["date"])

    keep = ["date", "r_waerlst", "r_bshieldt", "sxxp", "vix_yf"]
    # Left join: the media series exist for every corpus day, while the
    # Bloomberg indices begin later. Correlations below are computed pairwise,
    # so the media-versus-media block uses the full corpus and only the
    # media-versus-returns columns are restricted to the Bloomberg overlap.
    panel = perception.merge(spine[keep], on="date", how="left")
    panel = panel.sort_values("date").set_index("date")

    out = pd.DataFrame(index=panel.index)
    for eco in ECOSYSTEMS:
        # Attention and tone enter the regressions as daily changes.
        out[f"att_{eco}"] = panel[f"att_{eco}"].diff()
        out[f"tone_{eco}"] = panel[f"tone_{eco}"].diff()
    out["r_waerlst"] = panel["r_waerlst"]
    out["r_bshieldt"] = panel["r_bshieldt"]
    out["r_sxxp"] = panel["sxxp"]
    out["d_vix"] = panel["vix_yf"].diff()
    # Deliberately not dropna(): pandas' .corr() uses pairwise-complete
    # observations, which is what keeps the media block on the full corpus.
    return out


def block(panel: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Ecosystem-by-ecosystem correlations, plus columns against the outcomes."""
    cols = [f"{prefix}_{eco}" for eco in ECOSYSTEMS]
    corr = panel[cols + ["r_waerlst", "r_bshieldt"]].corr()
    out = corr.loc[cols, cols + ["r_waerlst", "r_bshieldt"]]
    out.index = [LABEL[e] for e in ECOSYSTEMS]
    out.columns = [LABEL[e] for e in ECOSYSTEMS] + ["WAERLST return", "BSHIELDT return"]
    return out


def main() -> None:
    panel = load_panel()
    att = block(panel, "att")
    tone = block(panel, "tone")

    att.insert(0, "panel", "A: attention-share changes")
    tone.insert(0, "panel", "B: conflict-tone changes")
    combined = pd.concat([att, tone])
    combined.index.name = "ecosystem"

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "thesis_correlations.csv"
    combined.round(3).to_csv(dest)

    media = [f"{p}_{e}" for p in ("att", "tone") for e in ECOSYSTEMS]
    print(f"corpus days (media block):   {panel[media].dropna().shape[0]}")
    print(f"Bloomberg overlap (returns): {panel[['r_waerlst', 'r_bshieldt']].dropna().shape[0]}")
    print(f"span {panel.index.min().date()} to {panel.index.max().date()}")
    print()
    print("Panel A: attention-share changes")
    print(att.drop(columns="panel").round(3).to_string())
    print()
    print("Panel B: conflict-tone changes")
    print(tone.drop(columns="panel").round(3).to_string())
    print()
    # The two numbers the descriptive text quotes directly.
    a = att.drop(columns="panel")
    off = a.loc[
        [LABEL[e] for e in ECOSYSTEMS], [LABEL[e] for e in ECOSYSTEMS]
    ].where(lambda d: d < 0.999)
    print(f"max off-diagonal attention correlation: {off.max().max():.3f}")
    print(f"UA vs native-English attention: {a.loc['Ukrainian', 'Native-English']:.3f}")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
