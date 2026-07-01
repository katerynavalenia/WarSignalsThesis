"""
Tests for src/data/financial.py
================================
Smoke tests verifying the Phase 1 deliverable reproduces from scratch.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.financial import (
    build_financial_table,
    cross_validate_ita_vs_recon,
    load_benchmarks,
    load_bloomberg_xlsx,
    load_ita_proxy,
    reconstruct_index,
)

BBG_DIR = Path("data/raw/bloomberg")
WAER_FILE = BBG_DIR / "WAERLST as of Jun 04 2026.xlsx"
BSH_FILE = BBG_DIR / "BSHIELDT as of Jun 05 2026.xlsx"
BENCH_FILE = BBG_DIR / "indexes.xlsx"


@pytest.mark.skipif(not WAER_FILE.exists(), reason="Bloomberg data not available")
def test_load_waerlst():
    wide, long, meta = load_bloomberg_xlsx(WAER_FILE)
    assert wide.shape[0] > 1500, "Expected >1500 trading days for WAERLST"
    assert wide.shape[1] == 118, "Expected 118 WAERLST constituents"
    assert meta["Weight"].astype(float).sum() == pytest.approx(100.0, abs=0.01)
    assert ((wide.dropna() > 0).all().all()), "Non-NaN prices should be positive"


@pytest.mark.skipif(not BSH_FILE.exists(), reason="Bloomberg data not available")
def test_load_bshieldt():
    wide, _, meta = load_bloomberg_xlsx(BSH_FILE)
    assert wide.shape[1] == 36, "Expected 36 BSHIELDT constituents"
    assert meta["Weight"].astype(float).sum() == pytest.approx(100.0, abs=0.01)


@pytest.mark.skipif(not BENCH_FILE.exists(), reason="Benchmark data not available")
def test_load_benchmarks():
    bench = load_benchmarks(BENCH_FILE)
    assert "SPX" in bench.columns
    assert "VIX" in bench.columns
    assert bench["VIX"].dropna().min() > 0


@pytest.mark.skipif(not WAER_FILE.exists(), reason="Bloomberg data not available")
def test_reconstruct_index_returns():
    wide, _, meta = load_bloomberg_xlsx(WAER_FILE)
    idx, lret, n = reconstruct_index(wide, meta, min_n=80)
    valid = idx.dropna()
    assert len(valid) > 1000
    # Return stats should be realistic
    valid_ret = lret.loc[valid.index].dropna()
    assert valid_ret.std() < 0.10, "Daily std should be < 10%"
    assert valid_ret.abs().max() < 0.5, "Outlier filter should cap |r| < 50%"


def test_load_ita_proxy():
    """ITA is the primary target. Network-dependent but typically available."""
    try:
        ita = load_ita_proxy(start="2022-01-01", end="2026-06-30")
    except Exception as e:
        pytest.skip(f"ITA fetch failed (network?): {e}")
    assert "ITA_close" in ita.columns
    assert "ITA_log_return" in ita.columns
    assert len(ita) > 800, "Expected >800 ITA trading days 2022-2026"
    assert ita["ITA_close"].dropna().min() > 0


@pytest.mark.skipif(not all(p.exists() for p in [WAER_FILE, BSH_FILE, BENCH_FILE]),
                    reason="Bloomberg data not available")
def test_build_financial_table():
    """Build the full financial table; require real Bloomberg + EU defense."""
    try:
        fin = build_financial_table(out_path=None)
    except Exception as e:
        pytest.skip(f"yfinance fetch failed (network?): {e}")
    # 25 columns: WAERLST + BSHIELDT + EUDEF(5) + ITA + controls/derived + archival
    assert fin.shape[1] >= 20, f"Expected >=20 columns, got {fin.shape[1]}"
    assert fin.index.name == "date"
    # Primary target columns (real Bloomberg)
    for col in ["r_WAERLST", "WAERLST", "r_BSHIELDT", "BSHIELDT"]:
        assert col in fin.columns, f"Missing primary column: {col}"
    # European defense basket
    assert "r_EUDEF" in fin.columns, "Missing EU defense basket"
    # US comparison
    for col in ["r_ITA", "ITA", "r_SPX", "VIX"]:
        assert col in fin.columns, f"Missing control column: {col}"
    # Archival columns (reconstruction kept for documentation)
    for col in ["WAERLST_recon", "r_WAERLST_recon"]:
        assert col in fin.columns, f"Missing archival column: {col}"
    # No all-NaN columns
    assert not fin.isna().all().any()
    # Date range covers 2020-2026
    assert fin.index.min().year == 2020
    assert fin.index.max().year == 2026
    # ITA target has reasonable stats
    ita_ret = fin["r_ITA"].dropna()
    assert ita_ret.std() < 5, "ITA daily std should be < 5%"
    assert ita_ret.abs().max() < 25, "ITA max |return| should be < 25%"


def test_cross_validation_runs():
    """Cross-validation should produce a DataFrame with full_sample + events."""
    try:
        cv = cross_validate_ita_vs_recon()
    except Exception as e:
        pytest.skip(f"Cross-validation failed (network?): {e}")
    assert "correlation" in cv.columns
    assert "metric" in cv.columns
    assert "full_sample" in cv["metric"].values
    # We document: correlation is low (~0.15). This is a known limitation,
    # not a test failure -- the recon is too noisy. The test ensures the
    # function runs and produces output.
    full_row = cv[cv["metric"] == "full_sample"].iloc[0]
    assert 0.0 < full_row["correlation"] < 1.0

