"""Build the descriptive-statistics table reported in the thesis.

The table has to describe two different things, and an earlier version
described only the first:

* the **levels** of the perception indices, which is what the reader needs to
  see that Ukrainian and Russian outlets run at 55--95% conflict coverage while
  Western ones sit below 10%; and
* the **daily changes**, which are what every regression in the thesis actually
  uses. A reader who asks "what is the standard deviation of the variable in
  your main regression?" must be able to answer it from the table.

Run from the repository root::

    python scripts/make_thesis_descriptives.py

Writes ``outputs/tables/thesis_descriptives.csv`` and prints the numbers in the
order they appear in the manuscript.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs" / "tables"

ECOSYSTEMS = ["UA", "RU_STATE", "RU_INDEP", "WEST", "EN_GLOBAL"]

LABEL = {
    "UA": "Ukrainian",
    "RU_STATE": "Russian state",
    "RU_INDEP": "Russian independent",
    "WEST": "Western",
    "EN_GLOBAL": "Native-English",
}


def stats(series: pd.Series, label: str, unit: str, period: str) -> dict:
    s = series.dropna()
    return {
        "variable": label,
        "unit": unit,
        "mean": s.mean(),
        "sd": s.std(),
        "min": s.min(),
        "max": s.max(),
        "n": int(s.size),
        "period": period,
    }


def main() -> None:
    perception = pd.read_parquet(INTERIM / "perception_indices.parquet")
    perception = perception.reset_index()
    perception["date"] = pd.to_datetime(perception["date"])
    perception = perception.sort_values("date").set_index("date")

    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    spine["date"] = pd.to_datetime(spine["date"])
    spine = spine.sort_values("date").set_index("date")

    rows = []

    # --- Panel A: financial outcomes, on the sample where each actually trades.
    fin_span = "Bloomberg sample"
    for col, label in [
        ("r_waerlst", "WAERLST return"),
        ("r_bshieldt", "BSHIELDT return"),
        ("r_ita", "ITA return"),
        ("sxxp", "STOXX 600 return"),
    ]:
        s = spine[col].dropna()
        period = f"{s.index.min():%b %Y}--{s.index.max():%b %Y}"
        rows.append(stats(s, label, "%", period))
    s = spine["vix_yf"].dropna()
    rows.append(
        stats(s, "VIX", "index pts", f"{s.index.min():%b %Y}--{s.index.max():%b %Y}")
    )

    # --- Panel B: perception indices in LEVELS, full corpus.
    corpus = f"{perception.index.min():%b %Y}--{perception.index.max():%b %Y}"
    for eco in ECOSYSTEMS:
        rows.append(
            stats(perception[f"att_{eco}"], f"{LABEL[eco]} attention share", "%", corpus)
        )
    for eco in ECOSYSTEMS:
        rows.append(
            stats(perception[f"tone_{eco}"], f"{LABEL[eco]} conflict tone", "score", corpus)
        )

    # --- Panel C: the actual regressors, i.e. daily CHANGES.
    for eco in ECOSYSTEMS:
        rows.append(
            stats(
                perception[f"att_{eco}"].diff(),
                f"D.{LABEL[eco]} attention share",
                "pp/day",
                corpus,
            )
        )
    for eco in ECOSYSTEMS:
        rows.append(
            stats(
                perception[f"tone_{eco}"].diff(),
                f"D.{LABEL[eco]} conflict tone",
                "pts/day",
                corpus,
            )
        )

    table = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "thesis_descriptives.csv"
    table.round(4).to_csv(dest, index=False)

    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(table.round(3).to_string(index=False))
    print(f"\nwrote {dest}")

    # --- The invasion tone comparison reported as its own table in the thesis.
    # Windows are the ones stated in that table's caption.
    pre = perception.loc["2021-11-01":"2022-02-23"]
    post = perception.loc["2022-02-24":"2022-06-05"]
    inv = pd.DataFrame(
        {
            "ecosystem": [LABEL[e] for e in ECOSYSTEMS],
            "pre": [pre[f"tone_{e}"].mean() for e in ECOSYSTEMS],
            "post": [post[f"tone_{e}"].mean() for e in ECOSYSTEMS],
        }
    )
    inv["shift"] = inv["post"] - inv["pre"]
    inv = inv.sort_values("shift")
    inv_dest = OUT / "thesis_invasion_tone.csv"
    inv.round(3).to_csv(inv_dest, index=False)
    print(f"\nInvasion tone, aggregate ({len(pre)} pre-days, {len(post)} post-days)")
    print(inv.round(2).to_string(index=False))

    # The fixed-outlet panel guards the aggregate against composition change:
    # outlets that entered or exited the corpus at the invasion cannot drive it.
    panel = pd.read_csv(OUT / "wedge_fixed_panel.csv")
    print("\nFixed-outlet panel (outlets present on both sides of the invasion)")
    for eco, g in panel.groupby("eco"):
        print(f"  {eco:9s} {len(g):2d} outlets, mean shift {g['shift'].mean():+.3f}")
    print(f"\nwrote {inv_dest}")


if __name__ == "__main__":
    main()
