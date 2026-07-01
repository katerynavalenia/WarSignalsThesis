"""Expanding-window OOS engine for the Phase 6 horse race.

This module is the workhorse of Phase 6. It takes a model matrix, a set of
model specifications, and runs an expanding-window forecast with a
fixed refit cadence (default every 20 trading days). The output is a
**long** DataFrame with one row per (date, fold, model, info_set, target,
horizon) — easy to pivot into the benchmark table.

Strict no-leakage guarantees (Master Plan §9 + §11.1):
1. ``train.max(date) < test.min(date)`` for every fold.
2. Features for the forecast at row ``t`` only see rows ``≤ t-1``
   (model matrix is pre-lagged; the engine never re-introduces a same-day
   feature).
3. GARCH / AR(1) / HistoricalMean only see returns up to the day *before*
   the forecast origin.
4. Refit only at multiples of ``refit_every`` within the test block; the
   trained model is reused on intermediate days.
5. The first training fold has at least ``min_train_obs`` rows; otherwise
   :class:`ValueError` is raised.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.features.build_model_matrix import make_train_test_split


logger = logging.getLogger(__name__)


__all__ = [
    "ExpandingWindowEngine",
    "ModelSpec",
    "run_horse_race_engine",
    "assert_no_future_data",
]


# ── Public dataclass ────────────────────────────────────────────────────────


class ModelSpec:
    """Specification of one model in the horse race.

    Parameters
    ----------
    name : str
        Short name used in the benchmark table (e.g. ``"historical_mean"``,
        ``"ridge"``, ``"garch"``).
    factory : callable
        Zero-argument callable that returns a fresh forecaster instance.
        The engine does not pass any arguments; configure defaults via the
        factory (e.g. ``lambda: RidgeForecaster(alpha=1.0)``).
    info_set : {"F", "P", "N", "PN", "PNG", None}, default "F"
        Which information set to use. Ignored for ``model_type="vol"``.
    model_type : {"returns", "vol"}, default "returns"
        ``"returns"`` models use the info-set features and predict a return
        target (``target_<X>_t<h>``). ``"vol"`` models (GARCH) are
        univariate and predict a variance target (``target_var_<X>_t<h>``).
    """

    __slots__ = ("name", "factory", "info_set", "model_type", "extra")

    def __init__(
        self,
        name: str,
        factory: Callable[[], Any],
        info_set: Optional[str] = "F",
        model_type: str = "returns",
        **extra: Any,
    ) -> None:
        if model_type not in ("returns", "vol"):
            raise ValueError(
                f"model_type must be 'returns' or 'vol', got {model_type!r}"
            )
        if model_type == "returns" and info_set is None:
            raise ValueError("returns models must specify an info_set")
        self.name = str(name)
        self.factory = factory
        self.info_set = info_set
        self.model_type = model_type
        # Phase 7.5: extra kwargs forwarded to the spec (e.g.
        # ``garch_x_info_set="F"`` for GARCH-X variants).
        self.extra = dict(extra)

    def __repr__(self) -> str:
        extra_str = (
            f", extra={self.extra!r}" if self.extra else ""
        )
        return (
            f"ModelSpec(name={self.name!r}, info_set={self.info_set!r}, "
            f"model_type={self.model_type!r}{extra_str})"
        )


# ── No-leakage guard ───────────────────────────────────────────────────────


def assert_no_future_data(
    train_dates: pd.Series,
    test_dates: pd.Series,
) -> None:
    """Raise :class:`ValueError` if any train date is ≥ any test date.

    Used as a defensive guard at every refit fold.
    """
    if len(train_dates) == 0 or len(test_dates) == 0:
        return
    train_max = pd.Timestamp(train_dates.max())
    test_min = pd.Timestamp(test_dates.min())
    if not (train_max < test_min):
        raise ValueError(
            f"LEAKAGE: train.max={train_max.date()} ≥ test.min={test_min.date()}"
        )


# ── Engine ─────────────────────────────────────────────────────────────────


class ExpandingWindowEngine:
    """Expanding-window OOS engine with strict no-leakage and refit cadence.

    Parameters
    ----------
    model_matrix : pd.DataFrame
        The model matrix (output of
        :func:`src.features.build_model_matrix.build_model_matrix`).
        Must have a ``date`` column and the appropriate ``target_*`` columns
        (set by the ``primary_target`` / ``secondary_target`` arguments).
    info_sets : dict
        ``{set_name: [column_list]}`` mapping (output of
        :func:`src.features.build_model_matrix.build_info_sets`).
    targets : list of str
        Source target column names (e.g. ``["r_ITA", "r_WAERLST_recon"]``).
        The engine looks up ``target_<name>_t<h>`` and ``target_var_<name>_t<h>``
        columns in the model matrix.
    horizons : list of int
        Forecast horizons (e.g. ``[1, 5]``).
    test_fraction : float, default 0.25
        Fraction of rows reserved for the test set.
    min_train_obs : int, default 500
        Minimum training observations required.
    refit_every : int, default 20
        Refit cadence in trading days. The model is retrained every
        ``refit_every`` rows within the test block.
    quick : bool, default False
        If True, run on the last 60 OOS days only (used for CI / dev
        smoke tests).
    quick_refit_every : int, default 5
        Refit cadence when ``quick=True``.
    random_seed : int, default 42
        Seed for any tie-breaking. GARCH has its own (deterministic) MLE.
    """

    def __init__(
        self,
        model_matrix: pd.DataFrame,
        info_sets: Dict[str, List[str]],
        targets: List[str],
        horizons: List[int],
        test_fraction: float = 0.25,
        min_train_obs: int = 500,
        refit_every: int = 20,
        quick: bool = False,
        quick_refit_every: int = 5,
        quick_n_days: int = 60,
        random_seed: int = 42,
    ) -> None:
        if "date" not in model_matrix.columns:
            raise KeyError("model_matrix must have a 'date' column")
        self.mm = model_matrix.reset_index(drop=True)
        self.info_sets = dict(info_sets)
        self.targets = list(targets)
        self.horizons = [int(h) for h in horizons]
        self.test_fraction = float(test_fraction)
        self.min_train_obs = int(min_train_obs)
        self.refit_every = int(refit_every)
        self.quick = bool(quick)
        self.quick_refit_every = int(quick_refit_every)
        self.quick_n_days = int(quick_n_days)
        self.random_seed = int(random_seed)
        self._models: List[ModelSpec] = []
        # Phase 7.6: optional post-fit hook. Called once per
        # (spec, target, horizon, refit_pos) with signature
        # (model, X_test, spec, target, horizon, fold) → None.
        # Used by the SHAP recorder.
        self._post_run_hook: Optional[Callable[..., None]] = None

    # ── Registration ──────────────────────────────────────────────────────

    def add_model(
        self,
        name: str,
        factory: Callable[[], Any],
        info_set: Optional[str] = "F",
        model_type: str = "returns",
    ) -> "ExpandingWindowEngine":
        """Register a model. Returns ``self`` for chaining."""
        self._models.append(
            ModelSpec(name=name, factory=factory, info_set=info_set,
                      model_type=model_type)
        )
        return self

    def add_spec(self, spec: ModelSpec) -> "ExpandingWindowEngine":
        self._models.append(spec)
        return self

    def set_post_run_hook(
        self, hook: Optional[Callable[..., None]],
    ) -> "ExpandingWindowEngine":
        """Register a callback to be invoked after each fit/predict fold.

        The hook signature is
        ``hook(model, X_test, spec, target, horizon, fold, **kwargs)``.
        Pass ``None`` to clear the hook.

        Used by the SHAP recorder (Phase 7.6).
        """
        self._post_run_hook = hook
        return self

    @property
    def n_models(self) -> int:
        return len(self._models)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _get_target_col(self, target: str, horizon: int, model_type: str) -> str:
        if model_type == "returns":
            return f"target_{target}_t{horizon}"
        return f"target_var_{target}_t{horizon}"

    def _refit_positions(
        self, train_mask: np.ndarray, test_mask: np.ndarray
    ) -> List[int]:
        """Return the absolute row positions where a refit should happen.

        The first refit is at the first test row; subsequent refits are
        every ``refit_every`` rows within the test block. The last test
        row is always a refit point (so the last fold may be smaller than
        ``refit_every``).
        """
        test_idx = np.where(test_mask)[0]
        if len(test_idx) == 0:
            return []
        first_test, last_test = int(test_idx[0]), int(test_idx[-1])
        refit_every = self.quick_refit_every if self.quick else self.refit_every
        positions: List[int] = list(range(first_test, last_test + 1, refit_every))
        if positions[-1] != last_test:
            positions.append(last_test)
        return positions

    def _get_train_test_split(
        self, train_mask: np.ndarray, test_mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, pd.Timestamp]:
        train_idx = np.where(train_mask)[0]
        test_idx = np.where(test_mask)[0]
        split_date = pd.Timestamp(self.mm["date"].iloc[test_idx[0]])
        return train_idx, test_idx, split_date

    def _features_for(self, info_set: Optional[str]) -> List[str]:
        if info_set is None:
            return []
        cols = self.info_sets.get(info_set, [])
        # Keep only columns that actually exist in the model matrix
        return [c for c in cols if c in self.mm.columns]

    def _find_vol_source_col(self, target: str) -> Optional[str]:
        """Find the best column to use as the GARCH source time series.

        The "best" column is the **most recent** lagged return of the
        target that exists in the model matrix. We look for
        ``<target>_lag1`` (= r at t-1) first, then ``<target>_lag2``,
        ``<target>_lag5``, etc. We do NOT consider columns like
        ``r_ITA_msadj_lag1`` (the market-adjusted return) because that
        is a different series and would inject look-ahead bias (msadj
        subtracts the contemporaneous market return).
        """
        import re

        def _lag_num(col: str) -> int:
            """Extract the lag number from a column name like ``r_ITA_lag1``."""
            m = re.search(r"_lag(\d+)$", col)
            return int(m.group(1)) if m else 999

        # Only consider columns whose suffix is exactly ``_<target>_lagN``
        # (e.g. ``r_ITA_lag1``, ``r_ITA_lag2``, ``r_ITA_lag5``,
        # ``r_WAERLST_recon_lag1``). The base must be the target name.
        candidates = []
        for c in self.mm.columns:
            if not c.startswith(target + "_lag"):
                continue
            if _lag_num(c) >= 100:
                continue
            # Must not be a target / variance / forecast column.
            if c.startswith("target_") or c.startswith("target_var_"):
                continue
            candidates.append(c)
        if candidates:
            # Sort by lag number (smallest first) and return the most
            # recent (smallest lag).
            candidates.sort(key=_lag_num)
            return candidates[0]
        return None

    def _fit_predict_one_fold(
        self,
        spec: ModelSpec,
        target: str,
        horizon: int,
        refit_pos: int,
        fold_end: int,
        fold: int = -1,
    ) -> List[Dict[str, Any]]:
        """Fit the model on rows ``[:refit_pos]`` and predict on
        ``[refit_pos:fold_end]``. Return a list of result rows."""
        target_col = self._get_target_col(target, horizon, spec.model_type)
        if target_col not in self.mm.columns:
            return []
        # For GARCH (vol) the source series is the most-recent lagged return
        # available in the model matrix. See ``_find_vol_source_col``.
        if spec.model_type == "vol":
            source_col = self._find_vol_source_col(target)
            if source_col is None:
                logger.warning("no lagged return column for target %s", target)
                return []
        else:
            source_col = target  # not actually used in the returns path

        feat_cols = self._features_for(spec.info_set) if spec.model_type == "returns" else []
        # Phase 7.5: GARCH-X uses an extra info set for exogenous regressors
        garch_x_info_set = spec.extra.get("garch_x_info_set") if spec.extra else None
        garch_x_cols: List[str] = []
        if spec.model_type == "vol" and garch_x_info_set:
            garch_x_cols = [
                c for c in self.info_sets.get(garch_x_info_set, [])
                if c in self.mm.columns
            ]
        # NaN-safe feature selection
        train_block = self.mm.iloc[:refit_pos]
        test_block = self.mm.iloc[refit_pos:fold_end]

        if spec.model_type == "returns":
            X_train = train_block[feat_cols] if feat_cols else None
            y_train = train_block[target_col]
            X_test = test_block[feat_cols] if feat_cols else None
        else:  # vol
            X_train = None
            y_train = train_block[source_col]
            X_test = None
            # GARCH-X: exog block for train (rows 0..refit_pos) and
            # horizon (rows refit_pos..fold_end).
            if garch_x_cols:
                X_exog_train = train_block[garch_x_cols]
                X_exog_horizon = test_block[garch_x_cols]
            else:
                X_exog_train = None
                X_exog_horizon = None

        # ── Defensive no-leakage guard ────────────────────────────────────
        assert_no_future_data(
            self.mm["date"].iloc[:refit_pos],
            self.mm["date"].iloc[refit_pos:fold_end],
        )

        # ── Fit + predict ─────────────────────────────────────────────────
        try:
            model = spec.factory()
            if spec.model_type == "returns":
                model.fit(X_train, y_train)
                preds = np.asarray(model.predict(X_test), dtype=float)
            else:
                # Vol models (GARCH) only see the past target series.
                # GARCH-X variants also see the exogenous regressors.
                if garch_x_cols and hasattr(model, "fit") and "X_exog" in model.fit.__code__.co_varnames:
                    model.fit(y_train, X_exog=X_exog_train)
                    var = np.asarray(
                        model.predict(
                            horizon=horizon, X_exog_horizon=X_exog_horizon,
                        ),
                        dtype=float,
                    )
                else:
                    model.fit(y_train)
                    var = np.asarray(
                        model.predict(horizon=horizon), dtype=float,
                    )
                if var.size == 0:
                    preds = np.full(len(test_block), np.nan)
                elif horizon == 1:
                    preds = np.full(len(test_block), float(var[0]))
                else:
                    preds = np.full(len(test_block), float(var[-1]))
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("model %s failed: %s", spec.name, exc)
            preds = np.full(len(test_block), np.nan)

        # ── Post-run hook (Phase 7.6 SHAP) ───────────────────────────────
        # Called only on the first day of each fold (i.e. when the model
        # was just refit) so we get one SHAP per refit, not per test row.
        if self._post_run_hook is not None and spec.model_type == "returns":
            try:
                self._post_run_hook(
                    model=model,
                    X_test=X_test if spec.model_type == "returns" else None,
                    spec=spec,
                    target=target,
                    horizon=horizon,
                    fold=fold,
                )
            except Exception as exc:  # pragma: no cover
                logger.debug("post_run_hook for %s failed: %s", spec.name, exc)

        # ── Realized values ──────────────────────────────────────────────
        realized = test_block[target_col].to_numpy(dtype=float)
        if len(preds) != len(realized):
            preds = np.full(len(realized), np.nan)

        # ── Emit one row per (date, fold) ─────────────────────────────────
        out: List[Dict[str, Any]] = []
        for i, abs_idx in enumerate(range(refit_pos, fold_end)):
            # refit_flag = 1 ONLY on the first day of this fold (i.e. the
            # day the model was refit). Subsequent days in the fold reuse
            # the just-fitted parameters.
            out.append({
                "date": self.mm["date"].iloc[abs_idx],
                "fold": -1,  # filled in by caller
                "model": spec.name,
                "info_set": spec.info_set if spec.info_set is not None else "-",
                "target": target,
                "horizon": horizon,
                "prediction": float(preds[i]) if np.isfinite(preds[i]) else np.nan,
                "realized": float(realized[i]) if np.isfinite(realized[i]) else np.nan,
                "train_n": int(refit_pos),
                "refit_flag": 1 if i == 0 else 0,
            })
        return out

    # ── Main entry point ──────────────────────────────────────────────────

    def run(self) -> pd.DataFrame:
        """Run the full expanding-window horse race. Returns a long DataFrame.

        Columns: ``date, fold, model, info_set, target, horizon,
        prediction, realized, train_n, refit_flag``.
        """
        if self.n_models == 0:
            raise RuntimeError(
                "No models registered. Call add_model() or add_spec() first."
            )

        train_mask, test_mask, split_date = make_train_test_split(
            self.mm,
            test_fraction=self.test_fraction,
            min_train_obs=self.min_train_obs,
        )
        if self.quick:
            # Restrict test_mask to the last quick_n_days rows
            test_idx = np.where(test_mask)[0]
            if len(test_idx) > self.quick_n_days:
                quick_mask = np.zeros_like(test_mask)
                quick_mask[test_idx[-self.quick_n_days:]] = True
                test_mask = quick_mask
        train_idx, test_idx, _ = self._get_train_test_split(train_mask, test_mask)
        if len(test_idx) == 0:
            raise RuntimeError("No test rows after split (and quick filter).")

        refit_positions = self._refit_positions(train_mask, test_mask)
        logger.info(
            "ExpandingWindowEngine: train=%d, test=%d, refits=%d, refit_every=%d",
            len(train_idx), len(test_idx), len(refit_positions), self.refit_every,
        )

        all_rows: List[Dict[str, Any]] = []
        for spec in self._models:
            for target in self.targets:
                for horizon in self.horizons:
                    for fold, refit_pos in enumerate(refit_positions):
                        fold_end = min(
                            refit_pos + (self.quick_refit_every
                                          if self.quick else self.refit_every),
                            len(self.mm),
                        )
                        # The last fold extends to the end of the test block
                        if fold == len(refit_positions) - 1:
                            fold_end = int(test_idx[-1]) + 1
                        rows = self._fit_predict_one_fold(
                            spec, target, horizon, refit_pos, fold_end, fold=fold,
                        )
                        for r in rows:
                            r["fold"] = fold
                            # r["refit_flag"] is already set correctly in
                            # ``_fit_predict_one_fold`` (1 on the first
                            # day of the fold, 0 on subsequent days).
                        all_rows.extend(rows)
        return pd.DataFrame(all_rows)


# ── Convenience: top-level runner ───────────────────────────────────────────


def run_horse_race_engine(
    model_matrix: pd.DataFrame,
    specs: List[ModelSpec],
    horizons: List[int] = (1, 5),
    targets: List[str] = ("r_ITA", "r_WAERLST_recon"),
    test_fraction: float = 0.25,
    min_train_obs: int = 500,
    refit_every: int = 20,
    quick: bool = False,
    **kwargs: Any,
) -> pd.DataFrame:
    """Build an engine, register ``specs``, and run it. Returns a long DataFrame."""
    eng = ExpandingWindowEngine(
        model_matrix=model_matrix,
        info_sets=model_matrix.attrs.get("info_sets", {}),
        targets=list(targets),
        horizons=list(horizons),
        test_fraction=test_fraction,
        min_train_obs=min_train_obs,
        refit_every=refit_every,
        quick=quick,
        **kwargs,
    )
    for s in specs:
        eng.add_spec(s)
    return eng.run()
