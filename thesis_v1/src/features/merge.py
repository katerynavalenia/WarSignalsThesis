"""Phase 5 merge: build the calendar-day master panel from Phase 1–3 sources.

Loads the four processed tables (``financial_daily``, ``attack_daily``,
``news_daily_enriched``, ``news_query_group_pivot``), standardizes their
``date`` column, and outer-joins them on a clean calendar-day index. The
resulting ``daily_master`` has one row per calendar day (2020-01-07 →
2026-06-21, the full financial window) and includes:

- all source columns (NaN where the source has no data for that day),
- ``waerlst_missing`` (1 if ``r_WAERLST_recon`` is NaN),
- ``is_weekend`` (1 if Saturday/Sunday),
- ``is_holiday`` (1 if the date is a US federal market holiday).

Per the 2026-06-30 decision log, ``date`` is the first regular column of the
output and has dtype ``datetime64[ns]``. Per the §9 weekend rule, financial
returns are NaN on weekends (no forward-fill); the target shift happens at
the *target* level in Phase 5D, not at the feature level here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import yaml

from src.utils.date_utils import (
    US_FEDERAL_HOLIDAYS,
    build_calendar_index,
    standardize_date_column,
)


# ── Paths config ────────────────────────────────────────────────────────────


def load_paths_config(paths_yaml: Optional[Union[str, Path]] = None) -> dict:
    """Load ``config/paths.yaml`` (or a custom path) and return the parsed dict.

    Raises ``FileNotFoundError`` if the file is missing.
    """
    if paths_yaml is None:
        paths_yaml = Path("config/paths.yaml")
    paths_yaml = Path(paths_yaml)
    if not paths_yaml.exists():
        raise FileNotFoundError(
            f"paths config not found at {paths_yaml}. "
            f"Copy config/paths.yaml.example to config/paths.yaml."
        )
    with open(paths_yaml, "r") as f:
        return yaml.safe_load(f)


# ── Loaders ─────────────────────────────────────────────────────────────────


def _load_source(
    paths_config: dict,
    subdir: str,
    filename: str,
    int_format: Optional[str] = None,
) -> pd.DataFrame:
    """Load a processed parquet and standardize its ``date`` column."""
    processed_root = Path(paths_config["data"]["processed"])
    path = processed_root / subdir / filename
    df = pd.read_parquet(path)
    return standardize_date_column(df, int_format=int_format or "%Y%m%d")


def load_financial(paths_config: dict) -> pd.DataFrame:
    """Load and standardize the financial daily table."""
    return _load_source(paths_config, "financial", "financial_daily.parquet")


def load_attack(paths_config: dict) -> pd.DataFrame:
    """Load and standardize the attack daily table."""
    return _load_source(paths_config, "attacks", "attack_daily.parquet")


def load_news_enriched(paths_config: dict) -> pd.DataFrame:
    """Load and standardize the news daily enriched table."""
    return _load_source(paths_config, "news", "news_daily_enriched.parquet")


def load_news_pivot(paths_config: dict) -> pd.DataFrame:
    """Load and standardize the news query×group pivot.

    Critical: the source parquet's ``date`` column is stored as
    ``category`` of strings in YYYYMMDD format; this loader casts it to
    ``datetime64[ns]`` via :func:`standardize_date_column`.
    """
    return _load_source(
        paths_config, "news", "news_query_group_pivot.parquet", int_format="%Y%m%d"
    )


# ── Merge ───────────────────────────────────────────────────────────────────


def build_daily_master(
    financial: pd.DataFrame,
    attack: pd.DataFrame,
    news: pd.DataFrame,
    news_pivot: pd.DataFrame,
    calendar_start: Optional[Union[str, pd.Timestamp]] = "2020-01-07",
    calendar_end: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """Outer-join the four sources on a calendar-day index.

    Parameters
    ----------
    financial, attack, news, news_pivot : pd.DataFrame
        DataFrames returned by the ``load_*`` helpers above. Must have a
        ``date`` column of dtype ``datetime64[ns]``.
    calendar_start, calendar_end : str or Timestamp, optional
        Inclusive bounds of the calendar index. ``calendar_start`` defaults
        to ``"2020-01-07"`` (the first financial trading day). ``calendar_end``
        defaults to the max date across all four sources.

    Returns
    -------
    pd.DataFrame
        One row per calendar day, with all source columns + ``waerlst_missing``,
        ``is_weekend``, ``is_holiday`` derived columns. ``date`` is the first
        column and is sorted ascending.
    """
    # 1. Build the calendar index.
    if calendar_end is None:
        calendar_end = pd.concat(
            [df["date"] for df in (financial, attack, news, news_pivot)]
        ).max()

    calendar = build_calendar_index(calendar_start, calendar_end)
    master = pd.DataFrame({"date": calendar})

    # 2. Left-join each source (calendar is the master). Detect column
    #    collisions (other than `date`) and raise a clear error.
    sources = (
        ("financial", financial),
        ("attack", attack),
        ("news", news),
        ("news_pivot", news_pivot),
    )
    for name, src in sources:
        # Dedupe on `date` — keep last — to be safe against any duplicate rows.
        src = src.drop_duplicates(subset=["date"], keep="last")
        collisions = set(master.columns) & set(src.columns) - {"date"}
        if collisions:
            raise ValueError(
                f"Column collision when merging {name}: {sorted(collisions)}. "
                f"Already in master: {[c for c in master.columns if c != 'date']}"
            )
        master = master.merge(src, on="date", how="left")

    # 3. Data-integrity fix (supervisor audit §1.4): no-attack days are
    #    a true zero, not a missing observation. The calendar left-join
    #    produces NaN for days outside the attack source's date range.
    #    Recode attack count columns to 0 and add a `has_attack_report` flag.
    attack_count_cols = [
        c for c in master.columns
        if c.startswith(("launched_", "destroyed_", "n_attack_events",
                         "n_records", "war_intensity", "large_attack_indicator"))
        or c in ("interception_rate", "weapon_diversity")
        or c.startswith("attack_")
    ]
    if attack_count_cols:
        master["has_attack_report"] = master[attack_count_cols[0]].notna().astype(np.int8)
        # Fill count columns with 0 (true zero = no attack that day)
        zero_fill = [c for c in attack_count_cols if c not in ("interception_rate", "weapon_diversity")]
        master[zero_fill] = master[zero_fill].fillna(0)
        # interception_rate and weapon_diversity are undefined when no attack;
        # leave as NaN (they are derived ratios, not counts)
    else:
        master["has_attack_report"] = np.int8(0)

    # 4. Derived columns.
    #    `waerlst_missing` is 1 wherever the WAERLST reconstruction is NaN;
    #    financial-only baselines can drop this column if they don't need
    #    the WAERLST signal.
    if "r_WAERLST_recon" in master.columns:
        master["waerlst_missing"] = master["r_WAERLST_recon"].isna().astype(np.int8)
    else:
        # If for some reason the column is missing, set all to 1 (signal: none).
        master["waerlst_missing"] = np.int8(1)

    #    `is_weekend` and `is_holiday` are calendar flags, NaN-free by
    #    construction. Vectorized for speed.
    master["is_weekend"] = (master["date"].dt.dayofweek >= 5).astype(np.int8)
    holiday_dates = US_FEDERAL_HOLIDAYS  # set of datetime.date
    master["is_holiday"] = master["date"].dt.date.isin(holiday_dates).astype(np.int8)

    # 4. Ensure `date` is the first column and the dtype is datetime64[ns].
    out = master.copy()
    out["date"] = pd.to_datetime(out["date"])
    cols = ["date"] + [c for c in out.columns if c != "date"]
    return out[cols].sort_values("date").reset_index(drop=True)
