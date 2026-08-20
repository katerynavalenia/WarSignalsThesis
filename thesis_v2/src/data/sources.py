"""Free, no-credential data sources for the Phase 1 long-sample spine.

Two sources are reachable without any API key or account, and both were
verified from a cloud session on 2026-08-20:

* **GPR** — Caldara & Iacoviello's Geopolitical Risk index, daily, 1985-01-01
  onward, published as a single ``.xls`` on the author's site. Supplies
  ``GPRD``, ``GPRD_ACT`` and ``GPRD_THREAT``, which is the realized-vs-expected
  decomposition the thesis mirrors in its own indices.
* **FRED** — the St. Louis Fed's ``fredgraph.csv`` endpoint, which serves any
  public series as CSV with no key. Supplies VIX, Brent, EUR/USD, the 10-year
  Treasury yield and the broad dollar index.

Equity prices are deliberately *not* here. Yahoo Finance rate-limits this
environment's shared egress IP and Stooq is behind a JavaScript challenge, so
the defence-equity panel comes from Bloomberg (2020 onward, already collected)
or from a keyed vendor. See ``docs/v3/phase1_data_sources.md``.
"""

from __future__ import annotations

import io
from typing import Iterable

import pandas as pd
import requests

GPR_DAILY_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

#: FRED series id -> the column name used throughout the thesis.
FRED_SERIES: dict[str, str] = {
    "VIXCLS": "vix",
    "DCOILBRENTEU": "brent",
    "DEXUSEU": "usd_eur",
    "DGS10": "ust10y",
    "DTWEXBGS": "usd_broad",
}

_TIMEOUT = 180


def _get(url: str, params: dict | None = None) -> bytes:
    r = requests.get(url, params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.content


def fetch_gpr_daily(url: str = GPR_DAILY_URL) -> pd.DataFrame:
    """Download and clean the daily GPR index.

    Returns ``date, gpr, gpr_act, gpr_threat`` with ``date`` as a regular
    first column of dtype ``datetime64[ns]`` — the repo-wide convention.

    The workbook ships both a ``DAY`` column (integer ``YYYYMMDD``) and a
    ``date`` column. ``DAY`` is parsed here because it is unambiguous;
    ``pd.read_excel`` has historically mangled the ``date`` column into
    nanoseconds-since-epoch on some pandas versions.
    """
    raw = pd.read_excel(io.BytesIO(_get(url)))
    return parse_gpr_frame(raw)


def parse_gpr_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean an already-loaded GPR workbook. Split out so tests need no network."""
    missing = {"DAY", "GPRD", "GPRD_ACT", "GPRD_THREAT"} - set(raw.columns)
    if missing:
        raise ValueError(f"GPR file is missing expected columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            # Cast to ns explicitly: pandas 3 parses to us by default, and the
            # v1 tables this must merge against are all datetime64[ns].
            "date": pd.to_datetime(
                raw["DAY"].astype("int64").astype(str), format="%Y%m%d"
            ).astype("datetime64[ns]"),
            "gpr": pd.to_numeric(raw["GPRD"], errors="coerce"),
            "gpr_act": pd.to_numeric(raw["GPRD_ACT"], errors="coerce"),
            "gpr_threat": pd.to_numeric(raw["GPRD_THREAT"], errors="coerce"),
        }
    )
    if out["date"].duplicated().any():
        raise ValueError("GPR file contains duplicate dates")
    return out.sort_values("date").reset_index(drop=True)


def fetch_fred_series(series_id: str, start: str = "2015-01-01") -> pd.Series:
    """Download one FRED series as a date-indexed float Series.

    FRED writes ``.`` for missing observations on non-trading days; those become
    ``NaN`` rather than being dropped, so the caller decides how to align them.
    """
    content = _get(FRED_CSV_URL, params={"id": series_id, "cosd": start})
    frame = pd.read_csv(io.BytesIO(content))
    return parse_fred_frame(frame, series_id)


def parse_fred_frame(frame: pd.DataFrame, series_id: str) -> pd.Series:
    """Clean an already-loaded FRED CSV. Split out so tests need no network."""
    date_col = frame.columns[0]  # "observation_date" (or legacy "DATE")
    value_col = series_id if series_id in frame.columns else frame.columns[1]
    s = pd.Series(
        pd.to_numeric(frame[value_col], errors="coerce").to_numpy(),
        index=pd.to_datetime(frame[date_col]),
        name=FRED_SERIES.get(series_id, series_id.lower()),
    )
    s.index.name = "date"
    return s.sort_index()


def fetch_fred_panel(
    series: Iterable[str] | None = None, start: str = "2015-01-01"
) -> pd.DataFrame:
    """Download several FRED series and join them on date.

    Returns a frame with ``date`` as a regular first column.
    """
    ids = list(series) if series is not None else list(FRED_SERIES)
    joined = pd.concat([fetch_fred_series(i, start=start) for i in ids], axis=1)
    return joined.sort_index().reset_index()
