"""
Script 09 - Panel Data Merge
==============================
Merges all processed data sources into a single firm-day panel dataset
ready for econometric analysis.

Panel structure: firm i x trading day t
Index: (ticker, date)

Variable groups:
  Outcome:      AR_it   - abnormal return from CAPM market model
  Channel 1:    WI_*_t  - UAF weapon intensity (drone/cruise/ballistic/total)
                IR_*_t  - UAF interception rate
  Channel 2:    GEI_t   - GPR-based geopolitical expectation index
                GPRD_t, GPRD_ACT_t, GPRD_THREAT_t - GPR components
  Channel 3:    WI_ACLED_t     - ACLED conflict intensity
                log_ukraine_war_t - GDELT media volume (if available)
  Moderator:    arms_share_i   - SIPRI composite defense exposure (0-1)
  Controls:     log_mcap_it    - log market cap (time-varying)
                VIX_t          - CBOE VIX
                log_brent_t    - Brent crude oil price (log)
                dlog_EURUSD_t  - EUR/USD daily change

  Interactions (key cross-sectional predictions):
    WI_total_t x arms_share_i
    GEI_t x arms_share_i
    IR_total_t x arms_share_i
    WI_drone_t x arms_share_i

Analysis windows:
  Main regressions: Oct 1, 2022 - Jun 4, 2026  (UAF data available from Oct 2022)
  Event study:      Feb 24, 2022 - Jun 4, 2026

Outputs:
  data/processed/panel_full.csv    - all firms, full date range
  data/processed/panel_main.csv    - 100 firms, Oct 2022 - Jun 2026, non-missing
  data/processed/panel_useu.csv    - US+Europe firms only (main subsample)
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")

# Analysis windows
MAIN_START  = pd.Timestamp("2022-10-01")   # UAF data starts Oct 2022
MAIN_END    = pd.Timestamp("2026-06-04")
EVENT_START = pd.Timestamp("2022-02-24")   # Invasion date

print("=" * 60)
print("Script 09 - Panel Data Merge")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# 1. LOAD ALL PROCESSED DATA
# ─────────────────────────────────────────────────────────────
print("\n[1/7] Loading processed data files...")

ar = pd.read_csv(os.path.join(PROC, "abnormal_returns.csv"), parse_dates=["date"])
uaf = pd.read_csv(os.path.join(PROC, "uaf_daily.csv"), parse_dates=["date"])
gpr = pd.read_csv(os.path.join(PROC, "gpr_daily.csv"), parse_dates=["date"])
acled = pd.read_csv(os.path.join(PROC, "acled_daily.csv"), parse_dates=["date"])
sipri = pd.read_csv(os.path.join(PROC, "sipri_exposure.csv"))
size = pd.read_csv(os.path.join(PROC, "size_daily.csv"), parse_dates=["date"])
bench = pd.read_csv(os.path.join(PROC, "benchmarks_daily.csv"), parse_dates=["date"])
firms_meta = pd.read_csv(os.path.join(PROC, "firms_metadata.csv"))

gdelt_path = os.path.join(PROC, "gdelt_topics_daily.csv")
gdelt_available = os.path.exists(gdelt_path)
if gdelt_available:
    gdelt = pd.read_csv(gdelt_path, parse_dates=["date"])
    print(f"  GDELT topics: {len(gdelt)} rows - LOADED")
else:
    print("  GDELT topics: NOT available (will use GPR only for media channel)")

print(f"  Abnormal returns: {len(ar):,} rows, {ar['ticker'].nunique()} firms")
print(f"  UAF daily:        {len(uaf):,} rows")
print(f"  GPR daily:        {len(gpr):,} rows")
print(f"  ACLED daily:      {len(acled):,} rows")
print(f"  SIPRI exposure:   {len(sipri)} firms")
print(f"  Size daily:       {len(size):,} rows")
print(f"  Benchmarks:       {len(bench):,} rows")

# ─────────────────────────────────────────────────────────────
# 2. PREPARE FIRM METADATA (moderators + region)
# ─────────────────────────────────────────────────────────────
print("\n[2/7] Preparing firm-level moderators...")

# Merge SIPRI exposure into firms metadata
# Note: AR already carries 'region'; drop duplicates before merging
firm_vars = firms_meta[["ticker", "currency", "bics_industry", "index_membership"]].copy()
sipri_cols = ["ticker", "arms_share_composite", "arms_share_norm",
              "arms_share_source", "in_sipri_top100", "arms_share_avg",
              "arms_rev_avg", "sipri_company"]
sipri_sub = sipri[[c for c in sipri_cols if c in sipri.columns]].copy()
firm_vars = firm_vars.merge(sipri_sub, on="ticker", how="left")

# Arms share as percentage for display
firm_vars["arms_pct"] = firm_vars["arms_share_composite"] * 100

print(f"  Firm-level vars: {len(firm_vars)} rows")
print(f"  SIPRI measured: {(firm_vars['arms_share_source'] == 'SIPRI_measured').sum()}")

# ─────────────────────────────────────────────────────────────
# 3. PREPARE BENCHMARK CONTROLS
# ─────────────────────────────────────────────────────────────
print("\n[3/7] Preparing market-level controls...")

bench = bench.sort_values("date").reset_index(drop=True)

# Convert to numeric
for col in ["VIX", "Brent", "EURUSD", "SPX", "SXXP", "MSCI_World"]:
    if col in bench.columns:
        bench[col] = pd.to_numeric(bench[col], errors="coerce")

# Log Brent + daily change
bench["log_brent"] = np.log(bench["Brent"].clip(lower=0.01))
bench["dlog_brent"] = bench["log_brent"].diff()

# Log VIX
bench["log_vix"] = np.log(bench["VIX"].clip(lower=0.01))
bench["dvix"] = bench["VIX"].diff()

# EUR/USD daily pct change
bench["dlog_EURUSD"] = np.log(bench["EURUSD"].clip(lower=0.01)).diff()

# Weekly VIX change (for event study windows)
bench["VIX_MA5"] = bench["VIX"].rolling(5, min_periods=1).mean()

# Note: AR already carries 'VIX' and 'r_Brent','r_EURUSD' from market model —
# only add the derived log/diff versions plus raw Brent/EURUSD not in AR
bench_cols = ["date", "log_vix", "dvix", "Brent", "log_brent", "dlog_brent",
              "EURUSD", "dlog_EURUSD"]
bench_clean = bench[bench_cols].copy()

print(f"  Benchmark controls: {bench_clean.columns.tolist()}")

# ─────────────────────────────────────────────────────────────
# 4. PREPARE TIME-SERIES CONFLICT VARIABLES
# ─────────────────────────────────────────────────────────────
print("\n[4/7] Preparing time-series conflict variables...")

# --- UAF variables ---
uaf = uaf.sort_values("date").reset_index(drop=True)
uaf_cols = [c for c in uaf.columns if c != "Unnamed: 0"]
uaf = uaf[uaf_cols]

# Lag variables (t-1) to prevent look-ahead in regressions
for col in ["WI_total", "WI_drone", "WI_cruise", "WI_ballistic",
            "IR_total", "IR_drone", "IR_cruise", "IR_ballistic"]:
    if col in uaf.columns:
        uaf[f"{col}_lag1"] = uaf[col].shift(1)

# Rolling 5-day average (medium-term intensity)
for col in ["WI_total", "WI_drone", "IR_total"]:
    if col in uaf.columns:
        uaf[f"{col}_ma5"] = uaf[col].rolling(5, min_periods=1).mean()

print(f"  UAF columns: {[c for c in uaf.columns if c != 'date']}")

# --- GPR variables ---
gpr = gpr.sort_values("date").reset_index(drop=True)
gpr_cols = ["date", "GPRD", "GPRD_ACT", "GPRD_THREAT",
            "log_GPRD", "log_GPRD_ACT", "log_GPRD_THREAT",
            "GEI", "GPRD_MA7", "GPRD_MA30", "GPRC_UKR", "GPRC_RUS"]
gpr_cols = [c for c in gpr_cols if c in gpr.columns]
gpr_clean = gpr[gpr_cols].copy()

# GEI change (first difference of expectations)
gpr_clean["dGEI"] = gpr_clean["GEI"].diff()
gpr_clean["GEI_lag1"] = gpr_clean["GEI"].shift(1)

# --- ACLED variables ---
acled = acled.sort_values("date").reset_index(drop=True)
acled_cols = [c for c in acled.columns if c != "Unnamed: 0"]
acled_clean = acled[acled_cols].copy() if acled_cols else acled.copy()

print(f"  GPR columns: {gpr_cols}")
acled_basic = [c for c in ["date", "WI_ACLED", "WI_ACLED_severity",
                            "WI_ACLED_drone", "WI_ACLED_shelling",
                            "WI_ACLED_armed"] if c in acled.columns]
print(f"  ACLED columns: {acled_basic}")

# --- GDELT (if available) ---
if gdelt_available:
    gdelt = gdelt.sort_values("date").reset_index(drop=True)
    gdelt_cols_use = ["date", "ukraine_war", "rearmament", "defense_spending",
                      "air_defense", "log_ukraine_war", "log_defense_spending",
                      "log_air_defense"]
    gdelt_cols_use = [c for c in gdelt_cols_use if c in gdelt.columns]

# ─────────────────────────────────────────────────────────────
# 5. BUILD FULL FIRM-DAY PANEL
# ─────────────────────────────────────────────────────────────
print("\n[5/7] Building firm-day panel...")

# Start with abnormal returns as the base
panel = ar.copy()
panel = panel.rename(columns={"abnormal_return": "AR",
                               "alpha": "model_alpha",
                               "beta": "model_beta"})

print(f"  AR base: {len(panel):,} rows, {panel['ticker'].nunique()} firms")
print(f"  Date range: {panel['date'].min().date()} to {panel['date'].max().date()}")

# --- Merge size (market cap) ---
size_merge = size[["date", "ticker", "market_cap_musd", "log_market_cap"]].copy()
panel = panel.merge(size_merge, on=["date", "ticker"], how="left")

# --- Merge firm-level moderators (static join) ---
panel = panel.merge(firm_vars, on="ticker", how="left")

# --- Merge market benchmarks ---
panel = panel.merge(bench_clean, on="date", how="left")

# --- Merge UAF variables ---
uaf_merge = uaf[["date"] + [c for c in uaf.columns if c != "date"]].copy()
panel = panel.merge(uaf_merge, on="date", how="left")

# --- Merge GPR variables ---
panel = panel.merge(gpr_clean, on="date", how="left")

# --- Merge ACLED variables ---
acled_merge = acled[[c for c in acled_basic]] if acled_basic else pd.DataFrame(columns=["date"])
if "date" in acled_merge.columns:
    panel = panel.merge(acled_merge, on="date", how="left")

# --- Merge GDELT (if available) ---
if gdelt_available and gdelt_cols_use:
    gdelt_merge = gdelt[gdelt_cols_use].copy()
    panel = panel.merge(gdelt_merge, on="date", how="left")

print(f"  Panel after merges: {len(panel):,} rows, {panel['ticker'].nunique()} firms")

# ─────────────────────────────────────────────────────────────
# 6. CREATE INTERACTION TERMS & DERIVED VARIABLES
# ─────────────────────────────────────────────────────────────
print("\n[6/7] Creating interaction terms...")

# Key interaction: weapons intensity x defense exposure
for wi_col in ["WI_total", "WI_drone", "WI_cruise", "WI_ballistic",
               "WI_total_lag1", "WI_drone_lag1"]:
    if wi_col in panel.columns:
        panel[f"{wi_col}_x_arms"] = panel[wi_col] * panel["arms_share_composite"]

# GPR expectation x defense exposure
for gei_col in ["GEI", "GEI_lag1", "dGEI", "log_GPRD_THREAT"]:
    if gei_col in panel.columns:
        panel[f"{gei_col}_x_arms"] = panel[gei_col] * panel["arms_share_composite"]

# Interception rate x defense exposure
for ir_col in ["IR_total", "IR_drone"]:
    if ir_col in panel.columns:
        panel[f"{ir_col}_x_arms"] = panel[ir_col] * panel["arms_share_composite"]

# ACLED x defense exposure
for acled_col in ["WI_ACLED", "WI_ACLED_severity"]:
    if acled_col in panel.columns:
        panel[f"{acled_col}_x_arms"] = panel[acled_col] * panel["arms_share_composite"]

# Binary indicators
panel["is_us"] = (panel["region"] == "US").astype(int)
panel["is_europe"] = (panel["region"] == "Europe").astype(int)
panel["is_sipri"] = (panel["arms_share_source"] == "SIPRI_measured").astype(int)
panel["is_useu"] = panel["region"].isin(["US", "Europe"]).astype(int)

# Post-invasion indicator
panel["post_invasion"] = (panel["date"] >= pd.Timestamp("2022-02-24")).astype(int)

# Weekly numbering (for clustering)
panel["week"] = panel["date"].dt.to_period("W").dt.start_time

print(f"  Interaction terms created: {[c for c in panel.columns if '_x_arms' in c]}")

# ─────────────────────────────────────────────────────────────
# 7. CREATE ANALYSIS SUBSETS & SAVE
# ─────────────────────────────────────────────────────────────
print("\n[7/7] Creating analysis subsets and saving...")

# Full panel (all firms, full date range)
panel_full = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
panel_full.to_csv(os.path.join(PROC, "panel_full.csv"), index=False)
print(f"  panel_full.csv:   {len(panel_full):,} rows")

# Main analysis panel: post-UAF period, non-missing AR
panel_main = panel_full[
    (panel_full["date"] >= MAIN_START) &
    (panel_full["date"] <= MAIN_END) &
    panel_full["AR"].notna()
].copy()
panel_main.to_csv(os.path.join(PROC, "panel_main.csv"), index=False)
print(f"  panel_main.csv:   {len(panel_main):,} rows  "
      f"({panel_main['ticker'].nunique()} firms, "
      f"{panel_main['date'].nunique()} days)")

# US+Europe subsample (for main regressions)
panel_useu = panel_main[panel_main["is_useu"] == 1].copy()
panel_useu.to_csv(os.path.join(PROC, "panel_useu.csv"), index=False)
print(f"  panel_useu.csv:   {len(panel_useu):,} rows  "
      f"({panel_useu['ticker'].nunique()} firms)")

# Event study panel (from Feb 24, 2022)
panel_event = panel_full[
    (panel_full["date"] >= EVENT_START) &
    panel_full["AR"].notna()
].copy()
panel_event.to_csv(os.path.join(PROC, "panel_event.csv"), index=False)
print(f"  panel_event.csv:  {len(panel_event):,} rows  "
      f"({panel_event['ticker'].nunique()} firms)")

# ─────────────────────────────────────────────────────────────
# 8. COVERAGE REPORT
# ─────────────────────────────────────────────────────────────
print("\n--- Coverage Report ---")
print(f"Main panel: {panel_main['ticker'].nunique()} firms x "
      f"{panel_main['date'].nunique()} trading days")
print(f"  US firms:     {panel_main[panel_main['is_us']==1]['ticker'].nunique()}")
print(f"  Europe firms: {panel_main[panel_main['is_europe']==1]['ticker'].nunique()}")
print(f"  Other firms:  {panel_main[panel_main['is_useu']==0]['ticker'].nunique()}")

# Variable completeness for main panel
key_vars = ["AR", "WI_total", "GEI", "arms_share_composite",
            "log_market_cap", "VIX", "log_brent"]
print("\nVariable completeness (main panel):")
for var in key_vars:
    if var in panel_main.columns:
        pct = panel_main[var].notna().mean() * 100
        print(f"  {var:25s}: {pct:5.1f}%")

# Average arms_share by region
if "region" in panel_main.columns:
    print("\nMean arms_share_composite by region (main panel):")
    reg_arms = panel_main.groupby("region")["arms_share_composite"].mean()
    print(reg_arms.round(3).to_dict())

# Summary stats for main variables
print("\nKey variable summary (main panel):")
summary_vars = ["AR", "WI_total", "WI_drone", "GEI", "IR_total",
                "arms_share_composite", "log_market_cap"]
summary_vars = [v for v in summary_vars if v in panel_main.columns]
desc = panel_main[summary_vars].describe().T[["mean", "std", "min", "max"]]
print(desc.round(4).to_string())

print("\nScript 09 complete.")
