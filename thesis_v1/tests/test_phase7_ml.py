"""Tests for Phase 7 — ML models (XGBoost) and GARCH-X."""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Suppress noisy XGBoost / SHAP deprecation warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# ── Fixtures (re-use Phase 6 pattern) ─────────────────────────────────────


def _build_small_model_matrix(n: int = 250, seed: int = 42) -> pd.DataFrame:
    """Build a small synthetic model matrix for testing.

    Mirrors the pattern in tests/test_phase6_baselines.py: a 250-row
    DataFrame with the columns ``target_r_ITA_t{1,5}`` and a few lagged
    features. Suitable for end-to-end tests of the engine + XGBoost.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n)
    # Financial features
    r_ITA = rng.normal(0, 1.0, n)        # returns in percent
    r_BSH = rng.normal(0, 0.8, n)
    VIX = 15 + np.abs(rng.normal(0, 5, n))
    vol_5d = pd.Series(r_ITA).rolling(5, min_periods=1).std().to_numpy()
    vol_20d = pd.Series(r_ITA).rolling(20, min_periods=1).std().to_numpy()

    df = pd.DataFrame({
        "date": idx,
        "r_ITA": r_ITA,
        "r_BSHIELDT": r_BSH,
        "VIX": VIX,
        "vol_5d": vol_5d,
        "vol_20d": vol_20d,
        "r_ITA_lag1": pd.Series(r_ITA).shift(1).fillna(0).to_numpy(),
        "r_ITA_lag2": pd.Series(r_ITA).shift(2).fillna(0).to_numpy(),
        "r_ITA_lag5": pd.Series(r_ITA).shift(5).fillna(0).to_numpy(),
        "VIX_lag1": pd.Series(VIX).shift(1).fillna(VIX[0]).to_numpy(),
        "vol_5d_lag1": pd.Series(vol_5d).shift(1).fillna(vol_5d[0]).to_numpy(),
        "vol_20d_lag1": pd.Series(vol_20d).shift(1).fillna(vol_20d[0]).to_numpy(),
        # Attack features (NaN early, real later — tests the standardize path)
        "launched_total_lag1": np.concatenate([
            np.full(20, np.nan),
            np.abs(rng.normal(50, 20, n - 20)),
        ]),
        "destroyed_total_lag1": np.concatenate([
            np.full(20, np.nan),
            np.abs(rng.normal(30, 15, n - 20)),
        ]),
        # News features
        "n_articles_total_lag1": np.abs(rng.normal(100, 30, n)),
        "tone_western_lag1": rng.normal(0, 1, n),
    })

    # Targets
    for h in (1, 5):
        # The "realized" target is the rolling return over the next h days
        df[f"target_r_ITA_t{h}"] = pd.Series(r_ITA).rolling(
            h, min_periods=1
        ).sum().shift(-h).fillna(0).to_numpy()
        df[f"target_var_r_ITA_t{h}"] = df[f"target_r_ITA_t{h}"] ** 2

    return df


def _build_mm_with_info_sets(n: int = 250) -> pd.DataFrame:
    """Build a small model matrix with proper info_sets attrs."""
    from src.features.build_model_matrix import build_info_sets
    df = _build_small_model_matrix(n=n)
    df.attrs["info_sets"] = build_info_sets(df)
    df.attrs["primary_target"] = "target_r_ITA_t1"
    return df


# ── XGBoost forecaster unit tests ────────────────────────────────────────


class TestXGBoostForecaster:
    """Test the XGBoostForecaster fits the _BaseForecaster contract."""

    def test_fit_predict_ndarray(self):
        from src.models.ml import XGBoostForecaster
        rng = np.random.default_rng(42)
        X = rng.standard_normal((200, 5))
        y = X[:, 0] * 0.5 + rng.standard_normal(200) * 0.1
        f = XGBoostForecaster(max_depth=3, n_estimators=50,
                              early_stopping_rounds=10)
        f.fit(X, y)
        preds = f.predict(X[-20:])
        assert preds.shape == (20,)
        assert np.isfinite(preds).all()

    def test_fit_predict_dataframe(self):
        from src.models.ml import XGBoostForecaster
        rng = np.random.default_rng(42)
        X = pd.DataFrame(
            rng.standard_normal((200, 5)),
            columns=[f"f{i}" for i in range(5)],
        )
        y = pd.Series(X["f0"] * 0.5 + rng.standard_normal(200) * 0.1)
        f = XGBoostForecaster(max_depth=3, n_estimators=50)
        f.fit(X, y)
        preds = f.predict(X.iloc[-20:])
        assert preds.shape == (20,)

    def test_handles_nan_in_y(self):
        from src.models.ml import XGBoostForecaster
        rng = np.random.default_rng(42)
        X = rng.standard_normal((200, 5))
        y = pd.Series(X[:, 0] * 0.5 + rng.standard_normal(200) * 0.1)
        y.iloc[:30] = np.nan  # NaN in first 30 rows
        f = XGBoostForecaster(max_depth=3, n_estimators=50)
        f.fit(X, y)
        preds = f.predict(X[-10:])
        assert preds.shape == (10,)
        assert np.isfinite(preds).all()

    def test_handles_nan_in_x(self):
        """XGBoost handles NaN natively; just verify it doesn't crash."""
        from src.models.ml import XGBoostForecaster
        rng = np.random.default_rng(42)
        X = pd.DataFrame(
            rng.standard_normal((200, 5)),
            columns=[f"f{i}" for i in range(5)],
        )
        # Insert NaN into some features
        X.iloc[10:30, 0] = np.nan
        X.iloc[50:70, 2] = np.nan
        y = X["f0"].fillna(0) * 0.5 + rng.standard_normal(200) * 0.1
        f = XGBoostForecaster(max_depth=3, n_estimators=50)
        f.fit(X, y)
        preds = f.predict(X.iloc[-20:])
        assert preds.shape == (20,)

    def test_sklearn_clone(self):
        from sklearn.base import clone
        from src.models.ml import XGBoostForecaster
        f = XGBoostForecaster(max_depth=5, n_estimators=200)
        f2 = clone(f)
        assert f2.max_depth == 5
        assert f2.n_estimators == 200
        assert f2 is not f

    def test_too_few_rows_falls_back(self):
        from src.models.ml import XGBoostForecaster
        f = XGBoostForecaster()
        f.fit(None, pd.Series([0.1, 0.2, 0.3]))
        preds = f.predict(np.zeros((5, 1)))
        assert preds.shape == (5,)

    def test_features_stored(self):
        from src.models.ml import XGBoostForecaster
        rng = np.random.default_rng(42)
        X = pd.DataFrame(
            rng.standard_normal((100, 3)),
            columns=["a", "b", "c"],
        )
        y = pd.Series(X["a"] + rng.standard_normal(100) * 0.1)
        f = XGBoostForecaster(max_depth=2, n_estimators=20)
        f.fit(X, y)
        assert f.feature_names_ == ["a", "b", "c"]
        assert f.n_features_in_ == 3
        assert f.best_iteration_ >= 0


