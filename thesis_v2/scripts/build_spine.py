"""Phase 1 — build the macro half of the long-sample spine.

Assembles the regime calendar, the GPR index and the FRED market controls into
one daily table covering 2015-02-18 onward, and writes a coverage report.

The equity half (defence returns, realized volatility, regional benchmarks) is
attached by a later step, because it needs a data source this environment
cannot reach — see ``docs/v3/data_sources.md``. Splitting the two means
the macro side is finished, versioned and testable now instead of waiting.

    cd thesis_v2 && python scripts/build_spine.py
    cd thesis_v2 && python scripts/build_spine.py --start 2015-02-18 --end 2026-06-30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.sources import FRED_SERIES, fetch_fred_panel, fetch_gpr_daily  # noqa: E402
from src.features.calendar import SAMPLE_START, build_calendar  # noqa: E402

OUT_PARQUET = Path("data/interim/spine_macro.parquet")
OUT_REPORT = Path("outputs/tables/spine_coverage.csv")


def build_spine(start: str, end: str) -> pd.DataFrame:
    cal = build_calendar(start, end)

    gpr = fetch_gpr_daily()
    fred = fetch_fred_panel(start=start)

    spine = cal.merge(gpr, on="date", how="left").merge(fred, on="date", how="left")

    # FRED and GPR are published only on business days. Carry the last value
    # forward across weekends and holidays so a weekend row shows the
    # information an investor actually holds, then flag which rows were filled
    # so no later step mistakes a carried value for a fresh observation.
    carried = ["gpr", "gpr_act", "gpr_threat", *FRED_SERIES.values()]
    present = [c for c in carried if c in spine.columns]
    spine["is_fresh_obs"] = spine[present].notna().any(axis=1)
    spine[present] = spine[present].ffill()
    return spine


def coverage_report(spine: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in spine.columns:
        if col in ("date", "regime"):
            continue
        s = spine[col]
        obs = s.notna()
        rows.append(
            {
                "column": col,
                "n_non_null": int(obs.sum()),
                "pct_covered": round(100 * obs.mean(), 2),
                "first_date": spine.loc[obs, "date"].min() if obs.any() else pd.NaT,
                "last_date": spine.loc[obs, "date"].max() if obs.any() else pd.NaT,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=str(SAMPLE_START.date()))
    ap.add_argument("--end", default="2026-06-30")
    args = ap.parse_args()

    spine = build_spine(args.start, args.end)
    report = coverage_report(spine)

    for p in (OUT_PARQUET, OUT_REPORT):
        p.parent.mkdir(parents=True, exist_ok=True)
    spine.to_parquet(OUT_PARQUET, index=False)
    report.to_csv(OUT_REPORT, index=False)

    print(f"spine: {len(spine):,} calendar days, {spine.shape[1]} columns")
    print(f"       {spine['date'].min().date()} -> {spine['date'].max().date()}")
    print("\nregime composition (calendar days):")
    print(spine["regime"].value_counts().sort_index().to_string())
    print("\ncoverage:")
    print(report.to_string(index=False))
    print(f"\nwrote {OUT_PARQUET} and {OUT_REPORT}")


if __name__ == "__main__":
    main()
