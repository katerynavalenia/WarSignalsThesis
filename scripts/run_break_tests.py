"""Formal break tests around February 2022 — supervisor comment #2.

The review asked what happens around the invasion. Chapter 5 shows it in plots
and pre/post means; this supplies the test.

Two questions, deliberately in this order:

1. **Is there a break at 24 February 2022?** Chow, with the date fixed by the
   event rather than chosen from the data.
2. **Where is the largest break if nobody says?** A supremum-Wald scan over
   candidate dates. If it lands on the invasion unprompted, that is much stronger
   than the first test, because the first test can only confirm a date the
   analyst supplied.

Run on the attention and tone series of every ecosystem, so the answer can differ
by ecosystem — which is the point, since Chapter 5's central claim is that
Russian state media did *not* break when everyone else did.

    python scripts/run_break_tests.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.perception import CORE, build_indices  # noqa: E402
from src.models.breaks import chow_test, supremum_break  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")
INVASION = "2022-02-24"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-boot", type=int, default=400)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_daily.parquet")
    idx = build_indices(daily)
    print(f"indices: {len(idx)} days, {idx.index.min().date()} -> {idx.index.max().date()}")

    rows = []
    for kind in ("att", "tone"):
        for eco in CORE:
            col = f"{kind}_{eco}"
            if col not in idx:
                continue
            s = idx[col].dropna()
            rec = {"series": col, "n": len(s)}
            try:
                c = chow_test(s, INVASION)
                rec |= {"chow_F": c.statistic, "chow_p": c.pvalue}
            except ValueError as exc:
                rec |= {"chow_F": float("nan"), "chow_p": float("nan"),
                        "note": str(exc)[:40]}
            try:
                b = supremum_break(s, n_boot=args.n_boot)
                rec |= {"sup_F": b.statistic, "sup_p": b.pvalue,
                        "argmax_break": b.break_date.date(),
                        "days_from_invasion": abs((b.break_date - pd.Timestamp(INVASION)).days)}
            except ValueError as exc:
                rec |= {"sup_F": float("nan"), "sup_p": float("nan"),
                        "argmax_break": None, "days_from_invasion": None,
                        "note": str(exc)[:40]}
            rows.append(rec)

    out = pd.DataFrame(rows)

    print("\n=== 1. CHOW: is there a break at 2022-02-24? (date fixed in advance) ===")
    print(out[["series", "n", "chow_F", "chow_p"]].round(4).to_string(index=False))

    print("\n=== 2. SUPREMUM: where is the largest break, unprompted? ===")
    print(out[["series", "sup_F", "sup_p", "argmax_break", "days_from_invasion"]]
          .round(4).to_string(index=False))

    near = out.dropna(subset=["days_from_invasion"])
    if len(near):
        hits = (near["days_from_invasion"] <= 60).sum()
        print(f"\n  {hits} of {len(near)} series place their largest break within")
        print("  60 days of the invasion without being told the date.")

    out.to_csv(args.out_dir / "structural_breaks.csv", index=False)
    print(f"\nwrote {args.out_dir/'structural_breaks.csv'}")


if __name__ == "__main__":
    main()
