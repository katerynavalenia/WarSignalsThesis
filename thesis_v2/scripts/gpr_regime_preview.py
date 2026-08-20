"""Phase 1 — what the surviving data already says about threat vs act.

The GDELT rebuild (Phase 2) is the expensive part of the v3 plan, and the plan's
priors about what it will find were set before anything was estimated on a
sample containing the 2021 build-up. This script tests those priors with data
that is available *now*: the two Bloomberg index workbooks (2020-01 → 2026-06,
which already span the build-up and the invasion), plus GPR and FRED, both free.

GPR is not a substitute for the thesis's own perception indices — but it is not
an arbitrary stand-in either. Caldara & Iacoviello build it from US, UK and
Canadian newspapers, so it is a *Western-media* threat/act decomposition, which
makes this a preview of the WEST arm specifically, and the benchmark the rebuilt
indices are validated against (``research_plan_v3.md`` §5.5).

    cd thesis_v2 && python scripts/gpr_regime_preview.py
    cd thesis_v2 && python scripts/gpr_regime_preview.py --bloomberg-dir ...

Findings are written up in ``docs/v3/gpr_regime_preview.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.bloomberg import add_return_features, load_indices  # noqa: E402
from src.data.sources import fetch_fred_series, fetch_gpr_daily  # noqa: E402
from src.features.calendar import assign_regime  # noqa: E402
from src.models.regime_response import (  # noqa: E402
    channel_race,
    interacted_race,
    race_by_regime,
)

DEFAULT_BLOOMBERG_DIR = Path("../thesis_v1/data/raw/bloomberg")
OUT_DIR = Path("outputs/tables")
TARGETS = ("bshieldt", "waerlst")


def build_panel(bloomberg_dir: Path, start: str, end: str) -> pd.DataFrame:
    """Join the defence indices to GPR and the market controls, one row per day.

    Trading days only: the dependent variables are index returns, so a calendar
    spine would contribute nothing but empty weekend rows here.
    """
    px = load_indices(bloomberg_dir)
    panel = add_return_features(px)

    gpr = fetch_gpr_daily()
    # SP500 is the reachable market control. FRED truncates it to a rolling ten
    # years, which covers this 2020-2026 window but will not reach 2015 — the
    # long sample needs a real regional benchmark (docs/v3/data_sources.md).
    vix = fetch_fred_series("VIXCLS", start=start).rename("vix")
    spx = fetch_fred_series("SP500", start=start).rename("spx")

    panel = (
        panel.merge(gpr, on="date", how="left")
        .merge(vix.reset_index(), on="date", how="left")
        .merge(spx.reset_index(), on="date", how="left")
    )
    panel = panel[(panel["date"] >= start) & (panel["date"] <= end)].copy()

    for col in ("gpr", "gpr_act", "gpr_threat", "vix", "spx"):
        panel[col] = panel[col].ffill(limit=4)

    panel["r_mkt"] = 100.0 * np.log(panel["spx"]).diff()
    panel["lvix"] = np.log(panel["vix"]).shift(1)
    panel["regime"] = assign_regime(panel["date"])
    panel = panel.set_index("date")
    return panel.dropna(subset=["r_bshieldt", "r_waerlst", "gpr_act", "gpr_threat"])


def regime_structure(panel: pd.DataFrame) -> pd.DataFrame:
    """Mean GPR by regime, and how separable threat and act are within each.

    The threat-to-act *ratio* is the case for extending the sample; the
    correlations are the case for working in changes — in levels the two
    channels look nearly collinear during attrition, in changes they never do.
    """
    rows = []
    for regime, s in panel.groupby("regime", observed=True):
        rows.append(
            {
                "regime": str(regime),
                "n": len(s),
                "gpr": s["gpr"].mean(),
                "act": s["gpr_act"].mean(),
                "threat": s["gpr_threat"].mean(),
                "threat_act_ratio": s["gpr_threat"].mean() / s["gpr_act"].mean(),
                "corr_levels": s["gpr_act"].corr(s["gpr_threat"]),
                "corr_changes": s["gpr_act"].diff().corr(s["gpr_threat"].diff()),
                "mean_ret_bshieldt": s["r_bshieldt"].mean(),
            }
        )
    return pd.DataFrame(rows)


def levels_vs_changes(panel: pd.DataFrame) -> pd.DataFrame:
    """Show that v2's volatility headline lives or dies on the transform."""
    rows = []
    attrition = panel[panel["regime"] == "attrition"]
    for form, use_changes in (("levels", False), ("changes", True)):
        for label, sub in (("attrition", attrition), ("pooled", panel)):
            for target in TARGETS:
                res = channel_race(sub, f"vol_{target}", use_changes=use_changes)
                if res is not None:
                    rows.append(
                        {"form": form, "sample": label, "target": target, **res}
                    )
    return pd.DataFrame(rows)