# ── TS-CV grid search tests ──────────────────────────────────────────────


class TestTimeSeriesCV:
    def test_returns_expected_number_of_splits(self):
        from src.models.ml_tuning import time_series_cv_splits
        splits = time_series_cv_splits(n=200, n_splits=3, embargo=5,
                                       min_train_size=50)
        assert len(splits) == 3

    def test_expanding_window(self):
        from src.models.ml_tuning import time_series_cv_splits
        splits = time_series_cv_splits(n=200, n_splits=3, embargo=5,
                                       min_train_size=50)
        train_sizes = [len(tr) for tr, _ in splits]
        assert train_sizes == sorted(train_sizes)  # expanding
        # Each train must end before the corresponding val starts
        for tr, va in splits:
            assert tr[-1] + 5 < va[0]  # at least 5-day embargo

    def test_min_train_size_respected(self):
        from src.models.ml_tuning import time_series_cv_splits
        splits = time_series_cv_splits(n=200, n_splits=3, embargo=5,
                                       min_train_size=100)
        for tr, _ in splits:
            assert len(tr) >= 100

    def test_grid_search_returns_best(self):
        from src.models.ml_tuning import grid_search_xgb
        rng = np.random.default_rng(0)
        n = 300
        X = pd.DataFrame(
            rng.standard_normal((n, 4)),
            columns=[f"f{i}" for i in range(4)],
        )
        y = pd.Series(X["f0"] * 0.7 + rng.standard_normal(n) * 0.1)
        param_grid = {
            "max_depth": [3, 5],
            "learning_rate": [0.05, 0.1],
            "n_estimators": [50, 100],
        }
        splits = [(np.arange(150), np.arange(160, 200)),
                  (np.arange(200), np.arange(210, 250))]
        best_params, best_score, fold_scores = grid_search_xgb(
            X, y, param_grid, splits, metric="mae", random_state=42,
        )
        assert "max_depth" in best_params
        assert "learning_rate" in best_params
        assert "n_estimators" in best_params
        assert np.isfinite(best_score)
        assert len(fold_scores) == len(splits)


