"""Ingest the daily ecosystem and threat/act series from BigQuery.

This is the expensive half of the pipeline and the only step that costs money or
needs a credential. It was originally run as a series of ad-hoc scripts; this
consolidates them so the corpus can be rebuilt, audited, or extended from the
repository alone.

The ingest is chunked because BigQuery bills for every referenced column across
every scanned partition, so a single query over eleven years exceeds a sensible
per-query ceiling even when the total sits inside the free tier. Chunk
boundaries are therefore a cost control, not a analytical choice, and results
are identical to a single query over the same span.

Total cost of the corpus as committed: roughly 900 GB scanned across all
invocations, inside BigQuery's 1 TB/month free tier.

    # what the committed parquets contain, rebuilt from scratch
    python scripts/ingest_gdelt.py --preset full
    python scripts/ingest_gdelt.py --preset threat-act
    python scripts/ingest_gdelt.py --preset holdout

    # or an arbitrary span
    python scripts/ingest_gdelt.py --start 2015-02-18 --end 2015-12-31

Requires a service-account key with BigQuery Job User. See
``docs/v3/environment_setup.md`` §3.2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.gdelt_bq import (  # noqa: E402
    client,
    daily_ecosystem_sql,
    dry_run_tb,
    run_guarded,
    threat_act_sql,
)

INTERIM = Path("data/interim")
ECOSYSTEM_OUT = INTERIM / "gdelt_ecosystems_daily.parquet"
THREAT_ACT_OUT = INTERIM / "gdelt_threat_act_daily.parquet"
HOLDOUT_OUT = INTERIM / "gdelt_ecosystems_holdout.parquet"

#: Chunks sized to stay under the per-query ceiling. `full` reproduces the
#: descriptive corpus; `holdout` is the Gate-5 sample, kept in a separate file so
#: it cannot be mixed into an in-sample estimate by accident.
PRESETS: dict[str, dict] = {
    "full": {
        "out": ECOSYSTEM_OUT,
        "kind": "ecosystem",
        "chunks": [
            ("2015-02-18", "2015-12-31"), ("2016-01-01", "2016-12-31"),
            ("2017-01-01", "2017-04-22"), ("2017-04-23", "2019-10-21"),
            ("2021-06-01", "2021-09-07"), ("2021-09-08", "2022-06-05"),
            ("2022-06-06", "2022-12-31"), ("2023-01-01", "2023-12-31"),
            ("2025-03-07", "2026-05-20"),
        ],
    },
    "holdout": {
        "out": HOLDOUT_OUT,
        "kind": "ecosystem",
        "chunks": [
            ("2019-10-22", "2020-06-30"), ("2020-07-01", "2021-05-31"),
            ("2024-01-01", "2024-12-31"),
        ],
    },
    "threat-act": {
        "out": THREAT_ACT_OUT,
        "kind": "threat_act",
        "chunks": [
            ("2017-04-23", "2018-02-28"), ("2018-03-01", "2018-12-31"),
            ("2019-01-01", "2019-10-21"), ("2021-09-08", "2022-06-05"),
            ("2025-03-07", "2026-05-20"),
        ],
    },
    # The threat/act split reads GDELT's Themes field, which scans at roughly
    # four times the cost of the Locations field the other queries use (0.88 TB
    # against 0.24 TB across the full archive). It was therefore first collected
    # only for the episode windows, 1,605 days, which left Gate 3 testing on
    # about 40% of the corpus while every other test used all of it. This preset
    # fills the remaining 2,422 days -- about 706 GB -- so the anticipation
    # regressions run on the same 4,027 days as everything else.
    "threat-act-fill": {
        "out": THREAT_ACT_OUT,
        "kind": "threat_act",
        "chunks": [
            ("2015-02-18", "2015-12-31"), ("2016-01-01", "2016-08-31"),
            ("2016-09-01", "2017-04-22"), ("2019-10-22", "2020-08-31"),
            ("2020-09-01", "2021-09-07"), ("2022-06-06", "2023-06-30"),
            ("2023-07-01", "2024-12-31"),
        ],
    },
}

ECOSYSTEM_INTS = ("n_total", "n_conflict")
ECOSYSTEM_FLOATS = ("share", "tone_conflict", "tone_all")
THREAT_ACT_INTS = ("n_conflict", "n_act", "n_threat")
THREAT_ACT_FLOATS = ("act_share", "threat_share")


def _normalise(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Force stable dtypes.

    BigQuery returns ``day`` as the ``db_dtypes`` DATE extension type, which does
    not survive a parquet round-trip — reading it back raises
    ``TypeError: data type 'dbdate' not understood``. Casting here rather than at
    read time keeps every consumer simple.
    """
    out = df.copy()
    out["day"] = pd.to_datetime(out["day"]).astype("datetime64[ns]")
    out["ecosystem"] = out["ecosystem"].astype(str)
    ints, floats = (
        (ECOSYSTEM_INTS, ECOSYSTEM_FLOATS) if kind == "ecosystem"
        else (THREAT_ACT_INTS, THREAT_ACT_FLOATS)
    )
    for c in ints:
        out[c] = out[c].astype("int64")
    for c in floats:
        out[c] = out[c].astype("float64")
    return out


