from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.user import User
from backend.services import optimization as svc

router = APIRouter()


def _summary(r: DBOptimizerRun) -> dict:
    return {
        "id": r.id, "created_at": r.created_at.isoformat() if r.created_at else None, "solver": r.solver_type,
        "status": r.status, "parent_run_id": r.parent_run_id, "event": r.event, "runtime_s": r.runtime_s,
        "time_model": r.time_model, "weights": r.weight_config, "metrics": r.metrics,
        "baseline_metrics": r.baseline_metrics, "unassigned_count": len(r.unassigned or []), "error": r.error,
    }


@router.get("/optimizer-runs")
def list_runs(limit: int = 25, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(DBOptimizerRun).order_by(DBOptimizerRun.created_at.desc()).limit(min(limit, 200)).all()
    return [_summary(r) for r in rows]


@router.get("/optimizer-runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return svc.plan_from_db(db, run_id)
    except ValueError:
        raise HTTPException(404, "Optimizer run not found")


@router.get("/jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Polling fallback for the WebSocket: job ids double as optimizer-run ids."""
    run = db.get(DBOptimizerRun, job_id)
    if run is None:
        return {"job_id": job_id, "status": "pending"}
    out = {"job_id": job_id, "status": run.status, "optimizer_run_id": run.id, "error": run.error}
    if run.status == "completed":
        m = run.metrics or {}
        out["result"] = {"routes": m.get("vehicles_used"), "unassigned": len(run.unassigned or []),
                         "predicted_late": m.get("predicted_late"), "total_distance": m.get("total_distance"),
                         "total_cost": m.get("total_cost")}
    return out
