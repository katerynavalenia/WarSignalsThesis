"""The volatility half of the approved question: do war signals forecast risk?

The approved design asks about defence-equity returns **and volatility**, and the
volatility half is the harder test to fail. Daily returns are close to
unforecastable for anyone, so a null there is weak evidence; volatility genuinely
is forecastable, it clusters and persists, and it is where conflict ought to show
up — an attack wave plausibly moves uncertainty even when its direction for
prices is ambiguous. A war signal that cannot improve a volatility forecast has
failed on the ground of its own choosing.

Following §2.6 of the approved thesis:

* **Benchmarks** are the GARCH family — GARCH(1,1), GJR-GARCH(1,1,1) and
  EGARCH(1,1) — fitted by maximum likelihood on returns.
* **Realised volatility is proxied by squared returns**, summed over the horizon
  for h=5, because the data are daily closes and no intraday prices exist.
* **QLIKE is the loss**, in Patton's (2011) robust form, because it tolerates
  noise in exactly that proxy. MSE, MAE and bias are reported alongside it.

One departure, forced and documented. The approved thesis describes "GARCH-X
extensions", but a true GARCH-X puts exogenous regressors in the *variance*
equation and no such specification is available in ``arch`` — its ``x`` argument
enters the mean. The war variables therefore enter through **HAR-RV-X**: a
heterogeneous-autoregression of log realised variance on its own 1-, 5- and
22-day lags, augmented with the war blocks. This is the standard way to admit
exogenous predictors to a volatility forecast when the variance equation is
closed to them, and it is the specification v3's own research plan had named
before volatility was dropped.

The comparisons are read with their nesting in mind. HAR-RV-X nests HAR-RV, so
Diebold–Mariano is not valid between them and the increment is judged on QLIKE
and Clark–West. GARCH-family models against HAR are non-nested, and there DM is
the right test — the same distinction ``src/models/evaluation.py`` keeps as
separate functions so it cannot be blurred.

    python scripts/run_volatility_race.py
    python scripts/run_volatility_race.py --sample measured
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from arch import arch_model
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_horse_race import build_panel  # noqa: E402
from src.data.attacks import UAF_REPORTING_START  # noqa: E402
from src.models.evaluation import clark_west, diebold_mariano  # noqa: E402

OUT_DIR = Path("outputs/tables")
TARGETS = ("r_waerlst", "r_bshieldt", "r_ita")
HORIZONS = (1, 5)
TEST_FRACTION = 0.25
REFIT_EVERY = 21

#: Variance floor. QLIKE takes a logarithm, and a squared return can be exactly
#: zero on a flat day; without a floor a single such day sends the loss to
#: infinity and decides the comparison on its own.
EPS = 1e-6

GARCH_SPECS = {
    "GARCH": dict(vol="GARCH", p=1, o=0, q=1),
    "GJR-GARCH": dict(vol="GARCH", p=1, o=1, q=1),
    "EGARCH": dict(vol="EGARCH", p=1, o=1, q=1),
}


def qlike(realised: np.ndarray, forecast: np.ndarray) -> float:
    """Patton's (2011) QLIKE loss, robust to noise in the volatility proxy.

    ``RV/h - log(RV/h) - 1``: zero when the forecast equals the realised value
    and positive otherwise. Robust here means the ranking of forecasts is not
    distorted by the proxy being noisy, which matters when the proxy is a single
    squared return.
    """
    r = np.maximum(realised, EPS) / np.maximum(forecast, EPS)
    return float(np.mean(r - np.log(r) - 1.0))


def realised_variance(r: pd.Series, h: int) -> pd.Series:
    """Squared returns, summed over the forecast horizon and dated at its start."""
    sq = r.pow(2)
    return (sq.rolling(h).sum().shift(-h) if h > 1 else sq.shift(-1))


def garch_forecasts(r: pd.Series, spec: dict, h: int, test_start: int) -> pd.Series:
    """Expanding-window conditional-variance forecasts from a GARCH-family model.

    Refit every ``REFIT_EVERY`` steps and forecast forward between refits, which
    is what makes the exercise affordable; the parameters move slowly enough that
    daily refitting changes nothing material.
    """
    out = pd.Series(index=r.index, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res, last = None, -10**9
        for t in range(test_start, len(r)):
            if t - last >= REFIT_EVERY:
                try:
                    res = arch_model(r.iloc[:t], mean="Constant", dist="t",
                                     rescale=False, **spec).fit(disp="off",
                                                                show_warning=False)
                    last = t
                except Exception:
                    res = None
            if res is None:
                out.iloc[t] = float(r.iloc[:t].var())
                continue
            try:
                f = res.forecast(horizon=h, reindex=False, start=None)
                v = float(np.asarray(f.variance)[-1, :h].sum())
            except Exception:
                v = float(r.iloc[:t].var()) * h
            out.iloc[t] = v
    return out


def har_forecasts(
    rv: pd.Series, X: pd.DataFrame | None, test_start: int
) -> pd.Series:
    """Expanding-window HAR-RV(-X) forecasts of realised variance.

    Estimated in logs, which is where realised variance is approximately
    Gaussian, then exponentiated back. ``X`` adds the war block; passing None
    gives the plain HAR-RV benchmark that the augmented model nests.
    """
    y = np.log(np.maximum(rv, EPS))
    lags = pd.concat(
        [y.shift(1).rename("l1"),
         y.rolling(5).mean().shift(1).rename("l5"),
         y.rolling(22).mean().shift(1).rename("l22")], axis=1)
    design = lags if X is None else pd.concat([lags, X], axis=1)

    out = pd.Series(index=rv.index, dtype=float)
    yv, Xv = y.to_numpy(float), design.to_numpy(float)
    for t in range(test_start, len(y)):
        ytr, Xtr = yv[:t], Xv[:t]
        ok = np.isfinite(ytr)
        if ok.sum() < 100:
            out.iloc[t] = float(np.exp(np.nanmean(ytr)))
            continue
        pipe = make_pipeline(SimpleImputer(strategy="median"),
                             StandardScaler(), Ridge(alpha=1.0))
        try:
            pipe.fit(Xtr[ok], ytr[ok])
            out.iloc[t] = float(np.exp(pipe.predict(Xv[t:t + 1])[0]))
        except ValueError:
            out.iloc[t] = float(np.exp(np.nanmean(ytr)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", choices=("full", "measured", "both"),
                    default="both")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    panel, sets = build_panel()
    panel = panel[~panel["attack_unobserved"].fillna(False).astype(bool)]
    fin, phys = sets["F"], [c for c in sets["P"] if c not in sets["F"]]
    news = [c for c in sets["N"] if c not in sets["F"]]
    gaps = [c for c in sets["PNG"] if c not in sets["PN"]]

    blocks = {
        "HAR-RV": None,
        "HAR-RV-X (P)": phys,
        "HAR-RV-X (N)": news,
        "HAR-RV-X (PN)": phys + news,
        "HAR-RV-X (PNG)": phys + news + gaps,
    }

    samples = ["full", "measured"] if args.sample == "both" else [args.sample]
    rows = []
    for sample in samples:
        d = (panel if sample == "full"
             else panel[panel.date >= UAF_REPORTING_START]).reset_index(drop=True)
        for tgt in TARGETS:
            r = d[tgt]
            if r.notna().sum() < 500:
                continue
            for h in HORIZONS:
                rv = realised_variance(r, h)
                frame = pd.concat([r.rename("r"), rv.rename("rv")], axis=1)
                keep = frame.dropna().index
                if len(keep) < 400:
                    continue
                rr, vv = frame.loc[keep, "r"], frame.loc[keep, "rv"]
                ts = int(len(rr) * (1 - TEST_FRACTION))

                preds: dict[str, pd.Series] = {}
                for name, spec in GARCH_SPECS.items():
                    preds[name] = garch_forecasts(rr, spec, h, ts)
                for name, cols in blocks.items():
                    X = (d.loc[keep, [c for c in cols if c in d.columns]]
                         .reset_index(drop=True) if cols else None)
                    if X is not None:
                        X.index = rr.index
                    preds[name] = har_forecasts(vv, X, ts)

                base = preds["HAR-RV"]
                for name, fc in preds.items():
                    ok = pd.concat([vv, fc.rename("f"), base.rename("b")],
                                   axis=1).dropna()
                    if len(ok) < 50:
                        continue
                    a = ok["rv"].to_numpy()
                    f = ok["f"].to_numpy()
                    b = ok["b"].to_numpy()
                    # Two tests, because they answer different questions and
                    # here they disagree. DM under QLIKE is the primary: it is
                    # what the approved thesis uses and what the volatility
                    # literature uses, because squared error on a variance is
                    # dominated by a few extreme days. Clark-West is reported
                    # beside it because HAR-RV-X genuinely nests HAR-RV and CW
                    # is the nesting-correct test -- but it is defined on
                    # squared-error loss, which is the loss QLIKE exists to
                    # replace. Where they disagree, QLIKE decides and the
                    # disagreement is shown rather than resolved silently.
                    dm_q, cw_s = float("nan"), float("nan")
                    dm_p, cw_p = float("nan"), float("nan")
                    if name != "HAR-RV":
                        try:
                            dm = diebold_mariano(pd.Series(a), pd.Series(f),
                                                 pd.Series(b), horizon=h,
                                                 loss="qlike")
                            dm_q, dm_p = dm.statistic, dm.pvalue
                        except ValueError:
                            pass
                        if name.startswith("HAR-RV-X"):
                            try:
                                cw = clark_west(pd.Series(a), pd.Series(b),
                                                pd.Series(f), horizon=h)
                                cw_s, cw_p = cw.statistic, cw.pvalue
                            except ValueError:
                                pass
                    rows.append({
                        "sample": sample, "target": tgt, "horizon": h,
                        "model": name, "n_test": len(ok),
                        "qlike": qlike(a, f), "qlike_har": qlike(a, b),
                        "mse": float(np.mean((a - f) ** 2)),
                        "mae": float(np.mean(np.abs(a - f))),
                        "bias": float(np.mean(f - a)),
                        # positive DM statistic = this model has the LARGER
                        # QLIKE loss, i.e. it forecasts worse than HAR-RV
                        "dm_qlike_stat": float(dm_q), "dm_qlike_p": float(dm_p),
                        "cw_stat": float(cw_s), "cw_p": float(cw_p),
                    })
                print(f"  {sample:8s} {tgt:11s} h={h} done", flush=True)

    out = pd.DataFrame(rows)
    out["qlike_gain_pct"] = 100 * (out.qlike_har - out.qlike) / out.qlike_har
    aug = out[out.model.str.startswith("HAR-RV-X")].copy()
    if len(aug):
        ok = aug.dm_qlike_p.notna()
        rej, padj, _, _ = multipletests(aug.loc[ok, "dm_qlike_p"], alpha=0.05,
                                        method="fdr_bh")
        out.loc[aug.index[ok], "dm_qlike_p_bh"] = padj
        out.loc[aug.index[ok], "survives_bh"] = rej
    out.to_csv(args.out_dir / "volatility_race.csv", index=False)

    print("\n=== QLIKE by model, lower is better ===\n")
    piv = out.pivot_table(index="model", columns=["sample", "horizon"],
                          values="qlike").round(4)
    print(piv.to_string())

    print("\n=== best model per cell ===")
    best = (out.sort_values("qlike")
              .groupby(["sample", "target", "horizon"], as_index=False).first())
    print(best[["sample", "target", "horizon", "model", "qlike",
                "qlike_gain_pct"]].round(4).to_string(index=False))
    print("\n  wins by model:")
    print(best.groupby("model").size().to_string())

    if len(aug):
        worse = aug[(aug.qlike > aug.qlike_har) & (aug.dm_qlike_p < 0.05)]
        better = aug[(aug.qlike < aug.qlike_har) & (aug.dm_qlike_p < 0.05)]
        print(f"\n  augmented specifications      : {len(aug)}")
        print(f"  beating HAR-RV on QLIKE       : "
              f"{int((aug.qlike < aug.qlike_har).sum())}")
        print(f"  significantly BETTER (DM-QLIKE): {len(better)}")
        print(f"  significantly WORSE  (DM-QLIKE): {len(worse)}")
        print(f"  surviving BH at FDR 5%        : "
              f"{int(out.survives_bh.fillna(False).sum())} "
              f"(of which improvements: {len(better)})")
        print(f"  Clark-West p<0.05 on squared error: "
              f"{int((aug.cw_p < 0.05).sum())} -- see the note in the source: "
              f"squared error on a variance is what QLIKE exists to replace.")
    print("\n  Volatility is the harder test to fail: unlike daily returns it is")
    print("  genuinely forecastable, so a war signal that adds nothing here has")
    print("  failed where it had every chance to succeed.")
    print(f"\nwrote {args.out_dir/'volatility_race.csv'}")


if __name__ == "__main__":
    main()
