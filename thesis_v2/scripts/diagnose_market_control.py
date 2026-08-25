"""Why the threat channel was an artefact — Chapter 8 §8.1.

This is the evidence for the largest retraction in the thesis. An earlier result
had threat shocks moving European defence returns at p=0.0001 during the 2021
build-up. It was estimated controlling for the S&P 500, because that was the only
market series then available. With the STOXX 600 the coefficient disappears.

Three things are established here, in order:

1. **The reversal.** For every target, the threat p-value collapses when the
   European benchmark replaces the American one.
2. **The mechanism.** ``corr(SPX, SXXP)`` is low in that window, so SP500 leaves
   most European market variation in the residual, and that residual is
   correlated with the threat shock. The regressor was proxying for an omitted
   control.
3. **What survives, which is better than what was lost.** Regressing the European
   market index *itself* on the two channels shows threat is priced market-wide
   in Europe — just not differentially in defence.

    cd thesis_v2 && python scripts/diagnose_market_control.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.regime_response import channel_race  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

BUILDUP = ("2021-11-01", "2022-02-23")
EPISODE = ("2021-11-22", "2022-03-22")
TARGETS = ("r_bshieldt", "eu_defence", "r_waerlst", "us_defence")


def load() -> pd.DataFrame:
    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    spine["lvix"] = np.log(spine["vix_yf"]).shift(1)
    return spine


def reversal(spine: pd.DataFrame) -> pd.DataFrame:
    """The same regression under three control sets."""
    rows = []
    for label, window in (("buildup", BUILDUP), ("buildup+invasion", EPISODE)):
        sub = spine.loc[window[0]: window[1]]
        for target in TARGETS:
            if target not in sub or sub[target].notna().sum() < 40:
                continue
            for control in ("spx", "sxxp", "none"):
                if control == "none":
                    res = channel_race(sub, target, controls=["lvix"])
                else:
                    res = channel_race(sub.rename(columns={control: "r_mkt"}), target)
                if res:
                    rows.append({"window": label, "target": target,
                                 "control": control, **res})
    return pd.DataFrame(rows)


def mechanism(spine: pd.DataFrame) -> pd.DataFrame:
    """How much European variation SP500 fails to span, and where it goes."""
    rows = []
    for label, window in (("buildup", BUILDUP), ("buildup+invasion", EPISODE)):
        w = spine.loc[window[0]: window[1]]
        beta = w["sxxp"].cov(w["spx"]) / w["spx"].var()
        resid = w["sxxp"] - beta * w["spx"]
        rows.append({
            "window": label,
            "corr_spx_sxxp": w["spx"].corr(w["sxxp"]),
            "sd_sxxp": w["sxxp"].std(),
            "sd_sxxp_orthogonal_to_spx": resid.std(),
            "corr_resid_dthreat": resid.corr(w["gpr_threat"].diff()),
            "corr_resid_dact": resid.corr(w["gpr_act"].diff()),
        })
    return pd.DataFrame(rows)


def survives(spine: pd.DataFrame) -> pd.DataFrame:
    """Is threat priced in the broad market rather than in defence?

    The market index is the dependent variable here, with no market control —
    the question is whether the index itself responds, not whether defence
    responds relative to it.
    """
    rows = []
    windows = {"buildup": BUILDUP, "buildup+invasion": EPISODE,
               "full sample": (None, None)}
    for label, (a, b) in windows.items():
        sub = spine.loc[a:b] if a else spine
        for index in ("sxxp", "spx"):
            res = channel_race(sub.rename(columns={index: "y"}), "y",
                               controls=["lvix"])
            if res:
                rows.append({"window": label, "index": index, **res})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    spine = load()

    rev = reversal(spine)
    print("=== 1. THE REVERSAL: threat p-value by market control ===\n")
    pivot = rev.pivot_table(index=["window", "target"], columns="control",
                            values="p_threat")
    print(pivot.round(4).to_string())
    print("\nSP500 is the control that was available when the result was found.")
    print("STOXX 600 is the one European defence equities actually need.")

    mech = mechanism(spine)
    print("\n\n=== 2. THE MECHANISM: what SP500 fails to span ===\n")
    print(mech.round(3).to_string(index=False))
    print("\nThe part of STOXX orthogonal to SP500 is nearly as large as STOXX")
    print("itself, and it correlates with the threat shock. Controlling only for")
    print("SP500 leaves that variation in the residual, where the threat")
    print("regressor picks it up.")

    surv = survives(spine)
    print("\n\n=== 3. WHAT SURVIVES: the market index as dependent variable ===\n")
    print(surv[["window", "index", "n", "act", "p_act", "threat", "p_threat"]]
          .round(4).to_string(index=False))
    print("\nThreat is priced in the broad European market, not differentially in")
    print("defence. That is a better sentence than the one it replaces.")

    rev.to_csv(args.out_dir / "market_control_reversal.csv", index=False)
    mech.to_csv(args.out_dir / "market_control_mechanism.csv", index=False)
    surv.to_csv(args.out_dir / "market_control_survives.csv", index=False)
    print(f"\nwrote three tables to {args.out_dir}")


if __name__ == "__main__":
    main()
