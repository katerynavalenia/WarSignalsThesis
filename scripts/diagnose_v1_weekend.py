"""Does the approved thesis's weekend grid change its own verdict?

The approved design models on a calendar-day grid, and on that grid the forecast
target is **duplicated across weekends**. Friday's realised return appears again
on Saturday and on Sunday: in `model_matrix.parquet`, 2023-03-03, 03-04 and 03-05
all carry ``target_r_WAERLST_t1 = 0.224885``. Across the matrix that is 388 of
1,358 rows — 29 per cent — and it breaks the independence assumption behind every
out-of-sample statistic the thesis reports.

Whether it *changes the answer* is a separate question from whether it is a flaw,
and it is answerable rather than arguable. This script runs the identical
evaluation twice on **v1's own matrix, with v1's own features and targets**,
changing one thing: the second run keeps weekday rows only. Nothing else differs,
so any gap between them is the weekend grid and nothing else.

It deliberately does *not* rebuild v1's design from scratch. An earlier attempt
to reproduce the calendar grid by forward-filling everything produced 48 of 60
specifications surviving correction — an artefact of that reconstruction, in
which lagged returns became identical to the target, and not a property of v1.
Testing v1's matrix directly is the only way to avoid inventing the answer.

    python scripts/diagnose_v1_weekend.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.evaluation import campbell_thompson_r2_oos, clark_west  # noqa: E402

MATRIX = Path("data/interim/attacks/model_matrix.parquet")
OUT_DIR = Path("outputs/tables")
TEST_FRACTION = 0.25

TARGETS = ("target_r_WAERLST_t1", "target_r_BSHIELDT_t1",
           "target_r_WAERLST_t5", "target_r_BSHIELDT_t5")


def blocks(m: pd.DataFrame) -> dict[str, list[str]]:
    """v1's own information sets, recovered from its column names."""
    phys = [c for c in m.columns
            if any(k in c.lower() for k in ("launch", "destroy", "intercept",
                                            "weapon", "attack"))
            and "n_articles" not in c and "_direct" not in c
            and not c.startswith("target")]
    news = [c for c in m.columns
            if (c.startswith(("n_articles", "n_tone")) or "_direct" in c
                or "narrative_gap" in c)
            and not c.startswith("target")]
    fin = [c for c in m.columns
           if c not in phys and c not in news and c != "date"
           and not c.startswith("target")
           and pd.api.types.is_numeric_dtype(m[c])]
    return {"F": fin, "P": fin + phys, "N": fin + news,
            "PN": fin + phys + news}


def oos_ridge(y: pd.Series, X: pd.DataFrame, test_start: int) -> pd.Series:
    """Expanding-window ridge, imputing missing features on training data only.

    The physical block is missing by construction on days with no published
    attack wave, and v1 leaned on XGBoost's native handling of that. Ridge has
    none, and dropping every row with any missing feature empties the matrix, so
    the median is imputed -- fitted on the training rows at each step, never on
    the row being forecast.
    """
    out = pd.Series(index=y.index, dtype=float)
    yv, Xv = y.to_numpy(float), X.to_numpy(float)
    for t in range(test_start, len(y)):
        ytr, Xtr = yv[:t], Xv[:t]
        ok = np.isfinite(ytr)
        if ok.sum() < 100:
            out.iloc[t] = float(np.nanmean(ytr))
            continue
        pipe = make_pipeline(SimpleImputer(strategy="median"),
                             StandardScaler(), Ridge(alpha=10.0))
        try:
            pipe.fit(Xtr[ok], ytr[ok])
            out.iloc[t] = float(pipe.predict(Xv[t:t + 1])[0])
        except ValueError:
            out.iloc[t] = float(np.nanmean(ytr))
    return out


def oos_mean(y: pd.Series, test_start: int) -> pd.Series:
    out = pd.Series(index=y.index, dtype=float)
    yv = y.to_numpy(float)
    for t in range(test_start, len(y)):
        out.iloc[t] = float(np.nanmean(yv[:t]))
    return out


def run(m: pd.DataFrame, label: str, sets: dict[str, list[str]]) -> list[dict]:
    rows = []
    for tgt in TARGETS:
        if tgt not in m:
            continue
        for name, cols in sets.items():
            use = [c for c in cols if c in m.columns]
            frame = m[[tgt] + use].dropna(subset=[tgt])
            keep = [c for c in use if frame[c].notna().mean() >= 0.5]
            frame = frame[[tgt] + keep]
            use = keep
            if len(frame) < 300 or not use:
                continue
            y, X = frame[tgt], frame[use]
            ts = int(len(y) * (1 - TEST_FRACTION))
            bench, fc = oos_mean(y, ts), oos_ridge(y, X, ts)
            ok = pd.concat([y, bench, fc], axis=1).dropna()
            if len(ok) < 50:
                continue
            a, b, c = ok.iloc[:, 0], ok.iloc[:, 1], ok.iloc[:, 2]
            cw = clark_west(a, b, c)
            rows.append({
                "grid": label, "target": tgt, "info_set": name,
                "n_rows": len(frame), "n_test": len(ok),
                "r2_oos": float(campbell_thompson_r2_oos(a, c, b)),
                "cw_stat": float(cw.statistic), "cw_p": float(cw.pvalue),
            })
            print(f"  {label:16s} {tgt:24s} {name:3s} done", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    m = pd.read_parquet(MATRIX)
    m["date"] = pd.to_datetime(m["date"])
    sets = blocks(m)
    print(f"v1 matrix: {len(m)} rows, "
          f"{m.date.min().date()} -> {m.date.max().date()}")
    for k, v in sets.items():
        print(f"  {k:3s} {len(v):3d} features")

    dup = m.groupby(m["target_r_WAERLST_t1"].round(10)).size()
    print(f"\n  duplicated target values: "
          f"{int((dup > 1).sum())} distinct values appear more than once")
    wknd = m[m.date.dt.dayofweek >= 5]
    print(f"  weekend rows: {len(wknd)} of {len(m)} "
          f"({100*len(wknd)/len(m):.0f}%)")

    rows = run(m, "as published", sets)
    rows += run(m[m.date.dt.dayofweek < 5].reset_index(drop=True),
                "weekdays only", sets)

    out = pd.DataFrame(rows)
    out.to_csv(args.out_dir / "v1_weekend_diagnostic.csv", index=False)

    print("\n=== the same evaluation, with and without the weekend rows ===\n")
    piv = out.pivot_table(index=["target", "info_set"], columns="grid",
                          values="r2_oos").round(4)
    print(piv.to_string())

    print("\n=== how many specifications beat the historical mean? ===")
    for g, sub in out.groupby("grid"):
        print(f"  {g:16s} positive R2_OS {int((sub.r2_oos > 0).sum()):2d}/{len(sub):2d}"
              f"   Clark-West p<0.05 {int((sub.cw_p < 0.05).sum()):2d}/{len(sub):2d}")

    print("\n=== which information set wins, per target ===")
    best = (out.sort_values("r2_oos", ascending=False)
              .groupby(["grid", "target"], as_index=False).first())
    print(best[["grid", "target", "info_set", "r2_oos", "cw_p"]]
          .round(4).to_string(index=False))
    print(f"\nwrote {args.out_dir/'v1_weekend_diagnostic.csv'}")


if __name__ == "__main__":
    main()
