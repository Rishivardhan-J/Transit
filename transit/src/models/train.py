"""Train and register a travel-time model bundle.

    python -m src.models.train --dataset legs  [--trials 12] [--sample 0]
    python -m src.models.train --dataset food

* Grouped chronological split (never random k-fold: PRD 6.1).
* LightGBM quantile models p10/p50/p90 with early stopping; Optuna tunes p50 and its parameters are
  reused for the other quantiles (documented deviation from per-quantile tuning, for runtime).
* Conformalized quantile regression (CQR) widens/narrows [p10, p90] on the validation split so the
  held-out 80% interval actually covers about 80%.
* Random Forest and XGBoost p50 challengers are scored on the same test split for the comparison.
* Reported against two naive baselines, so the lift over a geometry-only guess is visible.
"""
import argparse
import hashlib
import json
import logging
import os

import lightgbm as lgb
import mlflow
import numpy as np
import optuna
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.feature_engineering.feature_pipeline import (
    FOOD_FEATURES, LEG_FEATURES, build_feature_pipeline, haversine_km,
)
from src.models.config import RANDOM_SEED
from src.models.data_split import split_by_time
from src.models.evaluate import empirical_coverage, pinball_loss
from src.models.model_registry import save_bundle, set_latest
from src.paths import MLFLOW_URI, PROCESSED_DIR, RESULTS_DIR

logger = logging.getLogger("train")
optuna.logging.set_verbosity(optuna.logging.WARNING)

SPECS = {
    "legs": {
        "kind": "leg", "path": PROCESSED_DIR / "amazon_legs.parquet", "time_col": "route_date",
        "target": "travel_time_sec", "unit": "sec", "features": LEG_FEATURES,
    },
    "food": {
        "kind": "order", "path": PROCESSED_DIR / "food_model.parquet", "time_col": "created_at",
        "target": "actual_delivery_time_minutes", "unit": "min", "features": FOOD_FEATURES,
    },
}
# Features that exist only after the trip happened must never appear here (leakage audit).
# Raw columns that a caller may not know at serving time; the training-set median stands in for them.
SERVING_DEFAULT_COLS = {
    "leg": ["stop_idx", "n_stops", "to_n_packages", "to_volume_cm3", "to_n_time_windows", "from_service_sec", "capacity_cm3"],
    "order": ["prep_time_min", "courier_exp_yrs"],
}
FORBIDDEN = {"travel_time_sec", "actual_delivery_time_minutes", "route_score", "status", "delivered_at"}


def naive_baselines(spec, train, test, y_train):
    """B1: geometry x global speed. B2: geometry x per-group median speed (station / traffic level)."""
    if spec["kind"] == "leg":
        km = lambda d: haversine_km(d.from_lat, d.from_lng, d.to_lat, d.to_lng)
        spk = y_train / np.maximum(km(train), 0.05)
        g = float(np.median(spk))
        b1 = km(test) * g
        med = pd.Series(spk).groupby(train["station_code"].values).median()
        b2 = km(test) * test["station_code"].map(med).fillna(g).values
    else:
        mpk = y_train / np.maximum(train["distance_km"].values, 0.1)
        g = float(np.median(mpk))
        b1 = test["distance_km"].values * g
        med = pd.Series(mpk).groupby(train["traffic_level"].values).median()
        b2 = test["distance_km"].values * test["traffic_level"].map(med).fillna(g).values
    return {"naive_global_speed": np.asarray(b1), "naive_group_speed": np.asarray(b2)}


def point_metrics(y, p):
    return {
        "MAE": float(mean_absolute_error(y, p)), "RMSE": float(np.sqrt(mean_squared_error(y, p))),
        "R2": float(r2_score(y, p)), "WAPE": float(np.abs(y - p).sum() / np.abs(y).sum()),
    }


def fit_lgb(params, alpha, X, y, Xv, yv, cat, n_estimators=2000):
    m = lgb.LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=n_estimators, random_state=RANDOM_SEED,
                          n_jobs=-1, verbosity=-1, **params)
    m.fit(X, y, eval_set=[(Xv, yv)], eval_metric="quantile", categorical_feature=cat,
          callbacks=[lgb.early_stopping(50, verbose=False)])
    return m


