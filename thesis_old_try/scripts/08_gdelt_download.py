"""
Script 08 — GDELT Download (Defense Topics)
============================================
Downloads daily article counts for defense-related topics via GDELT DOC 2.0 API.
Uses SSL bypass for corporate network environments.
Also attempts to fetch top headlines per topic for FinBERT (saved separately).

Outputs:
  data/processed/gdelt_topics_daily.csv
    date, ukraine_war, rearmament, military_aid, defense_spending,
    weapons_demand, missiles_drones, procurement, air_defense
    (each column = daily article count, log-transformed: GEI_topic_t)
  data/raw/gdelt/headlines_for_finbert.csv  (for Colab FinBERT notebook)
"""

import os
import time
import json
import datetime
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# SSL bypass for corporate network
import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
RAW_GDELT = os.path.join(BASE, "data", "raw", "gdelt")
os.makedirs(RAW_GDELT, exist_ok=True)

# ─────────────────────────────────────────────
# GDELT DOC 2.0 API CONFIGURATION
# ─────────────────────────────────────────────
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

TOPICS = {
    "ukraine_war":      '"Ukraine" AND ("war" OR "invasion" OR "conflict" OR "Russia")',
    "rearmament":       '"rearmament" OR "defense spending" OR "NATO budget" OR "military buildup"',
    "military_aid":     '"military aid" OR "weapons delivery" OR "arms transfer" OR "defense package"',
    "defense_spending": '"defense budget" OR "defense spending" OR "military expenditure"',
    "weapons_demand":   '"weapons demand" OR "arms exports" OR "defense contracts" OR "military sales"',
    "missiles_drones":  '"missiles" AND ("drones" OR "UAV" OR "Shahed" OR "Kalibr")',
    "procurement":      '"defense procurement" OR "weapons contract" OR "military contract"',
    "air_defense":      '"air defense" OR "Patriot" OR "IRIS-T" OR "S-300" OR "missile defense"',
}

# Analysis period
START_DATE = datetime.date(2020, 1, 1)
END_DATE   = datetime.date(2026, 6, 20)

# Batch size: GDELT DOC API can handle at most ~3 months per query efficiently
BATCH_MONTHS = 3
SLEEP_BETWEEN = 3  # seconds between API calls


def gdelt_doc_query(query_str, start_dt, end_dt, mode="timelinevol", max_records=250):
    """
    Query GDELT DOC 2.0 API for article volume timeline.
    Returns a list of (date_str, count) tuples or empty list on failure.
    """
    params = {
        "query":    query_str,
        "mode":     mode,
        "format":   "json",
        "STARTDATETIME": start_dt.strftime("%Y%m%d%H%M%S"),
        "ENDDATETIME":   end_dt.strftime("%Y%m%d%H%M%S"),
        "TIMESPAN":      "CUSTOM",
    }
    if mode == "artlist":
        params["maxrecords"] = max_records
        params["sort"]       = "datedesc"

    try:
        resp = requests.get(GDELT_DOC_API, params=params,
                            timeout=30, verify=False)
        if resp.status_code != 200:
            return []
        data = resp.json()

        if mode == "timelinevol":
            # Response: {"timeline": [{"date": "20220224120000", "value": 123}, ...]}
            timeline = data.get("timeline", [{}])[0].get("data", [])
            return [(item.get("date", "")[:8], item.get("value", 0))
                    for item in timeline]
        elif mode == "artlist":
            articles = data.get("articles", [])
            return articles
    except Exception as e:
        print(f"    API error: {e}")
        return []


# ─────────────────────────────────────────────
# GENERATE DATE BATCHES
# ─────────────────────────────────────────────
def generate_batches(start, end, months):
    batches = []
    cur = start
    while cur < end:
        nxt = min(end, (cur.replace(day=1) +
                        datetime.timedelta(days=months * 31)).replace(day=1))
        batches.append((cur, nxt - datetime.timedelta(days=1)))
        cur = nxt
    return batches


batches = generate_batches(START_DATE, END_DATE, BATCH_MONTHS)
print(f"Date range: {START_DATE} to {END_DATE}")
print(f"Batches: {len(batches)} × ~{BATCH_MONTHS} months")
print(f"Topics:  {len(TOPICS)}")


# ─────────────────────────────────────────────
# DOWNLOAD VOLUME TIMELINES
# ─────────────────────────────────────────────
all_records = {}   # topic -> list of (date_str, count)