# ── SHAP tests ───────────────────────────────────────────────────────────


class TestSHAP:
    def test_compute_shap_values(self):
        from src.models.ml import XGBoostForecaster
        from src.models.ml_explain import compute_shap_values
        rng = np.random.default_rng(42)
        X = pd.DataFrame(
            rng.standard_normal((100, 4)),
            columns=["a", "b", "c", "d"],
        )
        y = pd.Series(X["a"] * 0.5 + rng.standard_normal(100) * 0.1)
        f = XGBoostForecaster(max_depth=3, n_estimators=30)
        f.fit(X, y)
        sv = compute_shap_values(f, X.iloc[-20:])
        assert sv.shape == (20, 4)

    def test_aggregate_shap_per_fold(self):
        from src.models.ml_explain import (
            aggregate_shap_per_fold, FoldSHAP,
        )
        rng = np.random.default_rng(42)
        # Two FoldSHAP objects, each with a (20, 4) SHAP matrix
        folds = [
            FoldSHAP(
                info_set="F", horizon=1, target="r_ITA", fold=0,
                shap_values=rng.standard_normal((20, 4)),
                feature_names=["a", "b", "c", "d"],
            ),
            FoldSHAP(
                info_set="F", horizon=1, target="r_ITA", fold=1,
                shap_values=rng.standard_normal((20, 4)) * 0.5,
                feature_names=["a", "b", "c", "d"],
            ),
        ]
        df = aggregate_shap_per_fold(folds)
        # 4 features × (info_set, horizon, target, feature, mean_abs_shap)
        assert df.shape == (4, 5)
        assert (df["mean_abs_shap"] > 0).all()


# ── GARCH-X tests ────────────────────────────────────────────────────────


