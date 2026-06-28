"""
Script 05 — ACLED Weekly Conflict Variables
============================================
Processes ACLED aggregated weekly data for Ukraine.
Creates daily conflict intensity variables (forward-filled from weekly).
Used as a robustness alternative to UAF data for full period coverage.

Outputs:
  data/processed/acled_daily.csv
    date, ACLED_events_Ukraine, ACLED_fatalities_Ukraine,
    ACLED_explosions, ACLED_battles, WI_ACLED, WI_ACLED_severity
"""

import os
import pandas as pd
import numpy as np
import openpyxl
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BASE, "data", "raw", "acled")
PROC = os.path.join(BASE, "data", "processed")

ACLED_AGG_FILE = os.path.join(RAW,
    "Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx")
ACLED_IND_FILE = os.path.join(RAW, "ACLED Data_2026-06-18.csv")

# ─────────────────────────────────────────────
# LOAD ACLED AGGREGATED (WEEKLY, TO JUN 2026)
# ─────────────────────────────────────────────
print("Loading ACLED aggregated weekly data...")

# File has stale dimension metadata — must specify max_row/max_col explicitly
wb = openpyxl.load_workbook(ACLED_AGG_FILE, read_only=True, data_only=True)
ws = wb.active
rows = []
for row in ws.iter_rows(max_row=200000, max_col=20, values_only=True):
    non_null = [x for x in row if x is not None]
    if non_null:
        rows.append(row[:13])  # 13 actual columns
wb.close()

headers = rows[0]
data    = rows[1:]
acled   = pd.DataFrame(data, columns=headers)
print(f"  Raw rows: {len(acled):,}, columns: {list(headers)}")

# Parse date
acled["WEEK"] = pd.to_datetime(acled["WEEK"], errors="coerce")
acled = acled.dropna(subset=["WEEK"])

# Numeric columns
for col in ["EVENTS", "FATALITIES"]:
    acled[col] = pd.to_numeric(acled[col], errors="coerce").fillna(0)

# Filter to Ukraine only
ukr = acled[acled["COUNTRY"].astype(str).str.strip() == "Ukraine"].copy()
print(f"  Ukraine rows: {len(ukr):,}")
print(f"  Date range: {ukr['WEEK'].min().date()} to {ukr['WEEK'].max().date()}")

# Aggregate by week and event type
# Key event types for conflict intensity
event_map = {
    "Explosions/Remote violence": "explosions",
    "Battles":                    "battles",
    "Strategic developments":     "strategic",
    "Violence against civilians": "civilian_violence",
    "Protests":                   "protests",
}

ukr_weekly = ukr.groupby("WEEK").agg(
    ACLED_events_total     = ("EVENTS",     "sum"),
    ACLED_fatalities_total = ("FATALITIES", "sum"),
).reset_index()

# Per event-type columns
for etype, col_name in event_map.items():
    subset = ukr[ukr["EVENT_TYPE"] == etype].groupby("WEEK")["EVENTS"].sum().reset_index()
    subset.columns = ["WEEK", f"ACLED_{col_name}"]
    ukr_weekly = ukr_weekly.merge(subset, on="WEEK", how="left")

ukr_weekly = ukr_weekly.fillna(0)
ukr_weekly = ukr_weekly.sort_values("WEEK").reset_index(drop=True)


# ─────────────────────────────────────────────
# WAR INTENSITY INDICES (weekly)
# ─────────────────────────────────────────────
# WI_ACLED = log(1 + total events in Ukraine that week)
ukr_weekly["WI_ACLED"] = np.log1p(ukr_weekly["ACLED_events_total"])

# Severity version: events + fatalities
ukr_weekly["WI_ACLED_severity"] = (
    np.log1p(ukr_weekly["ACLED_events_total"]) +
    np.log1p(ukr_weekly["ACLED_fatalities_total"])
)

print(f"\n  Weekly rows (Ukraine): {len(ukr_weekly)}")
print(f"  Mean WI_ACLED: {ukr_weekly['WI_ACLED'].mean():.3f}")
print(f"  Peak week: {ukr_weekly.loc[ukr_weekly['ACLED_events_total'].idxmax(), 'WEEK'].date()}"
      f" ({ukr_weekly['ACLED_events_total'].max():.0f} events)")


