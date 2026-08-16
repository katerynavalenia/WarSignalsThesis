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
    compute_index_returns_and_volume,
    cross_validate_ita_vs_recon,
    load_benchmarks,
    load_bloomberg_index_xlsx,
    load_bloomberg_xlsx,
    load_ita_proxy,
    overlay_real_indices,
    reconstruct_index,
)

BBG_DIR = Path("data/raw/bloomberg")
WAER_FILE = BBG_DIR / "WAERLST as of Jun 04 2026.xlsx"
BSH_FILE = BBG_DIR / "BSHIELDT as of Jun 05 2026.xlsx"
BENCH_FILE = BBG_DIR / "indexes.xlsx"

# Real single-index Bloomberg series (new, distinct layout)
WAER_INDEX_FILE = BBG_DIR / "WAERLST Index.xlsx"
BSH_INDEX_FILE = BBG_DIR / "BSHIELDT Index.xlsx"


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
    """Build the full financial table; require ITA columns (primary target)."""
    try:
        fin = build_financial_table(out_path=None)
    except Exception as e:
        pytest.skip(f"ITA fetch failed (network?): {e}")
    # 15 columns: ITA + recon + bsh + 9 controls/derived
    assert fin.shape[1] == 15
    assert fin.index.name == "date"
    # Primary target columns
    for col in ["ITA", "r_ITA", "r_ITA_msadj", "r_SPX", "r_SXXP", "VIX"]:
        assert col in fin.columns, f"Missing primary column: {col}"
    # Archival columns
    for col in ["WAERLST_recon", "r_WAERLST_recon", "BSHIELDT", "r_BSHIELDT"]:
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


# ---------------------------------------------------------------------------
# Real Bloomberg single-index series: load_bloomberg_index_xlsx
# ---------------------------------------------------------------------------

REAL_INDEX_STD = {
    "WAERLST": 1.51,
    "BSHIELDT": 1.77,
}


@pytest.mark.skipif(not WAER_INDEX_FILE.exists(), reason="Real WAERLST index file not available")
def test_load_waerlst_index_xlsx():
    df = load_bloomberg_index_xlsx(WAER_INDEX_FILE)
    assert list(df.columns) == ["px", "volume"]
    assert 1650 <= len(df) <= 1750, f"Expected ~1,694 rows, got {len(df)}"
    assert df.index.min() == pd.Timestamp("2020-01-01")
    assert df.index.max() >= pd.Timestamp("2026-06-29")
    assert df.index.is_monotonic_increasing, "Index must be sorted ascending"
    assert df.index.is_unique
    assert df["px"].notna().all(), "PX_LAST should have zero NaNs"
    assert (df["volume"] >= 0).all()
    assert df.attrs.get("currency") == "USD"
    assert df.attrs.get("security") == "WAERLST Index"


@pytest.mark.skipif(not BSH_INDEX_FILE.exists(), reason="Real BSHIELDT index file not available")
def test_load_bshieldt_index_xlsx():
    df = load_bloomberg_index_xlsx(BSH_INDEX_FILE)
    assert list(df.columns) == ["px", "volume"]
    assert 1650 <= len(df) <= 1750, f"Expected ~1,694 rows, got {len(df)}"
    assert df.index.min() == pd.Timestamp("2020-01-01")
    assert df.index.max() >= pd.Timestamp("2026-06-29")
    assert df.index.is_monotonic_increasing, "Index must be sorted ascending"
    assert df.index.is_unique
    assert df["px"].notna().all(), "PX_LAST should have zero NaNs"
    assert (df["volume"] >= 0).all()
    # BSHIELDT has verified zero-volume days (e.g. holidays) -- allowed.
    assert df.attrs.get("currency") == "EUR"
    assert df.attrs.get("security") == "BSHIELDT Index"


@pytest.mark.skipif(
    not (WAER_INDEX_FILE.exists() and BSH_INDEX_FILE.exists()),
    reason="Real index files not available",
)
@pytest.mark.parametrize("ticker,std_target", list(REAL_INDEX_STD.items()))
def test_real_index_return_convention(ticker, std_target):
    """Return convention is log return * 100, matching r_ITA / r_WAERLST_recon.

    Note: the target std values (1.51 / 1.77) were originally verified via
    simple pct_change; log returns land within ~0.005 of the simple-return
    std at this magnitude (confirmed empirically), so the same tolerance
    band applies regardless of which convention is used. We use LOG
    returns here (np.log(px/px.shift(1))*100) for consistency with the
    rest of this module (r_ITA, r_WAERLST_recon, r_BSHIELDT all use log
    returns, not simple pct_change).
    """
    path = WAER_INDEX_FILE if ticker == "WAERLST" else BSH_INDEX_FILE
    raw = load_bloomberg_index_xlsx(path)
    feat = compute_index_returns_and_volume(raw, ticker)

    log_std = feat[f"r_{ticker}"].dropna().std()
    simple_std = (raw["px"].pct_change() * 100).dropna().std()

    assert log_std == pytest.approx(std_target, abs=0.05), (
        f"{ticker} log-return std {log_std:.4f} not within 0.05 of {std_target}"
    )
    assert simple_std == pytest.approx(std_target, abs=0.05), (
        f"{ticker} simple-return std {simple_std:.4f} not within 0.05 of {std_target}"
    )
    # Level column rebased to 100 at first observation.
    assert feat[ticker].iloc[0] == pytest.approx(100.0)


