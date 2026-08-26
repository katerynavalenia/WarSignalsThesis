"""The approved thesis's horse race, restored — physical attacks versus news.

The approved design asks whether *physical Russian air-attack intensity* and
*multilingual news narratives* add out-of-sample predictive information for
defence-equity returns beyond financial controls. It answers by racing five
nested information sets:

    F    financial controls only
    P    F + physical air-attack variables
    N    F + news attention and tone
    PN   F + both
    PNG  PN + narrative gaps across source groups

Three things about this restoration differ from the version the supervisor read,
and all three are deliberate.

**The news layer is the rebuilt one.** v1 classified sources by the country an
article *mentioned*, drawing all three national series from one English-language
population — the measurement error the whole v3 rebuild exists to correct. The N
and G blocks here come from the publisher-classified ecosystems of §4.3. Racing
the physical layer against a broken news layer would not answer the question.

**The sample is trading days.** v1 modelled on a calendar-day grid on which the
forecast target is duplicated across weekends — Friday's realised return appears
again on Saturday and on Sunday, so 388 of its 1,358 rows carry a repeated label.
That breaks the independence every evaluation statistic here assumes. Whether it
changes v1's verdict is a separate question, tested directly on v1's own matrix
by ``scripts/diagnose_v1_weekend.py`` rather than guessed at here.

**The invasion window is excluded from every set, not just P.** Physical data
does not exist for 24 Feb – 28 Sep 2022 (see :mod:`src.data.attacks`). Dropping
those rows only from P-containing sets would leave the sets racing on different
samples, which is not a race. They are dropped from all of them.

Two samples are reported. ``full`` uses 2015–2026 with the pre-war period carried
as substantive zeros; ``measured`` restricts to 29 Sep 2022 onward, matching the
approved thesis's own coverage. Comparing them shows directly what the zero-fill
buys.

    python scripts/run_horse_race.py
    python scripts/run_horse_race.py --sample measured
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.attacks import UAF_REPORTING_START, load_attack_panel  # noqa: E402
from src.models.evaluation import campbell_thompson_r2_oos, clark_west  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")

TARGETS = ("r_waerlst", "r_bshieldt", "r_ita")
HORIZONS = (1, 5)

#: Held-out fraction, matching the approved design's "last quarter".
TEST_FRACTION = 0.25

#: XGBoost is refit every this many trading days rather than daily. Daily
#: refitting changes nothing material and multiplies runtime by twenty.
REFIT_EVERY = 21

#: Identical for every information set. The approved thesis's conservatism came
#: partly from not tuning per set, and a race in which one horse got tuning is
#: not a race.
XGB_PARAMS = dict(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
    n_jobs=4, random_state=0, verbosity=0,
)


def build_panel() -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Assemble the modelling panel and the column list of each information set."""
    spine = pd.read_parquet(INTERIM / "spine_full.parquet")
    macro = pd.read_parquet(INTERIM / "spine_macro.parquet")
    idx = pd.read_parquet(INTERIM / "perception_indices.parquet")

    d = spine.merge(
        macro[["date", "brent", "usd_eur", "ust10y", "usd_broad",
               "regime_pre_war", "regime_buildup", "regime_invasion",
               "regime_attrition"]],
        on="date", how="left",
    )
    d = d.merge(idx.reset_index().rename(columns={"index": "date"}),
                on="date", how="left")
    d = d.merge(load_attack_panel(spine["date"]), on="date", how="left")
    d = d.sort_values("date").reset_index(drop=True)

    # --- financial controls -------------------------------------------------
    fin = []
    for c in ("r_waerlst", "r_bshieldt", "r_ita", "spx", "sxxp"):
        d[f"{c}_lag1"] = d[c].shift(1)
        d[f"{c}_lag5"] = d[c].shift(5)
        fin += [f"{c}_lag1", f"{c}_lag5"]
    for c in ("vix_yf", "brent", "usd_eur", "ust10y", "usd_broad",
              "vol_waerlst", "vol_bshieldt"):
        d[f"{c}_lag1"] = d[c].shift(1)
        fin.append(f"{c}_lag1")
    fin += ["regime_pre_war", "regime_buildup", "regime_invasion",
            "regime_attrition"]

    # --- news: the rebuilt ecosystems ---------------------------------------
    eco = [c for c in d.columns if c.startswith(("att_", "tone_"))]
    news = []
    for c in eco:
        d[f"{c}_d1"] = d[c].diff().shift(1)
        news.append(f"{c}_d1")

    # --- narrative gaps ------------------------------------------------------
    gaps = []
    for a, b, name in (("UA", "WEST", "ua_west"), ("RU_STATE", "WEST", "ru_west"),
                       ("UA", "RU_STATE", "ua_ru"),
                       ("RU_STATE", "RU_INDEP", "state_indep")):
        ca, cb = f"tone_{a}", f"tone_{b}"
        if ca in d and cb in d:
            d[f"gap_{name}_lag1"] = (d[ca] - d[cb]).shift(1)
            gaps.append(f"gap_{name}_lag1")

    # --- physical ------------------------------------------------------------
    phys = [c for c in d.columns
            if c.endswith(("_lag1", "_lag3", "_rolling_lag1"))
            and any(k in c for k in ("launch", "destroy", "intercept",
                                     "weapon", "attack"))
            and not c.startswith(("att_", "tone_", "gap_"))]

    sets = {
        "F": fin,
        "P": fin + phys,
        "N": fin + news,
        "PN": fin + phys + news,
        "PNG": fin + phys + news + gaps,
    }
    return d, sets


