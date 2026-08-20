"""Attach the equity half of the long-sample spine, 2015–2026.

``build_spine.py`` assembled the macro half (GPR + FRED) and stopped, because a
cloud session cannot reach an equity source. From a residential connection Yahoo
serves every ticker the thesis needs with full history, so this closes the gap
without a vendor key — see ``src/data/equities.py`` for why that is not a
contradiction of ``docs/v3/data_sources.md`` §2.

Two things happen here that the Bloomberg-only work could not do:

1. **Regional benchmarks.** ``^STOXX`` gives European defence the control it
   actually needs. The threat-vs-act preview had to use SP500 for both indices,
   which was its largest caveat.
2. **The pre-registered basket test.** The free baskets are compared against
   WAERLST and BSHIELDT on their 2020–2026 overlap against criteria fixed in
   ``docs/v3/equity_validation.md`` §3 before any comparison was run.

    cd thesis_v2 && python scripts/build_equity_spine.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.bloomberg import add_return_features, load_indices  # noqa: E402
from src.data.equities import (  # noqa: E402
    BENCHMARKS,
    ETFS,
    EU_DEFENCE,
    US_DEFENCE,
    basket_coverage,
    build_basket,
    fetch_many,
)
from src.data.sources import fetch_gpr_daily  # noqa: E402
from src.data.validate_basket import validate_basket, validation_table  # noqa: E402
from src.features.calendar import assign_regime  # noqa: E402

DEFAULT_BLOOMBERG_DIR = Path("../thesis_v1/data/raw/bloomberg")
OUT_PANEL = Path("data/interim/spine_full.parquet")
OUT_DIR = Path("outputs/tables")


def build_equity_panel(start: str, end: str) -> tuple[pd.DataFrame, dict]:
    """Fetch every ticker and reduce to daily return series plus benchmarks."""
    print("fetching equities from Yahoo ...")
    us = fetch_many(US_DEFENCE, start=start, end=end)
    eu = fetch_many(EU_DEFENCE, start=start, end=end)
    etf = fetch_many(ETFS, start=start, end=end)
    bench = fetch_many(list(BENCHMARKS), start=start, end=end)
    print(f"  us={len(us)} eu={len(eu)} etf={len(etf)} bench={len(bench)}")

    cols = {
        "us_defence": build_basket(us),
        "eu_defence": build_basket(eu),
        "n_us": basket_coverage(us),
        "n_eu": basket_coverage(eu),
    }
    for t, f in etf.items():
        s = f.set_index("date")["adjclose"].astype(float)
        cols[f"r_{t.lower()}"] = 100.0 * np.log(s).diff()
    for t, name in BENCHMARKS.items():
        s = f_bench = bench[t].set_index("date")["adjclose"].astype(float)
        cols[name] = s if name.startswith("vix") else 100.0 * np.log(f_bench).diff()

    panel = pd.DataFrame(cols).sort_index()
    panel.index.name = "date"
    return panel.reset_index(), {"us": us, "eu": eu, "etf": etf}


def run_validation(panel: pd.DataFrame, bloomberg_dir: Path) -> pd.DataFrame:
    """The pre-registered free-basket-vs-Bloomberg comparison."""
    bbg = add_return_features(load_indices(bloomberg_dir)).set_index("date")
    p = panel.set_index("date")

    pairs = [
        ("us_defence vs WAERLST", p["us_defence"], bbg["r_waerlst"]),
        ("eu_defence vs BSHIELDT", p["eu_defence"], bbg["r_bshieldt"]),
        ("ITA etf vs WAERLST", p["r_ita"], bbg["r_waerlst"]),
        ("XAR etf vs WAERLST", p["r_xar"], bbg["r_waerlst"]),
        ("PPA etf vs WAERLST", p["r_ppa"], bbg["r_waerlst"]),
    ]
    results = []
    for name, cand, ref in pairs:
        try:
            results.append(validate_basket(cand.dropna(), ref.dropna(), name=name))
        except ValueError as exc:
            print(f"  SKIP {name}: {exc}")
    return validation_table(results)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2015-02-18")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--bloomberg-dir", type=Path, default=DEFAULT_BLOOMBERG_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    equity, _ = build_equity_panel("2014-12-01", args.end)

    gpr = fetch_gpr_daily()
    panel = equity.merge(gpr, on="date", how="left")
    panel = panel[(panel["date"] >= args.start) & (panel["date"] <= args.end)].copy()
    for c in ("gpr", "gpr_act", "gpr_threat"):
        panel[c] = panel[c].ffill(limit=4)
    panel["regime"] = assign_regime(panel["date"])

    # Bloomberg where it exists, so downstream work can use it as the referee.
    bbg = add_return_features(load_indices(args.bloomberg_dir))
    panel = panel.merge(
        bbg[["date", "r_waerlst", "r_bshieldt", "vol_waerlst", "vol_bshieldt"]],
        on="date",
        how="left",
    )

    panel = panel.dropna(subset=["us_defence", "eu_defence", "gpr_act"])
    print(
        f"\npanel: {panel['date'].min().date()} -> {panel['date'].max().date()}, "
        f"n={len(panel)} trading days"
    )
    print(panel.groupby("regime", observed=True).size().to_string())

    print("\n=== pre-registered basket validation (2020-2026 overlap) ===")
    table = run_validation(panel, args.bloomberg_dir)
    print(table.to_string(index=False))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    OUT_PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PANEL, index=False)
    table.to_csv(args.out_dir / "basket_validation.csv", index=False)
    print(f"\nwrote {OUT_PANEL} and {args.out_dir/'basket_validation.csv'}")


if __name__ == "__main__":
    main()
