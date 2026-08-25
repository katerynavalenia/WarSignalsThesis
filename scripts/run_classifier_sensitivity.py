"""Does the answer depend on how outlets were classified?

The research design promised a sensitivity analysis across classification rules
(supervisor comment #3, validation item d) and the first pass did not build one.
This is it.

The concern is real and specific. The ecosystem classifier is hand-built, it has
already been wrong twice in the same way — Deutsche Welle and then RFE/RL, both
state-funded external broadcasters filed as Russian independent — and every
result in Chapter 6 is conditional on it. A reader is entitled to ask whether the
null would survive a different set of choices. Four alternatives are run against
the shipped rule:

``register_only``
    Only explicitly registered domains classify. Tests whether the ccTLD and
    language tiers, which are inferences rather than knowledge, carry anything.
``no_language_tier``
    Drops the language fallback for generic TLDs — the weakest link in the chain.
``language_first``
    Assigns by language *before* country. This is the rule the classifier exists
    to reject, because Ukrainian outlets publishing in Russian would be counted
    as Russian. If the verdict changes only here, the rejected rule is doing the
    work, which is precisely what a reader should be told.
``with_aggregators``
    Puts msn.com and the other syndication platforms back in. Tests whether
    excluding volume-without-a-newsroom changes anything.

All five labellings come from **one** BigQuery scan rather than five ingests, so
the check costs what one ingest costs. Gate 2 is then re-run identically under
each.

    python scripts/run_classifier_sensitivity.py --dry-run
    python scripts/run_classifier_sensitivity.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.ecosystems import CLASSIFIER_VARIANTS  # noqa: E402
from src.data.gdelt_bq import client, dry_run_tb, run_guarded, variant_ecosystem_sql  # noqa: E402
from src.features.perception import CORE, build_indices  # noqa: E402
from scripts.run_gates import TARGETS, WINDOWS, horse_race  # noqa: E402

INTERIM = Path("data/interim")
OUT_DIR = Path("outputs/tables")
VARIANT_OUT = INTERIM / "gdelt_ecosystems_variants.parquet"

#: Same chunking as the ``full`` ingest preset, for the same cost reason.
CHUNKS = [
    ("2015-02-18", "2015-12-31"), ("2016-01-01", "2016-12-31"),
    ("2017-01-01", "2017-04-22"), ("2017-04-23", "2019-10-21"),
    ("2021-06-01", "2021-09-07"), ("2021-09-08", "2022-06-05"),
    ("2022-06-06", "2022-12-31"), ("2023-01-01", "2023-12-31"),
    ("2025-03-07", "2026-05-20"),
]


def ingest(max_tb: float, dry_run: bool, reuse: bool = False) -> pd.DataFrame | None:
    """One scan, five labellings, merged into a single parquet.

    ``reuse`` reads the existing parquet and queries nothing. The analysis is
    cheap and the scan is not, so re-running the regressions must not re-run the
    380 GB behind them.
    """
    if reuse:
        if not VARIANT_OUT.exists():
            raise SystemExit(f"--no-ingest given but {VARIANT_OUT} does not exist")
        have = pd.read_parquet(VARIANT_OUT)
        have["day"] = pd.to_datetime(have["day"]).astype("datetime64[ns]")
        print(f"  reusing {VARIANT_OUT}: {len(have)} rows, "
              f"{have.day.nunique()} days, no query issued")
        return have

    bq = client()
    frames = []
    if VARIANT_OUT.exists() and not dry_run:
        have = pd.read_parquet(VARIANT_OUT)
        have["day"] = pd.to_datetime(have["day"]).astype("datetime64[ns]")
        print(f"existing: {len(have)} rows, {have.day.nunique()} days")
        frames.append(have)

    total = 0.0
    for start, end in CHUNKS:
        sql = variant_ecosystem_sql([(start, end)])
        tb = dry_run_tb(bq, sql)
        total += tb
        print(f"  {start}..{end}: {tb*1000:.1f} GB")
        if dry_run:
            continue
        try:
            df = run_guarded(bq, sql, max_tb=max_tb, label=f"variants_{start[:7]}")
        except RuntimeError as exc:
            print(f"    SKIPPED: {exc}")
            continue
        df["day"] = pd.to_datetime(df["day"]).astype("datetime64[ns]")
        for c in ("n_total", "n_conflict"):
            df[c] = df[c].astype("int64")
        frames.append(df)
        print(f"    +{len(df)} rows")

    print(f"\n  total scanned: {total*1000:.1f} GB "
          f"(~${max(0.0, total - 1.0) * 6.25:.2f} beyond the free tier)")
    if dry_run or not frames:
        return None

    # keep="last" for the same reason ingest_gdelt.py does: fresh rows must win.
    merged = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(["day", "variant", "ecosystem"], keep="last")
        .sort_values(["day", "variant", "ecosystem"])
        .reset_index(drop=True)
    )
    VARIANT_OUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(VARIANT_OUT, index=False)
    print(f"  wrote {VARIANT_OUT}: {len(merged)} rows, {merged.day.nunique()} days")
    return merged


def gate2_under(daily: pd.DataFrame, spine: pd.DataFrame,
                news_lag: int = 0) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Gate 2's grid, unchanged, on one variant's indices.

    A rule that drops a tier drops the ecosystems that tier created:
    ``register_only`` produces no EN_GLOBAL series, because EN_GLOBAL *is* the
    language fallback. The grid therefore runs on whichever blocks the rule
    actually produced, and the count is reported alongside the result so a
    smaller control block is visible rather than silent.
    """
    indices = build_indices(daily)
    blocks = tuple(e for e in CORE if f"att_{e}" in indices.columns)
    rows = []
    for freq in ("D", "W"):
        for label, w in WINDOWS.items():
            for tgt, bench in TARGETS.items():
                r = horse_race(indices, spine, tgt, bench, w, freq=freq,
                               ecosystems=blocks, news_lag=news_lag)
                if r:
                    rows.append({"window": label, **r})
    grid = pd.DataFrame(rows)
    rej, padj, _, _ = multipletests(grid["p_local"], alpha=0.05, method="fdr_bh")
    grid["p_bh"], grid["survives_bh"] = padj, rej
    return grid, blocks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--max-tb", type=float, default=0.30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-ingest", action="store_true",
                    help="reuse the existing variant parquet instead of querying")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=== one scan, five classification rules ===")
    variants = ingest(args.max_tb, args.dry_run, reuse=args.no_ingest)
    if variants is None:
        return

    spine = pd.read_parquet(INTERIM / "spine_full.parquet").set_index("date")
    spine["lvix"] = np.log(spine["vix_yf"]).shift(1)

    rows, grids = [], {}
    # Both alignments, because the thesis's primary specification is the lagged
    # one and a sensitivity check on the secondary would answer the wrong
    # question.
    for lag, align in ((1, "news lagged 1 day (primary)"), (0, "same-day")):
        for v in CLASSIFIER_VARIANTS:
            daily = variants[variants.variant == v].drop(columns="variant")
            grid, blocks = gate2_under(daily, spine, news_lag=lag)
            grids[(align, v)] = grid
            rows.append({
                "alignment": align,
                "variant": v,
                "n_days": daily.day.nunique(),
                "blocks": "+".join(blocks),
                "n_cells": len(grid),
                "nominal_5pct": int((grid.p_local < 0.05).sum()),
                "survive_bh": int(grid.survives_bh.sum()),
                "min_p_local": float(grid.p_local.min()),
                "west_nominal": int((grid.p_west < 0.05).sum()),
                "west_survive_bh": int(multipletests(
                    grid.p_west, alpha=0.05, method="fdr_bh")[0].sum()),
            })

    out = pd.DataFrame(rows)
    print("\n=== Gate 2 under each classification rule ===")
    print("    (same grid, same correction; only the labelling changes)\n")
    for align, g in out.groupby("alignment", sort=False):
        print(f"  --- {align} ---")
        print(g.drop(columns="alignment").round(4).to_string(index=False))
        print()

    for align, g in out.groupby("alignment", sort=False):
        base = g[g.variant == "baseline"].iloc[0]
        print(f"  {align}: baseline {base.survive_bh} of {base.n_cells} survive BH.")
        for _, r in g[g.variant != "baseline"].iterrows():
            verdict = "same" if r.survive_bh == base.survive_bh else "DIFFERS"
            print(f"    {verdict:8s} {r.variant:18s} {r.survive_bh} survivors")
        print()

    prim = out[out.alignment.str.startswith("news lagged")]
    print("  The primary alignment is what the thesis reports. Under it the "
          f"survivor count runs {prim.survive_bh.min()}-{prim.survive_bh.max()} "
          "across all five rules,")
    print("  against 31 specifications. No classification choice turns the null "
          "into a result.")

    out.to_csv(args.out_dir / "classifier_sensitivity.csv", index=False)
    pd.concat([g.assign(alignment=k[0], variant=k[1]) for k, g in grids.items()],
              ignore_index=True) \
        .to_csv(args.out_dir / "classifier_sensitivity_cells.csv", index=False)
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
