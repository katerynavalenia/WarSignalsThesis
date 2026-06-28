"""
Script 06 — SIPRI Defense Exposure Matching
============================================
Parses SIPRI Top 100 arms companies (2020–2024 average).
Fuzzy-matches company names to Bloomberg tickers.
Builds continuous arms_revenue_share_i variable.

Outputs:
  data/processed/sipri_exposure.csv
    ticker, sipri_company, sipri_country, arms_share_avg,
    arms_rev_avg_musd, sipri_rank_2024, sipri_match_score, in_sipri_top100
"""

import os
import re
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BASE, "data", "raw", "sipri")
PROC = os.path.join(BASE, "data", "processed")

SIPRI_FILE = os.path.join(RAW, "SIPRI-Top-100-2002-2024 (2).xlsx")
FIRMS_FILE = os.path.join(PROC, "firms_metadata.csv")

# Years to average for the defense exposure measure
YEARS = [2020, 2021, 2022, 2023, 2024]


# ─────────────────────────────────────────────
# PARSE SIPRI SHEETS
# ─────────────────────────────────────────────
def parse_sipri_sheet(xl, year):
    """Parse one SIPRI year sheet → DataFrame with Rank, Company, Country, ArmsShare."""
    # Row 3 (0-indexed) contains the actual column headers
    df = pd.read_excel(xl, sheet_name=str(year), header=3)
    # Flatten / clean column names
    df.columns = (df.columns
                  .str.strip()
                  .str.replace(r"\s+", " ", regex=True)
                  .str.replace(r"\(.*?\)", "", regex=True)
                  .str.replace(r"\*Note.*", "", regex=True)
                  .str.strip())
    # Find key columns
    rank_col    = next((c for c in df.columns if "Rank" in c and str(year) in c), None)
    company_col = next((c for c in df.columns if "Company" in c), None)
    country_col = next((c for c in df.columns if "Country" in c), None)
    arms_rev_col = next((c for c in df.columns
                         if "Arms revenues" in c and str(year) in c
                         and "constant" not in c.lower()), None)
    total_rev_col = next((c for c in df.columns
                          if "Total revenues" in c and str(year) in c), None)
    arms_pct_col  = next((c for c in df.columns
                          if "%" in c or "percent" in c.lower() or "share" in c.lower()),
                         None)

    if company_col is None:
        return None

    out = pd.DataFrame()
    out["rank"]       = pd.to_numeric(df[rank_col], errors="coerce") if rank_col else np.nan
    out["company"]    = df[company_col].astype(str).str.strip()
    out["country"]    = df[country_col].astype(str).str.strip() if country_col else "Unknown"
    out["arms_rev"]   = pd.to_numeric(df[arms_rev_col],   errors="coerce") if arms_rev_col else np.nan
    out["total_rev"]  = pd.to_numeric(df[total_rev_col],  errors="coerce") if total_rev_col else np.nan
    out["arms_share"] = pd.to_numeric(df[arms_pct_col],   errors="coerce") if arms_pct_col else np.nan

    # If arms_share is given as ratio (0–1) convert to percentage
    if out["arms_share"].dropna().max() < 2:
        out["arms_share"] = out["arms_share"] * 100

    out["year"] = year
    # Drop metadata/footnote rows
    out = out.dropna(subset=["company"])
    out = out[out["company"].str.len() > 1]
    out = out[~out["company"].str.startswith("Source")]
    out = out[~out["company"].str.startswith("Notes")]
    out = out[~out["company"].str.startswith("nan")]
    return out


print("Parsing SIPRI sheets...")
xl = pd.ExcelFile(SIPRI_FILE)
frames = []
for y in YEARS:
    df_y = parse_sipri_sheet(xl, y)
    if df_y is not None and len(df_y) > 0:
        frames.append(df_y)
        print(f"  {y}: {len(df_y)} companies")

sipri_all = pd.concat(frames, ignore_index=True)

# Average arms share across years (by company name)
sipri_avg = (sipri_all.groupby("company")
             .agg(arms_share_avg = ("arms_share", "mean"),
                  arms_rev_avg   = ("arms_rev",   "mean"),
                  country        = ("country",     "first"))
             .reset_index()
             .rename(columns={"company": "sipri_company"}))

# Also get 2024 rank
sipri_2024 = sipri_all[sipri_all["year"] == 2024][["company", "rank"]].rename(
    columns={"rank": "sipri_rank_2024", "company": "sipri_company"})
sipri_avg = sipri_avg.merge(sipri_2024, on="sipri_company", how="left")
sipri_avg = sipri_avg.sort_values("sipri_rank_2024").reset_index(drop=True)
print(f"\nSIPRI unique companies: {len(sipri_avg)}")


# ─────────────────────────────────────────────
# FUZZY MATCHING: SIPRI names → Bloomberg tickers
# ─────────────────────────────────────────────
firms = pd.read_csv(FIRMS_FILE)
print(f"Bloomberg firms: {len(firms)}")

