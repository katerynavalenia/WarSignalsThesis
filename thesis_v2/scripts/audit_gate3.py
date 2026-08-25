"""Apply the Gate-3 pass rule strictly, and test its sign structure — Chapter 8 §8.2.

Two things the automated runner does not do.

**The strict rule.** ``run_gate3.py`` prints a verdict from a simplified
condition. The pre-registration is stricter: arm 1 requires the Russia-window
survivor to be a Bloomberg target or ITA, and arm 2 requires survivors in two
independent episode windows *with the same sign*. Applied strictly, both arms
fail where the runner's simplified logic can print PASS. The document governs;
this script is the reconciliation.

**The out-of-sample sign test.** The surviving weekly cells showed a coherent
structure — a shift toward anticipation raising defence returns and a shift
toward realization lowering them, which reads as buy-the-rumour-sell-the-fact in
Ukrainian media. Four signs were fixed from the 2021–2026 cells and tested on
2017–19, which was not ingested when they were written down. It does not
replicate: 8 of 12, indistinguishable from coin flips.

    cd thesis_v2 && python scripts/audit_gate3.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_gate3 import ECO, LOCAL, MIN_OBS_PER_PARAM, WINDOWS, load, zscore  # noqa: E402

OUT_DIR = Path("outputs/tables")
TARGETS = {"r_bshieldt": "sxxp", "r_waerlst": "spx", "r_ita": "spx",
           "eu_defence": "sxxp", "us_defence": "spx"}

#: Fixed from the 2021-2026 weekly cells, before 2017-19 was ingested.
PREDICTED_SIGNS = {"act_UA": -1, "thr_UA": +1, "act_RU_STATE": -1,
                   "act_RU_INDEP": +1}
HELD_OUT = ("2017-04-23", "2019-10-21")

#: Arm 1 of the pre-registered rule accepts only these as Russia-window
#: survivors. A free basket does not qualify.
ARM1_TARGETS = ("r_bshieldt", "r_waerlst", "r_ita")


def model(wide, spine, target, bench, window, freq="W", lag=1):
    d = wide.join(spine, how="inner")
    if window:
        d = d.loc[window[0]: window[1]]
    cols = [f"{p}_{e}" for e in ECO for p in ("act", "thr") if f"{p}_{e}" in d]
    if freq == "W":
        agg = {c: "mean" for c in cols} | {target: "sum", bench: "sum",
                                           "lvix": "last"}
        d = d[list(agg)].resample("W-FRI").agg(agg)
    X = pd.DataFrame(index=d.index)
    for c in cols:
        X[c] = zscore(d[c].diff().shift(lag))
    X["mkt"] = d[bench]
    X["lvix"] = zscore(d["lvix"])
    y = d[target]
    keep = X.notna().all(axis=1) & y.notna()
    X, y = X[keep], y[keep]
    if len(y) < max(30, MIN_OBS_PER_PARAM * (X.shape[1] + 1)) * 0.6:
        return None
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC",
                                             cov_kwds={"maxlags": 5})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    grid_path = args.out_dir / "gate3_threat_act.csv"
    if not grid_path.exists():
        raise SystemExit(f"run scripts/run_gate3.py first: {grid_path} missing")
    grid = pd.read_csv(grid_path)
    wide, spine = load()

    print("=== STRICT reading of the pre-registered pass rule ===\n")
    russia = grid[(grid.window == "Russia buildup+invasion") & grid.survives_bh]
    print(f"Arm 1 — BH survivor in the Russia window on a Bloomberg target or ITA")
    print(f"  survivors there: {list(russia.target) or 'none'}")
    arm1 = bool(russia.target.isin(ARM1_TARGETS).any())
    print(f"  qualifying under arm 1: {arm1}  ->  {'PASS' if arm1 else 'FAIL'}")

    episode_windows = ["Russia buildup+invasion", "2017-19 episodes",
                       "2025-26 episodes"]
    surv = grid[grid.survives_bh & grid.window.isin(episode_windows)]
    print(f"\nArm 2 — survivors in >= 2 independent episode windows, same sign")
    print(f"  windows with survivors: {sorted(surv.window.unique())}")

    rows = []
    for _, r in grid[grid.survives_bh].iterrows():
        m = model(wide, spine, r.target, TARGETS[r.target],
                  WINDOWS[r.window], r.freq)
        if m is None:
            continue
        for term in m.params.index:
            if any(term.endswith(e) for e in LOCAL):
                rows.append({"cell": f"{r.window[:14]}/{r.freq}/{r.target}",
                             "term": term, "coef": m.params[term],
                             "p": m.pvalues[term]})
    signs = pd.DataFrame(rows)
    if len(signs):
        piv = signs.pivot_table(index="term", columns="cell", values="coef")
        print("\n  sign agreement across surviving cells:")
        for term, row in piv.iterrows():
            v = row.dropna()
            if len(v) > 1:
                frac = max((v > 0).mean(), (v < 0).mean())
                print(f"    {term:<16} n={len(v)}  same-sign={frac:.2f}  "
                      f"mean={v.mean():+.3f}")

    print("\n\n=== OUT-OF-SAMPLE SIGN TEST ===")
    print(f"Signs fixed on 2021-2026; tested on {HELD_OUT[0]}..{HELD_OUT[1]},")
    print("which was not ingested when they were written down.\n")
    print(f"predicted: {PREDICTED_SIGNS}\n")

    oos_rows, matches, total = [], 0, 0
    for target, bench in (("r_ita", "spx"), ("us_defence", "spx"),
                          ("eu_defence", "sxxp")):
        m = model(wide, spine, target, bench, HELD_OUT)
        if m is None:
            continue
        hit = 0
        rec = {"target": target, "n": int(m.nobs)}
        for term, pred in PREDICTED_SIGNS.items():
            coef = m.params.get(term, np.nan)
            ok = np.sign(coef) == pred
            hit += bool(ok)
            rec[term] = round(float(coef), 4)
            rec[f"{term}_match"] = bool(ok)
        rec["matches"] = f"{hit}/{len(PREDICTED_SIGNS)}"
        matches += hit
        total += len(PREDICTED_SIGNS)
        oos_rows.append(rec)
        print(f"  {target:<12} n={int(m.nobs):>4}  {hit}/{len(PREDICTED_SIGNS)} signs match")

    if total:
        p = stats.binomtest(matches, total, 0.5, alternative="greater").pvalue
        print(f"\n  total: {matches}/{total} sign matches")
        print(f"  binomial vs coin-flip: p = {p:.4f}")
        print(f"  VERDICT: {'replicates' if p < 0.05 else 'DOES NOT replicate'}")

    pd.DataFrame(oos_rows).to_csv(args.out_dir / "gate3_oos_signs.csv", index=False)
    if len(signs):
        signs.to_csv(args.out_dir / "gate3_sign_consistency.csv", index=False)
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
