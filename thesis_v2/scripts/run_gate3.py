"""Gate 3 — does the threat/act structure of local media add over Western media?

Executes the test fixed in ``docs/v3/gate3_preregistration.md``. Nothing here
deviates from that document: the theme mapping, the grid, the one-day news lag,
the joint-F statistic, the Benjamini-Hochberg correction and the pass rule were
all written down before this script produced a number.

Gate 2 asked whether local ecosystems differ in *how much* they cover the
conflict and *how negatively*. This asks whether they differ in *what kind* of
coverage — anticipation versus realization — which is the sharper question and
the last specification under which the asset-pricing headline can survive.

    cd thesis_v2 && python scripts/run_gate3.py
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

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

ECO = ("UA", "RU_STATE", "RU_INDEP", "WEST", "EN_GLOBAL")
LOCAL = ("UA", "RU_STATE", "RU_INDEP")
WESTERN = ("WEST", "EN_GLOBAL")

TARGETS = {"r_bshieldt": "sxxp", "r_waerlst": "spx", "r_ita": "spx",
           "eu_defence": "sxxp", "us_defence": "spx"}
WINDOWS = {"Russia buildup+invasion": ("2021-11-22", "2022-03-22"),
           "all ingested days": None,
           "2017-19 episodes": ("2017-04-23", "2019-10-21"),
           "2025-26 episodes": ("2025-03-07", "2026-05-20")}

NEWS_LAG = 1  # pre-registered primary: GDELT UTC days vs ~16:30 UTC European close
MIN_OBS_PER_PARAM = 4


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    ta = pd.read_parquet(INTERIM / "gdelt_threat_act_daily.parquet")
    ta["day"] = pd.to_datetime(ta["day"]).astype("datetime64[ns]")
    wide = pd.concat(
        [
            ta.pivot(index="day", columns="ecosystem", values="act_share").add_prefix("act_"),
            ta.pivot(index="day", columns="ecosystem", values="threat_share").add_prefix("thr_"),
        ],
        axis=1,
    ).sort_index()
    wide.index.name = "date"

    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    spine["lvix"] = np.log(spine["vix_yf"]).shift(1)
    return wide, spine


def fit(wide, spine, target, bench, window, freq, news_lag):
    d = wide.join(spine, how="inner")
    if window:
        d = d.loc[window[0]: window[1]]
    if target not in d or d[target].notna().sum() < 40:
        return None

    cols = [f"{p}_{e}" for e in ECO for p in ("act", "thr") if f"{p}_{e}" in d]
    if freq == "W":
        agg = {c: "mean" for c in cols} | {target: "sum", bench: "sum", "lvix": "last"}
        d = d[list(agg)].resample("W-FRI").agg(agg)

    X = pd.DataFrame(index=d.index)
    for c in cols:
        X[c] = zscore(d[c].diff().shift(news_lag))
    X["mkt"] = d[bench]
    X["lvix"] = zscore(d["lvix"])

    y = d[target]
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < max(40, MIN_OBS_PER_PARAM * (X.shape[1] + 1)):
        return None

    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    loc = [c for c in X.columns if any(c.endswith(e) for e in LOCAL)]
    wst = [c for c in X.columns if any(c.endswith(e) for e in WESTERN)]
    p_local = float(np.squeeze(m.f_test(" = 0, ".join(loc) + " = 0").pvalue))
    p_west = float(np.squeeze(m.f_test(" = 0, ".join(wst) + " = 0").pvalue))
    if not np.isfinite(p_local):
        return None
    return {"freq": freq, "target": target, "n": int(m.nobs), "k": int(X.shape[1]) + 1,
            "r2": float(m.rsquared), "p_local": p_local, "p_west": p_west}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    wide, spine = load()
    print(f"threat/act indices: {wide.index.min().date()} -> {wide.index.max().date()}, "
          f"{len(wide)} days")

    for lag, tag in ((NEWS_LAG, "PRIMARY (news lagged 1 day)"),
                     (0, "SECONDARY (same-day)")):
        rows = []
        for freq in ("D", "W"):
            for label, w in WINDOWS.items():
                for tgt, bench in TARGETS.items():
                    r = fit(wide, spine, tgt, bench, w, freq, lag)
                    if r:
                        rows.append({"window": label, **r})
        g = pd.DataFrame(rows).sort_values("p_local").reset_index(drop=True)
        rej, padj, _, _ = multipletests(g["p_local"], alpha=0.05, method="fdr_bh")
        g["p_bh"], g["survives_bh"] = padj, rej

        print(f"\n\n===== GATE 3 — {tag} =====")
        print(g.head(12).round(4).to_string(index=False))
        print(f"\n  specifications             : {len(g)}")
        print(f"  nominally significant (5%) : {(g.p_local < 0.05).sum()} "
              f"(expected by chance {0.05*len(g):.1f})")
        print(f"  surviving BH at FDR 5%     : {int(g.survives_bh.sum())}")
        print(f"  positive control: WEST block significant in "
              f"{(g.p_west < 0.05).sum()} of {len(g)} cells "
              f"(min p={g.p_west.min():.4f})")

        russia = g[g.window == "Russia buildup+invasion"]
        print("  Russia window p_local: " + ", ".join(
            f"{t}/{f}={p:.3f}" for t, f, p in
            zip(russia.target, russia.freq, russia.p_local)))

        survivors = g[g.survives_bh]
        in_russia = (survivors.window == "Russia buildup+invasion").any()
        n_windows = survivors.window.nunique()
        verdict = "PASS" if (in_russia or n_windows >= 2) else "FAIL"
        print(f"\n  PRE-REGISTERED VERDICT: {verdict}")
        if lag == NEWS_LAG:
            g.to_csv(args.out_dir / "gate3_threat_act.csv", index=False)


if __name__ == "__main__":
    main()
