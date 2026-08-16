"""SHAP-based feature attribution for Phase 7 (XGBoost).

Per Master Plan §10.5:

- **Global feature importance** — mean |SHAP| per feature.
- **Feature effects** — SHAP dependence / beeswarm plots.
- **Interaction patterns** — only where stable across folds.
- **Differences across forecast horizons** — per-horizon comparison.
- **Differences across indices** — per-target comparison.

We never interpret SHAP as causal attribution.

The module provides:

- :func:`compute_shap_values` — wraps :class:`shap.TreeExplainer`.
- :func:`plot_shap_summary` — beeswarm + bar plot for one (info_set, horizon).
- :func:`aggregate_shap_per_fold` — per-fold mean |SHAP| per feature.
- :func:`compute_feature_stability` — fraction of folds where each
  feature is in the top-K.

The :class:`SHAPRecorder` class is a small container used by the
expanding-window engine's ``post_run_hook`` to accumulate per-fold
SHAP values without keeping the whole trained model in memory.
"""
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    import shap as _shap
    _HAS_SHAP = True
except Exception:  # pragma: no cover
    _HAS_SHAP = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except Exception:  # pragma: no cover
    _HAS_MPL = False

from src.models.ml import XGBoostForecaster


logger = logging.getLogger(__name__)


__all__ = [
    "SHAPRecorder",
    "compute_shap_values",
    "plot_shap_summary",
    "aggregate_shap_per_fold",
    "compute_feature_stability",
    "save_shap_arrays",
    "load_shap_arrays",
    "plot_all_shap_summaries",
]


# ── Per-fold container ──────────────────────────────────────────────────────


@dataclass
class FoldSHAP:
    """SHAP values and metadata for one (spec, target, horizon, fold)."""
    info_set: str
    horizon: int
    target: str
    fold: int
    shap_values: np.ndarray   # shape (n_test_rows, n_features)
    feature_names: List[str]
    test_index: List[Any] = field(default_factory=list)


