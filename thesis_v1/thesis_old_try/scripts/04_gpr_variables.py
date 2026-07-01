"""
Script 04 — GPR Variables
==========================
Extracts GPR daily series from XLS files.
Creates GEI_t (geopolitical expectations index) and component variables.

Outputs:
  data/processed/gpr_daily.csv
    date, GPRD, GPRD_ACT, GPRD_THREAT, GPRD_MA7, GPRD_MA30,
    GPRC_UKR, GPRC_RUS  (monthly, forward-filled to daily)
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BASE, "data", "raw", "gpr")
PROC = os.path.join(BASE, "data", "processed")

DAILY_FILE   = os.path.join(RAW, "data_gpr_daily_recent.xls")
MONTHLY_FILE = os.path.join(RAW, "data_gpr_export.xls")

# ─────────────────────────────────────────────
# LOAD GPR DAILY
# ─────────────────────────────────────────────
print("Loading GPR daily...")
gpr_d = pd.read_excel(DAILY_FILE)

print(f"  Raw shape: {gpr_d.shape}")
# The file has a lowercase 'date' column with proper datetime values
# and a 'DAY' column with YYYYMMDD integers — use 'date' directly
gpr_d.rename(columns={"date": "date"}, inplace=True)  # keep as-is
gpr_d.columns = [c.strip() for c in gpr_d.columns]
gpr_d["date"] = pd.to_datetime(gpr_d["date"], errors="coerce")
gpr_d = gpr_d.dropna(subset=["date"])
gpr_d = gpr_d.sort_values("date").reset_index(drop=True)

print(f"  Date range: {gpr_d['date'].min().date()} to {gpr_d['date'].max().date()}")

# Select and rename GPR components — file uses UPPERCASE column names for GPR values
col_map = {}
for col in gpr_d.columns:
    cu = col.upper()
    if cu == "GPRD" and col != "date":
        col_map[col] = "GPRD"
    elif cu in ("GPRD_ACT", "GPRACT", "GPR_ACT"):
        col_map[col] = "GPRD_ACT"
    elif cu in ("GPRD_THREAT", "GPRTHREAT", "GPR_THREAT"):
        col_map[col] = "GPRD_THREAT"
    elif cu in ("MA7", "GPRD_MA7"):
        col_map[col] = "GPRD_MA7"
    elif cu in ("MA30", "GPRD_MA30"):
        col_map[col] = "GPRD_MA30"

gpr_d.rename(columns=col_map, inplace=True)
print(f"  GPR columns found: {list(col_map.values())}")

# If MA7/MA30 not in file, compute them
if "GPRD_MA7" not in gpr_d.columns and "GPRD" in gpr_d.columns:
    gpr_d["GPRD_MA7"]  = gpr_d["GPRD"].rolling(7,  min_periods=1).mean()
    gpr_d["GPRD_MA30"] = gpr_d["GPRD"].rolling(30, min_periods=1).mean()

# Log-transform GPR for regression use (log(1+GPR))
for col in ["GPRD", "GPRD_ACT", "GPRD_THREAT"]:
    if col in gpr_d.columns:
        gpr_d[f"log_{col}"] = np.log1p(gpr_d[col])

# GEI = log(1 + GPRD_THREAT) — main media expectations variable
if "GPRD_THREAT" in gpr_d.columns:
    gpr_d["GEI"] = np.log1p(gpr_d["GPRD_THREAT"])
elif "GPRD" in gpr_d.columns:
    gpr_d["GEI"] = np.log1p(gpr_d["GPRD"])
    print("  WARNING: GPRD_THREAT not found, using full GPRD as GEI")

print(f"  Peak GPRD_THREAT day: {gpr_d.loc[gpr_d['GPRD_THREAT'].idxmax(), 'date'].date() if 'GPRD_THREAT' in gpr_d.columns else 'N/A'}")


# ─────────────────────────────────────────────
# LOAD GPR MONTHLY (country-specific UKR/RUS)
# ─────────────────────────────────────────────
print("\nLoading GPR monthly (country-specific)...")
gpr_m = pd.read_excel(MONTHLY_FILE)
gpr_m.columns = gpr_m.columns.str.strip()
print(f"  Raw shape: {gpr_m.shape}")

# Date column is 'month' (lowercase)
gpr_m.rename(columns={"month": "date"}, inplace=True)
gpr_m["date"] = pd.to_datetime(gpr_m["date"], errors="coerce")
gpr_m = gpr_m.dropna(subset=["date"])
# Filter to valid range (data starts ~1985 for most country series)
gpr_m = gpr_m[gpr_m["date"] >= pd.Timestamp("1985-01-01")]
gpr_m = gpr_m.sort_values("date").reset_index(drop=True)

# Find Ukraine and Russia country GPR columns
ukr_col = next((c for c in gpr_m.columns if "UKR" in c.upper() and "GPRC" in c.upper()), None)
rus_col = next((c for c in gpr_m.columns if "RUS" in c.upper() and "GPRC" in c.upper()), None)
print(f"  Ukraine GPR column: {ukr_col}")
print(f"  Russia GPR column:  {rus_col}")
print(f"  Date range: {gpr_m['date'].min().date()} to {gpr_m['date'].max().date()}")

keep_m = ["date"]
if ukr_col:
    gpr_m.rename(columns={ukr_col: "GPRC_UKR"}, inplace=True)
    keep_m.append("GPRC_UKR")
if rus_col:
    gpr_m.rename(columns={rus_col: "GPRC_RUS"}, inplace=True)
    keep_m.append("GPRC_RUS")

gpr_monthly_clean = gpr_m[keep_m].copy()


# ─────────────────────────────────────────────
# CREATE FULL DAILY CALENDAR & FORWARD-FILL
# ─────────────────────────────────────────────
# Build a complete daily calendar covering the full analysis period
date_min = pd.Timestamp("2019-12-31")
date_max = pd.Timestamp("2026-06-30")
full_calendar = pd.DataFrame({"date": pd.date_range(date_min, date_max, freq="D")})

# Merge daily GPR
gpr_daily_out = full_calendar.merge(gpr_d, on="date", how="left")

# Forward-fill weekend/holiday gaps in GPR
gpr_cols = [c for c in gpr_daily_out.columns if c != "date"]
gpr_daily_out[gpr_cols] = gpr_daily_out[gpr_cols].fillna(method="ffill")

# Merge monthly country GPR (forward-fill to daily)
gpr_daily_out = gpr_daily_out.merge(gpr_monthly_clean, on="date", how="left")
for col in ["GPRC_UKR", "GPRC_RUS"]:
    if col in gpr_daily_out.columns:
        gpr_daily_out[col] = gpr_daily_out[col].fillna(method="ffill")

# Restrict to analysis period (2020 onwards)
gpr_daily_out = gpr_daily_out[gpr_daily_out["date"] >= pd.Timestamp("2020-01-01")]
gpr_daily_out = gpr_daily_out.reset_index(drop=True)

print(f"\n  Final GPR daily rows: {len(gpr_daily_out)}")
print(f"  Columns: {gpr_daily_out.columns.tolist()}")

# Sanity check: key dates
for event_date in ["2022-02-23", "2022-02-24", "2022-02-25"]:
    row = gpr_daily_out[gpr_daily_out["date"] == event_date]
    if len(row) > 0:
        gprd_t = row["GPRD_THREAT"].values[0] if "GPRD_THREAT" in row.columns else "N/A"
        gprd_a = row["GPRD_ACT"].values[0]   if "GPRD_ACT"    in row.columns else "N/A"
        print(f"  {event_date}: GPRD_THREAT={gprd_t:.1f}, GPRD_ACT={gprd_a:.1f}" 
              if isinstance(gprd_t, float) else f"  {event_date}: columns missing")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_path = os.path.join(PROC, "gpr_daily.csv")
gpr_daily_out.to_csv(out_path, index=False)
print(f"\nSaved gpr_daily.csv — {len(gpr_daily_out)} rows")
print("Script 04 complete.")
