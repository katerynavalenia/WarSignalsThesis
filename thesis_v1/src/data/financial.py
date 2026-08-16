"""
src/data/financial.py
====================

Bloomberg data loading and index reconstruction for the War Signals thesis.

Functions
---------
load_bloomberg_xlsx(path)          -- Load a Bloomberg 'values only' sheet (constituents)
load_bloomberg_index_xlsx(path)    -- Load a Bloomberg single-index 'Worksheet' sheet
                                       (real WAERLST/BSHIELDT PX_LAST + PX_VOLUME series)
compute_index_returns_and_volume() -- Return/level/volume feature helper for the
                                       real index series
reconstruct_index(wide, meta)      -- Mcap-weighted return-based index reconstruction
load_benchmarks(path)              -- Load and clean the benchmark file
build_financial_table()            -- Build the modeling-ready daily table
overlay_real_indices()             -- Merge real WAERLST/BSHIELDT series onto an
                                       existing financial-ish DataFrame

The reconstruction methodology is documented in
docs/phase1_financial_audit.md (Section 4). The real-index integration is
documented in docs/real_index_integration_plan.md and the 2026-07-02
decision_log.md entry ("Target hierarchy restructured...").
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


def load_bloomberg_index_xlsx(path: str | Path) -> pd.DataFrame:
    """Load a real Bloomberg single-index daily series (e.g. WAERLST/BSHIELDT).

    This is a **different sheet layout** from :func:`load_bloomberg_xlsx`
    (which parses a "values only" constituent-level sheet). This function
    parses sheet ``Worksheet``, which has a small metadata header block
    (``Security``, ``Start Date``, ``End Date``, ``Period``, ``Currency``),
    a blank row, then a data table with header row ``Date, PX_LAST,
    PX_VOLUME``. The header row position is **located dynamically** (first
    row where column 0 == "Date") rather than hardcoded, since Bloomberg
    exports can shift the row offset.

    The export's date order is not guaranteed (a prior delivery was
    descending, the current one is ascending) -- this function always
    sorts ascending defensively and de-duplicates on date (keeping the
    last occurrence).

    Parameters
    ----------
    path : path
        Path to the ``<TICKER> Index.xlsx`` file.

    Returns
    -------
    DataFrame
        Date-indexed (ascending, deduped) frame with columns ``px``
        (from PX_LAST) and ``volume`` (from PX_VOLUME), both numeric
        float. Metadata (``security``, ``currency``, ``period``,
        ``start_date``, ``end_date``) is attached via ``.attrs``.
    """
    raw = pd.read_excel(path, sheet_name="Worksheet", header=None)

    # --- Metadata block: label in col 0, value in col 1 ---
    meta: dict[str, object] = {}
    meta_labels = {"Security", "Start Date", "End Date", "Period", "Currency"}
    for i in range(len(raw)):
        label = raw.iat[i, 0]
        if isinstance(label, str) and label.strip() in meta_labels:
            meta[label.strip().lower().replace(" ", "_")] = raw.iat[i, 1]
        if isinstance(label, str) and label.strip() == "Date":
            header_row = i
            break
    else:
        raise ValueError(f"Could not locate a 'Date' header row in {path}")

    # --- Data table ---
    data = raw.iloc[header_row + 1 :].copy()
    data.columns = raw.iloc[header_row].tolist()
    data = data.rename(columns={"Date": "date", "PX_LAST": "px", "PX_VOLUME": "volume"})
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    data["px"] = pd.to_numeric(data["px"], errors="coerce")
    data["volume"] = pd.to_numeric(data["volume"], errors="coerce")

    data = data.sort_values("date").drop_duplicates(subset="date", keep="last")
    out = data.set_index("date")[["px", "volume"]].sort_index()
    out.index.name = "date"

    out.attrs["security"] = meta.get("security")
    out.attrs["currency"] = meta.get("currency")
    out.attrs["period"] = meta.get("period")
    out.attrs["start_date"] = meta.get("start_date")
    out.attrs["end_date"] = meta.get("end_date")

    return out


def compute_index_returns_and_volume(
    df: pd.DataFrame, name: str, base: float = 100.0
) -> pd.DataFrame:
    """Derive return/level/volume features from a loaded real-index frame.

    Parameters
    ----------
    df : DataFrame
        Output of :func:`load_bloomberg_index_xlsx` -- date-indexed
        (ascending) with columns ``px``, ``volume``.
    name : str
        Index name suffix used in the output column names, e.g.
        ``"WAERLST"`` or ``"BSHIELDT"``.
    base : float
        Level to rebase the price series to on the first observation
        (matches the ``ITA_index`` / reconstructed-index convention
        elsewhere in this module: ``close / close.iloc[0] * base``).

    Returns
    -------
    DataFrame
        Date-indexed frame with columns:
          - ``{name}`` -- price level rebased to ``base`` at the first obs.
          - ``r_{name}`` -- log return in percent:
            ``np.log(px / px.shift(1)) * 100`` (matches the convention
            used for ``r_ITA`` / ``r_WAERLST_recon`` / ``r_BSHIELDT``
            elsewhere in this module -- NOT simple pct_change).
          - ``logvol_{name}`` -- ``log1p(volume)`` (zero-guarded: avoids
            ``-inf`` on zero-volume / holiday rows, which do occur, e.g.
            BSHIELDT has 28 zero-volume days in the verified file).
          - ``vol_z30_{name}`` -- 30-day rolling z-score of ``logvol``,
            computed causally: ``rolling(30)`` at day t uses days
            ``t-29..t`` only (no future information), so it is NaN for
            the first 29 observations and finite from day 30 onward.
          - ``dvol_{name}`` -- day-over-day change in ``logvol``.
    """
    px = df["px"].astype(float)
    vol = df["volume"].astype(float)

    out = pd.DataFrame(index=df.index)
    out.index.name = "date"

    out[name] = px / px.iloc[0] * base
    out[f"r_{name}"] = np.log(px / px.shift(1)) * 100

    logvol = np.log1p(vol)
    out[f"logvol_{name}"] = logvol
    roll_mean = logvol.rolling(30).mean()
    roll_std = logvol.rolling(30).std()
    out[f"vol_z30_{name}"] = (logvol - roll_mean) / roll_std
    out[f"dvol_{name}"] = logvol.diff()

    return out


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


# European defense equities for the geographic-robustness hypothesis (H6).
# These are more Ukraine-narrative-sensitive than US primes (LMT/RTX).
EU_DEFENSE_TICKERS = {
    "RHM.DE": "Rheinmetall",    # Germany — land systems, ammunition
    "LDO.MI": "Leonardo",       # Italy — defense electronics, helicopters
    "BA.L": "BAE Systems",      # UK — defense, aerospace
    "HO.PA": "Thales",          # France — defense electronics
    # Hensoldt (HGT.DE) delisted on yfinance; omitted. 4 names sufficient.
}


def load_eu_defense_basket(
    start: str = "2020-01-01",
    end: str = "2026-06-30",
) -> pd.DataFrame:
    """Load European defense equities via yfinance and build an equal-weight basket.

    .. note::
       Written for the 2026-07-01 supervisor-audit scope (``r_EUDEF`` as a
       tertiary target). The 2026-07-02 target hierarchy uses the real
       Bloomberg WAERLST/BSHIELDT series instead, so this loader is **not
       wired into** :func:`build_financial_table` — it is retained as a
       standalone helper for the H6 geographic-robustness check and for v2.

    Returns
    -------
    DataFrame
        Index: DatetimeIndex (ascending).
        Columns: individual log returns + 'r_EUDEF' (equal-weight basket return).
    """
    try:
        import yfinance as yf
    except ImportError as e:
        raise ImportError(
            "yfinance is required for European defense equities. "
            "Install with: pip install yfinance"
        ) from e

    tickers_str = " ".join(EU_DEFENSE_TICKERS.keys())
    raw = yf.download(tickers_str, start=start, end=end, auto_adjust=False,
                      progress=False)
    if raw.empty:
        raise RuntimeError("No European defense data returned by yfinance.")

    close = raw["Close"].copy()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index()

    # Individual log returns (in %)
    returns = np.log(close / close.shift(1)) * 100

    # Equal-weight basket: mean of available returns each day
    returns["r_EUDEF"] = returns.mean(axis=1)

    # Rename columns to human-readable
    rename = {t: f"r_{name.replace(' ', '')}" for t, name in EU_DEFENSE_TICKERS.items()}
    returns = returns.rename(columns=rename)

    return returns


def build_financial_table(
    bbg_dir: str | Path = DEFAULT_BBG_DIR,
    out_path: str | Path | None = None,
    include_ita: bool = True,
) -> pd.DataFrame:
    """Build the modeling-ready daily financial table.

    .. note::
       **Superseded 2026-07-02 (see decision_log.md).** Real Bloomberg
       WAERLST/BSHIELDT index series (PX_LAST + PX_VOLUME) are now
       available and are the primary/robustness targets going forward --
       see :func:`load_bloomberg_index_xlsx`, :func:`compute_index_returns_and_volume`,
       and :func:`overlay_real_indices`. This function's mcap-weighted
       **reconstruction** of BSHIELDT from constituent files is no longer
       the primary source for the ``BSHIELDT``/``r_BSHIELDT`` columns --
       those names are now reserved for the real series merged in by
       :func:`overlay_real_indices`. The reconstruction output of this
       function is renamed to ``BSHIELDT_recon`` / ``r_BSHIELDT_recon`` /
       ``r_BSHIELDT_recon_msadj`` and kept purely as an **archival**
       column (methodology cross-check), consistent with
       ``WAERLST_recon``/``r_WAERLST_recon`` naming. The reconstruction
       code path itself is left intact -- it still runs and produces
       these archival columns whenever the raw constituent files
       (``bbg_dir``) are available.

    Primary target: ITA (iShares U.S. Aerospace & Defense ETF) -- a real,
    liquid, USD-denominated defense index with full 6+ year history available
    free via yfinance. Historically used as the WAERLST proxy before the
    real Bloomberg WAERLST series arrived; now kept as an optional US
    robustness target (see decision_log.md 2026-07-02).

    The reconstructed WAERLST is kept as an **archival column** for
    transparency and cross-checking, but is NOT recommended for forecasting
    (ρ=0.14 vs ITA -- too noisy due to small-cap and multi-currency
    constituents; see Phase 1 audit §8).

    BSHIELDT is still reconstructed from constituents (no free full-history
    European defense index is available -- EUAD/ASWC start only in 2024),
    but the reconstruction is now demoted to an archival ``BSHIELDT_recon``
    column now that the real Bloomberg BSHIELDT series is available (merge
    it in with :func:`overlay_real_indices`).

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
          - r_ITA, ITA, r_ITA_msadj  (optional US defense proxy)
          - r_BSHIELDT_recon, BSHIELDT_recon  (European defense, archival
            reconstruction -- real BSHIELDT now merged separately)
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

    # === European robustness: BSHIELDT_recon (reconstructed, archival) ===
    # Demoted 2026-07-02: the real Bloomberg BSHIELDT series is now the
    # primary BSHIELDT/r_BSHIELDT source (merged separately via
    # overlay_real_indices). This reconstruction is kept as an archival
    # cross-check under the _recon suffix.
    fin["BSHIELDT_recon"] = bsh_idx.reindex(valid_dates)
    fin["r_BSHIELDT_recon"] = bsh_logret.reindex(valid_dates) * 100
    if "r_SXXP" in fin.columns:
        fin["r_BSHIELDT_recon_msadj"] = fin["r_BSHIELDT_recon"] - fin["r_SXXP"]

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


