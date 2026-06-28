"""
GDELT Media Expectation Index Download
=======================================
Downloads daily normalized article counts for defense-related topics
from the GDELT DOC 2.0 API, covering 2020-01-01 to today.

Output: data/raw/gdelt_topics_daily.csv
Columns: date, topic, article_volume_norm
"""

import requests
import pandas as pd
import time
import os
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Output folder ────────────────────────────────────────────────────────────
OUT_DIR = r"C:\Users\A00010311\Downloads\Master Thesis\data\raw"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Defense topic queries for GDELT ─────────────────────────────────────────
# Each key becomes a column in the output. Queries use GDELT boolean syntax.
TOPICS = {
    "ukraine_war":      '"Ukraine war" OR "Russian invasion" OR "war in Ukraine"',
    "rearmament":       '"NATO rearmament" OR "European rearmament" OR "rearmament"',
    "military_aid":     '"military aid" OR "weapons Ukraine" OR "arms delivery Ukraine"',
    "defense_spending": '"defense spending" OR "defence spending" OR "military spending"',
    "weapons_demand":   '"ammunition shortage" OR "weapons demand" OR "artillery shells"',
    "missiles_drones":  '"missile defense" OR "air defense" OR "drone warfare" OR "drone strike"',
    "procurement":      '"defense contract" OR "defense procurement" OR "arms deal"',
}

# ── Date batching: split into yearly chunks to stay within API limits ────────
START_DATE = datetime(2020, 1, 1)
END_DATE   = datetime.today()

def make_yearly_batches(start, end):
    """Split date range into yearly batches."""
    batches = []
    current = start
    while current < end:
        batch_end = min(datetime(current.year, 12, 31), end)
        batches.append((current, batch_end))
        current = datetime(current.year + 1, 1, 1)
    return batches

# ── GDELT DOC 2.0 API query ──────────────────────────────────────────────────
def query_gdelt(query, start_dt, end_dt, retries=3):
    """
    Query GDELT DOC 2.0 timeline for normalized article volume.
    Returns a DataFrame with columns: date, value
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query":          query,
        "mode":           "timelinevolnorm",   # normalized % of all articles
        "startdatetime":  start_dt.strftime("%Y%m%d000000"),
        "enddatetime":    end_dt.strftime("%Y%m%d235959"),
        "format":         "json",
        "TIMELINERES":    "DAY",
    }

    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60, verify=False)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code}, retrying ({attempt+1}/{retries})")
                time.sleep(5)
                continue

            data = r.json()

            if "timeline" not in data or not data["timeline"]:
                print(f"    No timeline data in response")
                return pd.DataFrame(columns=["date", "value"])

            series = data["timeline"][0].get("data", [])
            if not series:
                return pd.DataFrame(columns=["date", "value"])

            df = pd.DataFrame(series)
            df.columns = ["date", "value"]
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d%H%M%S").dt.date
            df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
            return df

        except Exception as e:
            print(f"    Error: {e}, retrying ({attempt+1}/{retries})")
            time.sleep(10)

    return pd.DataFrame(columns=["date", "value"])


# ── Main download loop ────────────────────────────────────────────────────────
all_results = []
batches = make_yearly_batches(START_DATE, END_DATE)

print(f"Downloading GDELT data: {START_DATE.date()} to {END_DATE.date()}")
print(f"Topics: {len(TOPICS)}  |  Yearly batches: {len(batches)}")
print("=" * 60)

for topic_name, query in TOPICS.items():
    print(f"\n[Topic] {topic_name}")
    topic_frames = []

    for batch_start, batch_end in batches:
        print(f"  Batch {batch_start.year}: {batch_start.date()} -> {batch_end.date()}", end=" ... ")
        df_batch = query_gdelt(query, batch_start, batch_end)

        if df_batch.empty:
            print("no data")
        else:
            df_batch["topic"] = topic_name
            topic_frames.append(df_batch)
            print(f"{len(df_batch)} days")

        time.sleep(2)   # be polite to the API

    if topic_frames:
        topic_df = pd.concat(topic_frames, ignore_index=True)
        all_results.append(topic_df)
        # Save intermediate result per topic
        topic_df.to_csv(os.path.join(OUT_DIR, f"gdelt_{topic_name}.csv"), index=False)
        print(f"  Saved {len(topic_df)} total rows for '{topic_name}'")

# ── Combine all topics into a wide-format panel ──────────────────────────────
if all_results:
    combined = pd.concat(all_results, ignore_index=True)

    # Pivot: rows = dates, columns = topics
    wide = combined.pivot_table(index="date", columns="topic", values="value", aggfunc="first")
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index()

    # Compute log(1 + value) for each topic
    for col in wide.columns:
        wide[f"log_{col}"] = (1 + wide[col]).apply(lambda x: x if pd.isna(x) else __import__("math").log(1 + x))

    out_path = os.path.join(OUT_DIR, "gdelt_topics_daily.csv")
    wide.to_csv(out_path)
    print(f"\n{'='*60}")
    print(f"Done! Combined file saved to: {out_path}")
    print(f"Shape: {wide.shape}")
    print(f"Date range: {wide.index.min().date()} to {wide.index.max().date()}")
    print(f"Columns: {list(wide.columns)}")
else:
    print("\nNo data downloaded. Check your internet connection.")
