import requests, urllib3
urllib3.disable_warnings()
url = "https://api.gdeltproject.org/api/v2/doc/doc"
params = {
    "query": "Ukraine defense",
    "mode": "timelinevol",
    "format": "json",
    "STARTDATETIME": "20220224000000",
    "ENDDATETIME": "20220228000000",
    "TIMESPAN": "CUSTOM"
}
try:
    r = requests.get(url, params=params, timeout=20, verify=False)
    print("Status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        print("Keys:", list(data.keys()))
        tl = data.get("timeline", [{}])
        pts = len(tl[0].get("data", [])) if tl else 0
        print("Timeline points:", pts)
    else:
        print("Body:", r.text[:300])
except Exception as e:
    print("ERROR:", e)