def clean_name(s):
    """Normalise company name for fuzzy matching."""
    s = str(s).lower()
    # Remove legal suffixes
    for suffix in [r"\bcorp\.?\b", r"\binc\.?\b", r"\bltd\.?\b", r"\bplc\.?\b",
                   r"\bag\b", r"\bsa\b", r"\bse\b", r"\bbv\b", r"\bnv\b",
                   r"\b(the)\b", r"\bco\.?\b", r"\bgroup\b", r"\bholdings?\b",
                   r"\blimited\b", r"\bgmbh\b", r"\bllc\b"]:
        s = re.sub(suffix, "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def token_similarity(a, b):
    """Token-based Jaccard similarity between two company name strings."""
    ta = set(clean_name(a).split())
    tb = set(clean_name(b).split())
    if not ta or not tb:
        return 0.0
    intersection = ta & tb
    union        = ta | tb
    return len(intersection) / len(union)

# Manual override mapping (SIPRI name → Bloomberg ticker)
# Handles the most important firms where automated matching may fail
MANUAL_MATCH = {
    "Lockheed Martin Corp.":      "LMT UN Equity",
    "RTX":                        "RTX UN Equity",
    "Northrop Grumman Corp.":     "NOC UN Equity",
    "BAE Systems":                "BA/ LN Equity",
    "General Dynamics Corp.":     "GD UN Equity",
    "Boeing":                     "BA UN Equity",
    "L3Harris Technologies":      "LHX UN Equity",
    "Leonardo":                   "LDO IM Equity",
    "Airbus":                     "AIR FP Equity",
    "Thales":                     "HO FP Equity",
    "Safran":                     "SAF FP Equity",
    "Rheinmetall":                "RHM GY Equity",
    "Rolls-Royce":                "RR/ LN Equity",
    "SAAB":                       "SAABB SS Equity",
    "TransDigm Group Inc":        "TDG UN Equity",
    "Huntington Ingalls":         "HII UN Equity",
    "Elbit Systems":              "ESLT IT Equity",
    "Rafael Advanced Defense":    "RAFAEL IT Equity",
    "General Electric":           "GE UN Equity",
    "Raytheon":                   "RTX UN Equity",
    "Leidos":                     "LDOS UN Equity",
    "SAIC":                       "SAIC UN Equity",
    "Textron":                    "TXT UN Equity",
    "Curtiss-Wright":             "CW UN Equity",
    "Kratos":                     "KTOS UQ Equity",
    "Palantir":                   "PLTR UN Equity",
    "Howmet Aerospace":           "HWM UN Equity",
    "Mercury Systems":            "MRCY UQ Equity",
    "Moog":                       "MOG/A UN Equity",
    "BWX Technologies":           "BWXT UN Equity",
    "CACI International":         "CACI UN Equity",
    "Heico":                      "HEI UN Equity",
    "Dassault Aviation":          "AM FP Equity",
    "MTU Aero Engines":           "MTX GY Equity",
}

# Bloomberg ticker → name lookup
bb_name_map = {row["ticker"]: str(row.get("name_full", row.get("name_short", ""))).upper()
               for _, row in firms.iterrows()}

matches = []
for _, sipri_row in sipri_avg.iterrows():
    company = sipri_row["sipri_company"]

    # 1. Try manual override first
    manual_ticker = None
    for key, ticker in MANUAL_MATCH.items():
        if key.lower() in company.lower() or company.lower() in key.lower():
            manual_ticker = ticker
            break

    if manual_ticker and manual_ticker in bb_name_map:
        matches.append({
            "sipri_company":  company,
            "ticker":         manual_ticker,
            "match_score":    1.0,
            "match_method":   "manual",
        })
        continue

    # 2. Fuzzy token matching against Bloomberg names
    best_score  = 0.0
    best_ticker = None
    for ticker, bb_name in bb_name_map.items():
        score = token_similarity(company, bb_name)
        if score > best_score:
            best_score  = score
            best_ticker = ticker

    if best_score >= 0.30:
        matches.append({
            "sipri_company":  company,
            "ticker":         best_ticker,
            "match_score":    round(best_score, 3),
            "match_method":   "fuzzy",
        })
    else:
        matches.append({
            "sipri_company":  company,
            "ticker":         None,
            "match_score":    round(best_score, 3),
            "match_method":   "no_match",
        })

match_df = pd.DataFrame(matches)
matched   = match_df[match_df["ticker"].notna()]
unmatched = match_df[match_df["ticker"].isna()]

print(f"\nMatching results:")
print(f"  Matched:   {len(matched)} / {len(sipri_avg)}")
print(f"  Unmatched: {len(unmatched)}")
print(f"  Unmatched companies: {unmatched['sipri_company'].tolist()[:10]}")


# ─────────────────────────────────────────────
# BUILD FINAL EXPOSURE TABLE
# ─────────────────────────────────────────────
sipri_final = sipri_avg.merge(match_df, on="sipri_company", how="left")
sipri_final = sipri_final[sipri_final["ticker"].notna()].copy()

# Deduplicate: if multiple SIPRI entries map to same ticker, keep highest arms_share
sipri_final = (sipri_final.sort_values("arms_share_avg", ascending=False)
               .drop_duplicates(subset=["ticker"], keep="first"))

# For all Bloomberg firms, ensure we have a row (even if no SIPRI match)
all_tickers = pd.DataFrame({"ticker": firms["ticker"]})
sipri_out = all_tickers.merge(sipri_final[["ticker", "sipri_company", "country",
                                           "arms_share_avg", "arms_rev_avg",
                                           "sipri_rank_2024", "match_score"]],
                              on="ticker", how="left")
sipri_out["in_sipri_top100"] = sipri_out["sipri_company"].notna().astype(int)

# For unmatched firms, impute arms_share = 0 (conservative assumption)
sipri_out["arms_share_avg"] = sipri_out["arms_share_avg"].fillna(0.0)

print(f"\nFinal SIPRI exposure table: {len(sipri_out)} firms")
print(f"  In SIPRI Top 100: {sipri_out['in_sipri_top100'].sum()}")
print(f"  Mean arms share (SIPRI firms): {sipri_out.loc[sipri_out['in_sipri_top100']==1,'arms_share_avg'].mean():.1f}%")
print("\nTop 15 matched firms:")
print(sipri_out[sipri_out["in_sipri_top100"]==1].sort_values("sipri_rank_2024")[
    ["ticker","sipri_company","arms_share_avg","sipri_rank_2024"]].head(15).to_string())


# ─────────────────────────────────────────────
# COMPOSITE DEFENSE EXPOSURE (all 128 firms)
# ─────────────────────────────────────────────
# For SIPRI-unmatched firms, impute arms_share based on:
#   1. Index membership (BSHIELDT = pure EU defense index → higher)
#   2. BICS industry
#
# Imputation tiers (documented in thesis as "estimated"):
#   SIPRI measured (39 firms):   use arms_share_avg as-is
#   BSHIELDT-only A&D (10):      impute 78%  (EU pure-defense index)
#   WAERLST+BSHIELDT A&D (26-39): already covered by SIPRI for most
#   WAERLST-only A&D (remaining): impute 55%
#   Non-A&D (6):                  impute 20%
#
# IMPUTATION MEDIAN references (from SIPRI-matched firms by region):
#   US firms in SIPRI: median arms_share ≈ 70%
#   EU firms in SIPRI: median arms_share ≈ 65%
#   Other:                                 55%

firms_full = pd.read_csv(FIRMS_FILE)
sipri_out = sipri_out.merge(
    firms_full[["ticker", "bics_industry", "index_membership", "region"]],
    on="ticker", how="left"
)

# Median arms share of SIPRI-matched firms as reference
sipri_matched_median = sipri_out.loc[sipri_out["in_sipri_top100"] == 1,
                                     "arms_share_avg"].median()
print(f"\nSIPRI-matched median arms_share: {sipri_matched_median:.1f}%")

def impute_arms_share(row):
    """Impute arms_share for non-SIPRI firms."""
    if row["in_sipri_top100"] == 1:
        return row["arms_share_avg"]    # use exact SIPRI value
    bics = str(row.get("bics_industry", "")).strip()
    idx  = str(row.get("index_membership", "")).strip()
    if bics != "Aerospace & Defense":
        return 20.0   # non-defense BICS
    if "BSHIELDT" in idx and "WAERLST" not in idx:
        return 78.0   # pure EU defense index only
    if "BSHIELDT" in idx:
        return 72.0   # in both indices
    return 55.0       # WAERLST-only A&D

sipri_out["arms_share_composite"] = sipri_out.apply(impute_arms_share, axis=1)
sipri_out["arms_share_source"] = sipri_out["in_sipri_top100"].map(
    {1: "SIPRI_measured", 0: "imputed"}
)

# Normalise to 0–1 range for regression use
sipri_out["arms_share_norm"] = sipri_out["arms_share_composite"] / 100.0

print("\nComposite arms_share distribution:")
print(sipri_out.groupby("arms_share_source")["arms_share_composite"].describe()[
    ["count","mean","min","max"]].to_string())
print("\nFirms by imputation tier:")
print(sipri_out.groupby(["arms_share_source","index_membership"])[
    "arms_share_composite"].agg(["count","mean"]).to_string())

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_path = os.path.join(PROC, "sipri_exposure.csv")
sipri_out.to_csv(out_path, index=False)
print(f"\nSaved sipri_exposure.csv - {len(sipri_out)} rows")
print(f"  SIPRI exact match:  {sipri_out['in_sipri_top100'].sum()} firms")
print(f"  Imputed (A&D BICS): {(sipri_out['in_sipri_top100']==0).sum()} firms")
print(f"  All have arms_share_composite: {sipri_out['arms_share_composite'].notna().sum()} firms")
print("Script 06 complete.")
