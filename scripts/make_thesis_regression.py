"""Estimate the main specification and report it as a coefficient table.

The gate scripts report joint F-tests, which answer the thesis's question but
never state an effect size: a reader cannot tell from them how large a move in
Ukrainian attention is associated with how large a move in defence returns.
This script estimates the same specification the gates use and reports the
coefficients themselves, with HAC(5) standard errors, in four nested columns:

    (1) controls only          market return and lagged log VIX
    (2) + Western block        the block the thesis finds is priced
    (3) + local block          the full model, news credited to publication day
    (4) full model, lagged     the same model at the only tradeable alignment

Columns (3) and (4) differ in one thing only -- whether the news is credited to
the day it was published or to the next trading day -- which is the contrast the
timing result rests on.

Run from the repository root::

    python scripts/make_thesis_regression.py

Writes ``outputs/tables/thesis_regression.csv``.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs" / "tables"

# Mirrors scripts/run_gates.py exactly: same blocks, same controls, same
# transform, same estimator. Only the reporting differs.
LOCAL = ("UA", "RU_STATE", "RU_INDEP")
WESTERN = ("WEST", "EN_GLOBAL")
TARGET, BENCH = "r_bshieldt", "sxxp"

LABEL = {
    "att_UA": "D.Ukrainian attention",
    "att_RU_STATE": "D.Russian state attention",
    "att_RU_INDEP": "D.Russian indep. attention",
    "att_WEST": "D.Western attention",
    "att_EN_GLOBAL": "D.Native-English attention",
    "tone_UA": "D.Ukrainian tone",
    "tone_RU_STATE": "D.Russian state tone",
    "tone_RU_INDEP": "D.Russian indep. tone",
    "tone_WEST": "D.Western tone",
    "tone_EN_GLOBAL": "D.Native-English tone",
    "mkt": "STOXX 600 return",
    "lvix": "Log VIX (lagged)",
}


def zscore(s: pd.Series) -> pd.Series:
    sd = s.std()
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else s * np.nan


def load() -> pd.DataFrame:
    perception = pd.read_parquet(INTERIM / "perception_indices.parquet").reset_index()
    perception["date"] = pd.to_datetime(perception["date"])
    perception = perception.set_index("date")

    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    spine["lvix"] = np.log(spine["vix_yf"]).shift(1)
    return perception.join(spine, how="inner")


def design(d: pd.DataFrame, blocks: tuple, news_lag: int) -> tuple:
    X = pd.DataFrame(index=d.index)
    for e in blocks:
        X[f"att_{e}"] = zscore(d[f"att_{e}"].diff().shift(news_lag))
        X[f"tone_{e}"] = zscore(d[f"tone_{e}"].diff().shift(news_lag))
    X["mkt"] = d[BENCH]
    X["lvix"] = zscore(d["lvix"])
    y = d[TARGET]
    keep = X.notna().all(axis=1) & y.notna()
    return X[keep], y[keep]


def stars(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def fit(d, blocks, news_lag):
    X, y = design(d, blocks, news_lag)
    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    out = {"n": int(m.nobs), "r2": float(m.rsquared)}
    for c in X.columns:
        out[c] = (m.params[c], m.bse[c], m.pvalues[c])
    for name, blk in (("local", LOCAL), ("west", WESTERN)):
        cols = [c for c in X.columns if any(c.endswith(e) for e in blk)]
        if cols:
            out[f"p_{name}"] = float(
                np.squeeze(m.f_test(" = 0, ".join(cols) + " = 0").pvalue)
            )
    return out


def main() -> None:
    d = load()
    specs = {
        "(1) Controls only": fit(d, (), 1),
        "(2) + Western block": fit(d, WESTERN, 1),
        "(3) + local, same-day": fit(d, WESTERN + LOCAL, 0),
        "(4) + local, lagged 1 day": fit(d, WESTERN + LOCAL, 1),
    }

    rows = []
    for var in list(LABEL) :
        row = {"variable": LABEL[var]}
        for name, r in specs.items():
            if var in r:
                b, se, p = r[var]
                row[name] = f"{b:.3f}{stars(p)} ({se:.3f})"
            else:
                row[name] = ""
        if any(row[k] for k in specs):
            rows.append(row)
    for stat, fmt in (("n", "{:d}"), ("r2", "{:.3f}"),
                      ("p_local", "{:.3f}"), ("p_west", "{:.3f}")):
        rows.append({"variable": stat} |
                    {n: (fmt.format(r[stat]) if stat in r else "")
                     for n, r in specs.items()})

    table = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "thesis_regression.csv"
    table.to_csv(dest, index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 40):
        print(table.to_string(index=False))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
