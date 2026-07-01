"""
Date utilities for Phase 5 merge and feature engineering.

Provides:
- ``standardize_date_column`` — ensure ``date`` is a regular ``datetime64[ns]`` column
  (handles index, integer YYYYMMDD, string, and existing-datetime inputs).
- ``build_calendar_index`` — produce a clean calendar-day index.
- ``is_trading_day`` — Mon–Fri flag (with optional US-holiday list).
- ``shift_to_next_trading_day`` — bump a date forward to the next trading day
  (used for the §9 weekend rule: Friday close → Monday pre-market).

Per the 2026-06-30 decision log, all processed tables in Phase 5+ must have
``date`` as a regular (non-index) ``datetime64[ns]`` column.
"""
from __future__ import annotations

from datetime import date as _date, timedelta
from typing import Iterable, Optional, Set, Union

import numpy as np
import pandas as pd

# Hardcoded US federal market holidays 2020-2026 (observed dates, not always exact).
# This list is sufficient for the Phase 5 modeling window (2022-09-29 → 2026-06-21).
_US_FEDERAL_HOLIDAYS_DT: pd.DatetimeIndex = pd.to_datetime([
    # 2020
    "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25",
    "2020-07-03", "2020-09-07", "2020-10-12", "2020-11-11", "2020-11-26",
    "2020-12-25",
    # 2021
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31",
    "2021-07-05", "2021-09-06", "2021-10-11", "2021-11-11", "2021-11-25",
    "2021-12-24",
    # 2022
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20",
    "2022-07-04", "2022-09-05", "2022-10-10", "2022-11-11", "2022-11-24",
    "2022-12-26",
    # 2023
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
    "2023-06-19", "2023-07-04", "2023-09-04", "2023-10-09", "2023-11-10",
    "2023-11-23", "2023-12-25",
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-10-14", "2024-11-11",
    "2024-11-28", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-10-13", "2025-11-11",
    "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-10-12", "2026-11-11",
    "2026-11-26", "2026-12-25",
])

US_FEDERAL_HOLIDAYS: Set[_date] = {_d.date() for _d in _US_FEDERAL_HOLIDAYS_DT}


def standardize_date_column(
    df: pd.DataFrame,
    date_col: str = "date",
    int_format: str = "%Y%m%d",
) -> pd.DataFrame:
    """Return a copy of ``df`` with ``date_col`` as a regular ``datetime64[ns]`` column.

    Handles the four date representations found across the Phase 1–3 outputs:

    1. ``date`` is the **named** index (financial, attack tables).
    2. ``date`` is an **unnamed** ``DatetimeIndex`` / ``Int64Index``.
    3. ``date`` is already a regular column with ``int`` dtype (YYYYMMDD ints,
       as in ``news_query_group_pivot``).
    4. ``date`` is already a regular column with ``object`` or ``datetime64`` dtype.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    date_col : str, default ``"date"``
        Name of the date column (or the index name to reset).
    int_format : str, default ``"%Y%m%d"``
        ``strftime`` format used when ``date_col`` is integer-typed
        (e.g. ``20220929`` → ``2022-09-29``).

    Returns
    -------
    pd.DataFrame
        Copy of ``df`` with ``date_col`` as a regular ``datetime64[ns]`` column
        in chronological order of the original (no sorting performed).

    Raises
    ------
    ValueError
        If ``date_col`` cannot be located in the index or columns.
    """
    out = df.copy()

    # Step 1 — locate the date column. If it's not a regular column, try to
    # promote it from the index. We only auto-promote a *datetime* index
    # (the integer-index path is taken care of by the `pd.to_datetime` cast
    # below once a column exists; auto-detecting RangeIndex would mis-classify
    # default pandas indices as dates).
    if date_col not in out.columns:
        if out.index.name == date_col:
            out = out.reset_index()
        elif (
            out.index.name is None
            and pd.api.types.is_datetime64_any_dtype(out.index)
        ):
            out = out.reset_index()
            if out.columns[0] != date_col:
                out = out.rename(columns={out.columns[0]: date_col})
        else:
            raise ValueError(
                f"Column '{date_col}' not found in DataFrame "
                f"(columns={list(out.columns)}, index_name={out.index.name!r}, "
                f"index_dtype={out.index.dtype})"
            )

    # Step 2 — cast to datetime64[ns].
    col = out[date_col]
    if pd.api.types.is_integer_dtype(col):
        # YYYYMMDD ints (news_query_group_pivot)
        out[date_col] = pd.to_datetime(col.astype(str), format=int_format)
    elif not pd.api.types.is_datetime64_any_dtype(col):
        out[date_col] = pd.to_datetime(col)

    return out


