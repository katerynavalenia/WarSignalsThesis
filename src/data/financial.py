"""
src/data/financial.py
====================

Bloomberg data loading and index reconstruction for the War Signals thesis.

Functions
---------
load_bloomberg_xlsx(path)        -- Load a Bloomberg 'values only' sheet
reconstruct_index(wide, meta)    -- Mcap-weighted return-based index reconstruction
load_benchmarks(path)            -- Load and clean the benchmark file
build_financial_table()          -- Build the modeling-ready daily table

The reconstruction methodology is documented in
docs/phase1_financial_audit.md (Section 4).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")

# Bloomberg 'values only' sheet structure
META_LABELS = [
    "Ticker", "Name", "Weight", "Shares", "Price",
    "NAME", "COUNTRY", "CRNCY", "CUR_MKT_CAP",
    "BICS_LEVEL_3_INDUSTRY_NAME",
]
N_META = len(META_LABELS)

# Path defaults (relative to project root)
DEFAULT_BBG_DIR = Path("data/raw/bloomberg")
DEFAULT_PROCESSED = Path("data/processed/financial")


def load_bloomberg_xlsx(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load a Bloomberg 'values only' sheet.

    Returns
    -------
    prices_wide : DataFrame
        date index x ticker columns of close prices.
    prices_long : DataFrame
        columns [date, ticker, price] -- long format.
    meta : DataFrame
        Full metadata (10 fields) for each constituent.
    """
    df = pd.read_excel(path, sheet_name="values only", header=None)

    # Metadata: rows 0..N_META-1, columns 1..end
    meta_dict: dict[str, pd.Series] = {}
    for i, label in enumerate(META_LABELS):
        if i < len(df):
            meta_dict[label] = df.iloc[i, 1:].values
    meta = pd.DataFrame(meta_dict)
    meta = meta.dropna(subset=["Ticker"])
    meta["Ticker"] = meta["Ticker"].astype(str).str.strip()
    meta = meta[meta["Ticker"] != "nan"].reset_index(drop=True)

    # Price data: rows N_META onward
    prices_raw = df.iloc[N_META:, :].copy()
    prices_raw.columns = ["date"] + df.iloc[0, 1:].tolist()
    prices_raw["date"] = pd.to_datetime(prices_raw["date"], errors="coerce")
    prices_raw = prices_raw.dropna(subset=["date"])

    valid_tickers = set(meta["Ticker"].tolist())
    keep_cols = ["date"] + [
        c for c in prices_raw.columns[1:] if str(c).strip() in valid_tickers
    ]
    prices_raw = prices_raw[keep_cols]

    prices_long = prices_raw.melt(
        id_vars="date", var_name="ticker", value_name="price"
    )
    prices_long["ticker"] = prices_long["ticker"].astype(str).str.strip()
    prices_long["price"] = pd.to_numeric(prices_long["price"], errors="coerce")
    prices_long = prices_long.dropna(subset=["price"])
    prices_long = prices_long.sort_values(["ticker", "date"]).reset_index(drop=True)

    prices_wide = prices_long.pivot(
        index="date", columns="ticker", values="price"
    ).sort_index()

    return prices_wide, prices_long, meta