def tune_p50(X, y, Xv, yv, cat, trials, sample):
    if trials <= 0:
        return {"num_leaves": 63, "learning_rate": 0.08, "min_child_samples": 40, "feature_fraction": 0.8,
                "bagging_fraction": 0.8, "bagging_freq": 1, "reg_lambda": 1.0}
    rng = np.random.RandomState(RANDOM_SEED)
    idx = rng.choice(len(X), min(sample, len(X)), replace=False)
    Xs, ys = X.iloc[idx], y[idx]

    def objective(t):
        params = {
            "num_leaves": t.suggest_int("num_leaves", 15, 255, log=True),
            "learning_rate": t.suggest_float("learning_rate", 0.03, 0.2, log=True),
            "min_child_samples": t.suggest_int("min_child_samples", 10, 200, log=True),
            "feature_fraction": t.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": t.suggest_float("bagging_fraction", 0.5, 1.0), "bagging_freq": 1,
            "reg_lambda": t.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }
        m = fit_lgb(params, 0.5, Xs, ys, Xv, yv, cat, n_estimators=600)
        return mean_absolute_error(yv, m.predict(Xv))

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    study.optimize(objective, n_trials=trials)
    p = dict(study.best_params)
    p.update(bagging_freq=1)
    return p


def conformal_offset(y, lo, hi, alpha=0.2):
    """CQR: the (1-alpha)(1+1/n) quantile of the conformity scores max(lo-y, y-hi)."""
    scores = np.maximum(lo - y, y - hi)
    n = len(y)
    level = min(1.0, (1 - alpha) * (1 + 1.0 / n))
    return float(np.quantile(scores, level))


def importances(model, X_test, y_test, cat, shap_n=2000, perm_n=20000):
    names = list(X_test.columns)
    gain = model.booster_.feature_importance(importance_type="gain").astype(float)
    gain = gain / gain.sum()
    sub = X_test.sample(min(perm_n, len(X_test)), random_state=RANDOM_SEED)
    perm = permutation_importance(model, sub, y_test[sub.index.map(lambda i: X_test.index.get_loc(i))],
                                  scoring="neg_mean_absolute_error", n_repeats=3, random_state=RANDOM_SEED, n_jobs=1)
    perm_imp = np.maximum(perm.importances_mean, 0)
    perm_imp = perm_imp / perm_imp.sum() if perm_imp.sum() > 0 else perm_imp
    shap_sub = X_test.sample(min(shap_n, len(X_test)), random_state=RANDOM_SEED)
    sv = shap.TreeExplainer(model).shap_values(shap_sub)
    sh = np.abs(sv).mean(axis=0)
    sh = sh / sh.sum()
    rho = spearmanr(gain, perm_imp).statistic
    rows = sorted(({"feature": n, "impurity": float(g), "permutation": float(p), "shap_mean_abs": float(s)}
                   for n, g, p, s in zip(names, gain, perm_imp, sh)), key=lambda r: -r["permutation"])
    return {"features": rows, "impurity_vs_permutation_spearman": float(rho)}