def ingest(chunks: list[tuple[str, str]], kind: str, out_path: Path,
           max_tb: float, dry_run: bool) -> pd.DataFrame | None:
    """Run one preset, merging into whatever the output file already holds."""
    bq = client()
    builder = daily_ecosystem_sql if kind == "ecosystem" else threat_act_sql

    frames = []
    if out_path.exists() and not dry_run:
        have = pd.read_parquet(out_path)
        have["day"] = pd.to_datetime(have["day"]).astype("datetime64[ns]")
        print(f"existing: {len(have)} rows, {have.day.nunique()} days")
        frames.append(have)

    total_tb = 0.0
    for start, end in chunks:
        sql = builder([(start, end)])
        tb = dry_run_tb(bq, sql)
        total_tb += tb
        print(f"\n{start}..{end}: {tb*1000:.1f} GB")
        if dry_run:
            continue
        try:
            df = run_guarded(bq, sql, max_tb=max_tb, label=f"{kind}_{start[:7]}")
        except RuntimeError as exc:
            print(f"  SKIPPED: {exc}")
            continue
        frames.append(_normalise(df, kind))
        print(f"  +{len(df)} rows")

    print(f"\ntotal scanned: {total_tb*1000:.1f} GB "
          f"(~${max(0.0, total_tb - 1.0) * 6.25:.2f} beyond the free tier)")
    if dry_run or not frames:
        return None

    # Existing rows go in first and freshly-queried rows after, so ``keep="last"``
    # is what makes a re-ingest actually re-ingest. With the default ``"first"``
    # the stale row wins every collision and a re-query is a silent no-op that
    # still scans -- and bills for -- the full partition. That is not
    # hypothetical: it is why the threat/act table survived a 454 GB re-run
    # byte-identical after the register was corrected.
    merged = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(["day", "ecosystem"], keep="last")
        .sort_values(["day", "ecosystem"])
        .reset_index(drop=True)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path, index=False)
    print(f"wrote {out_path}: {len(merged)} rows, {merged.day.nunique()} days, "
          f"{merged.day.min().date()} -> {merged.day.max().date()}")
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preset", choices=sorted(PRESETS))
    ap.add_argument("--start", help="ad-hoc span, with --end")
    ap.add_argument("--end")
    ap.add_argument("--kind", choices=("ecosystem", "threat_act"), default="ecosystem")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--max-tb", type=float, default=0.18,
                    help="per-query ceiling; the guard refuses anything larger")
    ap.add_argument("--dry-run", action="store_true",
                    help="price every chunk without running it")
    args = ap.parse_args()

    if args.preset:
        cfg = PRESETS[args.preset]
        ingest(cfg["chunks"], cfg["kind"], args.out or cfg["out"],
               args.max_tb, args.dry_run)
    elif args.start and args.end:
        default = ECOSYSTEM_OUT if args.kind == "ecosystem" else THREAT_ACT_OUT
        ingest([(args.start, args.end)], args.kind, args.out or default,
               args.max_tb, args.dry_run)
    else:
        ap.error("give --preset, or --start and --end")


if __name__ == "__main__":
    main()
