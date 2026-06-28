"""
Script 15 - Figures
====================
Produces all thesis figures.

Figure list:
  F1: Time series — WI_total, GEI, average daily AR (3-panel)
  F2: Event study CAR plot — invasion event [-10,+10], by region
  F3: Event study — all 5 events, [-5,+5] window, bar chart
  F4: Scatter — arms_share vs CAR at invasion (E1, [-3,+3])
  F5: Rolling coefficients — GEI_x_a and WI_total_x_a over time
  F6: Weapon type breakdown — monthly attack distribution

Outputs: output/figures/fig1_timeseries.png  ... fig6_weapons.png
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")   # non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
FIGS = os.path.join(BASE, "output", "figures")
os.makedirs(FIGS, exist_ok=True)

plt.rcParams.update({
    "font.family":  "sans-serif",
    "font.size":    10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "figure.dpi":   150,
    "figure.facecolor": "white",
})

print("=" * 60)
print("Script 15 - Figures")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
panel   = pd.read_csv(os.path.join(PROC, "panel_main.csv"),  parse_dates=["date"])
uaf     = pd.read_csv(os.path.join(PROC, "uaf_daily.csv"),   parse_dates=["date"])
gpr     = pd.read_csv(os.path.join(PROC, "gpr_daily.csv"),   parse_dates=["date"])
car_pan = pd.read_csv(os.path.join(PROC, "car_panel.csv"),   parse_dates=["event_date"])

firms = pd.read_csv(os.path.join(PROC, "firms_metadata.csv"))
sipri = pd.read_csv(os.path.join(PROC, "sipri_exposure.csv"))
rob   = pd.read_csv(os.path.join(BASE, "output", "tables", "table_subsample_rolling.csv"))

# Color palette
C_BLUE   = "#1f77b4"
C_ORANGE = "#ff7f0e"
C_RED    = "#d62728"
C_GREEN  = "#2ca02c"
C_GREY   = "#7f7f7f"

INVASION = pd.Timestamp("2022-02-24")

# ─────────────────────────────────────────────────────────────
# F1: Three-panel time series
# ─────────────────────────────────────────────────────────────
print("F1: Time series...")

# Daily average AR
daily_ar  = panel.groupby("date")["AR"].mean().reset_index()
daily_ar["AR_ma20"] = daily_ar["AR"].rolling(20, min_periods=5).mean()

# Merge with GPR and UAF
daily_gpr = gpr[["date", "GEI", "GPRD_THREAT"]].copy()
daily_uaf = uaf[["date", "WI_total", "WI_drone"]].copy()

fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

# Panel A: Average AR (20-day MA)
ax = axes[0]
ax.bar(daily_ar["date"], daily_ar["AR"], color=C_BLUE, alpha=0.3, width=1, label="Daily AR")
ax.plot(daily_ar["date"], daily_ar["AR_ma20"], color=C_BLUE, lw=1.5, label="20-day MA")
ax.axhline(0, color="black", lw=0.5)
ax.axvline(INVASION, color=C_RED, ls="--", lw=1.2, label="Invasion (Feb 24)")
ax.set_ylabel("Avg. Abnormal Return")
ax.set_title("Panel A: Average Daily Abnormal Return (100 defense firms)")
ax.legend(fontsize=8, loc="upper right")
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=1))

# Panel B: GEI (GPR Threat)
ax = axes[1]
ax.plot(daily_gpr["date"], daily_gpr["GEI"], color=C_ORANGE, lw=1.2)
ax.axvline(INVASION, color=C_RED, ls="--", lw=1.2)
ax.set_ylabel("GEI (log GPR Threat)")
ax.set_title("Panel B: Geopolitical Expectation Index (GEI_t)")
ax.set_ylim(bottom=0)

# Panel C: UAF Weapon Intensity
ax = axes[2]
ax.bar(daily_uaf["date"], daily_uaf["WI_total"], color=C_RED, alpha=0.5, width=1, label="WI total")
ax.bar(daily_uaf["date"], daily_uaf["WI_drone"], color=C_GREEN, alpha=0.6, width=1, label="WI drone")
ax.axvline(INVASION, color=C_RED, ls="--", lw=1.2)
ax.set_ylabel("WI (log 1+launched)")
ax.set_title("Panel C: UAF Weapon Intensity Index (WI_t)")
ax.legend(fontsize=8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig1_timeseries.png"), bbox_inches="tight")
plt.close()
print("  Saved fig1_timeseries.png")

# ─────────────────────────────────────────────────────────────
# F2: Event study CAR — E1 invasion, [-10,+10], by region
# ─────────────────────────────────────────────────────────────
print("F2: Event study CAR path...")

ar_df = pd.read_csv(os.path.join(PROC, "abnormal_returns.csv"), parse_dates=["date"])
# region is already in ar_df from Script 02

# Trading days around invasion
all_dates = ar_df["date"].sort_values().unique()
inv_idx   = np.searchsorted(all_dates, INVASION)
win_dates = all_dates[max(0, inv_idx-10): min(len(all_dates), inv_idx+11)]

ar_win = ar_df[ar_df["date"].isin(win_dates)].copy()
ar_win["event_day"] = ar_win["date"].map(
    {d: i - 10 for i, d in enumerate(win_dates)})

# Cumulative AR per firm
cumcar_data = {}
for region, grp in ar_win.groupby("region"):
    pivot = grp.pivot_table(index="event_day", values="AR",
                            aggfunc="mean", fill_value=0)
    pivot["CAR"] = pivot["AR"].cumsum()
    cumcar_data[region] = pivot["CAR"]

fig, ax = plt.subplots(figsize=(10, 5))
colors  = {"US": C_BLUE, "Europe": C_ORANGE, "Other": C_GREY, "Asia": C_GREEN}
for region, car_series in cumcar_data.items():
    ax.plot(car_series.index, car_series.values * 100,
            label=region, color=colors.get(region, "black"), lw=2)

ax.axvline(0, color="black", ls="--", lw=1, label="Event day (t=0)")
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Event day (t=0: Feb 24, 2022)")
ax.set_ylabel("Cumulative Abnormal Return (%)")
ax.set_title("Figure 2: Cumulative Abnormal Returns around Invasion\n"
             "(Window: [-10, +10] trading days, by region)")
ax.legend()
ax.set_xticks(range(-10, 11))
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig2_event_study_invasion.png"), bbox_inches="tight")
plt.close()
print("  Saved fig2_event_study_invasion.png")

# ─────────────────────────────────────────────────────────────
# F3: All 5 events — mean CAR [-5,+5] bar chart
# ─────────────────────────────────────────────────────────────
print("F3: All events bar chart...")

events_summary = car_pan[car_pan["window"] == "[-5,5]"].groupby("event").agg(
    CAR_all=("CAR", "mean"),
    CAR_US=("CAR", lambda x: x[car_pan.loc[x.index, "region"] == "US"].mean()
            if "region" in car_pan.columns else np.nan),
    N=("CAR", "count")
).reset_index()

# Use table instead since car_pan region may not be present
from pathlib import Path
tab_path = Path(BASE) / "output" / "tables" / "table_event_study.csv"
ev_tab = pd.read_csv(tab_path)
ev_55 = ev_tab[ev_tab["Window"] == "[-5,5]"].copy()

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(ev_55))
w = 0.25
bars_all  = ax.bar(x - w,   ev_55["CAR_all"]    * 100, w, label="All firms",    color=C_BLUE)
bars_us   = ax.bar(x,       ev_55["CAR_US"]     * 100, w, label="US firms",     color=C_ORANGE)
bars_eu   = ax.bar(x + w,   ev_55["CAR_Europe"] * 100, w, label="Europe firms", color=C_GREEN)

# Significance stars (from p_value)
for i, row in ev_55.iterrows():
    stars = ("***" if row["p_value"] < 0.01 else
             "**"  if row["p_value"] < 0.05 else
             "*"   if row["p_value"] < 0.10 else "")
    if stars:
        ax.text(x[ev_55.index.get_loc(i)] - w, row["CAR_all"] * 100 + 0.1,
                stars, ha="center", fontsize=9)

ax.axhline(0, color="black", lw=0.5)
ax.set_xticks(x)
event_labels = ["E1: Invasion\n(Feb 24,'22)", "E2: Zaporizhzhia\n(Mar 4,'22)",
                "E3: Kerch Bridge\n(Oct 8,'22)", "E4: Kakhovka Dam\n(Jun 6,'23)",
                "E5: Avdiivka\n(Feb 17,'24)"]
ax.set_xticklabels(event_labels, fontsize=8)
ax.set_ylabel("Mean CAR [-5,+5] (%)")
ax.set_title("Figure 3: Mean Cumulative Abnormal Returns [-5,+5] Around Key Events")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig3_all_events.png"), bbox_inches="tight")
plt.close()
print("  Saved fig3_all_events.png")

# ─────────────────────────────────────────────────────────────
# F4: Scatter — arms_share vs CAR at E1
# ─────────────────────────────────────────────────────────────
print("F4: Arms share vs CAR scatter...")

e1_cars = car_pan[(car_pan["event"] == "E1_Invasion") &
                  (car_pan["window"] == "[-3,3]")].copy()
e1_cars = e1_cars.merge(sipri[["ticker", "arms_share_composite",
                                "arms_share_source"]], on="ticker", how="left")

fig, ax = plt.subplots(figsize=(8, 5))
colors_src = {"SIPRI_measured": C_BLUE, "imputed": C_GREY}
for src, grp in e1_cars.groupby("arms_source"):
    ax.scatter(grp["arms_share"] / 100, grp["CAR"] * 100,
               alpha=0.6, s=40, label=src,
               color=colors_src.get(src, "black"))

# Add regression line
x_all = e1_cars["arms_share"].dropna() / 100
y_all = e1_cars["CAR"].dropna() * 100
if len(x_all) == len(y_all):
    from numpy.polynomial.polynomial import polyfit
    c0, c1 = polyfit(x_all, y_all, 1)
    x_line = np.linspace(x_all.min(), x_all.max(), 50)
    ax.plot(x_line, c0 + c1 * x_line, color=C_RED, lw=1.5, label="OLS fit")

ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Defense Revenue Share (arms_share, 0-1)")
ax.set_ylabel("CAR [-3,+3] around Invasion (%)")
ax.set_title("Figure 4: Defense Revenue Share vs. CAR at Invasion\n(E1, Feb 24, 2022, window [-3,+3])")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig4_armsshare_vs_car.png"), bbox_inches="tight")
plt.close()
print("  Saved fig4_armsshare_vs_car.png")

# ─────────────────────────────────────────────────────────────
# F5: Rolling coefficient plot — GEI_x_a and WI_total_x_a
# ─────────────────────────────────────────────────────────────
print("F5: Rolling coefficient plot...")

rob["period_mid"] = pd.to_datetime(rob["period_start"].str.replace(r"Q\d", "", regex=True)
                                    + "-01-01")
# Better: parse period_start as quarter
rob["period_mid"] = (pd.PeriodIndex(rob["period_start"], freq="Q")
                     .to_timestamp() + pd.DateOffset(months=1))

fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)

ax = axes[0]
ax.plot(rob["period_mid"], rob["GEI_x_a_coef"], marker="o", color=C_ORANGE, lw=1.5)
ax.axhline(0, color="black", lw=0.5, ls="--")
ax.set_ylabel("Coefficient")
ax.set_title("GEI x arms_share coefficient (rolling 6-month window)")
# Add significance markers
for _, row in rob.iterrows():
    if row.get("GEI_x_a_p", 1.0) < 0.10:
        ax.scatter(row["period_mid"], row["GEI_x_a_coef"], s=80,
                   color=C_RED, zorder=5, marker="*")

ax = axes[1]
ax.plot(rob["period_mid"], rob["WI_total_x_a_coef"], marker="o", color=C_BLUE, lw=1.5)
ax.axhline(0, color="black", lw=0.5, ls="--")
ax.set_ylabel("Coefficient")
ax.set_title("WI_total x arms_share coefficient (rolling 6-month window)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig5_rolling_coefs.png"), bbox_inches="tight")
plt.close()
print("  Saved fig5_rolling_coefs.png")

# ─────────────────────────────────────────────────────────────
# F6: Weapon type breakdown — stacked monthly bar
# ─────────────────────────────────────────────────────────────
print("F6: Weapon type breakdown...")

uaf["month"] = uaf["date"].dt.to_period("M")
monthly_weapons = uaf.groupby("month").agg(
    drone=("launched_drone", "sum"),
    cruise=("launched_cruise_missile", "sum"),
    ballistic=("launched_ballistic_missile", "sum"),
    recon=("launched_recon_uav", "sum"),
).reset_index()
monthly_weapons["month_dt"] = monthly_weapons["month"].dt.to_timestamp()

fig, ax = plt.subplots(figsize=(13, 5))
x = monthly_weapons["month_dt"]
ax.bar(x, monthly_weapons["drone"],    color=C_BLUE,   alpha=0.85, label="Drone (Shahed/UAV)")
ax.bar(x, monthly_weapons["cruise"],   color=C_ORANGE, alpha=0.85, bottom=monthly_weapons["drone"],
       label="Cruise missile")
ax.bar(x, monthly_weapons["ballistic"], color=C_RED,   alpha=0.85,
       bottom=monthly_weapons["drone"] + monthly_weapons["cruise"], label="Ballistic missile")
ax.bar(x, monthly_weapons["recon"],    color=C_GREEN,  alpha=0.85,
       bottom=monthly_weapons["drone"] + monthly_weapons["cruise"] + monthly_weapons["ballistic"],
       label="Recon UAV")

ax.set_ylabel("Total launched (units/month)")
ax.set_title("Figure 6: Monthly Weapon Launches by Type (UAF data, Oct 2022 – Jun 2026)")
ax.legend(fontsize=9)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b'%y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig6_weapons_breakdown.png"), bbox_inches="tight")
plt.close()
print("  Saved fig6_weapons_breakdown.png")

print("\nAll figures saved to output/figures/")
print("Script 15 complete.")