def build_calendar_index(
    start: Union[str, pd.Timestamp, _date],
    end: Union[str, pd.Timestamp, _date],
    freq: str = "D",
) -> pd.DatetimeIndex:
    """Return a clean ``DatetimeIndex`` from ``start`` to ``end`` (both inclusive).

    Parameters
    ----------
    start, end : str, Timestamp, or ``datetime.date``
        Inclusive endpoints.
    freq : str, default ``"D"``
        Pandas frequency string (``"D"`` = daily, ``"B"`` = business-day, …).

    Returns
    -------
    pd.DatetimeIndex
        One entry per date in the range.
    """
    return pd.date_range(start=start, end=end, freq=freq)


def _coerce_to_date(d: Union[str, pd.Timestamp, _date]) -> _date:
    """Coerce ``str`` / ``Timestamp`` / ``datetime.date`` to a ``datetime.date``."""
    if isinstance(d, _date) and not isinstance(d, pd.Timestamp):
        return d
    if isinstance(d, pd.Timestamp):
        return d.date()
    if isinstance(d, str):
        return pd.to_datetime(d).date()
    raise TypeError(f"Cannot coerce {type(d).__name__} to datetime.date")


def is_trading_day(
    d: Union[str, pd.Timestamp, _date],
    holidays: Union[str, Set[_date], None] = "US",
) -> bool:
    """Return ``True`` if ``d`` is a trading day (Mon–Fri and not a holiday).

    Parameters
    ----------
    d : str, Timestamp, or ``datetime.date``
        Date to check.
    holidays : {"US", None, set of ``datetime.date``}, default ``"US"``
        - ``"US"`` — use the hardcoded ``US_FEDERAL_HOLIDAYS`` set.
        - ``None`` — no holiday filter (only Mon–Fri check).
        - ``set`` — custom holiday set (e.g. ``{date(2024, 1, 2)}``).

    Returns
    -------
    bool
    """
    d = _coerce_to_date(d)
    if d.weekday() >= 5:
        return False
    if holidays is None:
        return True
    if holidays == "US":
        return d not in US_FEDERAL_HOLIDAYS
    return d not in holidays


def shift_to_next_trading_day(
    d: Union[str, pd.Timestamp, _date],
    holidays: Union[str, Set[_date], None] = "US",
) -> _date:
    """Return ``d`` if it is a trading day, else advance until the next one.

    Used for the §9 weekend rule: a feature row at date ``d`` is mapped to the
    next trading day for the *target* column.

    Parameters
    ----------
    d : str, Timestamp, or ``datetime.date``
        Date to shift.
    holidays : {"US", None, set}, default ``"US"``
        Same semantics as in :func:`is_trading_day`.

    Returns
    -------
    datetime.date
    """
    d = _coerce_to_date(d)
    current = d
    # Bound the loop to avoid infinite loops if `holidays` blocks a long stretch.
    for _ in range(10):
        if is_trading_day(current, holidays):
            return current
        current = current + timedelta(days=1)
    raise RuntimeError(
        f"shift_to_next_trading_day could not find a trading day within 10 days of {d}"
    )