def window_sensitivity(panel: pd.DataFrame, starts: list[str]) -> pd.DataFrame:
    """Vary the build-up start date, holding the invasion end fixed.

    The build-up boundary is a judgement call, so the result has to be shown to
    survive moving it rather than asserted at one date.
    """
    rows = []
    for start in starts:
        sub = panel[(panel.index >= start) & (panel.index < "2022-02-24")]
        for target in TARGETS:
            res = channel_race(sub, f"r_{target}")
            if res is not None:
                rows.append({"window_start": start, "target": target, **res})
    return pd.DataFrame(rows)


def placebo(panel: pd.DataFrame) -> pd.DataFrame:
    """The build-up window shifted back one year, when nothing was building up."""
    rows = []
    sub = panel[(panel.index >= "2020-11-01") & (panel.index < "2021-02-24")]
    for target in TARGETS:
        res = channel_race(sub, f"r_{target}")
        if res is not None:
            rows.append({"sample": "placebo 2020-11 -> 2021-02", "target": target, **res})
    return pd.DataFrame(rows)


def predictability(panel: pd.DataFrame) -> pd.DataFrame:
    """Does either channel forecast *tomorrow's* return? (SQ3, in miniature.)

    Not a substitute for the Phase 5 out-of-sample battery — an in-sample
    regression is the friendlier test, so a null here is informative about what
    the harder test will find.
    """
    rows = []
    for target in TARGETS:
        for label, sub in (
            ("attrition", panel[panel["regime"] == "attrition"]),
            ("buildup", panel[panel["regime"] == "buildup"]),
            ("pooled", panel),
        ):
            s = sub.copy()
            s[f"lead_{target}"] = s[f"r_{target}"].shift(-1)
            res = channel_race(s, f"lead_{target}", controls=["lvix"])
            if res is not None:
                rows.append({"sample": label, "target": target, **res})
    return pd.DataFrame(rows)


def _show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n=== {title} ===")
    print(frame.round(4).to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bloomberg-dir", type=Path, default=DEFAULT_BLOOMBERG_DIR)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    panel = build_panel(args.bloomberg_dir, args.start, args.end)
    print(
        f"panel: {panel.index.min().date()} -> {panel.index.max().date()}, "
        f"n={len(panel)} trading days"
    )

    outputs = {
        "gpr_regime_structure": regime_structure(panel),
        "gpr_levels_vs_changes": levels_vs_changes(panel),
        "gpr_race_returns_bshieldt": race_by_regime(panel, "r_bshieldt"),
        "gpr_race_returns_waerlst": race_by_regime(panel, "r_waerlst"),
        "gpr_race_vol_bshieldt": race_by_regime(panel, "vol_bshieldt"),
        "gpr_race_vol_waerlst": race_by_regime(panel, "vol_waerlst"),
        "gpr_interacted_bshieldt": interacted_race(panel, "r_bshieldt"),
        "gpr_interacted_waerlst": interacted_race(panel, "r_waerlst"),
        "gpr_window_sensitivity": window_sensitivity(
            panel,
            ["2021-08-01", "2021-09-01", "2021-10-01", "2021-11-01", "2021-12-01"],
        ),
        "gpr_placebo": placebo(panel),
        "gpr_predictability": predictability(panel),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        _show(name, frame)
        frame.to_csv(args.out_dir / f"{name}.csv", index=False)
    print(f"\nwrote {len(outputs)} tables to {args.out_dir}")


if __name__ == "__main__":
    main()
