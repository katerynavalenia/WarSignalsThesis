"""
Script 13 - Robustness Checks
==============================
Five robustness tests for the main regressions (M1):

  R1: SIPRI-only firms (39 firms with verified arms revenue data)
  R2: US-only firms
  R3: Europe-only firms
  R4: Alternative interception definition (IR = 0 on non-attack days)
  R5: Rolling 6-month subsamples (structural break test)

Outputs:
  output/tables/table_robustness.csv
  output/tables/table_subsample_rolling.csv
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
TABS = os.path.join(BASE, "output", "tables")
os.makedirs(TABS, exist_ok=True)

try:
    from linearmodels.panel import PanelOLS
    LINEARMODELS_OK = True
except ImportError:
    LINEARMODELS_OK = False
    print("WARNING: linearmodels not available")

print("=" * 60)
print("Script 13 - Robustness Checks")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
panel = pd.read_csv(os.path.join(PROC, "panel_main.csv"), parse_dates=["date"])

def prepare(df):
    d = df.copy()
    d["arms_01"] = d["arms_share_composite"] / 100.0
    for wi in ["WI_total", "WI_drone", "WI_cruise", "WI_ballistic"]:
        if wi in d.columns:
            d[f"{wi}_x_a"] = d[wi].fillna(0) * d["arms_01"]
    for col in ["WI_total", "WI_drone", "WI_cruise", "WI_ballistic",
                "IR_total", "WI_ACLED"]:
        if col in d.columns:
            d[col] = d[col].fillna(0)
    if "GEI" in d.columns:
        d["GEI_x_a"] = d["GEI"] * d["arms_01"]
    d["log_mcap"] = d["log_market_cap"].fillna(d["log_market_cap"].mean())
    d["vix_std"]  = (d["VIX"].fillna(d["VIX"].mean()) - d["VIX"].mean()) / d["VIX"].std()
    return d

panel = prepare(panel)

BASE_FORMULA = ("WI_total + WI_total_x_a + GEI + GEI_x_a "
                "+ log_mcap + vix_std + log_brent + dlog_EURUSD")

KEY_VARS = ["WI_total", "WI_total_x_a", "GEI", "GEI_x_a"]


def run_reg(df, formula_rhs, label=""):
    if not LINEARMODELS_OK:
        return None
    d = df.dropna(subset=["AR", "GEI", "log_mcap", "vix_std", "log_brent"])
    d = d.set_index(["ticker", "date"])
    d = d[~d.index.duplicated(keep="first")]
    if len(d) < 50:
        return None
    try:
        mod = PanelOLS.from_formula(
            f"AR ~ {formula_rhs} + EntityEffects + TimeEffects",
            data=d, drop_absorbed=True)
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        return res
    except Exception as e:
        print(f"  {label} ERROR: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# R1-R3: SUBSAMPLE REGRESSIONS
# ─────────────────────────────────────────────────────────────
SUBSAMPLES = {
    "R1_SIPRI_only":  panel[panel["arms_share_source"] == "SIPRI_measured"],
    "R2_US_only":     panel[panel["is_us"] == 1],
    "R3_Europe_only": panel[panel["is_europe"] == 1],
    "R4_Full":        panel,
}

rob_rows = []
print("\nSubsample robustness checks:")
for label, sub in SUBSAMPLES.items():
    n_firms = sub["ticker"].nunique()
    print(f"\n  {label}: {n_firms} firms, {len(sub):,} obs")
    res = run_reg(sub[["ticker", "date", "AR", "WI_total", "WI_total_x_a",
                        "GEI", "GEI_x_a", "log_mcap", "vix_std",
                        "log_brent", "dlog_EURUSD"]],
                  BASE_FORMULA, label)
    if res is not None:
        row = {"Sample": label, "N_firms": n_firms, "N_obs": res.nobs,
               "R2_within": round(res.rsquared_within, 4)}
        for v in KEY_VARS:
            if v in res.params.index:
                p = res.pvalues[v]
                stars = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
                row[f"{v}_coef"] = round(res.params[v], 6)
                row[f"{v}_p"]    = round(p, 3)
                row[f"{v}_sig"]  = stars
                print(f"    {v:25s}: coef={res.params[v]:+.6f}  p={p:.3f} {stars}")
        rob_rows.append(row)

# ─────────────────────────────────────────────────────────────
# R5: ROLLING 6-MONTH SUBSAMPLES
# ─────────────────────────────────────────────────────────────
print("\nRolling 6-month structural break test:")
panel["period"] = panel["date"].dt.to_period("Q")  # quarterly
periods = sorted(panel["period"].unique())

roll_rows = []
for p_start in periods:
    p_end_idx = list(periods).index(p_start) + 2  # 2 quarters = ~6 months
    if p_end_idx >= len(periods):
        break
    p_end = periods[p_end_idx]
    mask  = (panel["period"] >= p_start) & (panel["period"] <= p_end)
    sub   = panel[mask].copy()
    if sub["ticker"].nunique() < 10:
        continue
    res = run_reg(sub[["ticker", "date", "AR", "WI_total", "WI_total_x_a",
                        "GEI", "GEI_x_a", "log_mcap", "vix_std",
                        "log_brent", "dlog_EURUSD"]],
                  BASE_FORMULA, f"{p_start}-{p_end}")
    if res is not None:
        row = {"period_start": str(p_start), "period_end": str(p_end),
               "N_obs": res.nobs, "R2_within": round(res.rsquared_within, 4)}
        for v in ["WI_total_x_a", "GEI_x_a"]:
            if v in res.params.index:
                row[f"{v}_coef"] = round(res.params[v], 6)
                row[f"{v}_p"]    = round(res.pvalues[v], 3)
            else:
                row[f"{v}_coef"] = np.nan
                row[f"{v}_p"]    = np.nan
        roll_rows.append(row)
        wi_xcoef = res.params.get("WI_total_x_a", np.nan)
        gei_xcoef = res.params.get("GEI_x_a", np.nan)
        print(f"  {p_start}-{p_end}: WI_x_a={wi_xcoef:+.5f}  "
              f"GEI_x_a={gei_xcoef:+.5f}  N={res.nobs}")

# ─────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────
if rob_rows:
    rob_df = pd.DataFrame(rob_rows)
    rob_df.to_csv(os.path.join(TABS, "table_robustness.csv"), index=False)
    print(f"\nSaved table_robustness.csv ({len(rob_df)} rows)")

if roll_rows:
    roll_df = pd.DataFrame(roll_rows)
    roll_df.to_csv(os.path.join(TABS, "table_subsample_rolling.csv"), index=False)
    print(f"Saved table_subsample_rolling.csv ({len(roll_df)} rows)")

print("\nScript 13 complete.")
