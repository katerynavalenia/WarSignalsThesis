"""Long-history equity data from Yahoo's chart endpoint.

``docs/v3/data_sources.md`` §2 records that Yahoo returns 429 and Stooq serves a
JavaScript challenge, and concludes the equity half of the spine cannot be built
without a keyed vendor. That is true of a **cloud session**, whose shared egress
IP is rate-limited — it is not true from a residential connection, where the same
endpoint serves full history for every ticker the thesis needs, including
``^STOXX`` (STOXX Europe 600), the European benchmark the Bloomberg-only preview
had to substitute SP500 for.

So this module exists to make the 2015–2026 sample reachable with no credential
and no vendor. The Bloomberg indices remain the referee on their 2020–2026
overlap (``docs/v3/equity_validation.md``); nothing here replaces them.

Deliberately no ``yfinance`` dependency: the chart endpoint is one HTTP call
returning JSON, and owning the parse keeps the failure modes visible instead of
buried in a library that changes its scraping strategy between releases.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

import pandas as pd

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

#: Yahoo rejects the default urllib agent.
_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

#: Defence names, chosen for listing history reaching 2015 and for spanning the
#: SIPRI exposure spectrum. Hensoldt (IPO 2020) and Renk (IPO 2024) are excluded
#: — a basket must not silently change composition mid-sample.
US_DEFENCE = ["LMT", "RTX", "NOC", "GD", "LHX", "HII", "BA"]
EU_DEFENCE = ["RHM.DE", "HO.PA", "BA.L", "LDO.MI", "SAAB-B.ST", "AM.PA"]

#: Sector ETFs — an independent cross-check on the hand-built baskets.
ETFS = ["ITA", "XAR", "PPA"]

#: Regional benchmarks. ^STOXX is the control BSHIELDT actually needs; the
#: Bloomberg-only preview had to use SP500 for both, which was its main caveat.
BENCHMARKS = {"^GSPC": "spx", "^STOXX": "sxxp", "^VIX": "vix_yf"}


def fetch_chart(
    ticker: str,
    start: str | date = "2014-12-01",
    end: str | date = "2026-07-01",
    retries: int = 3,
) -> pd.DataFrame:
    """Daily OHLCV for one ticker as ``date, open, high, low, close, adjclose, volume``.

    ``adjclose`` is dividend- and split-adjusted; ``close`` is not. Returns use
    ``adjclose``, but ``high``/``low`` are raw, which is what the Parkinson
    volatility estimator wants — mixing the two would misstate the range.
    """
    p1 = int(datetime.combine(pd.Timestamp(start).date(), datetime.min.time(), timezone.utc).timestamp())
    p2 = int(datetime.combine(pd.Timestamp(end).date(), datetime.min.time(), timezone.utc).timestamp())
    url = f"{CHART_URL.format(ticker=ticker)}?period1={p1}&period2={p2}&interval=1d"

    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=_HEADERS), timeout=60
            ) as r:
                payload = json.load(r)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"{ticker}: chart request failed after {retries} tries") from last

    return parse_chart(payload, ticker)


def parse_chart(payload: dict, ticker: str) -> pd.DataFrame:
    """Turn a chart-endpoint payload into a frame. Split out so tests need no network."""
    result = (payload.get("chart") or {}).get("result")
    if not result:
        err = (payload.get("chart") or {}).get("error")
        raise ValueError(f"{ticker}: no result in payload ({err})")
    res = result[0]

    stamps = res.get("timestamp")
    if not stamps:
        raise ValueError(f"{ticker}: payload carries no timestamps")

    quote = res["indicators"]["quote"][0]
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(pd.Series(stamps), unit="s", utc=True)
            .dt.tz_localize(None)
            .dt.normalize()
            .astype("datetime64[ns]"),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        }
    )
    adj = (res.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    frame["adjclose"] = adj if adj is not None else frame["close"]

    frame = frame.dropna(subset=["close"]).drop_duplicates(subset="date", keep="last")
    return frame.sort_values("date").reset_index(drop=True)


def fetch_many(tickers: list[str], pause: float = 0.4, **kwargs) -> dict[str, pd.DataFrame]:
    """Fetch several tickers, pausing between calls to stay polite.

    A ticker that fails is reported and skipped rather than aborting the run —
    an eleven-year pull should not be lost to one delisted symbol.
    """
    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            out[t] = fetch_chart(t, **kwargs)
        except (RuntimeError, ValueError) as exc:
            print(f"  SKIP {t}: {exc}")
            continue
        time.sleep(pause)
    return out


def build_basket(
    frames: dict[str, pd.DataFrame], weighting: str = "equal"
) -> pd.Series:
    """Combine per-ticker frames into one daily basket return series, in percent.

    ``equal`` rebalances daily to equal weights — the transparent default. It is
    also the conservative one here: a cap-weighted European basket would be
    dominated by Rheinmetall, whose 2022 move alone could carry the result
    (``docs/v3/equity_validation.md`` §1).

    Constituents are *not* required to span the whole window; a ticker
    contributes on the days it has data, and the daily cross-sectional mean is
    taken over whatever is present. The count of contributors per day is what
    makes that honest, so callers should keep :func:`basket_coverage` alongside.
    """
    if weighting != "equal":
        raise ValueError(f"unsupported weighting: {weighting!r}")
    rets = {}
    for t, f in frames.items():
        s = f.set_index("date")["adjclose"].astype(float)
        rets[t] = 100.0 * (s / s.shift(1)).apply(_safe_log)
    wide = pd.DataFrame(rets).sort_index()
    return wide.mean(axis=1, skipna=True).rename("basket_return")


def basket_coverage(frames: dict[str, pd.DataFrame]) -> pd.Series:
    """How many constituents actually contribute on each day."""
    present = {
        t: f.set_index("date")["adjclose"].notna() for t, f in frames.items()
    }
    return pd.DataFrame(present).sort_index().sum(axis=1).rename("n_constituents")


def _safe_log(x: float) -> float:
    import math

    return math.log(x) if isinstance(x, float) and x > 0 else float("nan")