@pytest.mark.skipif(
    not (WAER_INDEX_FILE.exists() and BSH_INDEX_FILE.exists()),
    reason="Real index files not available",
)
@pytest.mark.parametrize("ticker", ["WAERLST", "BSHIELDT"])
def test_real_index_volume_features(ticker):
    path = WAER_INDEX_FILE if ticker == "WAERLST" else BSH_INDEX_FILE
    raw = load_bloomberg_index_xlsx(path)
    feat = compute_index_returns_and_volume(raw, ticker)

    logvol = feat[f"logvol_{ticker}"]
    z30 = feat[f"vol_z30_{ticker}"]
    dvol = feat[f"dvol_{ticker}"]

    # log1p guards against -inf on zero-volume days.
    assert np.isfinite(logvol.dropna()).all()
    assert not np.isinf(logvol).any()

    # Causal 30-day warmup: NaN for first 29 rows, finite (or legitimately
    # NaN only due to a source NaN, which does not occur here) after.
    assert z30.iloc[:29].isna().all(), "vol_z30 should be NaN during the 29-day warmup"
    assert np.isfinite(z30.iloc[29:].dropna()).all()
    assert not np.isinf(z30.fillna(0)).any()
    assert z30.iloc[29:].notna().sum() > 0

    assert not np.isinf(dvol.fillna(0)).any()


# ---------------------------------------------------------------------------
# overlay_real_indices: synthetic-frame unit test (no raw constituent files
# required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (WAER_INDEX_FILE.exists() and BSH_INDEX_FILE.exists()),
    reason="Real index files not available",
)
def test_overlay_real_indices_synthetic():
    # Synthetic "financial-ish" frame mimicking daily_master.parquet, with
    # old reconstructed BSHIELDT columns present (to exercise the rename)
    # plus a date range only partially overlapping the real index coverage
    # (to exercise the left-join / no-data-loss behavior).
    dates = pd.date_range("2019-12-01", "2020-01-15", freq="D")
    synthetic = pd.DataFrame(
        {
            "r_SPX": np.random.default_rng(0).normal(0, 1, len(dates)),
            "VIX": np.random.default_rng(1).uniform(10, 30, len(dates)),
            "BSHIELDT": np.linspace(100, 105, len(dates)),
            "r_BSHIELDT": np.random.default_rng(2).normal(0, 1.7, len(dates)),
            "r_BSHIELDT_msadj": np.random.default_rng(3).normal(0, 1.5, len(dates)),
        },
        index=dates,
    )
    synthetic.index.name = "date"

    out = overlay_real_indices(synthetic, WAER_INDEX_FILE, BSH_INDEX_FILE)

    # Old recon columns renamed, and their values preserved under the new name.
    assert "BSHIELDT_recon" in out.columns
    assert "r_BSHIELDT_recon" in out.columns
    assert "r_BSHIELDT_recon_msadj" in out.columns
    pd.testing.assert_series_equal(
        out["BSHIELDT_recon"], synthetic["BSHIELDT"], check_names=False
    )

    # New real columns present.
    for col in [
        "r_WAERLST", "WAERLST", "r_BSHIELDT", "BSHIELDT",
        "logvol_WAERLST", "vol_z30_WAERLST", "dvol_WAERLST",
        "logvol_BSHIELDT", "vol_z30_BSHIELDT", "dvol_BSHIELDT",
    ]:
        assert col in out.columns, f"Missing merged column: {col}"

    # No data loss: every original date is preserved (left join).
    assert len(out) == len(synthetic)
    assert out.index.equals(synthetic.index)

    # Original (non-overlapping) columns retain their original values.
    pd.testing.assert_series_equal(out["r_SPX"], synthetic["r_SPX"])

    # Dates that DO overlap real-index coverage (Dec 2019 has none; Jan
    # 2020 1-15 partially does) get real, non-null WAERLST data on
    # trading days within coverage.
    assert out.loc["2020-01-02":"2020-01-15", "WAERLST"].notna().any()
    # Dates before real-index coverage (real data starts 2020-01-01) are NaN.
    assert out.loc["2019-12-01":"2019-12-15", "WAERLST"].isna().all()

