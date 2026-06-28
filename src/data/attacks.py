"""
src/data/attacks.py
====================

Physical attack dataset construction for the War Signals thesis.

Source: Ukrainian Air Force (UAF) daily attack reports.
Raw data: data/raw/attacks/missile_attacks_daily.csv
Reference: data/raw/attacks/missiles_and_uavs-reference.csv

Functions
---------
load_uaf_attacks()       -- Load and parse raw UAF attack records
load_weapon_reference()  -- Load the 64-row weapon classification reference
classify_weapon()        -- Map a model name to a category (uav/cruise/ballistic/...)
build_attack_daily()     -- Aggregate to a daily modeling table
validate_against_sources()  -- Sample validation against the source URLs

Methodology
-----------
- attack_date:    Date when the attack began (from `time_start`)
- report_date:    Date when the count was officially reported (defaulted to
                  attack_date if not directly recoverable)
- market_info_date: The day investors actually saw the count. For wave
                  attacks that span two calendar days, this is the day of
                  the report. Default: max(attack_date, time_end_date).
- No-attack days: explicit zeros (no forward fill) — a day without an
  attack is information.

See docs/phase2_attack_audit.md for the full audit.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Default paths
DEFAULT_RAW_DIR = Path("data/raw/attacks")
DEFAULT_PROCESSED = Path("data/processed/attacks")

# Category columns (cannonical order)
CATEGORIES = ["uav", "cruise_missile", "ballistic_missile", "recon_uav",
              "loitering_munition", "guided_bomb", "other"]

# Keyword-based fallback classifier (used when the model is not in WEAPON_CLASS
# and not in the reference table)
KEYWORD_RULES: list[tuple[str, str]] = [
    # (keyword, category)  -- case-insensitive substring match
    ("shahed",        "uav"),
    ("mohajer",       "uav"),
    ("fpv",           "loitering_munition"),
    ("lancet",        "loitering_munition"),
    ("kub-bla",       "loitering_munition"),
    ("switchblade",   "loitering_munition"),
    ("orlan",         "recon_uav"),
    ("supercam",      "recon_uav"),
    ("zala",          "recon_uav"),
    ("reconnaissance uav", "recon_uav"),
    ("elron",         "recon_uav"),
    ("eleron",        "recon_uav"),
    ("forpost",       "recon_uav"),
    ("granat",        "recon_uav"),
    ("merlin",        "recon_uav"),
    ("kartograf",     "recon_uav"),
    ("unknown uav",   "uav"),
    ("kalibr",        "cruise_missile"),
    ("x-101",         "cruise_missile"),
    ("x-555",         "cruise_missile"),
    ("x-59",          "cruise_missile"),
    ("x-69",          "cruise_missile"),
    ("x-22",          "cruise_missile"),
    ("x-32",          "cruise_missile"),
    ("x-35",          "cruise_missile"),
    ("kinzhal",       "cruise_missile"),
    ("x-47",          "cruise_missile"),
    ("oniks",         "cruise_missile"),
    ("onix",          "cruise_missile"),
    ("p-800",         "cruise_missile"),
    ("iskander",      "ballistic_missile"),
    ("kn-23",         "ballistic_missile"),
    ("tochka",        "ballistic_missile"),
    ("c-300",         "ballistic_missile"),
    ("c-400",         "ballistic_missile"),
    ("s-300",         "ballistic_missile"),
    ("молнія",        "ballistic_missile"),
    ("привет",        "ballistic_missile"),
    ("фенікс",        "ballistic_missile"),
    ("aerial bomb",   "guided_bomb"),
    ("kab-",          "guided_bomb"),
    ("jdam",          "guided_bomb"),
    ("glide",         "guided_bomb"),
    ("unknown missile", "other"),
]

# Explicit overrides (fuzzy string contains)
EXPLICIT_OVERRIDES: dict[str, str] = {
    "Shahed-136/131":  "uav",
    "Shahed-136":      "uav",
    "Shahed-131":      "uav",
    "Orlan-10":        "recon_uav",
    "Supercam":        "recon_uav",
    "ZALA":            "recon_uav",
    "Reconnaissance UAV": "recon_uav",
    "Merlin-VR":       "recon_uav",
    "Eleron":          "recon_uav",
    "Forpost":         "recon_uav",
    "Granat-4":        "recon_uav",
    "Orion":           "recon_uav",
    "Картограф":       "recon_uav",
    "X-101/X-555":     "cruise_missile",
    "X-59/X-69":       "cruise_missile",
    "X-47 Kinzhal":    "cruise_missile",
    "Iskander-M":      "ballistic_missile",
    "Iskander-K":      "ballistic_missile",
    "Iskander-M/KN-23": "ballistic_missile",
    "C-300":           "ballistic_missile",
    "S-300":           "ballistic_missile",
    "C-400":           "ballistic_missile",
    "C-400 and Iskander-M": "ballistic_missile",
    "C-300 and Iskander-M": "ballistic_missile",
    "C-300/C-400":     "ballistic_missile",
    "Kalibr":          "cruise_missile",
    "X-59":            "cruise_missile",
    "X-69":            "cruise_missile",
    "X-22":            "cruise_missile",
    "X-32":            "cruise_missile",
    "X-31":            "cruise_missile",
    "X-31P":           "cruise_missile",
    "X-35":            "cruise_missile",
    "3M22 Zircon":     "cruise_missile",
    "P-800 Oniks":     "cruise_missile",
    "Kh-47M2 Kinzhal": "cruise_missile",
    "Lancet":          "loitering_munition",
    "Kub":             "loitering_munition",
    "Kub-Bla":         "loitering_munition",
    "Mohajer-6":       "uav",
    "Молнія":          "ballistic_missile",
    "Привет-82":       "ballistic_missile",
    "Фенікс":          "ballistic_missile",
    "Aerial Bomb":     "guided_bomb",
    "Unknown UAV":     "uav",
    "Unknown Missile": "other",
}


def load_uaf_attacks(path: str | Path = DEFAULT_RAW_DIR / "missile_attacks_daily.csv"
                     ) -> pd.DataFrame:
    """Load and parse the raw UAF attack records.

    Returns a DataFrame with parsed timestamps, numeric counts, and a
    `category` column (via `classify_weapon`).
    """
    df = pd.read_csv(path)

    # Parse timestamps (be lenient: many cells have either a datetime string
    # or just a date)
    df["time_start"] = pd.to_datetime(df["time_start"], errors="coerce")
    df["time_end"] = pd.to_datetime(df["time_end"], errors="coerce")
    df["attack_date"] = df["time_start"].dt.date
    df["time_end_date"] = df["time_end"].dt.date

    # market_info_date: the day investors actually saw the count.
    # If time_end exists and differs from time_start, use that. Else
    # attack_date. This is documented in the audit and applies to
    # overnight waves (which dominate the dataset).
    # Vectorized: pick the latest non-NaT date among attack_date, time_end_date.
    end_d = pd.to_datetime(df["time_end_date"], errors="coerce")
    start_d = pd.to_datetime(df["attack_date"], errors="coerce")
    df["market_info_date"] = end_d.where(end_d > start_d, start_d)

    # Numeric safety
    for col in ["launched", "destroyed", "not_reach_goal", "still_attacking"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Negative counts -> NaN (data errors)
    for col in ["launched", "destroyed"]:
        df.loc[df[col] < 0, col] = np.nan

    # Classify
    df["category"] = df["model"].apply(classify_weapon)

    return df


def load_weapon_reference(path: str | Path = DEFAULT_RAW_DIR / "missiles_and_uavs-reference.csv"
                          ) -> pd.DataFrame:
    """Load the 64-row weapon reference table."""
    return pd.read_csv(path)


def classify_weapon(model: Optional[str]) -> str:
    """Map a weapon model name to one of CATEGORIES.

    Strategy
    --------
    1. Exact match in EXPLICIT_OVERRIDES (handles "Shahed-136/131" etc.)
    2. Substring match using KEYWORD_RULES, but **specific categories first**
       so that a combined string like "Iskander-M/KN-23 and X-59" classifies
       as ballistic_missile (the more lethal/major component) rather than
       cruise_missile. The order of KEYWORD_RULES is significant.
    3. Fallback: "other"
    """
    if model is None or (isinstance(model, float) and np.isnan(model)):
        return "other"
    s = str(model).strip()
    if not s:
        return "other"

    if s in EXPLICIT_OVERRIDES:
        return EXPLICIT_OVERRIDES[s]

    s_low = s.lower()
    # Prefer the most-severe / most-info category present.
    # Priority: ballistic > cruise > loitering > uav > recon > guided_bomb > other.
    PRIORITY = ["ballistic_missile", "cruise_missile", "loitering_munition",
                "uav", "recon_uav", "guided_bomb", "other"]
    for cat in PRIORITY:
        # Find any keyword for this category
        for kw, kcat in KEYWORD_RULES:
            if kcat == cat and kw in s_low:
                return cat
    return "other"


def build_attack_daily(
    raw_path: str | Path = DEFAULT_RAW_DIR / "missile_attacks_daily.csv",
    start: Optional[str] = "2022-09-29",
    end: Optional[str] = None,
    out_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """Build the daily modeling-ready attack table.

    Output columns
    --------------
    Per-day aggregates grouped by `market_info_date`:
      - launched_total, destroyed_total, interception_rate
      - launched_<cat>, destroyed_<cat>  for cat in CATEGORIES
      - weapon_diversity  (1 - sum_k s_k^2 where s_k = share of category k)
      - war_intensity     log(1 + launched_total)
      - n_attack_events
      - n_records
    """
    df = load_uaf_attacks(raw_path)
    df["market_info_date"] = pd.to_datetime(df["market_info_date"], errors="coerce")
    df = df.dropna(subset=["market_info_date"])

    # Daily aggregation
    daily_total = (
        df.groupby("market_info_date")
        .agg(
            launched_total=("launched", "sum"),
            destroyed_total=("destroyed", "sum"),
            n_records=("launched", "size"),
        )
        .reset_index()
    )

    # Per-category counts (pivot)
    by_cat_launched = (
        df.groupby(["market_info_date", "category"])["launched"]
        .sum()
        .unstack(fill_value=0)
    )
    by_cat_destroyed = (
        df.groupby(["market_info_date", "category"])["destroyed"]
        .sum()
        .unstack(fill_value=0)
    )
    # Ensure all categories present
    for cat in CATEGORIES:
        if cat not in by_cat_launched.columns:
            by_cat_launched[cat] = 0
        if cat not in by_cat_destroyed.columns:
            by_cat_destroyed[cat] = 0
    by_cat_launched = by_cat_launched[CATEGORIES]
    by_cat_destroyed = by_cat_destroyed[CATEGORIES]
    by_cat_launched.columns = [f"launched_{c}" for c in CATEGORIES]
    by_cat_destroyed.columns = [f"destroyed_{c}" for c in CATEGORIES]

    # Count distinct "attack events" per day (proxy: count of records per day)
    # In the UAF data each row is one "wave" of a given weapon.
    # Use number of unique models (or unique rows) as proxy for events.
    n_events = (
        df.groupby("market_info_date").size().rename("n_attack_events").to_frame()
    )

    # Merge all
    out = (
        daily_total
        .merge(by_cat_launched, left_on="market_info_date", right_index=True, how="left")
        .merge(by_cat_destroyed, left_on="market_info_date", right_index=True, how="left")
        .merge(n_events, left_on="market_info_date", right_index=True, how="left")
    )
    out = out.set_index("market_info_date").sort_index()
    out = out.fillna(0)

    # Derived: interception rate (safe)
    out["interception_rate"] = np.where(
        out["launched_total"] > 0,
        out["destroyed_total"] / out["launched_total"],
        np.nan,
    )

    # Derived: war intensity (log)
    out["war_intensity"] = np.log1p(out["launched_total"])

    # Derived: weapon diversity (Herfindahl complement)
    launched_cats = out[[f"launched_{c}" for c in CATEGORIES]].to_numpy()
    total_for_div = launched_cats.sum(axis=1, keepdims=True)
    shares = np.divide(
        launched_cats, total_for_div,
        out=np.zeros_like(launched_cats, dtype=float),
        where=total_for_div > 0,
    )
    hhi = (shares ** 2).sum(axis=1)
    out["weapon_diversity"] = np.where(total_for_div[:, 0] > 0, 1.0 - hhi, np.nan)

    # Optional: clip date range
    if start is not None:
        out = out.loc[out.index >= pd.Timestamp(start)]
    if end is not None:
        out = out.loc[out.index <= pd.Timestamp(end)]

    out.index.name = "date"
    out = out.astype({c: int for c in out.columns if c.startswith(("launched_", "destroyed_", "n_"))})

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(out_path)
        out.to_csv(out_path.with_suffix(".csv"))

    return out


def validate_against_sources(
    daily: pd.DataFrame,
    raw: Optional[pd.DataFrame] = None,
    raw_path: str | Path = DEFAULT_RAW_DIR / "missile_attacks_daily.csv",
    n_samples: int = 25,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample `n_samples` random days and cross-check with the raw data.

    Returns a DataFrame with one row per sampled day, comparing the
    aggregated `launched_total` and `destroyed_total` against the raw
    count (which is the same — this is a sanity check that the
    aggregator matches the raw data). For external validation against
    the source URLs, the report URL is included so the user can
    manually verify against the Facebook post.
    """
    if raw is None:
        raw = load_uaf_attacks(raw_path)

    rng = np.random.default_rng(seed)
    valid_dates = daily.index.unique()
    sample_dates = rng.choice(valid_dates, size=min(n_samples, len(valid_dates)),
                              replace=False)

    rows = []
    for d in sorted(sample_dates):
        d_ts = pd.Timestamp(d)
        sub_raw = raw[pd.to_datetime(raw["market_info_date"]) == d_ts]
        sub_daily = daily.loc[d_ts] if d_ts in daily.index else None
        if sub_daily is None:
            continue
        # First source URL on that day
        src = sub_raw["source"].dropna()
        primary_src = src.iloc[0] if len(src) > 0 else None
        rows.append({
            "date": d_ts.date(),
            "n_records_raw": len(sub_raw),
            "launched_aggregated": float(sub_daily["launched_total"]),
            "launched_raw_sum": float(sub_raw["launched"].sum()),
            "match_launched": float(sub_daily["launched_total"]) == float(sub_raw["launched"].sum()),
            "destroyed_aggregated": float(sub_daily["destroyed_total"]),
            "destroyed_raw_sum": float(sub_raw["destroyed"].sum()),
            "match_destroyed": float(sub_daily["destroyed_total"]) == float(sub_raw["destroyed"].sum()),
            "source_url": primary_src,
            "models": ", ".join(sub_raw["model"].astype(str).unique()[:5]),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    daily = build_attack_daily()
    print(f"Built daily attack table: {daily.shape}")
    print(f"Date range: {daily.index.min().date()} to {daily.index.max().date()}")
    print(f"Total attacks (launched): {daily['launched_total'].sum():.0f}")
    print(f"Total destroyed: {daily['destroyed_total'].sum():.0f}")
    print()
    print("Top 10 days by launched_total:")
    print(daily.nlargest(10, "launched_total")[["launched_total", "destroyed_total",
                                                  "interception_rate", "war_intensity"]].to_string())
    print()
    # Quick category breakdown
    print("Category totals:")
    for cat in CATEGORIES:
        tot = daily[f"launched_{cat}"].sum()
        if tot > 0:
            print(f"  {cat:20s} {tot:>10,.0f}")