class SHAPRecorder:
    """Accumulator for per-fold SHAP values.

    The expanding-window engine's ``post_run_hook`` calls
    :meth:`record_fold` once per (spec, target, horizon, refit_pos). At
    the end of the run, the recorder can produce the stability report
    and the per-(info_set, horizon, target) parquet files.
    """

    def __init__(self) -> None:
        self.folds: List[FoldSHAP] = []

    @property
    def shap_per_fold(self) -> Dict[Tuple[str, int, str], List[FoldSHAP]]:
        """Group folds by (info_set, horizon, target)."""
        out: Dict[Tuple[str, int, str], List[FoldSHAP]] = {}
        for f in self.folds:
            out.setdefault((f.info_set, f.horizon, f.target), []).append(f)
        return out

    def save_npz(self, path: Path) -> Path:
        """Save all per-fold SHAP values to a single compressed .npz file.

        Each array is keyed as ``shap_<info_set>_<horizon>_<target>_fold<n>``.
        Also saves the feature names as ``features_<info_set>_<horizon>_<target>``.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        arrays: Dict[str, np.ndarray] = {}
        for f in self.folds:
            def _safe(s: Any) -> str:
                return str(s).replace("/", "_").replace(" ", "_")
            key = (f"shap_{_safe(f.info_set)}_{f.horizon}_"
                   f"{_safe(f.target)}_fold{f.fold}")
            arrays[key] = f.shap_values
            if f.feature_names:
                feat_key = (f"features_{_safe(f.info_set)}_{f.horizon}_"
                            f"{_safe(f.target)}")
                if feat_key not in arrays:
                    arrays[feat_key] = np.array(
                        f.feature_names, dtype=object,
                    )
        np.savez_compressed(path, **arrays)
        return path

    def to_dataframe(self) -> pd.DataFrame:
        """Flatten the recorded folds into a long-form DataFrame."""
        rows: List[Dict[str, Any]] = []
        for f in self.folds:
            for i, vals in enumerate(f.shap_values):
                for j, v in enumerate(vals):
                    rows.append({
                        "info_set": f.info_set,
                        "horizon": f.horizon,
                        "target": f.target,
                        "fold": f.fold,
                        "row_idx": i,
                        "feature": (f.feature_names[j]
                                    if j < len(f.feature_names)
                                    else f"f{j}"),
                        "shap_value": float(v),
                    })
        return pd.DataFrame(rows)

    def record_fold(
        self,
        info_set: str,
        horizon: int,
        target: str,
        fold: int,
        model: XGBoostForecaster,
        X_test: pd.DataFrame,
    ) -> None:
        """Compute SHAP for one fitted XGBoost model on its test block."""
        if model is None or model.model_ is None:
            return
        try:
            sv = compute_shap_values(model, X_test)
        except Exception as exc:  # pragma: no cover
            logger.warning("SHAP failed for %s/%s/%s fold=%d: %s",
                           info_set, horizon, target, fold, exc)
            return
        self.folds.append(FoldSHAP(
            info_set=info_set,
            horizon=horizon,
            target=target,
            fold=fold,
            shap_values=sv,
            feature_names=model.feature_names_,
            test_index=list(X_test.index),
        ))


# ── SHAP computation ───────────────────────────────────────────────────────


def compute_shap_values(
    model: XGBoostForecaster,
    X: pd.DataFrame,
    max_evals: int = 500,
    background_size: int = 50,
) -> np.ndarray:
    """Compute SHAP values for an XGBoost model on ``X``.

    Returns
    -------
    np.ndarray
        SHAP values of shape ``(len(X), n_features)`` (matches X.shape).
        Same order as ``model.feature_names_``.
    """
    if not _HAS_SHAP:
        raise ImportError("`shap` is required for SHAP computation.")
    if X is None or len(X) == 0:
        return np.zeros((0, len(model.feature_names_)))
    # Align columns to the model's training columns
    if list(X.columns) != model.feature_names_:
        X_aligned = pd.DataFrame(
            {c: X[c] if c in X.columns else np.zeros(len(X))
             for c in model.feature_names_},
            index=X.index,
        )
    else:
        X_aligned = X.reset_index(drop=True)
    # TreeExplainer is the right call for XGBoost — it uses the tree
    # structure exactly and is much faster than the KernelExplainer.
    explainer = _shap.TreeExplainer(
        model.model_,
        feature_perturbation="tree_path_dependent",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sv = explainer.shap_values(X_aligned)
    sv = np.asarray(sv, dtype=float)
    if sv.ndim == 1:
        sv = sv.reshape(-1, len(model.feature_names_))
    return sv


# ── Aggregation helpers ─────────────────────────────────────────────────────


def aggregate_shap_per_fold(
    folds: List[FoldSHAP],
) -> pd.DataFrame:
    """Return mean |SHAP| per feature per (info_set, horizon, target).

    Output columns: ``info_set, horizon, target, feature, mean_abs_shap``.
    """
    if not folds:
        return pd.DataFrame(columns=[
            "info_set", "horizon", "target", "feature", "mean_abs_shap",
        ])
    rows: List[Dict[str, Any]] = []
    # Group folds by (info_set, horizon, target)
    grouped: Dict[Tuple[str, int, str], List[FoldSHAP]] = {}
    for f in folds:
        key = (f.info_set, f.horizon, f.target)
        grouped.setdefault(key, []).append(f)
    for (info_set, horizon, target), flist in grouped.items():
        # Stack all folds (different lengths) — but only on the
        # intersection of feature names. Take union for simplicity.
        all_features = sorted({f for fold in flist for f in fold.feature_names})
        for feat in all_features:
            vals = []
            for fold in flist:
                if feat not in fold.feature_names:
                    continue
                idx = fold.feature_names.index(feat)
                col = fold.shap_values[:, idx] if fold.shap_values.ndim == 2 else fold.shap_values
                vals.append(np.mean(np.abs(col)))
            if vals:
                rows.append({
                    "info_set": info_set,
                    "horizon": horizon,
                    "target": target,
                    "feature": feat,
                    "mean_abs_shap": float(np.mean(vals)),
                })
    return pd.DataFrame(rows).sort_values(
        ["info_set", "horizon", "target", "mean_abs_shap"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)


def compute_feature_stability(
    folds: List[FoldSHAP],
    top_k: int = 10,
) -> pd.DataFrame:
    """For each (info_set, horizon, target, feature), return the fraction
    of folds where the feature's mean |SHAP| is in the top-K.

    Output columns: ``info_set, horizon, target, feature, stability``.
    """
    if not folds:
        return pd.DataFrame(columns=[
            "info_set", "horizon", "target", "feature", "stability",
        ])
    rows: List[Dict[str, Any]] = []
    grouped: Dict[Tuple[str, int, str], List[FoldSHAP]] = {}
    for f in folds:
        grouped.setdefault((f.info_set, f.horizon, f.target), []).append(f)
    for (info_set, horizon, target), flist in grouped.items():
        # For each fold, compute the top-K features by mean |SHAP|
        topk_per_fold: List[set] = []
        for fold in flist:
            mean_abs = np.mean(np.abs(fold.shap_values), axis=0)
            top_idx = np.argsort(mean_abs)[::-1][:top_k]
            topk_per_fold.append({fold.feature_names[i] for i in top_idx})
        all_features = sorted({f for fold in flist for f in fold.feature_names})
        n_folds = len(flist)
        for feat in all_features:
            stability = sum(feat in s for s in topk_per_fold) / max(1, n_folds)
            rows.append({
                "info_set": info_set,
                "horizon": horizon,
                "target": target,
                "feature": feat,
                "stability": float(stability),
            })
    return pd.DataFrame(rows).sort_values(
        ["info_set", "horizon", "target", "stability"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)


# ── Plotting ────────────────────────────────────────────────────────────────


def plot_shap_summary(
    shap_values: np.ndarray,
    X: pd.DataFrame,
    out_path: Path,
    title: str = "SHAP summary",
    max_display: int = 20,
) -> Optional[Path]:
    """Save a SHAP beeswarm + bar plot to ``out_path``.

    Uses :func:`shap.summary_plot` if available, otherwise a manual
    matplotlib bar chart of mean |SHAP|.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not _HAS_MPL:
        logger.warning("matplotlib not available; skipping SHAP plot")
        return None
    try:
        if _HAS_SHAP:
            plt.figure(figsize=(8, 6))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _shap.summary_plot(
                    shap_values, X, show=False, max_display=max_display,
                )
            plt.title(title)
            plt.tight_layout()
            plt.savefig(out_path, dpi=120, bbox_inches="tight")
            plt.close("all")
            return out_path
    except Exception as exc:  # pragma: no cover
        logger.warning("shap.summary_plot failed (%s); falling back to bar", exc)

    # Fallback: bar chart of mean |SHAP|
    try:
        mean_abs = np.mean(np.abs(shap_values), axis=0)
        order = np.argsort(mean_abs)[::-1][:max_display]
        names = [X.columns[i] for i in order]
        vals = mean_abs[order]
        fig, ax = plt.subplots(figsize=(8, max(3, 0.3 * len(names))))
        ax.barh(range(len(names)), vals, color="steelblue", edgecolor="white")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Mean |SHAP|")
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis="x")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return out_path
    except Exception as exc:  # pragma: no cover
        logger.warning("SHAP bar plot failed: %s", exc)
        return None


