"""
Script 02 — Market Model & Abnormal Returns
============================================
Computes daily log returns for all firms and benchmarks.
Estimates CAPM market model on the pre-invasion estimation window.
Outputs abnormal returns (AR) for the full event window.

Estimation window : 2020-01-01 to 2022-01-24  (~530 trading days)
Event window      : 2022-02-24 onwards
Benchmarks        : SPX (US firms), SXXP (Europe), MSCI_World (Other/Asia)

Outputs:
  data/processed/returns_daily.csv       — all firms + benchmarks, log returns
  data/processed/market_model_params.csv — alpha, beta, R2 per firm
  data/processed/abnormal_returns.csv    — date, ticker, AR_it, R_it, R_bench
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC  = os.path.join(BASE, "data", "processed")

PRICES_FILE = os.path.join(PROC, "prices_daily.csv")
BENCH_FILE  = os.path.join(PROC, "benchmarks_daily.csv")
FIRMS_FILE  = os.path.join(PROC, "firms_metadata.csv")

# Windows
EST_START = pd.Timestamp("2020-01-01")
EST_END   = pd.Timestamp("2022-01-24")   # last day before pre-invasion period
EVENT_START = pd.Timestamp("2022-02-24") # invasion date

MIN_OBS_ESTIMATION = 100  # minimum trading days to estimate model

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
print("Loading data...")
prices = pd.read_csv(PRICES_FILE, parse_dates=["date"])
bench  = pd.read_csv(BENCH_FILE,  parse_dates=["date"])
firms  = pd.read_csv(FIRMS_FILE)

print(f"  Prices: {len(prices):,} rows, {prices['ticker'].nunique()} firms")
print(f"  Benchmarks: {len(bench):,} rows")

# ─────────────────────────────────────────────
# COMPUTE LOG RETURNS — FIRMS
# ─────────────────────────────────────────────
print("Computing firm log returns...")
prices = prices.sort_values(["ticker", "date"]).reset_index(drop=True)

# Keep only trading days (drop zeros/negatives which are data errors)
prices = prices[prices["price"] > 0]

# Log return within each ticker group
prices["log_return"] = prices.groupby("ticker")["price"].transform(
    lambda s: np.log(s).diff()
)
prices = prices.dropna(subset=["log_return"])

# Winsorise at 1% / 99% to remove data errors (e.g., -100% or +1000%)
low  = prices["log_return"].quantile(0.001)
high = prices["log_return"].quantile(0.999)
prices["log_return"] = prices["log_return"].clip(low, high)

print(f"  Returns: {len(prices):,} rows after removing NaN")

# ─────────────────────────────────────────────
# COMPUTE LOG RETURNS — BENCHMARKS
# ─────────────────────────────────────────────
print("Computing benchmark log returns...")
bench = bench.sort_values("date").reset_index(drop=True)

bench_price_cols = ["SPX", "SXXP", "Brent", "MSCI_World"]
bench_level_cols = ["VIX", "EURUSD"]   # these stay as levels, not returns

for col in bench_price_cols:
    bench[f"r_{col}"] = np.log(bench[col]).diff()

# VIX: use simple diff (level change), EURUSD: log return
bench["d_VIX"]    = bench["VIX"].diff()
bench["r_EURUSD"] = np.log(bench["EURUSD"]).diff()

# Forward-fill benchmark on non-trading days (e.g. US holiday but EU open)
bench_returns = bench[["date",
                        "r_SPX", "r_SXXP", "r_Brent", "r_MSCI_World",
                        "d_VIX", "r_EURUSD", "VIX", "EURUSD"]].copy()

# Fill NaN benchmark returns on weekends/holidays with 0
# (will be merged and filtered to firm trading days anyway)
for col in ["r_SPX", "r_SXXP", "r_Brent", "r_MSCI_World", "d_VIX", "r_EURUSD"]:
    bench_returns[col] = bench_returns[col].fillna(0)

# ─────────────────────────────────────────────
# ASSIGN BENCHMARK PER FIRM
# ─────────────────────────────────────────────
def get_benchmark_col(region):
    if region == "US":
        return "r_SPX"
    elif region == "Europe":
        return "r_SXXP"
    else:
        return "r_MSCI_World"

firm_region = firms.set_index("ticker")["region"].to_dict()

# ─────────────────────────────────────────────
# MERGE PRICES WITH BENCHMARKS
# ─────────────────────────────────────────────
print("Merging prices with benchmarks...")
panel = prices.merge(bench_returns, on="date", how="left")
panel["region"] = panel["ticker"].map(firm_region)
panel["benchmark_col"] = panel["region"].apply(get_benchmark_col)

# Extract the correct benchmark return per row
panel["r_market"] = panel.apply(
    lambda row: row[row["benchmark_col"]], axis=1
)

# ─────────────────────────────────────────────
# ESTIMATE MARKET MODEL PER FIRM
# (OLS on estimation window only)
# ─────────────────────────────────────────────
print("Estimating market model (CAPM) per firm...")

est_data = panel[
    (panel["date"] >= EST_START) &
    (panel["date"] <= EST_END)
].copy()

results = []

for ticker, grp in est_data.groupby("ticker"):
    grp = grp.dropna(subset=["log_return", "r_market"])
    n = len(grp)
    if n < MIN_OBS_ESTIMATION:
        print(f"  SKIP {ticker}: only {n} obs in estimation window")
        continue

    y = grp["log_return"].values
    x = grp["r_market"].values

    # OLS: y = alpha + beta*x + e
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    results.append({
        "ticker":    ticker,
        "alpha":     intercept,
        "beta":      slope,
        "r_squared": r_value ** 2,
        "beta_pval": p_value,
        "n_obs":     n,
        "region":    grp["region"].iloc[0],
        "benchmark": grp["benchmark_col"].iloc[0]
    })

params = pd.DataFrame(results)
print(f"  Market model estimated for {len(params)} firms")
print(f"  Median R2: {params['r_squared'].median():.3f}")
print(f"  Median beta: {params['beta'].median():.3f}")

# Flag any betas that seem unreliable
low_r2 = params[params["r_squared"] < 0.05]
if len(low_r2) > 0:
    print(f"  WARNING: {len(low_r2)} firms with R2 < 0.05 (noisy model):")
    print("   ", low_r2["ticker"].tolist())

# ─────────────────────────────────────────────
# COMPUTE ABNORMAL RETURNS
# AR_it = R_it - (alpha_i + beta_i * R_market_t)
# ─────────────────────────────────────────────
print("Computing abnormal returns...")

# Merge params into full panel
panel = panel.merge(
    params[["ticker", "alpha", "beta"]],
    on="ticker", how="left"
)

# Keep only firms for which we estimated the model
panel = panel.dropna(subset=["alpha", "beta"])

# Predicted return
panel["predicted_return"] = panel["alpha"] + panel["beta"] * panel["r_market"]

# Abnormal return
panel["AR"] = panel["log_return"] - panel["predicted_return"]

# ─────────────────────────────────────────────
# SPLIT INTO OUTPUTS
# ─────────────────────────────────────────────

# 1. Full returns panel (estimation + event window)
returns_cols = ["date", "ticker", "log_return", "r_market",
                "r_Brent", "d_VIX", "r_EURUSD", "VIX",
                "region", "benchmark_col"]
returns_out = panel[returns_cols].copy()

# 2. Abnormal returns — event window only
ar_out = panel[panel["date"] >= EVENT_START][
    ["date", "ticker", "AR", "log_return", "r_market",
     "r_Brent", "d_VIX", "r_EURUSD", "VIX", "region"]
].copy()
ar_out = ar_out.sort_values(["ticker", "date"]).reset_index(drop=True)

print(f"  Total AR obs: {len(ar_out):,}")
print(f"  Date range:   {ar_out['date'].min().date()} to {ar_out['date'].max().date()}")
print(f"  Unique firms: {ar_out['ticker'].nunique()}")

# Quick sanity: mean AR should be close to 0 over the full period
print(f"  Mean AR: {ar_out['AR'].mean():.6f}  (should be near 0)")
print(f"  Std AR:  {ar_out['AR'].std():.4f}")

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
params_out_path  = os.path.join(PROC, "market_model_params.csv")
returns_out_path = os.path.join(PROC, "returns_daily.csv")
ar_out_path      = os.path.join(PROC, "abnormal_returns.csv")

params.to_csv(params_out_path, index=False)
returns_out.to_csv(returns_out_path, index=False)
ar_out.to_csv(ar_out_path, index=False)

print(f"\nSaved market_model_params.csv  — {len(params)} firms")
print(f"Saved returns_daily.csv        — {len(returns_out):,} rows")
print(f"Saved abnormal_returns.csv     — {len(ar_out):,} rows")
print("\nScript 02 complete.")
