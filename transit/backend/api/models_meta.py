import logging
from functools import lru_cache
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.models_db.user import Role, User
from backend.security.rbac import require_role
from src.models.model_registry import list_bundles, load_bundle
from src.paths import MLFLOW_URI

router = APIRouter()
logger = logging.getLogger(__name__)


def _mlflow_runs(limit: int = 50):
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_URI)
        df = mlflow.search_runs(search_all_experiments=True, max_results=limit, order_by=["start_time DESC"], output_format="pandas")
    except Exception as e:  # MLflow is observability, not a hard dependency of the API
        logger.warning("MLflow unavailable: %s", e)
        return []
    clean = lambda v: None if v is None or (isinstance(v, float) and v != v) else v
    runs = []
    for _, r in df.iterrows():
        metrics = {c[len("metrics."):]: float(r[c]) for c in df.columns if c.startswith("metrics.") and r[c] == r[c]}
        if not metrics:
            continue
        runs.append({
            "run_id": r["run_id"], "model_type": "lightgbm", "dataset": clean(r.get("params.dataset")),
            "bundle": clean(r.get("params.bundle")), "metrics": metrics,
            "timestamp": r["start_time"].isoformat() if hasattr(r["start_time"], "isoformat") else str(r["start_time"]),
        })
    return runs


@router.get("/performance")
def get_model_performance(current_user: User = Depends(require_role(Role.researcher))):
    """Experiment history (MLflow) + version history of model bundles with metrics, baselines and challenger comparison."""
    bundles = list_bundles()
    return {
        "runs": _mlflow_runs(),
        "bundles": [{
            "version": b["version"], "kind": b["kind"], "dataset": b["dataset"], "unit": b["unit"], "active": b["active"],
            "created_at": b["created_at"], "metrics": b["metrics"], "baselines": b.get("baselines", {}),
            "comparison": b.get("comparison", {}), "rows": b["rows"], "leakage_audit": b.get("leakage_audit"),
        } for b in bundles],
    }


@router.get("/")
def get_models_metadata(current_user: User = Depends(require_role(Role.researcher))):
    out = {}
    for kind in ("leg", "order"):
        try:
            b = load_bundle(kind)
        except FileNotFoundError:
            out[kind] = None
            continue
        out[kind] = {"version": b.version, "unit": b.metadata["unit"], "features": b.metadata["features"],
                     "params": b.metadata["params"], "metrics": b.metadata["metrics"], "importance": b.importance}
    if not any(out.values()):
        raise HTTPException(503, "No trained models found. Run `python -m src.models.train --dataset legs`.")
    return out


@lru_cache(maxsize=4)
def _diagnostics(version: str, kind: str):
    import numpy as np
    import pandas as pd

    from src.models.data_split import split_by_time
    from src.models.serving import predict_quantiles
    from src.models.train import SPECS

    bundle = load_bundle(kind, version)
    spec = next(s for s in SPECS.values() if s["kind"] == kind)
    df = pd.read_parquet(spec["path"])
    _, _, test = split_by_time(df, spec["time_col"])
    test = test.sample(min(1500, len(test)), random_state=42)
    q = predict_quantiles(bundle, test)
    y = test[spec["target"]].to_numpy(dtype=float)
    resid = y - q["p50"].to_numpy()
    lo, hi = np.percentile(resid, 1), np.percentile(resid, 99)
    counts, edges = np.histogram(np.clip(resid, lo, hi), bins=24, range=(float(lo), float(hi)))
    return {
        "version": bundle.version, "unit": bundle.metadata["unit"], "n": int(len(test)),
        "points": [{"actual": float(a), "p50": float(p), "p10": float(l), "p90": float(h)}
                   for a, p, l, h in zip(y, q["p50"], q["p10"], q["p90"])],
        "residual_hist": [{"bin": f"{edges[i]:.3g}", "count": int(c)} for i, c in enumerate(counts)],
        "coverage": {"raw": bundle.metadata["metrics"]["test_coverage80_raw"], "calibrated": bundle.metadata["metrics"]["test_coverage80_cqr"], "target": 0.8},
    }


@router.get("/diagnostics")
def get_diagnostics(kind: str = "leg", current_user: User = Depends(require_role(Role.researcher))):
    """Predicted-vs-actual sample and residuals on the held-out test split of the active model."""
    if kind not in ("leg", "order"):
        raise HTTPException(422, "kind must be 'leg' or 'order'")
    try:
        return _diagnostics(load_bundle(kind).version, kind)
    except FileNotFoundError:
        raise HTTPException(503, "No trained model found.")
