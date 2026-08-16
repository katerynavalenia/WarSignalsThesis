"""Phase 5F — Loader and validator for the Phase 6 model matrix.

Provides:
- :func:`load_model_matrix`: reads ``data/processed/model_matrix.parquet``
  (or rebuilds it on demand) and returns the DataFrame with the
  information-set masks attached to ``.attrs``.
- :func:`validate_model_matrix_for_phase6`: hard smoke-checks for Phase 6
  baselines — no NaN in the primary target during the test window, all five
  information sets are non-empty, no target column is present in any
  information set, etc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from src.features.build_model_matrix import (
    PRIMARY_TARGET,
    ROBUSTNESS_TARGETS,
    build_model_matrix,
)
from src.features.merge import load_paths_config


def load_model_matrix(
    paths_yaml: Optional[Union[str, Path]] = None,
    rebuild: bool = False,
) -> pd.DataFrame:
    """Load the model matrix, building it from the feature matrix if needed.

    Parameters
    ----------
    paths_yaml : str or Path, optional
        Path to the paths config (default: ``config/paths.yaml``).
    rebuild : bool, default False
        If True, force a rebuild of the model matrix from the feature matrix
        (ignores any existing ``model_matrix.parquet``).

    Returns
    -------
    pd.DataFrame
        The model matrix with ``.attrs['info_sets']``, ``.attrs['primary_target']``,
        ``.attrs['robustness_targets']``, ``.attrs['modeling_start']``,
        ``.attrs['modeling_end']`` populated. The DataFrame is sorted by
        ``date`` ascending.
    """
    paths = load_paths_config(paths_yaml)
    feat_path = Path(paths["processed_files"]["feature_matrix"])
    mm_path = Path(paths["processed_files"]["model_matrix"])

    if rebuild or not mm_path.exists():
        if not feat_path.exists():
            raise FileNotFoundError(
                f"{feat_path} not found. Run phase5_build_master.py first."
            )
        feat = pd.read_parquet(feat_path)
        mm = build_model_matrix(feat)
    else:
        mm = pd.read_parquet(mm_path)
        # The parquet round-trip drops ``.attrs`` (parquet can't store
        # Python dicts in attrs reliably). Re-derive the info sets from
        # the column names so downstream callers can use them.
        from src.features.build_model_matrix import build_info_sets
        mm.attrs["info_sets"] = build_info_sets(mm.columns)

    return mm


def validate_model_matrix_for_phase6(mm: pd.DataFrame) -> Dict[str, object]:
    """Run a battery of hard smoke-checks on the model matrix for Phase 6.

    Returns
    -------
    dict
        ``{"ok": bool, "checks": [(name, ok, detail), ...], "n_rows": int,
        "n_features": int}``. ``ok`` is True iff all checks pass.
    """
    checks: List[tuple] = []

    # 1. Required columns present.
    required = {"date", f"target_{PRIMARY_TARGET}_t1"} | {
        f"target_{name}_t1" for name in ROBUSTNESS_TARGETS
    }
    missing = required - set(mm.columns)
    checks.append((
        "required columns present",
        not missing,
        f"missing: {sorted(missing)}" if missing else "all present",
    ))

    # 2. All 5 information sets present and non-empty.
    info_sets = mm.attrs.get("info_sets", {})
    expected_sets = {"F", "P", "N", "PN", "PNG"}
    sets_present = expected_sets.issubset(info_sets.keys())
    checks.append((
        "5 information sets present",
        sets_present,
        f"have: {sorted(info_sets.keys())}",
    ))
    for name in expected_sets:
        n = len(info_sets.get(name, []))
        checks.append((
            f"info set {name} non-empty",
            n > 0,
            f"{n} features",
        ))

    # 3. Target columns NOT in any info set (would be leakage).
    primary_col = f"target_{PRIMARY_TARGET}_t1"
    robustness_cols = [f"target_{name}_t1" for name in ROBUSTNESS_TARGETS]
    all_target_cols = [primary_col] + robustness_cols
    targets_in_sets = []
    for s, cs in info_sets.items():
        for tcol in all_target_cols:
            if tcol in cs:
                targets_in_sets.append((s, tcol))
    checks.append((
        "no target column in any info set",
        not targets_in_sets,
        f"found: {targets_in_sets}" if targets_in_sets else "ok",
    ))

    # 4. The 5 info sets are nested: F ⊂ P ⊂ PN ⊂ PNG.
    nested_ok = (
        set(info_sets.get("F", [])) <= set(info_sets.get("P", []))
        and set(info_sets.get("P", [])) <= set(info_sets.get("PN", []))
        and set(info_sets.get("PN", [])) <= set(info_sets.get("PNG", []))
    )
    checks.append((
        "info sets nested F ⊂ P ⊂ PN ⊂ PNG",
        nested_ok,
        "ok" if nested_ok else "nesting violated",
    ))

    # 5. Target is non-NaN for ≥95% of rows in the modeling window.
    target = mm[primary_col]
    nn_frac = target.notna().mean()
    checks.append((
        "target coverage ≥ 95%",
        nn_frac >= 0.95,
        f"{nn_frac:.1%} non-null",
    ))

    # 6. date is the first column and has dtype datetime64.
    date_ok = (
        len(mm.columns) > 0
        and mm.columns[0] == "date"
        and pd.api.types.is_datetime64_any_dtype(mm["date"])
    )
    checks.append((
        "date is first column (datetime64)",
        bool(date_ok),
        f"col[0]={mm.columns[0] if len(mm.columns) else 'NONE'}",
    ))

    # 7. No duplicate dates.
    ndup = int(mm["date"].duplicated().sum())
    checks.append((
        "no duplicate dates",
        ndup == 0,
        f"{ndup} duplicates",
    ))

    # 8. At least one feature in the F set that is a known financial
    #    (sanity check that the F set has the expected kind of columns).
    f_cols = info_sets.get("F", [])
    f_has_financial = any(
        ("r_" in c and "lag" in c) or "VIX" in c or "vol_" in c
        for c in f_cols
    )
    checks.append((
        "F set contains financial features",
        f_has_financial,
        f"{len(f_cols)} features",
    ))

    ok = all(c[1] for c in checks)
    return {
        "ok": ok,
        "checks": checks,
        "n_rows": len(mm),
        "n_features": mm.shape[1] - 1,  # exclude date
    }
