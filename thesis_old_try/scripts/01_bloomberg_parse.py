"""
Script 01 — Bloomberg Parse
===========================
Reads WAERLST and BSHIELDT 'values only' sheets plus indexes.xlsx.
Outputs:
  data/processed/firms_metadata.csv   — one row per firm
  data/processed/prices_daily.csv     — long format: date × ticker × price
  data/processed/benchmarks_daily.csv — date × benchmark prices
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_BB  = os.path.join(BASE, "data", "raw", "bloomberg")
PROC    = os.path.join(BASE, "data", "processed")
os.makedirs(PROC, exist_ok=True)

WAERLST_FILE = os.path.join(RAW_BB, "WAERLST as of Jun 04 2026.xlsx")
BSHIELDT_FILE = os.path.join(RAW_BB, "BSHIELDT as of Jun 05 2026.xlsx")
INDEXES_FILE  = os.path.join(RAW_BB, "indexes.xlsx")

# Metadata row labels as they appear in column 0 (rows 0–9)
META_LABELS = ["Ticker", "Name", "Weight", "Shares", "Price",
               "NAME", "COUNTRY", "CRNCY", "CUR_MKT_CAP",
               "BICS_LEVEL_3_INDUSTRY_NAME"]
N_META = len(META_LABELS)  # = 10; price data starts at row 10


# ─────────────────────────────────────────────
# HELPER: parse one Bloomberg 'values only' sheet
# ─────────────────────────────────────────────
def parse_bloomberg_sheet(filepath, index_name):
    """
    Returns:
      meta_df  : DataFrame [ticker, Name, Weight, ..., index_source]
      prices_df: DataFrame [date, ticker, price]
    """
    df = pd.read_excel(filepath, sheet_name="values only", header=None)

    # ── Metadata (rows 0 .. N_META-1, columns 1..)
    meta_dict = {}
    for i, label in enumerate(META_LABELS):
        row_vals = df.iloc[i, 1:].values          # skip col-0 label
        meta_dict[label] = row_vals

    meta_df = pd.DataFrame(meta_dict)
    meta_df.rename(columns={"Ticker": "ticker",
                             "Name": "name_short",
                             "NAME": "name_full",
                             "COUNTRY": "country",
                             "CRNCY": "currency",
                             "CUR_MKT_CAP": "mktcap",
                             "BICS_LEVEL_3_INDUSTRY_NAME": "bics_industry",
                             "Weight": "index_weight",
                             "Shares": "shares",
                             "Price": "current_price"}, inplace=True)

    # Drop columns where ticker is missing / NaN
    meta_df = meta_df.dropna(subset=["ticker"])
    meta_df["ticker"] = meta_df["ticker"].astype(str).str.strip()
    meta_df = meta_df[meta_df["ticker"] != "nan"]
    meta_df["index_source"] = index_name
    meta_df = meta_df.reset_index(drop=True)

    valid_tickers = meta_df["ticker"].tolist()

    # ── Prices (rows N_META onward)
    prices_raw = df.iloc[N_META:, :].copy()
    prices_raw.columns = ["date"] + df.iloc[0, 1:].tolist()
    prices_raw["date"] = pd.to_datetime(prices_raw["date"], errors="coerce")
    prices_raw = prices_raw.dropna(subset=["date"])

    # Keep only columns that are valid tickers
    keep_cols = ["date"] + [c for c in prices_raw.columns[1:]
                             if str(c).strip() in valid_tickers]
    prices_raw = prices_raw[keep_cols]

    # Melt to long format
    prices_long = prices_raw.melt(id_vars="date", var_name="ticker", value_name="price")
    prices_long["ticker"] = prices_long["ticker"].astype(str).str.strip()
    prices_long["price"] = pd.to_numeric(prices_long["price"], errors="coerce")

    # Drop rows with missing price (weekends / non-trading days)
    prices_long = prices_long.dropna(subset=["price"])
    prices_long = prices_long.sort_values(["ticker", "date"]).reset_index(drop=True)

    return meta_df, prices_long


# ─────────────────────────────────────────────
# PARSE BOTH BLOOMBERG FILES
# ─────────────────────────────────────────────
print("Parsing WAERLST...")
meta_w, prices_w = parse_bloomberg_sheet(WAERLST_FILE, "WAERLST")
print(f"  WAERLST: {len(meta_w)} firms, {len(prices_w):,} price rows")

print("Parsing BSHIELDT...")
meta_b, prices_b = parse_bloomberg_sheet(BSHIELDT_FILE, "BSHIELDT")
print(f"  BSHIELDT: {len(meta_b)} firms, {len(prices_b):,} price rows")


# ─────────────────────────────────────────────
# MERGE METADATA — firms can appear in both indices
# ─────────────────────────────────────────────
# Mark index membership
waerlst_tickers  = set(meta_w["ticker"])
bshieldt_tickers = set(meta_b["ticker"])
both             = waerlst_tickers & bshieldt_tickers

# Primary metadata: WAERLST first, supplement BSHIELDT-only firms
meta_all = pd.concat([meta_w, meta_b], ignore_index=True)

# Build clean index membership column
def get_membership(ticker):
    in_w = ticker in waerlst_tickers
    in_b = ticker in bshieldt_tickers
    if in_w and in_b:
        return "WAERLST+BSHIELDT"
    elif in_w:
        return "WAERLST"
    else:
        return "BSHIELDT"

# Drop duplicate tickers (keep first occurrence = WAERLST)
meta_all = meta_all.drop_duplicates(subset=["ticker"], keep="first").copy()
meta_all["index_membership"] = meta_all["ticker"].apply(get_membership)
meta_all = meta_all.drop(columns=["index_source"])

# Assign region for benchmark selection
def assign_region(row):
    ccy = str(row.get("currency", "")).strip().upper()
    ctry = str(row.get("country", "")).strip().upper()
    if ccy == "USD":
        return "US"
    elif ccy in ("EUR", "GBP", "GBX", "GBP", "SEK", "NOK", "DKK", "CHF", "PLN"):
        return "Europe"
    elif ccy in ("CNY", "CNH", "HKD"):
        return "Asia"
    else:
        return "Other"

meta_all["region"] = meta_all.apply(assign_region, axis=1)

print(f"\nCombined: {len(meta_all)} unique firms")
print("  Index membership:\n", meta_all["index_membership"].value_counts().to_dict())
print("  Currency breakdown:\n", meta_all["currency"].value_counts().to_dict())
print("  Region breakdown:\n", meta_all["region"].value_counts().to_dict())


# ─────────────────────────────────────────────
# MERGE PRICES — deduplicate same ticker from both files
# ─────────────────────────────────────────────
prices_all = pd.concat([prices_w, prices_b], ignore_index=True)
# For tickers in both files, keep the WAERLST version (drop BSHIELDT duplicate dates)
prices_all = prices_all.sort_values(["ticker", "date"])
prices_all = prices_all.drop_duplicates(subset=["ticker", "date"], keep="first")
prices_all = prices_all.reset_index(drop=True)

print(f"\nCombined prices: {len(prices_all):,} rows")
print(f"  Date range: {prices_all['date'].min().date()} to {prices_all['date'].max().date()}")
print(f"  Unique tickers: {prices_all['ticker'].nunique()}")

# Sanity check: any ticker in metadata missing from prices?
tickers_meta   = set(meta_all["ticker"])
tickers_prices = set(prices_all["ticker"])
missing_prices = tickers_meta - tickers_prices
if missing_prices:
    print(f"\n  WARNING: {len(missing_prices)} tickers in metadata have no prices: {missing_prices}")


# ─────────────────────────────────────────────
# PARSE BENCHMARKS (indexes.xlsx)
# ─────────────────────────────────────────────
print("\nParsing benchmarks (indexes.xlsx)...")
df_idx = pd.read_excel(INDEXES_FILE, sheet_name="values only", header=None)

# Row 0 has benchmark tickers: SPX Index, SXXP Index, VIX Index, CO1 Comdty, EURUSD Curncy, NDDUWI Index
bench_tickers = df_idx.iloc[0, 1:].tolist()

# Price data starts at row N_META
bench_prices = df_idx.iloc[N_META:, :].copy()
bench_prices.columns = ["date"] + bench_tickers
bench_prices["date"] = pd.to_datetime(bench_prices["date"], errors="coerce")
bench_prices = bench_prices.dropna(subset=["date"])
bench_prices = bench_prices.reset_index(drop=True)

# Convert benchmark columns to numeric
for col in bench_tickers:
    bench_prices[col] = pd.to_numeric(bench_prices[col], errors="coerce")

# Clean column names
bench_prices.rename(columns={
    "SPX Index":     "SPX",
    "SXXP Index":    "SXXP",
    "VIX Index":     "VIX",
    "CO1 Comdty":    "Brent",
    "EURUSD Curncy": "EURUSD",
    "NDDUWI Index":  "MSCI_World"
}, inplace=True)

print(f"  Benchmarks shape: {bench_prices.shape}")
print(f"  Date range: {bench_prices['date'].min().date()} to {bench_prices['date'].max().date()}")
print(f"  Columns: {bench_prices.columns.tolist()}")
missing_bench = bench_prices.isnull().sum()
print(f"  Missing values:\n{missing_bench[missing_bench > 0]}")


# ─────────────────────────────────────────────
# SAVE OUTPUTS
# ─────────────────────────────────────────────
firms_out = os.path.join(PROC, "firms_metadata.csv")
prices_out = os.path.join(PROC, "prices_daily.csv")
bench_out  = os.path.join(PROC, "benchmarks_daily.csv")

meta_all.to_csv(firms_out, index=False)
prices_all.to_csv(prices_out, index=False)
bench_prices.to_csv(bench_out, index=False)

print(f"\nSaved firms_metadata.csv    — {len(meta_all)} firms")
print(f"Saved prices_daily.csv      — {len(prices_all):,} rows")
print(f"Saved benchmarks_daily.csv  — {len(bench_prices):,} rows")
print("\nScript 01 complete.")
