"""Run the Gate-1 validation battery and the Gate-2 horse race, and write tables.

Reads the interim tables produced by ``build_equity_spine.py`` and the BigQuery
ingest, so it needs no network and no credentials — the expensive steps happen
once, and this is re-runnable against their output.

Gate 1 asks whether the rebuilt perception indices measure distinct media
populations. Gate 2 asks the thesis's actual question: do the local-language
ecosystems explain defence-equity returns that Western media do not already
explain? The second question is only meaningful if the first passes.

    python scripts/run_gates.py

Findings are written up in ``docs/v3/gate1_gate2_results.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.perception import CORE, build_indices, validation_report  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

LOCAL = ("UA", "RU_STATE", "RU_INDEP")
WESTERN = ("WEST", "EN_GLOBAL")
TARGETS = {
    "eu_defence": "sxxp",
    "us_defence": "spx",
    "r_ita": "spx",
    "r_bshieldt": "sxxp",
    "r_waerlst": "spx",
}
WINDOWS = {
    "Russia buildup+invasion": ("2021-11-22", "2022-03-22"),
    "all ingested days": None,
    "2017-19 episodes": ("2017-04-23", "2019-10-21"),
    "2025-26 episodes": ("2025-03-07", "2026-05-20"),
}


#: The external-validity check reported in Chapter 4. GPR is a *global* index and
#: these indices are Ukraine-specific, so the test is not "do they correlate"
#: but "do they correlate when GPR is about Ukraine and stop when it is not".
#: Both windows are the ingest chunk boundaries, so the figures are reproducible
#: from the committed data rather than depending on a hand-chosen span.
GPR_WINDOWS = {
    "2021-09 -> 2022-06 (GPR driven by Ukraine)": ("2021-09-08", "2022-06-05"),
    "2017-19 (GPR driven by Korea/Iran)": ("2017-04-23", "2019-10-21"),
}


def gpr_levels_check(indices: pd.DataFrame, gpr: pd.Series) -> pd.DataFrame:
    """Correlation of each ecosystem's attention share with GPR, in levels.

    Written to a table rather than computed by hand, because a validation figure
    quoted in three chapters has to be regenerable when the register changes.
    """
    rows = []
    for label, (a, b) in GPR_WINDOWS.items():
        m = (indices.index >= a) & (indices.index <= b)
        row = {"window": label, "n": int(m.sum())}
        for eco in CORE:
            col = f"att_{eco}"
            if col in indices.columns:
                row[eco] = float(indices.loc[m, col].corr(gpr[m]))
        rows.append(row)
    return pd.DataFrame(rows)


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def horse_race(
    indices: pd.DataFrame,
    spine: pd.DataFrame,
    target: str,
    bench: str,
    window: tuple[str, str] | None,
    freq: str = "D",
    use_tone: bool = True,
    min_obs_per_param: int = 4,
    news_lag: int = 0,
) -> dict | None:
    """Joint test of the local ecosystems conditional on the Western ones.

    The conditioning is the whole point. Tested alone every ecosystem looks
    significant, because they all spike on the same days; the question is
    whether local media carry anything *once Western coverage is accounted for*.
    """
    d = indices.join(spine, how="inner")
    if window:
        d = d.loc[window[0] : window[1]]
    if target not in d or d[target].notna().sum() < 40:
        return None

    if freq == "W":
        agg = {f"att_{e}": "mean" for e in CORE} | {f"tone_{e}": "mean" for e in CORE}
        agg |= {target: "sum", bench: "sum", "lvix": "last"}
        d = d[list(agg)].resample("W-FRI").agg(agg)

    X = pd.DataFrame(index=d.index)
    for e in CORE:
        X[f"att_{e}"] = zscore(d[f"att_{e}"].diff().shift(news_lag))
        if use_tone:
            X[f"tone_{e}"] = zscore(d[f"tone_{e}"].diff().shift(news_lag))
    X["mkt"] = d[bench]
    X["lvix"] = zscore(d["lvix"])

    y = d[target]
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < max(40, min_obs_per_param * (X.shape[1] + 1)):
        return None

    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    loc = [c for c in X.columns if any(c.endswith(e) for e in LOCAL)]
    west = [c for c in X.columns if any(c.endswith(e) for e in WESTERN)]
    p_local = float(np.squeeze(m.f_test(" = 0, ".join(loc) + " = 0").pvalue))
    p_west = float(np.squeeze(m.f_test(" = 0, ".join(west) + " = 0").pvalue))
    if not np.isfinite(p_local):
        return None
    return {
        "freq": freq,
        "target": target,
        "n": int(m.nobs),
        "k": int(X.shape[1]) + 1,
        "r2": float(m.rsquared),
        "p_local": p_local,
        "p_west": p_west,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    daily = pd.read_parquet(INTERIM / "gdelt_ecosystems_daily.parquet")
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    spine["lvix"] = np.log(spine["vix_yf"]).shift(1)

    indices = build_indices(daily)
    indices.to_parquet(INTERIM / "perception_indices.parquet")

    gpr = spine["gpr"].reindex(indices.index).ffill(limit=4)
    table, corr, verdict = validation_report(indices, gpr)

    print("=== GATE 1 ===")
    print(table.round(4).to_string(index=False))
    print("\npairwise correlation of attention changes:")
    print(corr.round(3).to_string())
    print("\nverdict:", {k: v for k, v in verdict.items()})
    table.to_csv(args.out_dir / "gate1_ecosystems.csv", index=False)
    corr.to_csv(args.out_dir / "gate1_collinearity.csv")

    levels = gpr_levels_check(indices, gpr)
    print("\nGPR correlation in levels (the external-validity check):")
    print(levels.round(4).to_string(index=False))
    levels.to_csv(args.out_dir / "gate1_gpr_levels.csv", index=False)

    rows = []
    for freq in ("D", "W"):
        for label, w in WINDOWS.items():
            for tgt, bench in TARGETS.items():
                r = horse_race(indices, spine, tgt, bench, w, freq=freq)
                if r:
                    rows.append({"window": label, **r})

    grid = pd.DataFrame(rows).sort_values("p_local").reset_index(drop=True)
    rej, padj, _, _ = multipletests(grid["p_local"], alpha=0.05, method="fdr_bh")
    grid["p_bh"] = padj
    grid["survives_bh"] = rej

    print("\n\n=== GATE 2: does LOCAL add over WESTERN? ===")
    print(grid.round(4).to_string(index=False))
    print(f"\nspecifications             : {len(grid)}")
    print(
        f"nominally significant (5%) : {(grid.p_local < 0.05).sum()} "
        f"(expected by chance {0.05*len(grid):.1f})"
    )
    print(f"surviving BH at FDR 5%     : {int(grid.survives_bh.sum())}")
    grid.to_csv(args.out_dir / "gate2_horse_race.csv", index=False)
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