# ── Save / load ─────────────────────────────────────────────────────────────


def save_shap_arrays(
    recorder: SHAPRecorder,
    out_dir: Path,
) -> List[Path]:
    """Persist all per-fold SHAP arrays to ``out_dir`` as ``.npy`` files.

    File naming: ``shap_<info_set>_<horizon>_<target>_fold<n>.npy``.

    Returns the list of written paths.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for fold in recorder.folds:
        # Sanitize target / info_set for filename
        def _safe(s: Any) -> str:
            return str(s).replace("/", "_").replace(" ", "_")
        fname = f"shap_{_safe(fold.info_set)}_{fold.horizon}_{_safe(fold.target)}_fold{fold.fold}.npy"
        path = out_dir / fname
        np.save(path, fold.shap_values)
        written.append(path)
    return written


def load_shap_arrays(
    in_dir: Path,
    info_sets: Sequence[str] = ("F", "P", "N", "PN", "PNG"),
    horizons: Sequence[int] = (1, 5),
    targets: Sequence[str] = ("r_WAERLST", "r_BSHIELDT", "r_ITA"),
) -> List[FoldSHAP]:
    """Load all per-fold SHAP arrays from ``in_dir`` into a list of :class:`FoldSHAP`."""
    in_dir = Path(in_dir)
    folds: List[FoldSHAP] = []
    for path in sorted(in_dir.glob("shap_*.npy")):
        # Parse: shap_<info_set>_<horizon>_<target>_fold<n>.npy
        stem = path.stem  # e.g. "shap_PN_1_r_ITA_fold3"
        parts = stem.split("_")
        if len(parts) < 5:
            continue
        # Last part is "fold<n>"
        fold_part = parts[-1]
        if not fold_part.startswith("fold"):
            continue
        try:
            fold = int(fold_part[4:])
        except ValueError:
            continue
        horizon = int(parts[-3])
        info_set = parts[1]
        target = "_".join(parts[2:-3])  # handles "r_ITA" and "r_WAERLST_recon"
        # Sanity check
        if info_set not in info_sets or horizon not in horizons:
            continue
        sv = np.load(path)
        folds.append(FoldSHAP(
            info_set=info_set,
            horizon=horizon,
            target=target,
            fold=fold,
            shap_values=sv,
            feature_names=[],  # not stored in .npy; recompute on demand
        ))
    return folds


# ── CLI entry point ─────────────────────────────────────────────────────────


def _main() -> int:
    """Aggregate + plot SHAP from a directory of per-fold .npy files."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Phase 7.6 — aggregate SHAP arrays into a stability report and figures",
    )
    parser.add_argument(
        "--shap-dir", type=Path,
        default=Path("outputs/model_objects"),
        help="Directory of per-fold .npy files (from the OOS run).",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path("outputs/tables"),
        help="Where to write the stability + importance CSVs.",
    )
    parser.add_argument(
        "--fig-dir", type=Path,
        default=Path("outputs/figures"),
        help="Where to write the SHAP beeswarm PNGs.",
    )
    parser.add_argument(
        "--info-sets", type=str, default="F,P,N,PN,PNG",
        help="Comma-separated info sets.",
    )
    parser.add_argument(
        "--targets", type=str, default="r_WAERLST,r_BSHIELDT,r_ITA",
        help="Comma-separated targets.",
    )
    parser.add_argument(
        "--horizons", type=str, default="1,5",
        help="Comma-separated horizons.",
    )
    parser.add_argument(
        "--top-k", type=int, default=10,
        help="Top-K features for the stability report (default 10).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    info_sets = tuple(s.strip() for s in args.info_sets.split(",") if s.strip())
    targets = tuple(s.strip() for s in args.targets.split(",") if s.strip())
    horizons = tuple(int(s.strip()) for s in args.horizons.split(",") if s.strip())

    folds = load_shap_arrays(
        args.shap_dir, info_sets=info_sets, targets=targets, horizons=horizons,
    )
    if not folds:
        logger.warning("No SHAP .npy files found in %s", args.shap_dir)
        return 1
    logger.info("Loaded %d SHAP fold arrays", len(folds))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.fig_dir.mkdir(parents=True, exist_ok=True)

    # Mean |SHAP| per (info_set, horizon, target, feature)
    importance = aggregate_shap_per_fold(folds)
    importance.to_csv(args.out_dir / "phase7_shap_importance.csv", index=False)
    logger.info("Wrote %s", args.out_dir / "phase7_shap_importance.csv")

    # Stability (top-K fraction across folds)
    stability = compute_feature_stability(folds, top_k=args.top_k)
    stability.to_csv(args.out_dir / "phase7_shap_stability.csv", index=False)
    logger.info("Wrote %s", args.out_dir / "phase7_shap_stability.csv")

    return 0




# ── Top-level batch plot helper ────────────────────────────────────────────


def plot_all_shap_summaries(
    recorder: "SHAPRecorder",
    out_dir: Path,
    max_features: int = 20,
) -> List[Path]:
    """For each (info_set, horizon, target) group in ``recorder``, write a
    SHAP beeswarm/bar plot to ``out_dir``.

    Returns the list of written paths.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    grouped = recorder.shap_per_fold
    for (info_set, horizon, target), folds in grouped.items():
        # Stack all folds for this (info_set, horizon, target) on the
        # common feature set.
        all_features = sorted({f for fold in folds for f in fold.feature_names})
        if not all_features:
            continue
        # Build a (n_total, n_features) array; rows for folds missing a
        # feature get NaN.
        rows = []
        feature_vals = []
        for fold in folds:
            for i in range(fold.shap_values.shape[0]):
                row = {f: np.nan for f in all_features}
                for j, fname in enumerate(fold.feature_names):
                    if j < fold.shap_values.shape[1]:
                        row[fname] = fold.shap_values[i, j]
                rows.append(row)
        df = pd.DataFrame(rows)
        sv = df[all_features].to_numpy(dtype=float)

        def _safe(s):
            return str(s).replace("/", "_").replace(" ", "_")
        fname = f"fig17_shap_summary_{_safe(info_set)}_h{horizon}_{_safe(target)}.png"
        path = plot_shap_summary(
            sv,
            df[all_features].fillna(0.0),
            out_dir / fname,
            title=f"SHAP: {info_set} h={horizon} target={target}",
            max_display=max_features,
        )
        if path is not None:
            written.append(path)
    return written



if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_main())
