"""
Script 03 — UAF Weapon-Type Variables (Novel Contribution)
===========================================================
Classifies each attack row into: drone / cruise_missile / ballistic_missile / other
Aggregates to daily level.
Creates war-intensity and interception-rate variables.

Outputs:
  data/processed/uaf_daily.csv
    date, WI_total, WI_drone, WI_cruise, WI_ballistic,
    IR_total, IR_drone, IR_cruise, IR_ballistic,
    launched_total, destroyed_total, (+ per-type counts)
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BASE, "data", "raw", "uaf")
PROC = os.path.join(BASE, "data", "processed")

ATTACKS_FILE = os.path.join(RAW, "missile_attacks_daily.csv")
CLASS_FILE   = os.path.join(RAW, "missiles_and_uavs-selected-columns.csv")

# ─────────────────────────────────────────────
# WEAPON CLASSIFICATION
# ─────────────────────────────────────────────
# Explicit classification for all models that appear in the attacks file.
# Categories: drone | cruise_missile | ballistic_missile | recon_uav | other
WEAPON_CLASS = {
    # Kamikaze / loitering / strike drones
    "Shahed-136/131":  "drone",
    "Shahed-136":      "drone",
    "Shahed-131":      "drone",
    "Lancet":          "drone",
    "Kub":             "drone",
    "Mohajer-6":       "drone",
    # Reconnaissance drones (less militarily impactful — separate from strike)
    "Orlan-10":        "recon_uav",
    "Supercam":        "recon_uav",
    "ZALA":            "recon_uav",
    "Orlan-10 and Supercam": "recon_uav",
    "Orlan-10 and ZALA":     "recon_uav",
    "Orlan-10 and Orlan-30 and ZALA and Supercam": "recon_uav",
    "Eleron":          "recon_uav",
    "Forpost":         "recon_uav",
    "Granat-4":        "recon_uav",
    "Orion":           "recon_uav",
    "Merlin-VR":       "recon_uav",
    "Reconnaissance UAV": "recon_uav",
    # Cruise missiles
    "Kalibr":          "cruise_missile",
    "X-101/X-555":     "cruise_missile",
    "X-101":           "cruise_missile",
    "X-555":           "cruise_missile",
    "X-59":            "cruise_missile",
    "X-59/X-69":       "cruise_missile",
    "X-69":            "cruise_missile",
    "X-22":            "cruise_missile",
    "X-32":            "cruise_missile",
    "Kh-47M2 Kinzhal": "cruise_missile",   # hypersonic air-launched
    "Kinzhal":         "cruise_missile",
    "Kh-101":          "cruise_missile",
    "3M-54 Kalibr":    "cruise_missile",
    # Ballistic missiles
    "Iskander-M":      "ballistic_missile",
    "Iskander-M/KN-23": "ballistic_missile",
    "KN-23":           "ballistic_missile",
    "C-300":           "ballistic_missile",   # S-300 used as ballistic
    "S-300":           "ballistic_missile",
    "Tochka-U":        "ballistic_missile",
    "Tochka":          "ballistic_missile",
    "Molniya":         "ballistic_missile",
    "Molunia":         "ballistic_missile",
    # Other known types
    "Unknown UAV":     "drone",
}

# Cyrillic model names (appear in the data) — map to Latin equivalents
CYRILLIC_MAP = {
    "\u041c\u043e\u043b\u043d\u0456\u044f": "ballistic_missile",  # Молнія
}

def classify_model(model_str):
    """Return weapon category for a given model string."""
    if pd.isna(model_str):
        return "other"
    m = str(model_str).strip()
    # Direct lookup
    if m in WEAPON_CLASS:
        return WEAPON_CLASS[m]
    # Cyrillic
    if m in CYRILLIC_MAP:
        return CYRILLIC_MAP[m]
    # Fuzzy keyword matching
    ml = m.lower()
    if any(k in ml for k in ["shahed", "lancet", "kub", "mohajer", "uav", "drone"]):
        return "drone"
    if any(k in ml for k in ["kalibr", "x-101", "x-59", "x-22", "kinzhal", "cruise"]):
        return "cruise_missile"
    if any(k in ml for k in ["iskander", "kn-23", "c-300", "s-300", "tochka", "ballistic",
                               "\u043c\u043e\u043b\u043d"]):
        return "ballistic_missile"
    if any(k in ml for k in ["orlan", "supercam", "zala", "eleron", "forpost", "recon"]):
        return "recon_uav"
    return "other"


# ─────────────────────────────────────────────
# LOAD & CLASSIFY ATTACKS
# ─────────────────────────────────────────────
print("Loading UAF attack data...")
attacks = pd.read_csv(ATTACKS_FILE, low_memory=False)
print(f"  Raw rows: {len(attacks):,}")

# Parse date
attacks["date"] = pd.to_datetime(attacks["time_start"], errors="coerce").dt.normalize()
attacks = attacks.dropna(subset=["date"])

# Clean launched/destroyed columns
attacks["launched"]  = pd.to_numeric(attacks["launched"],  errors="coerce").fillna(0)
attacks["destroyed"] = pd.to_numeric(attacks["destroyed"], errors="coerce").fillna(0)

# Ensure destroyed <= launched (data quality)
attacks["destroyed"] = attacks[["launched", "destroyed"]].min(axis=1)

# Classify weapon type
attacks["weapon_type"] = attacks["model"].apply(classify_model)

print("  Weapon type distribution:")
print("   ", attacks["weapon_type"].value_counts().to_dict())
print(f"  Date range: {attacks['date'].min().date()} to {attacks['date'].max().date()}")


# ─────────────────────────────────────────────
# AGGREGATE TO DAILY
# ─────────────────────────────────────────────
print("Aggregating to daily...")

# Total
daily_total = attacks.groupby("date").agg(
    launched_total  = ("launched",  "sum"),
    destroyed_total = ("destroyed", "sum"),
).reset_index()

# By weapon type — pivot
daily_types = attacks.groupby(["date", "weapon_type"]).agg(
    launched  = ("launched",  "sum"),
    destroyed = ("destroyed", "sum"),
).reset_index()

daily_pivot = daily_types.pivot_table(
    index="date",
    columns="weapon_type",
    values=["launched", "destroyed"],
    aggfunc="sum",
    fill_value=0
).reset_index()

# Flatten multi-level columns
daily_pivot.columns = ["date"] + [
    f"{v}_{c}" for v, c in daily_pivot.columns[1:]
]

# Merge total + per-type
daily = daily_total.merge(daily_pivot, on="date", how="outer").fillna(0)
daily = daily.sort_values("date").reset_index(drop=True)

# Ensure columns exist (in case a type has zero rows)
for wtype in ["drone", "cruise_missile", "ballistic_missile", "recon_uav", "other"]:
    for pfx in ["launched", "destroyed"]:
        col = f"{pfx}_{wtype}"
        if col not in daily.columns:
            daily[col] = 0


# ─────────────────────────────────────────────
# CREATE WAR INTENSITY & INTERCEPTION RATE
# ─────────────────────────────────────────────

def safe_ir(destroyed, launched):
    """Interception rate = destroyed / launched; 0 if no attack."""
    mask = launched > 0
    ir = pd.Series(index=launched.index, dtype=float)
    ir[mask]  = destroyed[mask] / launched[mask]
    ir[~mask] = np.nan   # no attack day → NaN (not zero)
    return ir

# Log-transformed war intensity: log(1 + launched)
daily["WI_total"]      = np.log1p(daily["launched_total"])
daily["WI_drone"]      = np.log1p(daily["launched_drone"])
daily["WI_cruise"]     = np.log1p(daily["launched_cruise_missile"])
daily["WI_ballistic"]  = np.log1p(daily["launched_ballistic_missile"])
daily["WI_recon"]      = np.log1p(daily["launched_recon_uav"])

# Interception rates
daily["IR_total"]     = safe_ir(daily["destroyed_total"],          daily["launched_total"])
daily["IR_drone"]     = safe_ir(daily["destroyed_drone"],          daily["launched_drone"])
daily["IR_cruise"]    = safe_ir(daily["destroyed_cruise_missile"], daily["launched_cruise_missile"])
daily["IR_ballistic"] = safe_ir(daily["destroyed_ballistic_missile"], daily["launched_ballistic_missile"])

# Attack day indicator
daily["attack_day"] = (daily["launched_total"] > 0).astype(int)

print(f"  Daily rows: {len(daily)}")
print(f"  Attack days: {daily['attack_day'].sum()}")
print(f"  Mean WI_total (attack days): {daily.loc[daily['attack_day']==1,'WI_total'].mean():.3f}")
print(f"  Mean IR_total (attack days): {daily.loc[daily['attack_day']==1,'IR_total'].mean():.3f}")

# Summary by type
for wtype, wi_col in [("drone","WI_drone"),("cruise","WI_cruise"),("ballistic","WI_ballistic")]:
    l_col = f"launched_{wtype}" if wtype != "cruise" else "launched_cruise_missile"
    if wtype == "ballistic":
        l_col = "launched_ballistic_missile"
    total_launched = daily[l_col].sum()
    active_days = (daily[l_col] > 0).sum()
    print(f"  {wtype}: {total_launched:.0f} total launched, {active_days} active days")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
# Keep clean output columns
out_cols = [
    "date", "attack_day",
    "launched_total", "destroyed_total",
    "launched_drone",             "destroyed_drone",
    "launched_cruise_missile",    "destroyed_cruise_missile",
    "launched_ballistic_missile", "destroyed_ballistic_missile",
    "launched_recon_uav",         "destroyed_recon_uav",
    "WI_total", "WI_drone", "WI_cruise", "WI_ballistic", "WI_recon",
    "IR_total", "IR_drone", "IR_cruise", "IR_ballistic",
]
daily_out = daily[[c for c in out_cols if c in daily.columns]]

out_path = os.path.join(PROC, "uaf_daily.csv")
daily_out.to_csv(out_path, index=False)
print(f"\nSaved uaf_daily.csv — {len(daily_out)} rows")
print("Script 03 complete.")
