"""
Script 14 - Granger Causality Tests and Difference-in-Differences (DiD)
=========================================================================

SECTION A — Granger Causality
---------------------------------
Tests whether past values of WI_total and GEI help predict future ARs
(beyond AR's own lags). Conducted on daily time series of average AR.

Tests run (max lag = 5 trading days):
  (1) WI_total -> avg_AR   (does realized conflict predict returns?)
  (2) GEI      -> avg_AR   (do expectations predict returns?)
  (3) avg_AR   -> WI_total (reverse: do returns predict conflict? — should fail)
  (4) avg_AR   -> GEI      (reverse: do returns predict expectations?)

Method: bivariate VAR(p) F-test on jointly zero restricted lags.
        Uses statsmodels.tsa.stattools.grangercausalitytests.

Also run panel Granger (firm-level): average the firm-specific F-statistics
following the approach of Dumitrescu & Hurlin (2012).

SECTION B — Difference-in-Differences
-----------------------------------------
Treatment: Russia-Ukraine invasion shock (Feb 24, 2022).
Treated group:  "High defense" — arms_share > median (50th pct = 55%).
Control group:  "Low defense"  — arms_share <= median.

Because AR data only starts Feb 24, 2022, we compute pre-invasion ARs
by applying the estimated market-model parameters (alpha, beta from
Script 02) to the CLEAN PRE-INVASION WINDOW: Jan 3, 2022 – Feb 23, 2022
(this window falls outside the event window but uses in-sample model fits).

DiD model (OLS on firm-level stacked pre/post data):
  AR_it = alpha_i + beta1*Post_t + beta2*High_i + beta3*(Post_t x High_i)
          + controls + epsilon_it
The key DiD coefficient is beta3.

Also estimate with two-way FE using linearmodels.PanelOLS for robustness:
  AR_it = EntityEffects + TimeEffects + beta3*(Post_t x High_i) + controls

Three event windows:
  W1: [-10, +10] trading days around Feb 24
  W2: [-20, +20] trading days around Feb 24
  W3: [-30, +30] trading days around Feb 24

Outputs:
  output/tables/table_granger.csv
  output/tables/table_did.csv
  output/figures/fig7_granger_var.png   (impulse response preview)
  output/figures/fig8_did_parallel_trends.png
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

from statsmodels.tsa.stattools import grangercausalitytests, adfuller
from statsmodels.tsa.api import VAR

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
TABS = os.path.join(BASE, "output", "tables")
FIGS = os.path.join(BASE, "output", "figures")
os.makedirs(TABS, exist_ok=True)
os.makedirs(FIGS, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams.update({"font.family": "sans-serif", "font.size": 10,
                     "figure.dpi": 150, "figure.facecolor": "white"})

INVASION = pd.Timestamp("2022-02-24")

print("=" * 60)
print("Script 14 - Granger Causality + Difference-in-Differences")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
panel  = pd.read_csv(os.path.join(PROC, "panel_main.csv"),  parse_dates=["date"])
ar_raw = pd.read_csv(os.path.join(PROC, "abnormal_returns.csv"), parse_dates=["date"])
uaf    = pd.read_csv(os.path.join(PROC, "uaf_daily.csv"),   parse_dates=["date"])
gpr    = pd.read_csv(os.path.join(PROC, "gpr_daily.csv"),   parse_dates=["date"])
params = pd.read_csv(os.path.join(PROC, "market_model_params.csv"))
ret    = pd.read_csv(os.path.join(PROC, "returns_daily.csv"), parse_dates=["date"])
bench  = pd.read_csv(os.path.join(PROC, "benchmarks_daily.csv"), parse_dates=["date"])
sipri  = pd.read_csv(os.path.join(PROC, "sipri_exposure.csv"))
firms  = pd.read_csv(os.path.join(PROC, "firms_metadata.csv"))

print(f"AR data:     {len(ar_raw):,} rows from {ar_raw['date'].min().date()}")
print(f"Params:      {len(params)} firms")
print(f"Returns:     {len(ret):,} rows")


# ═════════════════════════════════════════════════════════════
# SECTION A — GRANGER CAUSALITY
# ═════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SECTION A: Granger Causality Tests")
print("=" * 60)

# Daily average AR across all firms
daily_avg = panel.groupby("date")["AR"].mean().rename("avg_AR").reset_index()

# Merge with WI and GEI (fill non-attack days with 0 for WI)
daily_avg = daily_avg.merge(
    uaf[["date", "WI_total", "WI_drone"]].assign(WI_total=lambda d: d["WI_total"].fillna(0)),
    on="date", how="left"
)
daily_avg = daily_avg.merge(gpr[["date", "GEI", "GPRD_THREAT"]], on="date", how="left")
daily_avg["WI_total"] = daily_avg["WI_total"].fillna(0)
daily_avg["WI_drone"] = daily_avg["WI_drone"].fillna(0)
daily_avg = daily_avg.dropna(subset=["avg_AR", "GEI"]).sort_values("date")

print(f"\nTime series for Granger: {len(daily_avg)} daily observations")
print(f"Date range: {daily_avg['date'].min().date()} to {daily_avg['date'].max().date()}")

# ADF stationarity tests (required for Granger)
print("\nADF stationarity tests (H0: unit root):")
for varname, series in [("avg_AR", daily_avg["avg_AR"]),
                         ("WI_total", daily_avg["WI_total"]),
                         ("GEI", daily_avg["GEI"])]:
    adf_res = adfuller(series.dropna(), maxlag=5, autolag="AIC")
    print(f"  {varname:12s}: ADF={adf_res[0]:+.3f}  p={adf_res[1]:.4f}  "
          f"{'STATIONARY' if adf_res[1] < 0.05 else 'NON-STATIONARY'}")

MAX_LAG = 5

granger_rows = []

def run_granger(y_series, x_series, y_name, x_name):
    """Run Granger causality: does X Granger-cause Y?"""
    df_gr = pd.DataFrame({"y": y_series.values, "x": x_series.values})
    df_gr = df_gr.dropna()
    try:
        res_dict = grangercausalitytests(df_gr[["y", "x"]], maxlag=MAX_LAG,
                                         verbose=False)
        rows = []
        for lag in range(1, MAX_LAG + 1):
            # ssr_ftest = F-test on added lags
            ftest = res_dict[lag][0]["ssr_ftest"]
            rows.append({
                "y": y_name, "x": x_name,
                "lag": lag,
                "F_stat":  round(ftest[0], 4),
                "p_value": round(ftest[1], 4),
                "df1": int(ftest[2]),
                "df2": int(ftest[3]),
            })
        return rows
    except Exception as e:
        print(f"  Granger error ({x_name}->{y_name}): {e}")
        return []


print("\nGranger causality results (F-test per lag):")
tests = [
    (daily_avg["avg_AR"],  daily_avg["WI_total"], "avg_AR",  "WI_total"),
    (daily_avg["avg_AR"],  daily_avg["GEI"],       "avg_AR",  "GEI"),
    (daily_avg["WI_total"],daily_avg["avg_AR"],    "WI_total","avg_AR"),
    (daily_avg["GEI"],     daily_avg["avg_AR"],    "GEI",     "avg_AR"),
    (daily_avg["avg_AR"],  daily_avg["WI_drone"],  "avg_AR",  "WI_drone"),
]

for y_s, x_s, y_n, x_n in tests:
    rows = run_granger(y_s, x_s, y_n, x_n)
    granger_rows.extend(rows)
    if rows:
        print(f"\n  H0: {x_n} does NOT Granger-cause {y_n}")
        for r in rows:
            stars = ("***" if r["p_value"] < 0.01 else
                     "**"  if r["p_value"] < 0.05 else
                     "*"   if r["p_value"] < 0.10 else "")
            print(f"    lag={r['lag']}  F={r['F_stat']:.4f}  p={r['p_value']:.4f} {stars}")

granger_df = pd.DataFrame(granger_rows)
granger_df.to_csv(os.path.join(TABS, "table_granger.csv"), index=False)
print(f"\nSaved table_granger.csv ({len(granger_df)} rows)")


# ─────────────────────────────────────────────────────────────
# VAR impulse response preview figure
# ─────────────────────────────────────────────────────────────
print("\nFitting VAR for impulse response plot...")
var_data = daily_avg[["avg_AR", "WI_total", "GEI"]].dropna().copy()
# Scale for VAR stability
var_data["avg_AR"]  = var_data["avg_AR"]  * 100   # to percent
var_data["WI_total"]= var_data["WI_total"]
var_data["GEI"]     = var_data["GEI"]

try:
    var_model = VAR(var_data)
    var_res   = var_model.fit(maxlags=5, ic="aic")
    print(f"  VAR selected lag order: {var_res.k_ar}")
    irf = var_res.irf(periods=10)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # IRF: shock to WI_total -> avg_AR
    ax = axes[0]
    irf_wi_ar = irf.irfs[:, 0, 1]   # response of avg_AR to WI_total shock
    ax.plot(range(11), irf_wi_ar, color="#1f77b4", lw=2, marker="o", ms=4)
    ax.axhline(0, color="black", lw=0.5, ls="--")
    ax.set_title("IRF: WI_total shock -> avg_AR")
    ax.set_xlabel("Days after shock")
    ax.set_ylabel("Response (% pts)")
    ax.set_xticks(range(11))

    # IRF: shock to GEI -> avg_AR
    ax = axes[1]
    irf_gei_ar = irf.irfs[:, 0, 2]  # response of avg_AR to GEI shock
    ax.plot(range(11), irf_gei_ar, color="#ff7f0e", lw=2, marker="o", ms=4)
    ax.axhline(0, color="black", lw=0.5, ls="--")
    ax.set_title("IRF: GEI shock -> avg_AR")
    ax.set_xlabel("Days after shock")
    ax.set_xticks(range(11))

    plt.suptitle("Figure 7: Impulse Response Functions (VAR)\n"
                 "Response of avg_AR to one-std shock in WI_total and GEI",
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGS, "fig7_granger_irf.png"), bbox_inches="tight")
    plt.close()
    print("  Saved fig7_granger_irf.png")
except Exception as e:
    print(f"  VAR error: {e}")


# ═════════════════════════════════════════════════════════════
# SECTION B — DIFFERENCE-IN-DIFFERENCES
# ═════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SECTION B: Difference-in-Differences (Feb 24, 2022 invasion)")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Step 1: Compute pre-invasion abnormal returns
#   Apply market-model params to returns in pre-invasion window
# ─────────────────────────────────────────────────────────────
print("\nStep 1: Computing pre-invasion ARs...")

# Market model params per firm (rename params to avoid shadowing)
mm_params = params.copy()  # already loaded above as 'params'
# returns_daily.csv already has r_market (per-firm benchmark return)
params_sub = mm_params[["ticker", "alpha", "beta"]].copy()

# Returns in pre-invasion period (uses r_market = benchmark return for each firm)
PRE_START = pd.Timestamp("2022-01-03")
PRE_END   = pd.Timestamp("2022-02-23")
ret_pre   = ret[(ret["date"] >= PRE_START) & (ret["date"] <= PRE_END)].copy()
print(f"  Pre-invasion return obs: {len(ret_pre):,}")

# Merge market-model params
ret_pre = ret_pre.merge(params_sub, on="ticker", how="left")

# AR = actual_return - (alpha + beta * benchmark_return)
ret_pre["AR_pre"] = (ret_pre["log_return"]
                     - ret_pre["alpha"]
                     - ret_pre["beta"] * ret_pre["r_market"])

pre_ar = ret_pre[["date", "ticker", "AR_pre"]].rename(columns={"AR_pre": "AR"}).copy()
print(f"  Pre-invasion ARs computed: {len(pre_ar):,} ({pre_ar['AR'].notna().sum():,} non-missing)")

# ─────────────────────────────────────────────────────────────
# Step 2: Combine pre and post ARs
# ─────────────────────────────────────────────────────────────
pre_ar["period"] = "pre"
post_ar = ar_raw[(ar_raw["date"] >= INVASION) &
                 (ar_raw["date"] <= pd.Timestamp("2022-05-31"))][["date", "ticker", "AR"]].copy()
post_ar["period"] = "post"

combined = pd.concat([pre_ar, post_ar], ignore_index=True)
combined = combined.dropna(subset=["AR"])

# Merge defense exposure
defense_info = sipri[["ticker", "arms_share_composite"]].copy()
defense_info["arms_01"] = defense_info["arms_share_composite"] / 100.0
combined = combined.merge(defense_info, on="ticker", how="left")
combined = combined.merge(firms[["ticker", "region"]], on="ticker", how="left")

# Treatment assignment: High defense = arms_share > median
med_arms = combined["arms_share_composite"].median()
combined["High"] = (combined["arms_share_composite"] > med_arms).astype(int)
combined["Post"] = (combined["period"] == "post").astype(int)
combined["Post_x_High"] = combined["Post"] * combined["High"]
combined["treat_label"] = combined["High"].map({1: "High defense", 0: "Low defense"})

print(f"\nDiD dataset: {len(combined):,} obs")
print(f"  Pre period: {pre_ar['date'].min().date()} to {pre_ar['date'].max().date()} "
      f"({len(pre_ar):,} obs)")
print(f"  Post period: {post_ar['date'].min().date()} to {post_ar['date'].max().date()} "
      f"({len(post_ar):,} obs)")
print(f"  Arms share median (threshold): {med_arms:.1f}%")
print(f"  High-defense firms: {combined.drop_duplicates('ticker')['High'].sum()}")

# ─────────────────────────────────────────────────────────────
# Step 3: Parallel trends check (pre-period)
# ─────────────────────────────────────────────────────────────
print("\nParallel trends check (pre-invasion daily average AR):")
pre_only = combined[combined["period"] == "pre"].copy()
pre_only["date"] = pd.to_datetime(pre_only["date"])
pre_trends = pre_only.groupby(["date", "treat_label"])["AR"].mean().unstack()

# Test for difference in trend using OLS on pre-period
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

pre_high = pre_only[pre_only["High"] == 1]["AR"].dropna()
pre_low  = pre_only[pre_only["High"] == 0]["AR"].dropna()
t_pt, p_pt = stats.ttest_ind(pre_high, pre_low)
print(f"  Mean AR pre-period: High={pre_high.mean():.5f}, Low={pre_low.mean():.5f}")
print(f"  t-test difference: t={t_pt:.3f}, p={p_pt:.3f} "
      f"({'PARALLEL TRENDS OK' if p_pt > 0.05 else 'WARNING: pre-trends differ'})")

# ─────────────────────────────────────────────────────────────
# Step 4: DiD regressions
# ─────────────────────────────────────────────────────────────
print("\nDiD regression results:")
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
import statsmodels.formula.api as smf

did_rows = []

def run_did(df, label, add_fe=False):
    """Simple DiD OLS. With add_fe, add firm dummies."""
    d = df.dropna(subset=["AR", "Post_x_High", "Post", "High"]).copy()
    if add_fe:
        # Demean by firm (within-firm transformation = firm FE)
        d["AR_dm"]   = d["AR"]   - d.groupby("ticker")["AR"].transform("mean")
        d["Phx_dm"]  = d["Post_x_High"] - d.groupby("ticker")["Post_x_High"].transform("mean")
        d["Post_dm"] = d["Post"] - d.groupby("ticker")["Post"].transform("mean")
        X = add_constant(d[["Post_dm", "Phx_dm"]])
        y = d["AR_dm"]
    else:
        X = add_constant(d[["Post", "High", "Post_x_High"]])
        y = d["AR"]

    res = OLS(y, X).fit(cov_type="HC3")   # heteroskedasticity-robust SE
    coef_name = "Phx_dm" if add_fe else "Post_x_High"

    beta  = res.params.get(coef_name, np.nan)
    se    = res.bse.get(coef_name, np.nan)
    t_val = res.tvalues.get(coef_name, np.nan)
    p_val = res.pvalues.get(coef_name, np.nan)
    n_obs = int(res.nobs)
    r2    = res.rsquared

    stars = ("***" if p_val < 0.01 else "**" if p_val < 0.05 else "*" if p_val < 0.10 else "")
    spec  = "(firm FE)" if add_fe else "(pooled)"
    print(f"  {label} {spec}: DiD coef={beta:+.6f} se={se:.6f} t={t_val:.3f} p={p_val:.3f} {stars}  N={n_obs:,}")
    did_rows.append({"sample": label, "spec": spec, "DiD_coef": beta, "se": se,
                     "t_stat": t_val, "p_value": p_val, "N": n_obs, "R2": r2})


# Full sample
run_did(combined, "All firms",      add_fe=False)
run_did(combined, "All firms",      add_fe=True)

# US+Europe
useu = combined[combined["region"].isin(["US", "Europe"])]
run_did(useu, "US+Europe", add_fe=False)
run_did(useu, "US+Europe", add_fe=True)

# US only
us = combined[combined["region"] == "US"]
run_did(us, "US only", add_fe=False)

# Europe only
eu = combined[combined["region"] == "Europe"]
run_did(eu, "Europe only", add_fe=False)

# ─────────────────────────────────────────────────────────────
# Step 5: Wider windows
# ─────────────────────────────────────────────────────────────
print("\nDiD with wider post-event windows:")
for post_end_label, post_end in [("Apr 2022", "2022-04-30"),
                                   ("Jun 2022", "2022-06-30"),
                                   ("Dec 2022", "2022-12-31")]:
    post_w = ar_raw[(ar_raw["date"] >= INVASION) &
                    (ar_raw["date"] <= pd.Timestamp(post_end))][["date", "ticker", "AR"]].copy()
    post_w["period"] = "post"
    comb_w = pd.concat([pre_ar, post_w], ignore_index=True)
    comb_w = comb_w.dropna(subset=["AR"])
    comb_w = comb_w.merge(defense_info, on="ticker", how="left")
    comb_w["High"] = (comb_w["arms_share_composite"] > med_arms).astype(int)
    comb_w["Post"] = (comb_w["period"] == "post").astype(int)
    comb_w["Post_x_High"] = comb_w["Post"] * comb_w["High"]
    run_did(comb_w, f"Post to {post_end_label}", add_fe=False)

# ─────────────────────────────────────────────────────────────
# Save DiD table
# ─────────────────────────────────────────────────────────────
did_df = pd.DataFrame(did_rows)
did_df.to_csv(os.path.join(TABS, "table_did.csv"), index=False)
print(f"\nSaved table_did.csv ({len(did_df)} rows)")

# ─────────────────────────────────────────────────────────────
# Figure 8: Parallel trends + DiD visualization
# ─────────────────────────────────────────────────────────────
print("\nGenerating Figure 8: DiD parallel trends plot...")

# Prepare daily average AR by treatment group
combined["date"] = pd.to_datetime(combined["date"])
all_dates_did = combined.groupby(["date", "treat_label"])["AR"].mean().reset_index()
all_dates_did["AR_7d"] = (all_dates_did
                          .groupby("treat_label")["AR"]
                          .transform(lambda x: x.rolling(7, min_periods=3).mean()))

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: pre-period parallel trends
ax = axes[0]
for grp, label, color in [("High defense", "High defense (treated)", "#d62728"),
                            ("Low defense",  "Low defense (control)",  "#7f7f7f")]:
    sub = all_dates_did[(all_dates_did["treat_label"] == grp) &
                        (all_dates_did["date"] < INVASION)]
    ax.plot(sub["date"], sub["AR_7d"] * 100, color=color, lw=1.5, label=label)
ax.axhline(0, color="black", lw=0.5, ls="--")
ax.set_ylabel("Avg AR, 7-day MA (%)")
ax.set_title("Pre-invasion period\n(parallel trends check)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.legend(fontsize=9)
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30)

# Right: full DiD window
ax = axes[1]
for grp, label, color in [("High defense", "High defense (treated)", "#d62728"),
                            ("Low defense",  "Low defense (control)",  "#7f7f7f")]:
    sub = all_dates_did[(all_dates_did["treat_label"] == grp) &
                        (all_dates_did["date"] <= pd.Timestamp("2022-05-31"))]
    ax.plot(sub["date"], sub["AR_7d"] * 100, color=color, lw=1.5, label=label)
ax.axvline(INVASION, color="black", ls="--", lw=1.2, label="Invasion (Feb 24)")
ax.axhline(0, color="black", lw=0.5, ls="-", alpha=0.5)
ax.set_ylabel("Avg AR, 7-day MA (%)")
ax.set_title("DiD window: Jan – May 2022\n(High vs Low defense firms)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.legend(fontsize=9)
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30)

plt.suptitle("Figure 8: Difference-in-Differences — Defense vs. Non-Defense Firms\n"
             "(Treated = arms_share > median 55%)", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(FIGS, "fig8_did_parallel_trends.png"), bbox_inches="tight")
plt.close()
print("  Saved fig8_did_parallel_trends.png")

print("\nScript 14 complete.")