# ─────────────────────────────────────────────
# EXPAND WEEKLY TO DAILY (forward-fill within week)
# ─────────────────────────────────────────────
# For each week, assign values to all 7 days of that week
date_min = pd.Timestamp("2020-01-01")
date_max = pd.Timestamp("2026-06-30")
full_dates = pd.DataFrame({"date": pd.date_range(date_min, date_max, freq="D")})

# ACLED week = start-of-week; assign to all days in that week via merge_asof
ukr_weekly.rename(columns={"WEEK": "date"}, inplace=True)
full_dates = full_dates.sort_values("date")
ukr_weekly = ukr_weekly.sort_values("date")

acled_daily = pd.merge_asof(full_dates, ukr_weekly, on="date", direction="backward")

# Fill any remaining NaN with 0 (before ACLED starts or gaps)
fill_cols = [c for c in acled_daily.columns if c != "date"]
acled_daily[fill_cols] = acled_daily[fill_cols].fillna(0)

print(f"\n  Expanded to daily: {len(acled_daily)} rows")
print(f"  Date range: {acled_daily['date'].min().date()} to {acled_daily['date'].max().date()}")

# Sanity: check invasion week
inv_week = acled_daily[acled_daily["date"] == "2022-02-28"]
if len(inv_week) > 0:
    print(f"  Invasion week (Feb 28, 2022): {inv_week['ACLED_events_total'].values[0]:.0f} events")


# ─────────────────────────────────────────────
# ALSO LOAD INDIVIDUAL ACLED FOR DAILY GRANULARITY (Feb 2022 – Jun 2025)
# This provides daily (not weekly) conflict variables as additional signal
# ─────────────────────────────────────────────
print("\nLoading ACLED individual events (daily, 2020-2025)...")
acled_ind = pd.read_csv(ACLED_IND_FILE, low_memory=False)
acled_ind["event_date"] = pd.to_datetime(acled_ind["event_date"], errors="coerce")
acled_ind = acled_ind.dropna(subset=["event_date"])

# Ukraine only
ukr_ind = acled_ind[acled_ind["country"] == "Ukraine"].copy()
print(f"  Ukraine individual events: {len(ukr_ind):,}")
print(f"  Date range: {ukr_ind['event_date'].min().date()} to {ukr_ind['event_date'].max().date()}")

# Aggregate to daily
ukr_ind_daily = ukr_ind.groupby("event_date").agg(
    ind_events_total     = ("event_date", "count"),
    ind_fatalities_total = ("fatalities", "sum"),
).reset_index().rename(columns={"event_date": "date"})

# Sub-type aggregations
for sub, col in [("Shelling/artillery/missile attack", "ind_shelling"),
                 ("Air/drone strike", "ind_drone_strike"),
                 ("Armed clash", "ind_armed_clash")]:
    sub_daily = ukr_ind[ukr_ind["sub_event_type"] == sub].groupby(
        "event_date").size().reset_index(name=col)
    sub_daily.rename(columns={"event_date": "date"}, inplace=True)
    ukr_ind_daily = ukr_ind_daily.merge(sub_daily, on="date", how="left")

ukr_ind_daily = ukr_ind_daily.fillna(0)
ukr_ind_daily["WI_ACLED_daily"] = np.log1p(ukr_ind_daily["ind_events_total"])

# Merge into acled_daily
acled_daily = acled_daily.merge(ukr_ind_daily, on="date", how="left")
# Fill NaN (dates beyond Jun 2025 where individual file ends)
ind_cols = [c for c in acled_daily.columns if c.startswith("ind_") or c == "WI_ACLED_daily"]
acled_daily[ind_cols] = acled_daily[ind_cols].fillna(0)


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_path = os.path.join(PROC, "acled_daily.csv")
acled_daily.to_csv(out_path, index=False)
print(f"\nSaved acled_daily.csv — {len(acled_daily)} rows, {len(acled_daily.columns)} cols")
print(f"Columns: {acled_daily.columns.tolist()}")
print("Script 05 complete.")
