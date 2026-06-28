"""
Script 11 - Event Study
========================
Computes cumulative abnormal returns (CARs) around five key events:

Events:
  E1: 2022-02-24  Full-scale invasion begins
  E2: 2022-03-06  First major Ukrainian counterattack / Zaporizhzhia plant attack
  E3: 2022-10-08  Kerch Bridge bombing (UAF October 2022 escalation start)
  E4: 2023-06-06  Kakhovka dam destruction
  E5: 2024-02-17  Avdiivka falls (symbolic Russian advance)

Windows tested: (-1,+1), (-3,+3), (-5,+5), (-10,+10)

Outputs:
  output/tables/table_event_study.csv   - full CAR table
  output/tables/table_event_car_summary.csv  - mean CAR by group
  data/processed/car_panel.csv          - firm-level CARs for all events
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC  = os.path.join(BASE, "data", "processed")
TABS  = os.path.join(BASE, "output", "tables")
os.makedirs(TABS, exist_ok=True)

print("=" * 60)
print("Script 11 - Event Study")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
ar_df = pd.read_csv(os.path.join(PROC, "abnormal_returns.csv"), parse_dates=["date"])
sipri = pd.read_csv(os.path.join(PROC, "sipri_exposure.csv"))
firms = pd.read_csv(os.path.join(PROC, "firms_metadata.csv"))

ar_df = ar_df.sort_values(["ticker", "date"]).reset_index(drop=True)
ar_df = ar_df.merge(sipri[["ticker", "arms_share_composite", "arms_share_source",
                             "in_sipri_top100"]], on="ticker", how="left")
# region already in ar_df from Script 02 output

# Normalize arms share
ar_df["arms_share_01"] = ar_df["arms_share_composite"] / 100.0

print(f"AR data: {len(ar_df):,} rows, {ar_df['ticker'].nunique()} firms")
print(f"Date range: {ar_df['date'].min().date()} to {ar_df['date'].max().date()}")

# ─────────────────────────────────────────────────────────────
# EVENT DEFINITIONS
# ─────────────────────────────────────────────────────────────
EVENTS = {
    "E1_Invasion":     pd.Timestamp("2022-02-24"),
    "E2_Zaporizhzhia": pd.Timestamp("2022-03-04"),
    "E3_Kerch_Bridge": pd.Timestamp("2022-10-08"),
    "E4_Kakhovka_Dam": pd.Timestamp("2023-06-06"),
    "E5_Avdiivka":     pd.Timestamp("2024-02-17"),
}

WINDOWS = [(-1, 1), (-3, 3), (-5, 5), (-10, 10)]

# Get trading days as a sorted array
all_dates = ar_df["date"].sort_values().unique()

def get_trading_dates(event_date, days_before, days_after):
    """Return trading dates in window around event date."""
    idx = np.searchsorted(all_dates, event_date)
    if idx >= len(all_dates):
        return []
    start_idx = max(0, idx + days_before)
    end_idx   = min(len(all_dates) - 1, idx + days_after)
    return all_dates[start_idx:end_idx + 1]

# ─────────────────────────────────────────────────────────────
# COMPUTE CARs
# ─────────────────────────────────────────────────────────────
all_cars = []

for event_name, event_date in EVENTS.items():
    print(f"\n{event_name} ({event_date.date()}):")

    for win_start, win_end in WINDOWS:
        window_dates = get_trading_dates(event_date, win_start, win_end)
        if len(window_dates) == 0:
            continue

        # Get ARs in window for all firms
        mask = ar_df["date"].isin(window_dates)
        win_df = ar_df[mask].copy()

        # CAR per firm = sum of AR over window
        car = (win_df.groupby("ticker")
                     .agg(CAR=("AR", "sum"),
                          n_days=("AR", "count"),
                          arms_share=("arms_share_composite", "first"),
                          arms_share_01=("arms_share_01", "first"),
                          arms_source=("arms_share_source", "first"),
                          in_sipri=("in_sipri_top100", "first"))
                     .reset_index())
        # region comes from ar_df itself
        region_map = ar_df.drop_duplicates("ticker").set_index("ticker")["region"]
        car["region"] = car["ticker"].map(region_map)

        car["event"] = event_name
        car["event_date"] = event_date
        car["window"] = f"[{win_start},{win_end}]"
        car["win_start"] = win_start
        car["win_end"]   = win_end
        all_cars.append(car)

        # Print mean CAR by group
        n = len(car)
        m_car = car["CAR"].mean()
        t_stat, p_val = stats.ttest_1samp(car["CAR"].dropna(), 0)

        # High vs low defense exposure (above/below median arms_share)
        med = car["arms_share"].median()
        hi = car[car["arms_share"] >= med]["CAR"]
        lo = car[car["arms_share"] < med]["CAR"]
        t2, p2 = stats.ttest_ind(hi.dropna(), lo.dropna())

        print(f"  Window [{win_start:+d},{win_end:+d}]: "
              f"mean CAR={m_car:+.4f}  t={t_stat:.2f}  p={p_val:.3f}  n={n} | "
              f"Hi-Lo CAR diff={hi.mean()-lo.mean():+.4f}  p={p2:.3f}")

# Combine all CARs
car_panel = pd.concat(all_cars, ignore_index=True)
car_panel.to_csv(os.path.join(PROC, "car_panel.csv"), index=False)
print(f"\nSaved car_panel.csv: {len(car_panel)} rows")

# ─────────────────────────────────────────────────────────────
# SUMMARY TABLE — mean CAR by event x window x group
# ─────────────────────────────────────────────────────────────
print("\n--- Mean CAR by Event and Window ---")
summary_rows = []

for event_name in EVENTS:
    for win_start, win_end in WINDOWS:
        wlabel = f"[{win_start},{win_end}]"
        subset = car_panel[(car_panel["event"] == event_name) &
                           (car_panel["window"] == wlabel)]
        if len(subset) == 0:
            continue

        all_car = subset["CAR"].dropna()
        t_all, p_all = stats.ttest_1samp(all_car, 0) if len(all_car) > 1 else (np.nan, np.nan)

        us_car   = subset[subset["region"] == "US"]["CAR"].dropna()
        eu_car   = subset[subset["region"] == "Europe"]["CAR"].dropna()
        sipri_car = subset[subset["in_sipri"] == 1]["CAR"].dropna()

        # High vs low defense
        med = subset["arms_share"].median()
        hi_car = subset[subset["arms_share"] >= med]["CAR"].dropna()
        lo_car = subset[subset["arms_share"] < med]["CAR"].dropna()
        diff = hi_car.mean() - lo_car.mean() if len(hi_car) > 0 and len(lo_car) > 0 else np.nan
        _, p_diff = stats.ttest_ind(hi_car, lo_car) if len(hi_car) > 1 and len(lo_car) > 1 else (np.nan, np.nan)

        summary_rows.append({
            "Event":        event_name,
            "Window":       wlabel,
            "N_firms":      len(subset),
            "CAR_all":      round(float(all_car.mean()), 4) if len(all_car) > 0 else np.nan,
            "t_stat":       round(float(t_all), 3) if not np.isnan(t_all) else np.nan,
            "p_value":      round(float(p_all), 3) if not np.isnan(p_all) else np.nan,
            "CAR_US":       round(float(us_car.mean()), 4)   if len(us_car) > 0 else np.nan,
            "CAR_Europe":   round(float(eu_car.mean()), 4)   if len(eu_car) > 0 else np.nan,
            "CAR_SIPRI":    round(float(sipri_car.mean()), 4) if len(sipri_car) > 0 else np.nan,
            "CAR_HiDef":    round(float(hi_car.mean()), 4)   if len(hi_car) > 0 else np.nan,
            "CAR_LoDef":    round(float(lo_car.mean()), 4)   if len(lo_car) > 0 else np.nan,
            "HiLo_diff":    round(float(diff), 4)            if not np.isnan(diff) else np.nan,
            "p_HiLo":       round(float(p_diff), 3)          if not np.isnan(p_diff) else np.nan,
        })

event_summary = pd.DataFrame(summary_rows)
event_summary.to_csv(os.path.join(TABS, "table_event_study.csv"), index=False)
print(event_summary.to_string(index=False))

print("\nScript 11 complete.")