def run(dataset: str, trials: int, tune_sample: int, max_rows: int):
    spec = SPECS[dataset]
    df = pd.read_parquet(spec["path"])
    if max_rows and len(df) > max_rows:
        df = df.sample(max_rows, random_state=RANDOM_SEED)
    data_hash = hashlib.sha1(pd.util.hash_pandas_object(df[[spec["target"]]], index=False).values.tobytes()).hexdigest()[:12]
    train, val, test = split_by_time(df, spec["time_col"])
    logger.info("rows train/val/test = %d/%d/%d", len(train), len(val), len(test))
    assert train[spec["time_col"]].max() <= val[spec["time_col"]].min() <= test[spec["time_col"]].min()

    y_tr, y_va, y_te = (d[spec["target"]].values.astype(float) for d in (train, val, test))
    pipe = build_feature_pipeline(spec["kind"])
    X_tr = pipe.fit_transform(train, y_tr)           # fitted on train only
    X_va, X_te = pipe.transform(val), pipe.transform(test)
    cat = pipe.named_steps["encoder"].cat_cols
    feats = list(X_tr.columns)
    assert not (set(feats) & FORBIDDEN), f"post-outcome feature in model inputs: {set(feats) & FORBIDDEN}"
    assert set(feats) <= set(spec["features"])

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(f"transit-{dataset}")
    with mlflow.start_run(run_name=f"lgbm-{dataset}"):
        params = tune_p50(X_tr, y_tr, X_va, y_va, cat, trials, tune_sample)
        logger.info("params %s", params)
        models = {q: fit_lgb(params, a, X_tr, y_tr, X_va, y_va, cat) for q, a in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9))}

        val_lo, val_hi = models["p10"].predict(X_va), models["p90"].predict(X_va)
        qhat = conformal_offset(y_va, val_lo, val_hi)
        raw = {q: m.predict(X_te) for q, m in models.items()}
        lo = np.minimum(raw["p10"] - qhat, raw["p50"])
        hi = np.maximum(raw["p90"] + qhat, raw["p50"])
        lo = np.maximum(lo, 0.0)

        metrics = {f"test_{k}": v for k, v in point_metrics(y_te, raw["p50"]).items()}
        metrics.update({
            "test_pinball_p10": pinball_loss(y_te, lo, 0.1), "test_pinball_p50": pinball_loss(y_te, raw["p50"], 0.5),
            "test_pinball_p90": pinball_loss(y_te, hi, 0.9),
            "test_coverage80_raw": float(empirical_coverage(y_te, raw["p10"], raw["p90"])),
            "test_coverage80_cqr": float(empirical_coverage(y_te, lo, hi)),
            "test_interval_width_mean": float(np.mean(hi - lo)),
            "test_quantile_crossing_rate": float(np.mean((raw["p10"] > raw["p50"]) | (raw["p50"] > raw["p90"]))),
            "cqr_offset": qhat,
        })
        baselines = {n: point_metrics(y_te, p) for n, p in naive_baselines(spec, train, test, y_tr).items()}
        best_naive = min(b["MAE"] for b in baselines.values())
        metrics["test_mae_lift_vs_best_naive"] = 1 - metrics["test_MAE"] / best_naive

        # challengers on the same split (p50 only; subsampled for runtime)
        sub = np.random.RandomState(RANDOM_SEED).choice(len(X_tr), min(150_000, len(X_tr)), replace=False)
        rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=5, n_jobs=-1, random_state=RANDOM_SEED)
        rf.fit(X_tr.iloc[sub].fillna(-1), y_tr[sub])
        comparison = {"lightgbm": point_metrics(y_te, raw["p50"]),
                      "random_forest": point_metrics(y_te, rf.predict(X_te.fillna(-1)))}
        try:
            import xgboost as xgb
            xg = xgb.XGBRegressor(objective="reg:quantileerror", quantile_alpha=0.5, n_estimators=400, learning_rate=0.1,
                                  max_depth=8, n_jobs=-1, random_state=RANDOM_SEED, tree_method="hist")
            xg.fit(X_tr, y_tr)
            comparison["xgboost"] = point_metrics(y_te, xg.predict(X_te))
        except Exception as e:  # challenger is optional
            logger.warning("xgboost challenger skipped: %s", e)

        imp = importances(models["p50"], X_te, y_te, cat)
        top = [r["feature"] for r in imp["features"][:5]]
        logger.info("top permutation features: %s", top)

        meta = {
            "dataset": dataset, "unit": spec["unit"], "target": spec["target"], "seed": RANDOM_SEED,
            "features": feats, "categorical": cat, "params": params, "data_hash": data_hash,
            "rows": {"train": len(train), "val": len(val), "test": len(test)},
            "time_ranges": {k: [str(d[spec["time_col"]].min()), str(d[spec["time_col"]].max())]
                            for k, d in (("train", train), ("val", val), ("test", test))},
            "metrics": metrics, "baselines": baselines, "comparison": comparison,
            "leakage_audit": {"forbidden_features_present": False, "r2_above_0.97": metrics["test_R2"] > 0.97,
                              "note": "R2>0.97 requires manual SHAP review (PRD 18.1)" if metrics["test_R2"] > 0.97 else "ok"},
            "defaults": {c: float(train[c].median()) for c in SERVING_DEFAULT_COLS[spec["kind"]]},
            "best_iterations": {q: int(m.best_iteration_ or 0) for q, m in models.items()},
        }
        d = save_bundle(spec["kind"], pipe, models, meta, imp)
        set_latest(spec["kind"], d)
        mlflow.log_params({k: v for k, v in params.items()})
        mlflow.log_param("dataset", dataset); mlflow.log_param("bundle", d.name)
        mlflow.log_metrics({k: v for k, v in metrics.items() if np.isfinite(v)})
        mlflow.log_artifact(str(d / "metadata.json")); mlflow.log_artifact(str(d / "importance.json"))

    print(json.dumps({"bundle": d.name, "metrics": metrics, "baselines": baselines, "comparison": comparison,
                      "top_features": top, "impurity_vs_permutation_spearman": imp["impurity_vs_permutation_spearman"]}, indent=2))
    return d


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=list(SPECS), required=True)
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--tune-sample", type=int, default=150_000)
    ap.add_argument("--max-rows", type=int, default=0, help="subsample for quick runs")
    a = ap.parse_args()
    run(a.dataset, a.trials, a.tune_sample, a.max_rows)
