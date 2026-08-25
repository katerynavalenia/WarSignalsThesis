"""Diagnose which GDELT stream the v1 news indicators were built from.

Motivation
----------
`thesis_v1/gkg_bulk_download.py` downloads from
``http://data.gdeltproject.org/gkg/YYYYMMDD.gkg.csv.zip`` — the **GKG 1.0
daily** stream. The Phase 3 audits describe the resulting Ukrainian / Russian /
Western tone series as "multilingual". This script checks that claim directly by
sampling single days from three GDELT streams and reporting, per stream:

* number of records,
* top-level-domain composition (proxy for *where the outlet is*),
* source-language composition (``srclc:`` in the V2.1 TranslationInfo field),
* the number of ``.ru`` / ``.ua`` outlets actually present.

Run
---
    python thesis_v2/scripts/diagnose_gdelt_streams.py
    python thesis_v2/scripts/diagnose_gdelt_streams.py --dates 20160301 20220301

Findings are written up in ``docs/v3/gdelt_measurement_diagnosis.md``.
"""

from __future__ import annotations

import argparse
import collections
import io
import zipfile

import requests

V1_DAILY = "http://data.gdeltproject.org/gkg/{d}.gkg.csv.zip"
V2_ENGLISH = "http://data.gdeltproject.org/gdeltv2/{d}120000.gkg.csv.zip"
V2_TRANSLINGUAL = "http://data.gdeltproject.org/gdeltv2/{d}120000.translation.gkg.csv.zip"

DEFAULT_DATES = ["20160301", "20200301", "20250301"]


def _fetch(url: str) -> str | None:
    r = requests.get(url, timeout=300)
    if r.status_code != 200:
        return None
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        return zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")


def _tld(domain: str) -> str:
    domain = domain.strip().lower()
    return domain.rsplit(".", 1)[-1] if "." in domain else ""


def scan_v1(csv_text: str) -> dict:
    """GKG 1.0 daily: tab-separated, field 9 = SOURCES (semicolon-joined)."""
    tld = collections.Counter()
    rows = 0
    for line in csv_text.splitlines():
        fields = line.split("\t")
        if len(fields) < 11 or not line.startswith("20"):
            continue
        rows += 1
        for src in fields[9].split(";"):
            if src.strip():
                tld[_tld(src)] += 1
    return {"rows": rows, "tld": tld, "lang": collections.Counter({"(no language field)": rows})}


def scan_v2(csv_text: str) -> dict:
    """GKG 2.0 (English or translingual): 27 columns.

    Column 3 = V2SourceCommonName, column 25 = V2.1TranslationInfo
    (``srclc:<lang>;srclang:<engine>``). Records with no TranslationInfo are
    natively English.
    """
    tld = collections.Counter()
    lang = collections.Counter()
    rows = 0
    for line in csv_text.splitlines():
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 26:
            continue
        rows += 1
        tld[_tld(fields[3])] += 1
        info = next((f for f in fields if "srclc:" in f), "")
        lang[info.split("srclc:")[1].split(";")[0] if info else "eng (native)"] += 1
    return {"rows": rows, "tld": tld, "lang": lang}


def report(label: str, url: str, scan) -> None:
    text = _fetch(url)
    if text is None:
        print(f"\n### {label}\n  UNAVAILABLE: {url}")
        return
    out = scan(text)
    tld, lang = out["tld"], out["lang"]
    print(f"\n### {label}\n  url:            {url}")
    print(f"  records:        {out['rows']:,}")
    print(f"  top TLDs:       {tld.most_common(8)}")
    print(f"  .ru / .ua:      {tld.get('ru', 0):,} / {tld.get('ua', 0):,}")
    print(f"  top languages:  {lang.most_common(8)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dates", nargs="+", default=DEFAULT_DATES,
                    help="YYYYMMDD dates to sample (default: %(default)s)")
    args = ap.parse_args()

    for d in args.dates:
        print("=" * 72)
        print(f"DATE {d}")
        print("=" * 72)
        report("GKG 1.0 daily  (stream used by thesis_v1)", V1_DAILY.format(d=d), scan_v1)
        report("GKG 2.0 English (12:00 slice)", V2_ENGLISH.format(d=d), scan_v2)
        report("GKG 2.0 TRANSLINGUAL (12:00 slice)", V2_TRANSLINGUAL.format(d=d), scan_v2)


if __name__ == "__main__":
    main()
