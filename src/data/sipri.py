"""SIPRI arms-revenue exposure, and the listed firms it can be matched to.

The design's fifth question asked whether the market prices a firm's *own* war
exposure — whether pure-play defence producers respond more to conflict than
diversified industrials. It was dropped because the firm-level panel and the
SIPRI matching from earlier phases no longer exist anywhere.

They do not need to. SIPRI publishes the Top-100 arms-producing companies
openly, with arms revenue and total revenue per firm per year, which is the
exposure measure the question needs. Prices come from the same free endpoint the
rest of the equity spine uses. The question is recoverable without the lost data.

**The name-to-ticker map is hand-curated rather than fuzzy-matched.** Fuzzy
matching over company names is exactly where a silent error would enter: "General
Dynamics" and "General Electric" are close in string distance and nothing alike
in exposure, and a mismatch would attach the wrong exposure to the wrong returns
without failing any test. The map below covers the listed firms with continuous
price history over the sample; state-owned and unlisted producers are
deliberately absent because they have no returns to explain.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: SIPRI company name -> Yahoo ticker, for listed firms with history to 2015.
#: Names are matched on SIPRI's own spelling, which varies across years; the
#: parser normalises before lookup.
SIPRI_TO_TICKER: dict[str, str] = {
    "lockheed martin corp.": "LMT",
    "lockheed martin": "LMT",
    "raytheon technologies": "RTX",
    "rtx": "RTX",
    "raytheon co.": "RTX",
    "northrop grumman corp.": "NOC",
    "northrop grumman": "NOC",
    "boeing": "BA",
    "the boeing company": "BA",
    "general dynamics corp.": "GD",
    "general dynamics": "GD",
    "l3harris technologies": "LHX",
    "l3 technologies": "LHX",
    "huntington ingalls industries": "HII",
    "bae systems": "BA.L",
    "rolls-royce": "RR.L",
    "babcock international group": "BAB.L",
    "thales": "HO.PA",
    "airbus": "AIR.PA",
    "airbus group": "AIR.PA",
    "safran": "SAF.PA",
    "dassault aviation": "AM.PA",
    "leonardo": "LDO.MI",
    "finmeccanica": "LDO.MI",
    "fincantieri": "FCT.MI",
    "rheinmetall": "RHM.DE",
    "hensoldt": "HAG.DE",
    "thyssenkrupp": "TKA.DE",
    "saab": "SAAB-B.ST",
    "kongsberg gruppen": "KOG.OL",
    "leidos": "LDOS",
    "booz allen hamilton": "BAH",
    "caci international": "CACI",
    "textron": "TXT",
    "honeywell international": "HON",
    "general electric": "GE",
    "elbit systems": "ESLT",
    "mitsubishi heavy industries": "7011.T",
    "kawasaki heavy industries": "7012.T",
    "singapore technologies engineering": "S63.SI",
    "hanwha aerospace": "012450.KS",
    "korea aerospace industries": "047810.KS",
}


def _normalise(name: str) -> str:
    s = str(name).strip().lower()
    for junk in (" corp.", " corporation", " co.", " inc.", " plc", " ltd",
                 " group", " company", " sa", " spa", " ab", " asa", " se"):
        if s.endswith(junk):
            s = s[: -len(junk)].strip()
    return s


def parse_sipri(path: str | Path) -> pd.DataFrame:
    """Read every yearly sheet into a long ``year, company, country, arms_share`` table.

    ``arms_share`` is arms revenue over total revenue — the standard continuous
    exposure measure, bounded to [0, 1]. Firms reporting arms revenue without
    total revenue (common for divisions of private groups) yield a missing share
    rather than an imputed one.
    """
    xl = pd.ExcelFile(path)
    frames = []
    for sheet in xl.sheet_names:
        if not sheet.strip().isdigit():
            continue
        year = int(sheet.strip())
        raw = xl.parse(sheet, header=3)
        cols = {str(c).strip().lower(): c for c in raw.columns}

        def find(*keys):
            for k, orig in cols.items():
                if all(t in k for t in keys):
                    return orig
            return None

        c_company = find("company")
        c_country = find("country")
        c_arms = find("arms revenues", str(year)) or find("arms revenues")
        c_total = find("total revenues")
        if not all([c_company, c_arms, c_total]):
            continue

        d = raw[[c for c in (c_company, c_country, c_arms, c_total) if c]].copy()
        d.columns = ["company", "country", "arms", "total"][: d.shape[1]]
        d = d[d["company"].notna()]
        for c in ("arms", "total"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["year"] = year
        d["arms_share"] = (d["arms"] / d["total"]).clip(0, 1)
        frames.append(d)

    out = pd.concat(frames, ignore_index=True)
    out["key"] = out["company"].map(_normalise)
    return out[["year", "company", "key", "country", "arms", "total", "arms_share"]]


def match_tickers(sipri: pd.DataFrame) -> pd.DataFrame:
    """Attach tickers, keeping only firms in the curated map.

    Returns one row per (ticker, year) with the exposure measure. Firms appearing
    under several SIPRI spellings collapse onto one ticker.
    """
    d = sipri.copy()
    d["ticker"] = d["key"].map(SIPRI_TO_TICKER)
    matched = d[d["ticker"].notna()].copy()
    return (
        matched.groupby(["ticker", "year"], as_index=False)
        .agg(company=("company", "first"), country=("country", "first"),
             arms=("arms", "sum"), total=("total", "max"),
             arms_share=("arms_share", "mean"))
        .sort_values(["ticker", "year"])
    )


def exposure_panel(matched: pd.DataFrame) -> pd.DataFrame:
    """One exposure value per ticker: the mean arms share over available years.

    A firm's arms share moves slowly, and using a time-varying value would make
    the exposure gradient partly a story about firms changing business mix rather
    than about the market pricing exposure. The mean over the sample is the
    stable summary the question needs; ``years`` records how much it rests on.
    """
    g = matched.groupby("ticker").agg(
        company=("company", "first"),
        country=("country", "first"),
        arms_share=("arms_share", "mean"),
        years=("year", "nunique"),
        last_year=("year", "max"),
    )
    return g.sort_values("arms_share", ascending=False)
