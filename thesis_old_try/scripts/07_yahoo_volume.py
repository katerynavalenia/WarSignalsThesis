"""
Script 07 — Market Cap & Size Control Variable
===============================================
Yahoo Finance is blocked by the corporate SSL proxy, so volume cannot be
downloaded. Instead, we compute daily market capitalisation from Bloomberg
data (already available): market_cap_it = price_it × shares_i.

This is a stronger size control than volume:
  - Uses the same source as prices (consistent)
  - Time-varying: price changes daily
  - log(market_cap) is the standard size control in panel finance regressions

Outputs:
  data/processed/size_daily.csv
    date, ticker, market_cap_musd, log_market_cap
    (market_cap in millions USD — converted via static FX from Bloomberg metadata)
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")

PRICES_FILE = os.path.join(PROC, "prices_daily.csv")
FIRMS_FILE  = os.path.join(PROC, "firms_metadata.csv")
BENCH_FILE  = os.path.join(PROC, "benchmarks_daily.csv")

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
print("Loading Bloomberg prices and metadata...")
prices = pd.read_csv(PRICES_FILE, parse_dates=["date"])
firms  = pd.read_csv(FIRMS_FILE)
bench  = pd.read_csv(BENCH_FILE,  parse_dates=["date"])

print(f"  Prices: {len(prices):,} rows")
print(f"  Firms:  {len(firms)} rows")

# ─────────────────────────────────────────────
# SHARES OUTSTANDING (static from Bloomberg metadata)
# Bloomberg reports shares in thousands — confirm unit
# ─────────────────────────────────────────────
firms["shares"] = pd.to_numeric(firms["shares"], errors="coerce")
# Bloomberg reports shares in MILLIONS — market_cap_musd = price × shares directly
# (price in USD × shares in millions = market cap in millions USD)
firms["shares_musd_divisor"] = 1.0   # no extra division needed

# ─────────────────────────────────────────────
# APPROXIMATE FX CONVERSION RATES (static, 2020-2026 average)
# For simplicity use approximate average rates — sufficient for size control
# ─────────────────────────────────────────────
FX_TO_USD = {
    "USD": 1.00,
    "EUR": 1.08,   # EUR/USD average ~1.08 over 2020-2026
    "GBp": 0.0125, # GBp (pence) to USD: ~0.0125 (1 GBp = 0.0125 USD)
    "GBP": 1.25,
    "CNY": 0.14,
    "CNH": 0.14,
    "INR": 0.012,
    "ILs": 0.27,   # Israeli Shekel
    "KRW": 0.00075,
    "CAD": 0.76,
    "AUD": 0.68,
    "TRY": 0.032,
    "SEK": 0.096,
    "NOK": 0.094,
    "HKD": 0.128,
    "TWD": 0.031,
    "BRL": 0.20,
    "SGD": 0.74,
    "JPY": 0.0067,
    "CHF": 1.10,
    "MYR": 0.22,
    "AED": 0.27,
}

# Add FX rate to firms
firms["fx_to_usd"] = firms["currency"].map(FX_TO_USD).fillna(1.0)

# ─────────────────────────────────────────────
# COMPUTE DAILY MARKET CAP
# market_cap_usd_t = price_t × shares × fx_to_usd
# ─────────────────────────────────────────────
print("Computing daily market cap...")

# Merge shares and FX into prices
shares_map = firms.set_index("ticker")["shares"].to_dict()
fx_map     = firms.set_index("ticker")["fx_to_usd"].to_dict()

prices["shares_musd"] = prices["ticker"].map(shares_map)
prices["fx_to_usd"]   = prices["ticker"].map(fx_map)

# market_cap_musd = price (local) × fx_to_usd × shares_millions
prices["market_cap_musd"] = prices["price"] * prices["fx_to_usd"] * prices["shares_musd"]

# Log market cap (main regression control)
prices["log_market_cap"] = np.log(prices["market_cap_musd"].clip(lower=0.001))

# Sanity check
mktcap_stats = prices.groupby("ticker")["market_cap_musd"].mean().sort_values(ascending=False)
print("\nTop 10 firms by average market cap (USD million):")
print(mktcap_stats.head(10).round(0).to_dict())
print("\nBottom 5 firms by average market cap:")
print(mktcap_stats.tail(5).round(0).to_dict())
print(f"\nMissing market_cap: {prices['market_cap_musd'].isna().sum()} rows")

# ─────────────────────────────────────────────
# ALSO COMPUTE DAILY EURUSD (for EUR-denominated firm returns)
# ─────────────────────────────────────────────
eurusd = bench[["date", "EURUSD"]].copy()
eurusd["EURUSD"] = pd.to_numeric(eurusd["EURUSD"], errors="coerce")
eurusd = eurusd.dropna(subset=["EURUSD"])

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
size_out = prices[["date", "ticker", "market_cap_musd", "log_market_cap"]].copy()
size_out = size_out.dropna(subset=["market_cap_musd"])
size_out = size_out.sort_values(["ticker", "date"]).reset_index(drop=True)

out_path = os.path.join(PROC, "size_daily.csv")
size_out.to_csv(out_path, index=False)

print(f"\nSaved size_daily.csv — {len(size_out):,} rows")
print(f"  Date range: {size_out['date'].min().date()} to {size_out['date'].max().date()}")
print(f"  Unique tickers: {size_out['ticker'].nunique()}")
print('Script 07 complete.')
