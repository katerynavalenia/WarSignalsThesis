"""Loaders for the Bloomberg defence-index workbooks.

``WAERLST Index.xlsx`` (global A&D, USD) and ``BSHIELDT Index.xlsx`` (European
defence, EUR) are the only proprietary series that survived the v1/v2 data
attrition, and they are why a long-sample analysis is possible before the
free-basket question (``docs/v3/phase1_equity_validation.md``) is settled: they
cover **2020-01-01 → 2026-06-30**, which already contains the 2021 build-up and
the February-2022 re-rating that the reviewed paper missed.

The workbooks are Bloomberg's standard export: five metadata rows (security,
start, end, period, currency), a blank row, then a ``Date / PX_LAST /
PX_VOLUME`` header and the observations in *reverse* chronological order.
Parsing is split from reading so the test suite never needs the files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

#: Workbook stem -> the column name used for that index throughout the thesis.
INDICES: dict[str, str] = {
    "WAERLST": "waerlst",
    "BSHIELDT": "bshieldt",
}


def parse_index_workbook(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean one already-loaded Bloomberg export (read with ``header=None``).

    Returns ``date, px, volume`` sorted ascending, with ``date`` as a plain
    ``datetime64[ns]`` column — the repo-wide convention.
    """
    header_rows = raw.index[raw[0].astype(str).str.strip() == "Date"]
    if len(header_rows) != 1:
        raise ValueError(
            f"expected exactly one 'Date' header row, found {len(header_rows)}"
        )
    start = int(header_rows[0]) + 1

    body = raw.loc[start:, [0, 1, 2]].copy()
    body.columns = ["date", "px", "volume"]
    body["date"] = pd.to_datetime(body["date"], errors="coerce").astype(
        "datetime64[ns]"
    )
    for col in ("px", "volume"):
        body[col] = pd.to_numeric(body[col], errors="coerce")

    body = body.dropna(subset=["date", "px"])
    if body["date"].duplicated().any():
        raise ValueError("workbook contains duplicate dates")
    return body.sort_values("date").reset_index(drop=True)


def read_index_workbook(path: str | Path) -> pd.DataFrame:
    """Read and clean one Bloomberg index export from disk."""
    return parse_index_workbook(pd.read_excel(path, header=None))


def load_indices(raw_dir: str | Path) -> pd.DataFrame:
    """Load every workbook in :data:`INDICES` and join them on date.

    ``raw_dir`` is the directory holding ``<STEM> Index.xlsx`` — in this repo
    ``thesis_v1/data/raw/bloomberg``. The files are gitignored; they are also
    mirrored to Drive at ``WarSignalsThesis_Data/data/raw/bloomberg/``.
    """
    raw_dir = Path(raw_dir)
    frames = []
    for stem, col in INDICES.items():
        one = read_index_workbook(raw_dir / f"{stem} Index.xlsx")
        frames.append(one.set_index("date")["px"].rename(col))
    return pd.concat(frames, axis=1).sort_index().reset_index()


def add_return_features(
    panel: pd.DataFrame, columns: list[str] | None = None, rv_window: int = 5
) -> pd.DataFrame:
    """Attach log returns and two volatility proxies to a price panel.

    For each price column ``c`` adds:

    ``r_c``
        daily log return in percent.
    ``vol_c``
        ``|r_c|``, the absolute-return proxy v2 used — kept so its results stay
        directly comparable.
    ``rv{rv_window}_c``
        rolling realized volatility, the root mean squared return over
        ``rv_window`` days. Less noisy than ``|r|``, and the quantity a
        HAR-type model actually targets.

    Returns are *not* currency-adjusted: BSHIELDT is quoted in EUR and WAERLST
    in USD, which matters for level comparisons but not for the standardized
    within-index regressions this module feeds.
    """
    out = panel.copy()
    cols = columns if columns is not None else [c for c in INDICES.values() if c in out]
    for c in cols:
        r = 100.0 * np.log(out[c]).diff()
        out[f"r_{c}"] = r
        out[f"vol_{c}"] = r.abs()
        out[f"rv{rv_window}_{c}"] = (
            r.pow(2).rolling(rv_window, min_periods=rv_window).mean().pow(0.5)
        )
    return out
