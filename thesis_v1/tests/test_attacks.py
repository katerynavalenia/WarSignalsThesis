"""
Tests for src/data/attacks.py
=============================
Smoke tests verifying the Phase 2 attack-data pipeline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.attacks import (
    CATEGORIES,
    build_attack_daily,
    classify_weapon,
    load_uaf_attacks,
    load_weapon_reference,
    validate_against_sources,
)

RAW_DIR = Path("data/raw/attacks")
RAW_FILE = RAW_DIR / "missile_attacks_daily.csv"
REF_FILE = RAW_DIR / "missiles_and_uavs-reference.csv"


# ----- classifier ---------------------------------------------------------

@pytest.mark.parametrize("model,expected", [
    ("Shahed-136/131", "uav"),
    ("Iskander-M", "ballistic_missile"),
    ("Kalibr", "cruise_missile"),
    ("Orlan-10", "recon_uav"),
    ("Lancet", "loitering_munition"),
    ("X-47 Kinzhal", "cruise_missile"),
    ("C-300", "ballistic_missile"),
    ("Unknown UAV", "uav"),
    ("Unknown Missile", "other"),
    ("Молнія", "ballistic_missile"),
    ("Привет-82", "ballistic_missile"),
    ("Фенікс", "ballistic_missile"),
    ("Картограф", "recon_uav"),
    ("Aerial Bomb", "guided_bomb"),
    ("X-101/X-555 and Kalibr", "cruise_missile"),
    ("C-300/C-400", "ballistic_missile"),
    ("C-400 and Iskander-M", "ballistic_missile"),
    ("Iskander-M/KN-23 and Iskander-K and X-59/X-69", "ballistic_missile"),
    ("Orlan-10 and Orlan-30 and ZALA and Supercam", "recon_uav"),
])
def test_classify_weapon(model, expected):
    assert classify_weapon(model) == expected


def test_classify_weapon_handles_nan():
    assert classify_weapon(None) == "other"
    assert classify_weapon(np.nan) == "other"
    assert classify_weapon("") == "other"


# ----- loader -------------------------------------------------------------

@pytest.mark.skipif(not RAW_FILE.exists(), reason="Raw UAF data not available")
def test_load_uaf_attacks():
    df = load_uaf_attacks(RAW_FILE)
    assert len(df) > 3000
    assert "market_info_date" in df.columns
    assert "category" in df.columns
    assert df["category"].notna().all()
    # All rows should classify to one of the canonical categories
    assert set(df["category"].unique()).issubset(set(CATEGORIES))
    # Negative counts replaced with NaN
    assert (df["launched"].dropna() >= 0).all()
    assert (df["destroyed"].dropna() >= 0).all()


# ----- daily aggregation -------------------------------------------------

@pytest.mark.skipif(not RAW_FILE.exists(), reason="Raw UAF data not available")
def test_build_attack_daily():
    daily = build_attack_daily(out_path=None)
    # Should have all CATEGORIES as launched_/destroyed_ columns
    for cat in CATEGORIES:
        assert f"launched_{cat}" in daily.columns
        assert f"destroyed_{cat}" in daily.columns
    # Required derived columns
    for col in ["interception_rate", "weapon_diversity", "war_intensity",
                "n_attack_events", "n_records"]:
        assert col in daily.columns
    # Date range
    assert daily.index.min() >= pd.Timestamp("2022-09-29")
    assert daily.index.max() <= pd.Timestamp("2026-06-30")
    # Realistic sums
    assert daily["launched_total"].sum() > 50_000
    assert daily["destroyed_total"].sum() > 30_000
    # IR should be in [0, 1] when defined
    ir = daily["interception_rate"].dropna()
    assert (ir >= 0).all() and (ir <= 1).all()
    # Diversity should be in [0, 1] when defined
    div = daily["weapon_diversity"].dropna()
    assert (div >= 0).all() and (div <= 1).all()


@pytest.mark.skipif(not RAW_FILE.exists(), reason="Raw UAF data not available")
def test_build_attack_daily_no_future_dates():
    """market_info_date should never be later than time_end."""
    df = load_uaf_attacks(RAW_FILE)
    daily = build_attack_daily(out_path=None)
    # Every daily row's index date should be >= attack_date
    # for the contributing raw rows
    df_check = df.dropna(subset=["market_info_date", "time_start"]).copy()
    df_check["market_info_date"] = pd.to_datetime(df_check["market_info_date"])
    df_check["attack_date"] = pd.to_datetime(df_check["attack_date"])
    bad = (df_check["market_info_date"] < df_check["attack_date"]).sum()
    assert bad == 0, f"market_info_date < attack_date in {bad} rows"


# ----- validation --------------------------------------------------------

@pytest.mark.skipif(not RAW_FILE.exists(), reason="Raw UAF data not available")
def test_validate_against_sources():
    daily = build_attack_daily(out_path=None)
    val = validate_against_sources(daily, n_samples=15, seed=123)
    assert len(val) > 0
    # Aggregated launched should equal raw launched sum
    assert (val["match_launched"]).all()
    assert (val["match_destroyed"]).all()
    # Each row should have a source URL
    assert val["source_url"].notna().all()


# ----- reference --------------------------------------------------------

@pytest.mark.skipif(not REF_FILE.exists(), reason="Reference data not available")
def test_load_weapon_reference():
    ref = load_weapon_reference(REF_FILE)
    assert len(ref) == 64
    assert "category" in ref.columns
    assert "national_origin" in ref.columns
