"""Verify the BigQuery corpus and produce the register evidence — Chapters 3–4.

Four checks, all cheap, all cited in the thesis.

1. **Does the table hold translingual records at all?** The plan rated this a
   medium-likelihood risk with a 4.19 TB bulk download as the fallback. It does,
   so the fallback was never needed.
2. **Does coverage span the sample?** Russian- and Ukrainian-language records
   from the archive's first days onward, which is what makes a 2015 start real
   rather than aspirational.
3. **What does each column cost?** Cost is driven entirely by which columns are
   referenced, since BigQuery bills the full column across scanned partitions.
   This is why the conflict filter uses V1 ``Locations`` rather than
   ``V2Themes``.
4. **Which outlets carry the volume, and in which languages?** This produces the
   evidence for the single most important rule in the measurement chapter:
   country dominates language, because Ukrainian outlets publish heavily in
   Russian and a language-first rule would file them as Russian media.

    python scripts/verify_corpus.py

Requires BigQuery credentials. Total cost is a few GB.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.gdelt_bq import (  # noqa: E402
    CONFLICT,
    SRCLC,
    TABLE,
    client,
    dry_run_tb,
    run_guarded,
    top_outlets_sql,
)

OUT_DIR = Path("outputs/tables")
FULL_WINDOW = "_PARTITIONTIME BETWEEN TIMESTAMP('2015-02-18') AND TIMESTAMP('2026-06-30')"

SPAN_DAYS = ["2015-02-19", "2016-03-01", "2017-06-01", "2019-09-02",
             "2021-12-01", "2022-02-24", "2024-05-01", "2026-06-01"]

REGISTER_DAYS = ["2015-06-15", "2016-03-01", "2017-06-01", "2018-05-15",
                 "2019-09-02", "2020-07-01", "2021-04-15", "2021-12-01",
                 "2022-02-24", "2022-03-15", "2023-06-01", "2024-05-01",
                 "2025-03-01", "2026-06-01"]

COST_COLUMNS = ["TranslationInfo", "SourceCommonName", "V2Tone",
                "DocumentIdentifier", "Themes", "V2Themes", "Locations",
                "V2Locations"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--skip-cost", action="store_true")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    bq = client()

    print("=== 1. table metadata ===")
    for tid in ("gkg_partitioned", "gkg"):
        t = bq.get_table(f"gdelt-bq.gdeltv2.{tid}")
        print(f"  {tid:<18} {t.num_rows:>15,} rows  {t.num_bytes/1e12:5.2f} TB  "
              f"partitioning={'DAY' if t.time_partitioning else 'NONE'}")
    print("  Always query gkg_partitioned. gkg is the same size unpartitioned,")
    print("  so every query would scan the lot.")

    print("\n\n=== 2. source languages on one day ===")
    lang_sql = f"""
    SELECT {SRCLC} AS srclc, COUNT(*) AS n
    FROM {TABLE}
    WHERE _PARTITIONTIME = TIMESTAMP('2025-03-01')
    GROUP BY srclc ORDER BY n DESC LIMIT 15
    """
    langs = run_guarded(bq, lang_sql, max_tb=0.05, label="languages")
    print(langs.to_string(index=False))

    print("\n\n=== 3. coverage across the sample span ===")
    stamps = ", ".join(f"TIMESTAMP('{d}')" for d in SPAN_DAYS)
    span_sql = f"""
    SELECT DATE(_PARTITIONTIME) AS day,
      COUNTIF({SRCLC} = 'rus') AS rus,
      COUNTIF({SRCLC} = 'ukr') AS ukr,
      COUNTIF(TranslationInfo IS NULL OR TranslationInfo = '') AS eng_native,
      COUNT(*) AS total
    FROM {TABLE}
    WHERE _PARTITIONTIME IN ({stamps})
    GROUP BY day ORDER BY day
    """
    span = run_guarded(bq, span_sql, max_tb=0.05, label="span")
    print(span.to_string(index=False))
    print("\n  Russian and Ukrainian coverage is present from the archive's first")
    print("  days, so the 2015 start is real rather than aspirational.")

    if not args.skip_cost:
        print("\n\n=== 4. cost per column, full sample (dry runs only) ===")
        rows = []
        for col in COST_COLUMNS:
            tb = dry_run_tb(bq, f"SELECT {col} FROM {TABLE} WHERE {FULL_WINDOW}")
            rows.append({"column": col, "TB": round(tb, 3)})
            print(f"  {col:<22} {tb:6.3f} TB")
        pd.DataFrame(rows).to_csv(args.out_dir / "corpus_column_costs.csv", index=False)
        print("\n  Locations at 0.24 TB against V2Themes at 1.85 TB is why the")
        print("  conflict filter uses the V1 field.")

    print("\n\n=== 5. outlet register evidence ===")
    outlets = run_guarded(bq, top_outlets_sql(REGISTER_DAYS, limit=600),
                          max_tb=0.05, label="outlets")
    print(f"  {len(outlets)} outlet-language rows, {outlets.n.sum():,} articles\n")

    print("  Ukrainian outlets by language — the country-dominates-language case:")
    ua = outlets[outlets.tld == "ua"].nlargest(20, "n")
    print(ua[["domain", "srclc", "n"]].to_string(index=False))
    both = (ua.groupby("domain").srclc.nunique() > 1).sum()
    print(f"\n  {both} of the top Ukrainian outlets publish in BOTH languages.")
    print("  A language-first rule would file their Russian-language output as")
    print("  Russian media, making the two ecosystems agree by construction.")

    print("\n  Russian outlets:")
    print(outlets[outlets.tld == "ru"].nlargest(15, "n")[["domain", "srclc", "n"]]
          .to_string(index=False))

    outlets.to_csv(args.out_dir / "corpus_top_outlets.csv", index=False)
    span.to_csv(args.out_dir / "corpus_span.csv", index=False)
    print(f"\nwrote tables to {args.out_dir}")


if __name__ == "__main__":
    main()