def reconstruct_index(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    min_n: int = 50,
    outlier_threshold: float = 0.5,
    base: float = 100.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Market-cap weighted, returns-based index reconstruction.

    For each day, computes the cross-sectional mcap-weighted average log
    return across constituents, then cumulates from `base`.

    Parameters
    ----------
    wide : DataFrame
        Date-indexed wide price matrix.
    meta : DataFrame
        Constituent metadata (must have columns ``Ticker`` and ``CUR_MKT_CAP``).
    min_n : int
        Minimum number of valid constituents required on a day to retain it.
    outlier_threshold : float
        Daily log returns with |r| > threshold are treated as data errors
        and dropped.
    base : float
        Index level on the first valid day.

    Returns
    -------
    index : Series
        Cumulative index level, NaN on days with insufficient coverage.
    log_return : Series
        Daily log return of the reconstructed index.
    n_data : Series
        Number of constituents with valid returns on each day.
    """
    mcap = pd.to_numeric(meta.set_index("Ticker")["CUR_MKT_CAP"], errors="coerce")
    common = wide.columns.intersection(mcap.index)
    mcap_aligned = mcap.reindex(common).astype(float)
    prices = wide[common]

    log_ret = np.log(prices / prices.shift(1))
    valid_returns = log_ret.where(log_ret.abs() < outlier_threshold)
    weighted = (valid_returns.fillna(0) * mcap_aligned).sum(axis=1)
    weight_sum = (valid_returns.notna() * mcap_aligned).sum(axis=1)
    avg_ret = weighted / weight_sum

    index_cum = np.exp(avg_ret.fillna(0).cumsum()) * base
    n_data = valid_returns.notna().sum(axis=1)
    valid_days = n_data >= min_n
    index_cum = index_cum.where(valid_days, np.nan)
    return index_cum, avg_ret, n_data


def load_benchmarks(path: str | Path) -> pd.DataFrame:
    """Load and clean the benchmark file (indexes.xlsx).

    Returns a wide DataFrame with columns
    [SPX, SXXP, VIX, Brent, EURUSD, MSCI_World].
    """
    df = pd.read_excel(path, sheet_name="values only", header=None)
    bench_tickers = df.iloc[0, 1:].tolist()

    bench_prices = df.iloc[N_META:, :].copy()
    bench_prices.columns = ["date"] + bench_tickers
    bench_prices["date"] = pd.to_datetime(bench_prices["date"], errors="coerce")
    bench_prices = bench_prices.dropna(subset=["date"]).reset_index(drop=True)
    for col in bench_tickers:
        bench_prices[col] = pd.to_numeric(bench_prices[col], errors="coerce")

    rename = {
        "SPX Index": "SPX",
        "SXXP Index": "SXXP",
        "VIX Index": "VIX",
        "CO1 Comdty": "Brent",
        "EURUSD Curncy": "EURUSD",
        "NDDUWI Index": "MSCI_World",
    }
    return bench_prices.rename(columns=rename).set_index("date").sort_index()


def load_ita_proxy(start: str = "2020-01-01", end: str = "2026-06-30") -> pd.DataFrame:
    """Load ITA (iShares U.S. Aerospace & Defense ETF) as a WAERLST proxy.

    ITA tracks the iShares U.S. Aerospace & Defense Index, a curated subset
    of the same defense universe as WAERLST. Used as the primary target
    while we await the official Bloomberg WAERLST time series.

    Returns
    -------
    DataFrame
        Columns: ['ITA_close', 'ITA_log_return', 'ITA_index'].
        Index: DatetimeIndex of trading days.
    """
    try:
        import yfinance as yf
    except ImportError as e:
        raise ImportError(
            "yfinance is required for ITA proxy. Install with: pip install yfinance"
        ) from e

    raw = yf.Ticker("ITA").history(start=start, end=end, auto_adjust=False)
    if raw.empty:
        raise RuntimeError("No ITA data returned by yfinance.")

    close = raw["Close"].copy()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index()

    out = pd.DataFrame(index=close.index)
    out["ITA_close"] = close
    out["ITA_log_return"] = np.log(close / close.shift(1))
    # Normalize to 100 on first valid day
    out["ITA_index"] = close / close.iloc[0] * 100
    return out


def build_financial_table(
    bbg_dir: str | Path = DEFAULT_BBG_DIR,
    out_path: str | Path | None = None,
    include_ita: bool = True,
) -> pd.DataFrame:
    """Build the modeling-ready daily financial table.

    Primary target: ITA (iShares U.S. Aerospace & Defense ETF) -- a real,
    liquid, USD-denominated defense index with full 6+ year history available
    free via yfinance. We use this as the proxy for WAERLST (Bloomberg
    World Aerospace & Defense Total Return) until the official Bloomberg
    series arrives.

    The reconstructed WAERLST is kept as an **archival column** for
    transparency and cross-checking, but is NOT recommended for forecasting
    (ρ=0.14 vs ITA -- too noisy due to small-cap and multi-currency
    constituents; see Phase 1 audit §8).

    BSHIELDT is still reconstructed from constituents (no free full-history
    European defense index is available -- EUAD/ASWC start only in 2024).

    Parameters
    ----------
    bbg_dir : path
        Directory containing the Bloomberg .xlsx exports.
    out_path : path, optional
        If given, save the result as parquet + csv.
    include_ita : bool
        If True (default), fetch ITA via yfinance. If False or fetch fails,
        ITA columns are NaN and the user must populate them.

    Returns
    -------
    DataFrame
        Daily modeling table (1,610 × 15). Primary columns:
          - r_ITA, ITA, r_ITA_msadj  (primary target, US defense proxy)
          - r_BSHIELDT, BSHIELDT     (European defense, reconstructed)
          - WAERLST_recon, r_WAERLST_recon  (archival, low quality)
          - r_SPX, r_SXXP, r_MSCI_World, r_Brent, r_EURUSD, VIX, d_VIX
    """
    bbg_dir = Path(bbg_dir)

    waer_wide, _, waer_meta = load_bloomberg_xlsx(
        bbg_dir / "WAERLST as of Jun 04 2026.xlsx"
    )
    bsh_wide, _, bsh_meta = load_bloomberg_xlsx(
        bbg_dir / "BSHIELDT as of Jun 05 2026.xlsx"
    )
    bench = load_benchmarks(bbg_dir / "indexes.xlsx")

    waer_idx, waer_logret, _ = reconstruct_index(waer_wide, waer_meta, min_n=80)
    bsh_idx, bsh_logret, _ = reconstruct_index(bsh_wide, bsh_meta, min_n=20)

    # ITA proxy (PRIMARY target for WAERLST)
    ita = None
    if include_ita:
        try:
            ita = load_ita_proxy(
                start=waer_idx.dropna().index.min().strftime("%Y-%m-%d"),
                end=waer_idx.dropna().index.max().strftime("%Y-%m-%d"),
            )
        except Exception as exc:  # pragma: no cover
            warnings.warn(f"ITA fetch failed: {exc}. Continuing without ITA.")

    # Date index: prefer ITA dates (cleanest, longest history)
    if ita is not None:
        valid_dates = ita.dropna(subset=["ITA_close"]).index
    else:
        valid_dates = waer_idx.dropna().index

    fin = pd.DataFrame(index=valid_dates)
    fin.index.name = "date"

    # === PRIMARY TARGET: ITA (US defense ETF proxy) ===
    if ita is not None:
        fin["ITA"] = ita.loc[valid_dates, "ITA_index"]
        fin["r_ITA"] = ita.loc[valid_dates, "ITA_log_return"] * 100

    # === Controls: market + macro ===
    bench_ret = np.log(bench / bench.shift(1)) * 100
    for col in ["SPX", "SXXP", "MSCI_World", "Brent", "EURUSD"]:
        if col in bench_ret.columns:
            fin[f"r_{col}"] = bench_ret.loc[valid_dates, col]
    if "VIX" in bench.columns:
        fin["VIX"] = bench.loc[valid_dates, "VIX"]
        fin["d_VIX"] = bench.loc[valid_dates, "VIX"].diff()

    # === Derived: market-adjusted ITA (vs MSCI World) ===
    if "r_ITA" in fin.columns and "r_MSCI_World" in fin.columns:
        fin["r_ITA_msadj"] = fin["r_ITA"] - fin["r_MSCI_World"]

    # === European robustness: BSHIELDT (reconstructed, no clean free proxy) ===
    fin["BSHIELDT"] = bsh_idx.reindex(valid_dates)
    fin["r_BSHIELDT"] = bsh_logret.reindex(valid_dates) * 100
    if "r_SXXP" in fin.columns:
        fin["r_BSHIELDT_msadj"] = fin["r_BSHIELDT"] - fin["r_SXXP"]

    # === ARCHIVAL: Bloomberg-reconstructed WAERLST (low quality, see audit) ===
    # Kept for transparency and to support the methodology discussion in
    # the thesis. NOT to be used as the forecasting target.
    fin["WAERLST_recon"] = waer_idx.reindex(valid_dates)
    fin["r_WAERLST_recon"] = waer_logret.reindex(valid_dates) * 100

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fin.to_parquet(out_path)
        fin.to_csv(out_path.with_suffix(".csv"))

    return fin


def cross_validate_ita_vs_recon(
    bbg_dir: str | Path = DEFAULT_BBG_DIR,
) -> pd.DataFrame:
    """Cross-validate ITA proxy against the reconstructed WAERLST.

    Returns a DataFrame with full-sample stats and event-window comparisons.

    **Important caveat:** As of Phase 1, the recon vs ITA correlation is
    only ~0.15, meaning the Bloomberg-reconstructed WAERLST is too noisy
    to be a faithful proxy. The recon is therefore kept for archival and
    methodology-documentation purposes only; ITA is the primary target.
    """
    fin = build_financial_table(bbg_dir=bbg_dir, include_ita=True)
    df = pd.DataFrame({
        "ita_logret": fin["r_ITA"] / 100,
        "recon_logret": fin["r_WAERLST_recon"] / 100,
    }).dropna()

    corr = df["ita_logret"].corr(df["recon_logret"])
    var_x = df["ita_logret"].var()
    var_y = df["recon_logret"].var()
    beta = df["ita_logret"].cov(df["recon_logret"]) / var_x
    alpha = df["recon_logret"].mean() - beta * df["ita_logret"].mean()

    events = {
        "COVID crash (Mar 2020)": ("2020-02-20", "2020-04-01"),
        "Russian invasion (Feb 2022)": ("2022-02-15", "2022-04-01"),
        "Hamas-Israel (Oct 2023)": ("2023-10-01", "2023-11-15"),
    }
    event_stats = []
    for label, (start, end) in events.items():
        sub = df.loc[start:end]
        if len(sub) > 5:
            event_stats.append({
                "metric": label,
                "N": len(sub),
                "ita_mean_%": sub["ita_logret"].mean() * 100,
                "recon_mean_%": sub["recon_logret"].mean() * 100,
                "ita_std_%": sub["ita_logret"].std() * 100,
                "recon_std_%": sub["recon_logret"].std() * 100,
                "correlation": sub["ita_logret"].corr(sub["recon_logret"]),
                "beta_ita_to_recon": np.nan,
                "alpha_%": np.nan,
                "variance_ratio_recon_over_ita": np.nan,
            })

    return pd.concat(
        [
            pd.DataFrame([{
                "metric": "full_sample",
                "N": len(df),
                "ita_mean_%": df["ita_logret"].mean() * 100,
                "recon_mean_%": df["recon_logret"].mean() * 100,
                "ita_std_%": df["ita_logret"].std() * 100,
                "recon_std_%": df["recon_logret"].std() * 100,
                "correlation": corr,
                "beta_ita_to_recon": beta,
                "alpha_%": alpha * 100,
                "variance_ratio_recon_over_ita": var_y / var_x,
            }]),
            pd.DataFrame(event_stats),
        ],
        ignore_index=True,
    )


if __name__ == "__main__":
    fin = build_financial_table()
    print(f"Built financial table: {fin.shape}")
    print(f"Date range: {fin.index.min().date()} to {fin.index.max().date()}")
    print(fin.describe().round(3))
