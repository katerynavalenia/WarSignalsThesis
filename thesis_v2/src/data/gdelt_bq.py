"""GDELT 2.0 Translingual GKG via BigQuery.

Verified 2026-08-20 against `gdelt-bq.gdeltv2.gkg_partitioned` (1.83 bn rows,
21.8 TB, day-partitioned): translingual records are present for the whole
archive, so the plan's fallback to a 4.19 TB bulk download is not needed. On a
single day in 2025 the table carries ~9.7k Russian-language and ~3.2k
Ukrainian-language records, against the **7 `.ru` articles per day** in the
GKG 1.0 stream v1 used.

**Always query `gkg_partitioned`, never `gkg`** — the latter is the same 21.8 TB
unpartitioned, so every query scans the lot.

Cost is driven purely by which columns are referenced, since BigQuery bills for
the full column across scanned partitions regardless of the filter. Measured
over the full 2015–2026 window:

    TranslationInfo    0.033 TB      Themes (V1)     0.881 TB
    SourceCommonName   0.027 TB      V2Themes        1.853 TB
    V2Tone             0.175 TB      Locations (V1)  0.242 TB
    DocumentIdentifier 0.180 TB      V2Locations     0.728 TB

So the conflict filter uses **V1 `Locations`** (FIPS country codes, `UP`
Ukraine / `RS` Russia) rather than `V2Themes`, and the publisher comes from
`SourceCommonName` rather than the full URL. That combination is 0.477 TB for
the whole sample — inside the free tier.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

TABLE = "`gdelt-bq.gdeltv2.gkg_partitioned`"

#: FIPS country codes as they appear in V1 Locations.
UKRAINE_FIPS = "UP"
RUSSIA_FIPS = "RS"

DEFAULT_KEY = Path.home() / ".config/gcp/warsignals-bq.json"


def client(project: str = "warsignals-thesis", key_path: Path | None = None):
    """A BigQuery client, authenticating from the service-account key on disk."""
    from google.cloud import bigquery

    key = Path(key_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_KEY))
    if key.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key)
    return bigquery.Client(project=project)


def dry_run_tb(bq, sql: str) -> float:
    """Terabytes a query would scan, without running it."""
    from google.cloud import bigquery

    job = bq.query(
        sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    )
    return job.total_bytes_processed / 1e12


def run_guarded(bq, sql: str, max_tb: float = 0.25, label: str = "query") -> pd.DataFrame:
    """Price a query, refuse it if it is too large, then run it.

    The guard is the point: a mistyped partition filter turns a 40 GB scan into a
    22 TB one, and the daily quota is a blunt backstop that fails *after* the
    money is spent. Nothing in this module runs unpriced.
    """
    tb = dry_run_tb(bq, sql)
    print(f"  [{label}] dry run: {tb*1000:.1f} GB (~${max(0.0, tb-1.0)*6.25:.2f})")
    if tb > max_tb:
        raise RuntimeError(
            f"{label}: would scan {tb:.3f} TB, above the {max_tb} TB ceiling. "
            "Narrow the window or the column list."
        )
    return bq.query(sql).result().to_dataframe()


def partition_filter(start: str, end: str) -> str:
    return (
        f"_PARTITIONTIME BETWEEN TIMESTAMP('{start}') AND TIMESTAMP('{end}')"
    )


#: srclc is carried inside TranslationInfo as e.g. "srclc:rus;srcclmid:...".
SRCLC = r"REGEXP_EXTRACT(TranslationInfo, r'srclc:([a-zA-Z]+)')"

#: The last dot-segment of the domain. Not a country for .com/.org/.net, which
#: is exactly why language and a curated register are needed alongside it.
TLD = r"REGEXP_EXTRACT(SourceCommonName, r'\.([a-z]+)$')"

#: An article counts as conflict-related if it geolocates to Ukraine or Russia.
CONFLICT = (
    f"(Locations LIKE '%#{UKRAINE_FIPS}#%' OR Locations LIKE '%#{RUSSIA_FIPS}#%')"
)


def daily_ecosystem_sql(windows: list[tuple[str, str]]) -> str:
    """Daily per-ecosystem volume, attention share and tone, aggregated server-side.

    Returns one row per (day, ecosystem) carrying:

    ``n_total``
        every article that ecosystem published that day.
    ``n_conflict``
        those geolocating to Ukraine or Russia.
    ``share``
        ``n_conflict / n_total`` — the attention measure. §5.4 makes shares
        mandatory rather than raw counts because GDELT's source coverage drifts
        heavily over eleven years (the same sampled day yields 546k articles in
        2015, 837k in 2016 and 316k in 2026), which would otherwise show up as a
        spurious trend in every volume series.
    ``tone_conflict`` / ``tone_all``
        mean GKG tone, over conflict articles and over everything.

    ``windows`` is a list of (start, end) date pairs. Only those partitions are
    scanned, so cost scales with days requested, not with the archive.
    """
    from src.data.ecosystems import build_case_sql

    clauses = " OR ".join(
        f"(_PARTITIONTIME BETWEEN TIMESTAMP('{a}') AND TIMESTAMP('{b}'))"
        for a, b in windows
    )
    case = build_case_sql(srclc_expr=SRCLC)
    return f"""
    WITH tagged AS (
      SELECT
        DATE(_PARTITIONTIME) AS day,
        {case} AS ecosystem,
        {CONFLICT} AS is_conflict,
        SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone
      FROM {TABLE}
      WHERE ({clauses}) AND SourceCommonName IS NOT NULL
    )
    SELECT
      day,
      ecosystem,
      COUNT(*) AS n_total,
      COUNTIF(is_conflict) AS n_conflict,
      SAFE_DIVIDE(COUNTIF(is_conflict), COUNT(*)) AS share,
      AVG(IF(is_conflict, tone, NULL)) AS tone_conflict,
      AVG(tone) AS tone_all
    FROM tagged
    WHERE ecosystem != 'AGGREGATOR'
    GROUP BY day, ecosystem
    ORDER BY day, ecosystem
    """


#: Realized violence. Fixed in docs/v3/gate3_preregistration.md before the test.
ACT_THEMES = (
    "KILL", "WOUND", "CRISISLEX_T03_DEAD", "CRISISLEX_T02_INJURED",
    "ARMEDCONFLICT", "TERROR", "SIEGE", "REBELLION", "MANMADE_DISASTER_IMPLIED",
)

#: Anticipation, capability, deterrence.
THREAT_THEMES = (
    "THREATEN", "MILITARY", "TAX_WEAPONS", "TAX_FNCACT_TROOPS", "BORDER",
    "NUCLEAR", "SANCTIONS", "EPU_CATS_NATIONAL_SECURITY", "USPEC_UNCERTAINTY1",
    "SECURITY_SERVICES",
)


def _theme_match(themes: tuple[str, ...]) -> str:
    """SQL predicate: does the V1 Themes string contain any of these themes?

    Matched with delimiters on both sides so ``MILITARY`` does not also fire on
    ``TAX_MILITARY_TITLE``, and ``KILL`` does not fire on ``SKILL``-type codes.
    """
    joined = ";' || Themes || ';"
    tests = " OR ".join(f"STRPOS('{joined}', ';{t};') > 0" for t in themes)
    return f"({tests})"


def threat_act_sql(windows: list[tuple[str, str]]) -> str:
    """Daily per-ecosystem ACT and THREAT shares of conflict coverage.

    GDELT's GKG themes are assigned by one classifier to machine-translated text
    across all 65 source languages, so the same taxonomy applies to a Ukrainian,
    Russian and American article alike. That is what makes an anticipation
    measure comparable across ecosystems without hand-validating a dictionary
    per language.

    Shares are of each ecosystem's own *conflict* output, so they answer "what
    kind of conflict coverage is this ecosystem producing today", independent of
    how much it is producing or how GDELT's source list has drifted.
    """
    from src.data.ecosystems import build_case_sql

    clauses = " OR ".join(
        f"(_PARTITIONTIME BETWEEN TIMESTAMP('{a}') AND TIMESTAMP('{b}'))"
        for a, b in windows
    )
    case = build_case_sql(srclc_expr=SRCLC)
    return f"""
    WITH tagged AS (
      SELECT
        DATE(_PARTITIONTIME) AS day,
        {case} AS ecosystem,
        {_theme_match(ACT_THEMES)}    AS is_act,
        {_theme_match(THREAT_THEMES)} AS is_threat
      FROM {TABLE}
      WHERE ({clauses})
        AND SourceCommonName IS NOT NULL
        AND {CONFLICT}
        AND Themes IS NOT NULL
    )
    SELECT
      day,
      ecosystem,
      COUNT(*) AS n_conflict,
      COUNTIF(is_act) AS n_act,
      COUNTIF(is_threat) AS n_threat,
      SAFE_DIVIDE(COUNTIF(is_act), COUNT(*)) AS act_share,
      SAFE_DIVIDE(COUNTIF(is_threat), COUNT(*)) AS threat_share
    FROM tagged
    WHERE ecosystem NOT IN ('AGGREGATOR', 'OTHER')
    GROUP BY day, ecosystem
    ORDER BY day, ecosystem
    """


def top_outlets_sql(days: list[str], limit: int = 400) -> str:
    """Highest-volume conflict-covering outlets, for building the register by hand.

    Sampled days rather than the full archive: the register only needs to cover
    the outlets that carry most of the volume, and those are stable enough that a
    spread of sample days finds them at a fraction of the cost.
    """
    stamps = ", ".join(f"TIMESTAMP('{d}')" for d in days)
    return f"""
    SELECT
      SourceCommonName AS domain,
      {TLD}   AS tld,
      {SRCLC} AS srclc,
      COUNT(*) AS n
    FROM {TABLE}
    WHERE _PARTITIONTIME IN ({stamps})
      AND {CONFLICT}
      AND SourceCommonName IS NOT NULL
    GROUP BY domain, tld, srclc
    ORDER BY n DESC
    LIMIT {limit}
    """
