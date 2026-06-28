import requests, pandas as pd
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://api.gdeltproject.org/api/v2/doc/doc"
params = {
    "query": '"Ukraine war" OR "Russian invasion"',
    "mode": "timelinevolnorm",
    "startdatetime": "20220201000000",
    "enddatetime": "20220310235959",
    "format": "json",
    "TIMELINERES": "DAY"
}
r = requests.get(url, params=params, timeout=60, verify=False)
print("Status:", r.status_code)
data = r.json()
print("Keys:", list(data.keys()))
if "timeline" in data:
    series = data["timeline"][0].get("data", [])
    df = pd.DataFrame(series)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d%H%M%S").dt.date
    print("Rows returned:", len(df))
    print(df.to_string())
else:
    print("Full response:", str(data)[:1000])
