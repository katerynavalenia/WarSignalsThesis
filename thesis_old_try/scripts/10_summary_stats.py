"""
Script 10 - Summary Statistics
================================
Produces Table 1 (summary stats), Table 2 (correlation matrix),
and variable description table for the thesis.

Outputs:
  output/tables/table1_summary_stats.csv
  output/tables/table2_correlations.csv
  output/tables/table3_firms_list.csv
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC  = os.path.join(BASE, "data", "processed")
TABS  = os.path.join(BASE, "output", "tables")
os.makedirs(TABS, exist_ok=True)

print("=" * 60)
print("Script 10 - Summary Statistics")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
panel = pd.read_csv(os.path.join(PROC, "panel_main.csv"), parse_dates=["date"])
firms = pd.read_csv(os.path.join(PROC, "firms_metadata.csv"))
sipri = pd.read_csv(os.path.join(PROC, "sipri_exposure.csv"))

print(f"Main panel: {len(panel):,} rows, {panel['ticker'].nunique()} firms")

# Normalize arms_share to 0-1 for display
panel["arms_share_01"] = panel["arms_share_composite"] / 100.0

# ─────────────────────────────────────────────────────────────
# TABLE 1 — Summary statistics for main variables
# ─────────────────────────────────────────────────────────────
VAR_LABELS = {
    "AR":                    "Abnormal Return (AR_it)",
    "WI_total":              "Weapon Intensity — Total (WI_total_t)",
    "WI_drone":              "Weapon Intensity — Drone (WI_drone_t)",
    "WI_cruise":             "Weapon Intensity — Cruise Missile (WI_cruise_t)",
    "WI_ballistic":          "Weapon Intensity — Ballistic (WI_ballistic_t)",
    "IR_total":              "Interception Rate — Total (IR_total_t)",
    "GEI":                   "Geopolitical Expectation Index (GEI_t)",
    "GPRD_THREAT":           "GPR Threat Component (GPRD_THREAT_t)",
    "WI_ACLED":              "ACLED Conflict Intensity (WI_ACLED_t)",
    "arms_share_01":         "Defense Revenue Share (arms_share_i, 0-1)",
    "log_market_cap":        "Log Market Cap (log_mcap_it)",
    "VIX":                   "VIX (volatility index)",
    "log_brent":             "Log Brent Crude (log_brent_t)",
    "dlog_EURUSD":           "Delta Log EUR/USD",
}

rows = []
for var, label in VAR_LABELS.items():
    if var not in panel.columns:
        continue
    s = panel[var].dropna()
    rows.append({
        "Variable":   label,
        "N":          int(s.notna().sum()),
        "Mean":       round(s.mean(), 4),
        "Std Dev":    round(s.std(), 4),
        "Min":        round(s.min(), 4),
        "P25":        round(s.quantile(0.25), 4),
        "Median":     round(s.median(), 4),
        "P75":        round(s.quantile(0.75), 4),
        "Max":        round(s.max(), 4),
    })

tab1 = pd.DataFrame(rows)
tab1.to_csv(os.path.join(TABS, "table1_summary_stats.csv"), index=False)
print("\nTable 1 — Summary statistics:")
print(tab1[["Variable", "N", "Mean", "Std Dev", "Min", "Max"]].to_string(index=False))

# ─────────────────────────────────────────────────────────────
# TABLE 2 — Correlation matrix (key variables)
# ─────────────────────────────────────────────────────────────
corr_vars = ["AR", "WI_total", "WI_drone", "GEI", "IR_total",
             "arms_share_01", "log_market_cap", "VIX", "log_brent"]
corr_vars = [v for v in corr_vars if v in panel.columns]

# Use daily mean across firms for time-series correlations
daily = panel.groupby("date")[corr_vars].mean()
corr_matrix = daily.corr().round(3)
corr_matrix.to_csv(os.path.join(TABS, "table2_correlations.csv"))
print("\nTable 2 — Correlation matrix (daily averages):")
print(corr_matrix.to_string())

# ─────────────────────────────────────────────────────────────
# TABLE 3 — Firm list with defense exposure
# ─────────────────────────────────────────────────────────────
firm_info = firms.merge(sipri[["ticker", "arms_share_composite", "arms_share_source",
                                "sipri_company", "in_sipri_top100"]], 
                        on="ticker", how="left")
firm_info = firm_info[["ticker", "name_full", "region", "country", "currency",
                        "bics_industry", "index_membership",
                        "arms_share_composite", "arms_share_source",
                        "sipri_company", "in_sipri_top100"]].copy()
firm_info = firm_info.sort_values(["region", "arms_share_composite"], ascending=[True, False])
firm_info.to_csv(os.path.join(TABS, "table3_firms_list.csv"), index=False)
print(f"\nTable 3 — Firm list: {len(firm_info)} firms saved")
print(f"  SIPRI top-100 firms: {int(firm_info['in_sipri_top100'].sum())}")
print(f"  By region: {firm_info['region'].value_counts().to_dict()}")

# ─────────────────────────────────────────────────────────────
# TABLE 4 — Arms share distribution
# ─────────────────────────────────────────────────────────────
# Firm-level (one obs per firm)
firm_panel = panel.drop_duplicates("ticker")[["ticker", "region", "arms_share_composite",
                                               "arms_share_source", "is_sipri"]].copy()
print("\nArms share by region and source:")
grp = firm_panel.groupby(["region", "arms_share_source"])["arms_share_composite"]
print(grp.agg(["count", "mean", "std"]).round(2).to_string())

# Distribution quintiles of arms_share across firms
print("\nArms share quintile distribution across firms:")
qs = firm_panel["arms_share_composite"].describe(percentiles=[.2, .4, .6, .8]).round(1)
print(qs.to_dict())

print("\nScript 10 complete.")