def expanding_oos(
    y: pd.Series, X: pd.DataFrame, model: str, test_start: int
) -> pd.Series:
    """One-step-ahead expanding-window forecasts over the held-out tail.

    Every fit uses only rows strictly before the forecast date, and the features
    are already lagged, so nothing dated on or after the forecast date enters.
    """
    out = pd.Series(index=y.index, dtype=float)
    yv, Xv = y.to_numpy(float), X.to_numpy(float)

    fitted, last_fit = None, -10**9
    for t in range(test_start, len(y)):
        if model == "mean":
            out.iloc[t] = float(np.nanmean(yv[:t]))
            continue
        if t - last_fit >= (REFIT_EVERY if model == "xgb" else 1):
            ytr, Xtr = yv[:t], Xv[:t]
            ok = np.isfinite(ytr) & np.isfinite(Xtr).all(axis=1)
            if ok.sum() < 100:
                out.iloc[t] = float(np.nanmean(ytr))
                continue
            if model == "ridge":
                sc = StandardScaler().fit(Xtr[ok])
                m = Ridge(alpha=10.0).fit(sc.transform(Xtr[ok]), ytr[ok])
                fitted = (sc, m)
            else:
                fitted = XGBRegressor(**XGB_PARAMS).fit(Xtr[ok], ytr[ok])
            last_fit = t
        if fitted is None or not np.isfinite(Xv[t]).all():
            out.iloc[t] = float(np.nanmean(yv[:t]))
            continue
        if model == "ridge":
            sc, m = fitted
            out.iloc[t] = float(m.predict(sc.transform(Xv[t:t + 1]))[0])
        else:
            out.iloc[t] = float(fitted.predict(Xv[t:t + 1])[0])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", choices=("full", "measured", "both"),
                    default="both")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    panel, sets = build_panel()
    print(f"panel: {len(panel)} rows, {panel.date.min().date()} -> "
          f"{panel.date.max().date()}")
    for k, v in sets.items():
        print(f"  {k:4s} {len(v):3d} features")

    # The invasion window leaves every set, not just the physical ones, so the
    # sets race on one sample. This is enforced, not assumed.
    before = len(panel)
    panel = panel[~panel["attack_unobserved"].fillna(False).astype(bool)]
    print(f"\ndropped {before - len(panel)} rows where physical data does not "
          f"exist (24 Feb - 28 Sep 2022)")
    assert not panel["attack_unobserved"].fillna(False).any()

    samples = (["full", "measured"] if args.sample == "both" else [args.sample])
    rows = []
    for sample in samples:
        d = panel if sample == "full" else panel[panel.date >= UAF_REPORTING_START]
        for tgt in TARGETS:
            for h in HORIZONS:
                y = (d[tgt].rolling(h).sum().shift(-h) if h > 1
                     else d[tgt].shift(-1))
                y = y.rename("y")
                for name, cols in sets.items():
                    use = [c for c in cols if c in d.columns]
                    frame = pd.concat([y, d[use]], axis=1).dropna()
                    if len(frame) < 400:
                        continue
                    yy, XX = frame["y"], frame[use]
                    test_start = int(len(yy) * (1 - TEST_FRACTION))
                    bench = expanding_oos(yy, XX, "mean", test_start)
                    for model in ("ridge", "xgb"):
                        fc = expanding_oos(yy, XX, model, test_start)
                        ok = pd.concat([yy, bench, fc], axis=1).dropna()
                        if len(ok) < 50:
                            continue
                        # Series, not arrays: the evaluation helpers align on
                        # the index before testing.
                        a, b, c = ok.iloc[:, 0], ok.iloc[:, 1], ok.iloc[:, 2]
                        r2 = campbell_thompson_r2_oos(a, c, b)
                        # Clark-West, not Diebold-Mariano: every set nests the
                        # one before it (F subset P subset PN subset PNG), and
                        # DM is invalid under nesting. Comparing nested sets on
                        # raw MAE -- as the approved thesis does -- is biased
                        # toward the smaller model, so both are reported.
                        cw = clark_west(a, b, c, horizon=h)
                        rows.append({
                            "sample": sample, "target": tgt, "horizon": h,
                            "info_set": name, "model": model,
                            "n_features": len(use), "n_train": test_start,
                            "n_test": len(ok),
                            "mae": float(np.mean(np.abs(a - c))),
                            "mae_bench": float(np.mean(np.abs(a - b))),
                            "r2_oos": float(r2),
                            "cw_stat": float(cw.statistic),
                            "cw_p": float(cw.pvalue),
                        })
                    print(f"  {sample:8s} {tgt:11s} h={h} {name:4s} done",
                          flush=True)

    out = pd.DataFrame(rows)
    out["mae_gain_pct"] = 100 * (out.mae_bench - out.mae) / out.mae_bench
    rej, padj, _, _ = multipletests(out.cw_p, alpha=0.05, method="fdr_bh")
    out["cw_p_bh"], out["survives_bh"] = padj, rej

    out.to_csv(args.out_dir / "horse_race.csv", index=False)

    print("\n=== best information set per cell, by out-of-sample R2 ===\n")
    best = (out.sort_values("r2_oos", ascending=False)
              .groupby(["sample", "target", "horizon"], as_index=False).first())
    print(best[["sample", "target", "horizon", "info_set", "model", "r2_oos",
                "mae_gain_pct", "cw_p"]].round(4).to_string(index=False))

    print("\n=== how often does each set win its cell? ===")
    print(best.groupby(["sample", "info_set"]).size().to_string())

    print(f"\n  specifications            : {len(out)}")
    print(f"  positive R2_OS            : {int((out.r2_oos > 0).sum())}")
    print(f"  Clark-West p<0.05 nominal : {int((out.cw_p < 0.05).sum())}")
    print(f"  surviving BH at FDR 5%    : {int(out.survives_bh.sum())}")
    print("\n  This race was NOT pre-registered. Any positive is exploratory,")
    print("  and Section 8.2 is what happens when that caveat is dropped.")
    print(f"\nwrote {args.out_dir/'horse_race.csv'}")


if __name__ == "__main__":
    main()