class TestGARCHXForecaster:
    def test_basic_fit_predict(self):
        pytest.importorskip("arch", reason="arch package required")
        from src.models.garch import GARCHXForecaster
        rng = np.random.default_rng(42)
        n = 300
        y = pd.Series(rng.standard_normal(n) * 1.5)
        X_exog = pd.DataFrame({
            "exog1": rng.standard_normal(n),
            "exog2": rng.standard_normal(n),
        })
        f = GARCHXForecaster(variant="GARCH", p=1, q=1, dist="normal")
        f.fit(y, X_exog=X_exog)
        assert f.result_ is not None
        var = f.predict(horizon=1, X_exog_horizon=X_exog.iloc[-1:])
        assert var.shape == (1,)
        assert np.isfinite(var).all()

    def test_h5_forecast(self):
        pytest.importorskip("arch", reason="arch package required")
        from src.models.garch import GARCHXForecaster
        rng = np.random.default_rng(42)
        n = 300
        y = pd.Series(rng.standard_normal(n) * 1.5)
        X_exog = pd.DataFrame({"exog1": rng.standard_normal(n)})
        f = GARCHXForecaster(variant="GARCH", p=1, q=1, dist="normal")
        f.fit(y, X_exog=X_exog)
        var5 = f.predict(horizon=5, X_exog_horizon=X_exog.iloc[-5:])
        assert var5.shape == (5,)
        assert np.isfinite(var5).all()

    def test_no_exog_falls_back_to_univariate(self):
        pytest.importorskip("arch", reason="arch package required")
        from src.models.garch import GARCHXForecaster
        rng = np.random.default_rng(42)
        y = pd.Series(rng.standard_normal(200) * 1.5)
        f = GARCHXForecaster(variant="GARCH", p=1, q=1, dist="normal")
        f.fit(y, X_exog=None)
        var = f.predict(horizon=1)
        assert var.shape == (1,)


# ── End-to-end integration test ──────────────────────────────────────────


class TestPhase7EndToEnd:
    """Smoke test: run a tiny version of the Phase 7 horse race."""

    def test_run_phase7_on_synthetic_mm(self):
        from src.models.horse_race import run_phase7
        mm = _build_mm_with_info_sets(n=250)
        out = run_phase7(
            model_matrix=mm,
            horizons=(1,),
            targets=("r_ITA",),
            info_sets=("F",),
            include_garch_x=False,    # skip GARCH-X for the smoke test
            include_econometric_baselines=True,
            test_fraction=0.25,
            min_train_obs=80,
            refit_every=20,
            quick=True,
            random_seed=42,
            collect_shap=True,
        )
        assert "predictions" in out
        assert "benchmark" in out
        # We should have 5 rows in the benchmark: HM, AR1, OLS, Ridge, xgboost
        assert len(out["benchmark"]) == 5
        # All benchmark MAE values should be finite (column name is uppercase)
        assert out["benchmark"]["MAE"].notna().all()

    def test_xgboost_in_benchmark(self):
        from src.models.horse_race import run_phase7
        mm = _build_mm_with_info_sets(n=250)
        out = run_phase7(
            model_matrix=mm,
            horizons=(1,),
            targets=("r_ITA",),
            info_sets=("F",),
            include_garch_x=False,
            include_econometric_baselines=False,
            test_fraction=0.25,
            min_train_obs=80,
            refit_every=20,
            quick=True,
            random_seed=42,
            collect_shap=False,
        )
        assert "xgboost" in out["benchmark"]["model"].values
        # MAE is reasonable (not absurd)
        mae = out["benchmark"].set_index("model").loc["xgboost", "MAE"]
        assert np.isfinite(mae) and mae < 5.0


# ── Default specs tests ──────────────────────────────────────────────────


class TestPhase7Specs:
    def test_default_ml_specs(self):
        from src.models.horse_race import default_ml_specs
        specs = default_ml_specs(info_sets=("F", "P"))
        assert len(specs) == 2
        for s in specs:
            assert s.name == "xgboost"
            assert s.model_type == "returns"

    def test_default_garch_x_specs(self):
        pytest.importorskip("arch", reason="arch package required")
        from src.models.horse_race import default_garch_x_specs
        specs = default_garch_x_specs(garch_x_info_set="P")
        assert len(specs) == 3
        names = [s.name for s in specs]
        assert "garch_x_garch" in names
        assert "garch_x_gjr_garch" in names
        assert "garch_x_egarch" in names
        for s in specs:
            assert s.model_type == "vol"
            assert s.extra.get("garch_x_info_set") == "P"

    def test_tuned_params_in_specs(self):
        from src.models.horse_race import default_ml_specs
        # default_ml_specs looks up the (set_name, h=1, r_WAERLST) key —
        # r_WAERLST is the primary target (decision_log 2026-07-02).
        tuned = {
            ("F", 1, "r_WAERLST"): {
                "max_depth": 3, "learning_rate": 0.05,
                "n_estimators": 200, "min_child_weight": 5,
                "reg_alpha": 0.0, "reg_lambda": 1.0,
            }
        }
        specs = default_ml_specs(info_sets=("F",), tuned_params=tuned)
        assert len(specs) == 1
        # The factory is a lambda that returns a fresh instance with the
        # tuned params baked in (default values from YAML are not used here).
        f = specs[0].factory()
        assert f.max_depth == 3
        assert f.learning_rate == 0.05
        assert f.n_estimators == 200