def overlay_real_indices(
    df: pd.DataFrame,
    waerlst_path: str | Path,
    bshieldt_path: str | Path,
) -> pd.DataFrame:
    """Merge real WAERLST/BSHIELDT series onto an existing financial table.

    Takes an existing date-indexed financial-ish DataFrame -- e.g. the
    cached ``data/processed/daily_master.parquet`` or the output of
    :func:`build_financial_table` -- and left-joins in the real Bloomberg
    ``r_WAERLST``, ``r_BSHIELDT``, ``WAERLST``, ``BSHIELDT``, and volume
    features (``logvol_*``, ``vol_z30_*``, ``dvol_*``). Any pre-existing
    reconstructed BSHIELDT columns (``BSHIELDT``, ``r_BSHIELDT``,
    ``r_BSHIELDT_msadj``, produced by the old constituent-based
    :func:`reconstruct_index` path in :func:`build_financial_table`) are
    renamed to the ``_recon`` suffix (``BSHIELDT_recon``,
    ``r_BSHIELDT_recon``, ``r_BSHIELDT_recon_msadj``) before the real
    columns are attached, since the real series now takes the plain names.

    This function does **not** require the raw Bloomberg constituent
    files (``WAERLST as of ...xlsx``, ``BSHIELDT as of ...xlsx``,
    ``indexes.xlsx``) -- only the two real single-index ``.xlsx`` paths.

    Return/level/volume features are computed on the **native, contiguous
    trading-day series** of each real index first (so rolling windows and
    day-over-day diffs are not corrupted by gaps), and only then left-joined
    onto ``df``'s date index -- preserving every row of ``df``, including
    dates that fall outside the real-index coverage (those get NaN for the
    new columns).

    Parameters
    ----------
    df : DataFrame
        Existing date-indexed financial(-ish) table to overlay onto.
    waerlst_path : path
        Path to ``WAERLST Index.xlsx`` (real Bloomberg single-index sheet).
    bshieldt_path : path
        Path to ``BSHIELDT Index.xlsx`` (real Bloomberg single-index sheet).

    Returns
    -------
    DataFrame
        Copy of ``df`` with old BSHIELDT recon columns renamed and the
        new real WAERLST/BSHIELDT return, level, and volume columns
        left-joined in on the date index.
    """
    out = df.copy()

    rename_map = {
        "BSHIELDT": "BSHIELDT_recon",
        "r_BSHIELDT": "r_BSHIELDT_recon",
        "r_BSHIELDT_msadj": "r_BSHIELDT_recon_msadj",
    }
    rename_map = {k: v for k, v in rename_map.items() if k in out.columns}
    out = out.rename(columns=rename_map)

    waer_raw = load_bloomberg_index_xlsx(waerlst_path)
    bsh_raw = load_bloomberg_index_xlsx(bshieldt_path)

    waer_feat = compute_index_returns_and_volume(waer_raw, "WAERLST")
    bsh_feat = compute_index_returns_and_volume(bsh_raw, "BSHIELDT")

    merged = waer_feat.join(bsh_feat, how="outer")
    out = out.join(merged, how="left")

    return out


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
