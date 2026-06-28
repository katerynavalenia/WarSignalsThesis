"""
Script 12 - Panel Regressions (Main Results)
=============================================
Four main specifications:
  M1: AR_it ~ WI_total_t + WI_total_x_arms + GEI_t + GEI_x_arms
              + controls + FE_i + FE_t

  M2: M1 + weapon-type breakdown (drone, cruise, ballistic)

  M3: M1 + interception rate (IR_total) + IR_total_x_arms
              (tests 'defense-as-opportunity' hypothesis)

  M4: M1 + ACLED conflict intensity (robustness: alternative conflict measure)

All models: EntityEffects + TimeEffects, cluster SE by entity (firm).
Sample: panel_main (all 100 firms, Oct 2022 - Jun 2026).
US+Europe subsample from panel_useu.

Key hypotheses tested:
  H1: beta(WI_total_x_arms) > 0  [conflict drives defense stocks up]
  H2: beta(GEI_x_arms) > 0       [expectations channel]
  H3: beta(IR_total_x_arms) < 0  [high interception = less need = lower AR?]
       OR > 0                     [demonstration effect = higher AR?]
  H4: Drone > Cruise > Ballistic for coefficient magnitude

Outputs:
  output/tables/table_reg_main.csv      - M1-M4 full sample
  output/tables/table_reg_useu.csv      - M1-M4 US+Europe subsample
  data/processed/regression_results.csv - machine-readable results
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
    from linearmodels.panel import PanelOLS, PooledOLS
    from linearmodels.panel import BetweenOLS
    LINEARMODELS_OK = True
    print("linearmodels loaded successfully")
except ImportError:
    LINEARMODELS_OK = False
    print("WARNING: linearmodels not installed. Run: pip install linearmodels")

print("=" * 60)
print("Script 12 - Panel Regressions")
print("=" * 60)

# ── Load ──────────────────────────────────────────────────────
panel = pd.read_csv(os.path.join(PROC, "panel_main.csv"), parse_dates=["date"])
panel_useu = pd.read_csv(os.path.join(PROC, "panel_useu.csv"), parse_dates=["date"])

print(f"Main panel:    {len(panel):,} rows, {panel['ticker'].nunique()} firms")
print(f"US+EU panel:   {len(panel_useu):,} rows, {panel_useu['ticker'].nunique()} firms")

# ─────────────────────────────────────────────────────────────
# VARIABLE PREPARATION
# ─────────────────────────────────────────────────────────────
def prepare_panel(df, name="panel"):
    d = df.copy()
    # Normalize arms_share to 0-1
    d["arms_01"] = d["arms_share_composite"] / 100.0

    # Re-compute interaction terms with normalized arms_share
    for wi in ["WI_total", "WI_drone", "WI_cruise", "WI_ballistic",
               "WI_total_lag1", "WI_drone_lag1"]:
        if wi in d.columns:
            d[f"{wi}_x_a"] = d[wi] * d["arms_01"]

    for gei in ["GEI", "GEI_lag1", "dGEI"]:
        if gei in d.columns:
            d[f"{gei}_x_a"] = d[gei] * d["arms_01"]

    for ir in ["IR_total", "IR_drone"]:
        if ir in d.columns:
            d[f"{ir}_x_a"] = d[ir] * d["arms_01"]

    if "WI_ACLED" in d.columns:
        d["WI_ACLED_x_a"] = d["WI_ACLED"] * d["arms_01"]

    # Fill UAF NaN with 0 on non-attack days
    uaf_cols = [c for c in d.columns if c.startswith("WI_") or c.startswith("IR_")]
    for c in uaf_cols:
        d[c] = d[c].fillna(0)

    # Demean log_market_cap for interpretability (within-firm anyway via FE)
    d["log_mcap"] = d["log_market_cap"].fillna(d["log_market_cap"].mean())
    d["vix_std"]  = (d["VIX"].fillna(d["VIX"].mean()) - d["VIX"].mean()) / d["VIX"].std()

    print(f"\n{name} prepared: {len(d):,} rows")
    print(f"  Missing AR: {d['AR'].isna().sum()}")
    return d

panel_p    = prepare_panel(panel,       "Main panel")
panel_useu_p = prepare_panel(panel_useu, "US+EU panel")


def set_panel_index(df):
    """Set MultiIndex (ticker, date) for linearmodels."""
    d = df.copy()
    d = d.dropna(subset=["AR"])
    d = d.set_index(["ticker", "date"])
    # Remove duplicate indices
    d = d[~d.index.duplicated(keep="first")]
    return d


# ─────────────────────────────────────────────────────────────
# REGRESSION HELPER
# ─────────────────────────────────────────────────────────────
def run_panel_reg(df_indexed, formula_rhs, model_name="M", absorb_time=True):
    """
    Run PanelOLS with entity + time effects and clustered SE.
    Returns result object or None on error.
    """
    if not LINEARMODELS_OK:
        return None

    lhs = "AR"
    # Drop rows missing any RHS variable
    rhs_vars = [v.strip() for v in formula_rhs.replace("+", " ").split()
                if v.strip() not in ("~", "1", "0")]
    use_cols = [lhs] + rhs_vars
    use_cols_present = [c for c in use_cols if c in df_indexed.columns]
    d = df_indexed[use_cols_present].dropna()

    if len(d) < 100:
        print(f"  {model_name}: too few obs ({len(d)})")
        return None

    try:
        from linearmodels.panel import PanelOLS
        formula = f"{lhs} ~ {formula_rhs}"
        if absorb_time:
            formula += " + TimeEffects"
        mod = PanelOLS.from_formula(formula + " + EntityEffects", data=d,
                                    drop_absorbed=True)
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        return res
    except Exception as e:
        print(f"  {model_name} ERROR: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# MODEL SPECIFICATIONS
# ─────────────────────────────────────────────────────────────
CONTROLS = "log_mcap + vix_std + log_brent + dlog_EURUSD"

SPECS = {
    "M1_baseline": (
        "WI_total + WI_total_x_a + GEI + GEI_x_a + " + CONTROLS,
        "WI total + GEI channel, controls"
    ),
    "M2_weapon_types": (
        "WI_drone + WI_drone_x_a + WI_cruise + WI_cruise_x_a "
        "+ WI_ballistic + WI_ballistic_x_a + GEI + GEI_x_a + " + CONTROLS,
        "Weapon-type breakdown"
    ),
    "M3_interception": (
        "WI_total + WI_total_x_a + IR_total + IR_total_x_a "
        "+ GEI + GEI_x_a + " + CONTROLS,
        "Interception rate (defense success)"
    ),
    "M4_acled": (
        "WI_total + WI_total_x_a + WI_ACLED + WI_ACLED_x_a "
        "+ GEI + GEI_x_a + " + CONTROLS,
        "ACLED conflict alt. measure"
    ),
    "M5_gpr_only": (
        "GEI + GEI_x_a + " + CONTROLS,
        "Media channel only (no UAF)"
    ),
    "M6_lag": (
        "WI_total_lag1 + WI_total_lag1_x_a + GEI_lag1 + GEI_lag1_x_a + " + CONTROLS,
        "Lagged WI and GEI"
    ),
}

# ─────────────────────────────────────────────────────────────
# RUN REGRESSIONS — MAIN PANEL
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("MAIN PANEL RESULTS (all 100 firms)")
print("=" * 60)

results_all = {}
df_main_idx = set_panel_index(panel_p)

for mname, (rhs, desc) in SPECS.items():
    print(f"\n{mname}: {desc}")
    res = run_panel_reg(df_main_idx, rhs, mname)
    if res is not None:
        results_all[mname] = res
        params = res.params
        pvals  = res.pvalues
        # Print key coefficients
        key_vars = [v for v in params.index
                    if any(kw in v for kw in ["WI_total", "WI_drone", "WI_cruise",
                                               "WI_ballistic", "GEI", "IR_total",
                                               "WI_ACLED"])]
        for v in key_vars:
            stars = ("***" if pvals[v] < 0.01 else
                     "**"  if pvals[v] < 0.05 else
                     "*"   if pvals[v] < 0.10 else "")
            print(f"  {v:35s} coef={params[v]:+.6f}  p={pvals[v]:.3f} {stars}")
        print(f"  R2_within={res.rsquared_within:.4f}  N={res.nobs:,}")


# ─────────────────────────────────────────────────────────────
# RUN REGRESSIONS — US+EUROPE PANEL
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("US+EUROPE PANEL RESULTS (62 firms)")
print("=" * 60)

results_useu = {}
df_useu_idx = set_panel_index(panel_useu_p)

for mname, (rhs, desc) in SPECS.items():
    if mname in ("M4_acled", "M6_lag"):
        continue   # run only core models for US+EU
    print(f"\n{mname}: {desc}")
    res = run_panel_reg(df_useu_idx, rhs, mname + "_useu")
    if res is not None:
        results_useu[mname] = res
        params = res.params
        pvals  = res.pvalues
        key_vars = [v for v in params.index
                    if any(kw in v for kw in ["WI_total", "WI_drone", "WI_cruise",
                                               "WI_ballistic", "GEI", "IR_total"])]
        for v in key_vars:
            stars = ("***" if pvals[v] < 0.01 else
                     "**"  if pvals[v] < 0.05 else
                     "*"   if pvals[v] < 0.10 else "")
            print(f"  {v:35s} coef={params[v]:+.6f}  p={pvals[v]:.3f} {stars}")
        print(f"  R2_within={res.rsquared_within:.4f}  N={res.nobs:,}")


# ─────────────────────────────────────────────────────────────
# SAVE REGRESSION RESULTS TO CSV
# ─────────────────────────────────────────────────────────────
def results_to_df(results_dict, sample_label):
    rows = []
    for mname, res in results_dict.items():
        for var in res.params.index:
            rows.append({
                "sample":  sample_label,
                "model":   mname,
                "variable": var,
                "coef":    res.params[var],
                "se":      res.std_errors[var],
                "t_stat":  res.tstats[var],
                "p_value": res.pvalues[var],
                "n_obs":   res.nobs,
                "r2_within": res.rsquared_within,
            })
    return pd.DataFrame(rows)

reg_df_main = results_to_df(results_all,   "all_firms")
reg_df_useu = results_to_df(results_useu,  "useu_firms")
reg_results = pd.concat([reg_df_main, reg_df_useu], ignore_index=True)
reg_results.to_csv(os.path.join(PROC, "regression_results.csv"), index=False)
print(f"\nSaved regression_results.csv: {len(reg_results)} coefficient rows")


# ─────────────────────────────────────────────────────────────
# FORMAT PUBLICATION-STYLE TABLES
# ─────────────────────────────────────────────────────────────
def format_reg_table(results_dict, var_list, caption=""):
    """Pivot regression results to wide format (models as columns)."""
    rows = []
    for var in var_list:
        row = {"Variable": var}
        for mname, res in results_dict.items():
            if var in res.params.index:
                c = res.params[var]
                p = res.pvalues[var]
                s = res.std_errors[var]
                stars = ("***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else "")
                row[mname] = f"{c:+.5f}{stars}"
                row[f"{mname}_se"] = f"({s:.5f})"
            else:
                row[mname] = ""
                row[f"{mname}_se"] = ""
        rows.append(row)
    # Add fit stats
    for stat, label in [("nobs", "N"), ("rsquared_within", "R2_within")]:
        row = {"Variable": label}
        for mname, res in results_dict.items():
            v = getattr(res, stat, None)
            if v is not None:
                row[mname] = f"{int(v):,}" if label == "N" else f"{v:.4f}"
        rows.append(row)
    return pd.DataFrame(rows)


KEY_VARS = ["WI_total", "WI_total_x_a", "WI_drone", "WI_drone_x_a",
            "WI_cruise", "WI_cruise_x_a", "WI_ballistic", "WI_ballistic_x_a",
            "GEI", "GEI_x_a", "IR_total", "IR_total_x_a",
            "WI_ACLED", "WI_ACLED_x_a",
            "log_mcap", "vix_std", "log_brent", "dlog_EURUSD"]

if results_all:
    tab_main = format_reg_table(results_all, KEY_VARS, "Main panel")
    tab_main.to_csv(os.path.join(TABS, "table_reg_main.csv"), index=False)
    print("Saved table_reg_main.csv")

if results_useu:
    tab_useu = format_reg_table(results_useu, KEY_VARS, "US+EU panel")
    tab_useu.to_csv(os.path.join(TABS, "table_reg_useu.csv"), index=False)
    print("Saved table_reg_useu.csv")

print("\nScript 12 complete.")