for topic, query in TOPICS.items():
    print(f"\n--- Topic: {topic} ---")
    topic_records = []
    for (s, e) in batches:
        print(f"  {s} to {e}...", end=" ", flush=True)
        records = gdelt_doc_query(query, s, e, mode="timelinevol")
        topic_records.extend(records)
        print(f"{len(records)} points")
        time.sleep(SLEEP_BETWEEN)

    all_records[topic] = topic_records
    print(f"  Total records: {len(topic_records)}")


# ─────────────────────────────────────────────
# BUILD DAILY DATAFRAME
# ─────────────────────────────────────────────
print("\nBuilding daily GDELT table...")

full_dates = pd.date_range(START_DATE, END_DATE, freq="D")
gdelt_daily = pd.DataFrame({"date": full_dates})

for topic, records in all_records.items():
    if not records:
        gdelt_daily[topic] = 0
        continue
    df_t = pd.DataFrame(records, columns=["date_str", "count"])
    df_t["date"] = pd.to_datetime(df_t["date_str"], format="%Y%m%d", errors="coerce")
    df_t["count"] = pd.to_numeric(df_t["count"], errors="coerce").fillna(0)
    # Average if multiple records per day (GDELT sometimes returns sub-daily)
    df_t = df_t.groupby("date")["count"].sum().reset_index()
    gdelt_daily = gdelt_daily.merge(df_t.rename(columns={"count": topic}),
                                    on="date", how="left")

gdelt_daily = gdelt_daily.fillna(0)

# Log-transform: GEI_topic = log(1 + count)
for topic in TOPICS:
    if topic in gdelt_daily.columns:
        gdelt_daily[f"log_{topic}"] = np.log1p(gdelt_daily[topic])

print(f"GDELT daily rows: {len(gdelt_daily)}")
print("Sample (invasion day):")
inv = gdelt_daily[gdelt_daily["date"] == "2022-02-24"]
if len(inv) > 0:
    print(inv[["date"] + list(TOPICS.keys())].to_string())


# ─────────────────────────────────────────────
# DOWNLOAD HEADLINES FOR FINBERT (top firms only)
# ─────────────────────────────────────────────
print("\nDownloading sample headlines for FinBERT (top defense firms)...")

FIRM_QUERIES = {
    "Lockheed Martin": '"Lockheed Martin" AND ("defense" OR "missile" OR "contract")',
    "RTX":             '"Raytheon" OR "RTX" AND ("defense" OR "missile" OR "contract")',
    "Northrop Grumman": '"Northrop Grumman" AND ("defense" OR "B-21" OR "missile")',
    "BAE Systems":     '"BAE Systems" AND ("defense" OR "contract" OR "weapons")',
    "Rheinmetall":     '"Rheinmetall" AND ("defense" OR "ammunition" OR "tanks")',
    "Leonardo":        '"Leonardo" AND ("defense" OR "helicopter" OR "missile")',
    "Thales":          '"Thales" AND ("defense" OR "radar" OR "surveillance")',
    "Airbus":          '"Airbus" AND ("defense" OR "military" OR "contract")',
}

headline_records = []
sample_start = datetime.date(2022, 1, 1)
sample_end   = datetime.date(2026, 6, 1)
sample_batches = generate_batches(sample_start, sample_end, 6)  # 6-month batches

for firm, query in FIRM_QUERIES.items():
    print(f"  {firm}...")
    for (s, e) in sample_batches:
        articles = gdelt_doc_query(query, s, e, mode="artlist", max_records=50)
        for art in articles:
            headline_records.append({
                "firm":     firm,
                "date":     art.get("seendate", "")[:8],
                "title":    art.get("title", ""),
                "url":      art.get("url", ""),
                "language": art.get("language", ""),
            })
        time.sleep(1)

headlines_df = pd.DataFrame(headline_records)
if len(headlines_df) > 0:
    # Keep English headlines only (for FinBERT)
    headlines_df = headlines_df[headlines_df["language"] == "English"].copy()
    headlines_df["date"] = pd.to_datetime(headlines_df["date"], format="%Y%m%d",
                                          errors="coerce")
    headlines_out = os.path.join(RAW_GDELT, "headlines_for_finbert.csv")
    headlines_df.to_csv(headlines_out, index=False)
    print(f"  Saved {len(headlines_df)} headlines to headlines_for_finbert.csv")
else:
    print("  No headlines downloaded (API may be unavailable).")


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_path = os.path.join(PROC, "gdelt_topics_daily.csv")
gdelt_daily.to_csv(out_path, index=False)
print(f"\nSaved gdelt_topics_daily.csv - {len(gdelt_daily)} rows")
print("Script 08 complete.")
