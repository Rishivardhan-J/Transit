import logging
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