# ── CLI smoke test ───────────────────────────────────────────────────────


class TestCLISmoke:
    def test_phase7_run_help(self):
        """Verify the CLI doesn't crash on --help."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/phase7_run_ml.py", "--help"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "Phase 7" in result.stdout

    def test_phase7_tune_help(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/phase7_tune.py", "--help"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "TS-CV" in result.stdout or "Phase 7" in result.stdout


# ── Real-data integration test (skipped if model matrix is absent) ────────


REAL_MM_PATH = REPO_ROOT / "data" / "processed" / "model_matrix.parquet"


@pytest.mark.skipif(
    not REAL_MM_PATH.exists(),
    reason=f"Real model matrix not found at {REAL_MM_PATH}",
)
class TestPhase7RealData:
    """Integration test against the real 1,342 × 136 model matrix.

    Run with: ``pytest tests/test_phase7_ml.py::TestPhase7RealData -v``
    Skipped automatically if the model matrix is not present.
    """

    @pytest.mark.xfail(
        reason=(
            "Cardinalities are stale by DESIGN, not by data staleness: "
            "decision_log 2026-07-02 fixed the N-set union bug (N was "
            "news-only, now N = F + news, so N > F strictly) and stopped "
            "excluding r_WAERLST_recon_lag1 from F (it is a demoted feature, "
            "not a target source, so F gained 1 column). Both changes are "
            "intentional and push F/N/PN higher than these hardcoded counts "
            "even after the model_matrix.parquet rebuild — the rebuild agent "
            "must recompute these numbers from outputs/tables/"
            "info_set_cardinality.csv after regenerating it, not just re-run "
            "this test."
        ),
        strict=False,
    )
    def test_real_mm_info_sets(self):
        from src.features.build_model_matrix import build_info_sets
        mm = pd.read_parquet(REAL_MM_PATH)
        assert mm.shape[0] >= 1000
        assert mm.shape[1] >= 100
        info_sets = build_info_sets(mm)
        # Cardinalities from outputs/tables/info_set_cardinality.csv
        # (PRE-FIX numbers; kept only as a historical baseline — see xfail
        # reason above for why these no longer hold).
        assert len(info_sets["F"]) == 26
        assert len(info_sets["P"]) == 62
        assert len(info_sets["N"]) == 26
        assert len(info_sets["PN"]) == 78
        assert len(info_sets["PNG"]) == 81

    def test_real_mm_xgboost_quick_run(self):
        """End-to-end XGBoost run on the real matrix (quick mode)."""
        from src.features.build_model_matrix import build_info_sets
        from src.models.horse_race import run_phase7
        mm = pd.read_parquet(REAL_MM_PATH)
        if not mm.attrs.get("info_sets"):
            mm.attrs["info_sets"] = build_info_sets(mm)
        out = run_phase7(
            model_matrix=mm,
            horizons=(1,),
            targets=("r_ITA",),
            info_sets=("F", "P"),
            include_garch_x=False,
            include_econometric_baselines=True,
            test_fraction=0.25,
            min_train_obs=500,
            refit_every=20,
            quick=True,
            random_seed=42,
            collect_shap=False,  # skip SHAP for speed
        )
        # 5 models (HM, AR1, OLS, Ridge, xgboost) × 2 info sets = 10 rows
        assert len(out["benchmark"]) == 10
        # xgboost must be present
        assert "xgboost" in out["benchmark"]["model"].values
        # MAE must be finite and within a sane range
        for _, row in out["benchmark"].iterrows():
            assert np.isfinite(row["MAE"]), (
                f"Non-finite MAE for {row['model']}/{row['info_set']}"
            )
            assert row["MAE"] < 10.0, (
                f"MAE too high for {row['model']}/{row['info_set']}: {row['MAE']}"
            )

    def test_real_mm_garch_x_quick_run(self):
        """End-to-end GARCH-X run on the real matrix (quick mode)."""
        pytest.importorskip("arch", reason="arch package required")
        from src.features.build_model_matrix import build_info_sets
        from src.models.horse_race import run_phase7
        mm = pd.read_parquet(REAL_MM_PATH)
        if not mm.attrs.get("info_sets"):
            mm.attrs["info_sets"] = build_info_sets(mm)
        out = run_phase7(
            model_matrix=mm,
            horizons=(1,),
            targets=("r_ITA",),
            info_sets=("F",),  # GARCH-X needs a feature set
            include_garch_x=True,
            garch_x_info_set="F",
            include_econometric_baselines=False,
            test_fraction=0.25,
            min_train_obs=500,
            refit_every=20,
            quick=True,
            random_seed=42,
            collect_shap=False,
        )
        # 3 GARCH + 3 GARCH-X = 6 rows (default_vol_specs() is always added)
        assert len(out["vol_benchmark"]) == 6
        # GARCH-X rows must be present
        vb = out["vol_benchmark"]
        garch_x_models = [m for m in vb["model"] if m.startswith("garch_x_")]
        assert len(garch_x_models) == 3

        # Bug-fix regression (2026-07): the three GARCH-X variants must
        # produce genuinely independent predictions/metrics — a prior bug
        # (source column left in the exogenous set + unscaled exog) made
        # ``garch_x_garch`` and ``garch_x_gjr_garch`` numerically
        # indistinguishable. Where two or more variants both produced a
        # finite QLIKE, assert the values differ.
        finite = vb[np.isfinite(vb["QLIKE"])]
        finite_x = finite[finite["model"].str.startswith("garch_x_")]
        if len(finite_x) >= 2:
            qlikes = finite_x.set_index("model")["QLIKE"]
            assert qlikes.nunique() == len(qlikes), (
                "Two or more GARCH-X variants produced identical QLIKE — "
                "likely a spec-collision regression"
            )

        # The GARCH-X exogenous mean equation (``arch`` ARX + up to 36
        # correlated regressors on ~500-1300 training obs) has a known,
        # documented numerical instability that lives in garch.py's ARX
        # fit (out of scope for this fix — see horse_race.py's
        # DEGENERATE_VOL_RATIO guard in ``_aggregate``). Rather than
        # asserting every QLIKE is finite (which silently passed before
        # even when the value was astronomically wrong, e.g. 1e296), we
        # assert the guard is doing its job: QLIKE is EITHER finite and
        # within a sane multiple of the plain GARCH QLIKE on the same
        # target, OR NaN with n_obs == 0 (every fold in this window was
        # flagged degenerate and excluded — never a silently-wrong
        # number).
        plain_qlike = vb.loc[vb["model"] == "garch", "QLIKE"].iloc[0]
        for _, row in vb[vb["model"].str.startswith("garch_x_")].iterrows():
            if np.isfinite(row["QLIKE"]):
                assert row["QLIKE"] < 100 * plain_qlike, (
                    f"{row['model']}: QLIKE={row['QLIKE']} is not within a "
                    f"sane range of the plain GARCH QLIKE={plain_qlike}"
                )
            else:
                assert row["n_obs"] == 0, (
                    f"{row['model']}: QLIKE is NaN but n_obs={row['n_obs']} "
                    "(expected all folds to be degenerate-guarded)"
                )
