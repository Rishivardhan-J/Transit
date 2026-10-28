from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.jobs.optimization_tasks import run_batch_optimization, run_incremental_reoptimization
from backend.models_db.converters import from_db_route, to_db_order
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.order import DBOrder
from backend.models_db.route import DBRoute
from backend.models_db.user import User
from backend.schemas.events import DisruptionEvent, NewOrderEvent
from backend.services import optimization as svc
from src.data_processing.schemas import OrderStatus, Route

router = APIRouter()


class OptimizeRequest(BaseModel):
    order_ids: List[str] = Field(default_factory=list, description="Empty = every pending/assigned/late order")
    vehicle_ids: List[str] = Field(default_factory=list, description="Empty = every active vehicle")
    solver_type: str = "hgs"
    weight_config: Dict[str, Any] = {"preset": "balanced"}
    risk_lambda: float = Field(0.25, ge=0.0, le=1.0, description="0 plans on median leg times, 1 on p90")
    max_runtime_s: float = Field(20.0, gt=0.0, le=120.0)


class WhatIfRequest(BaseModel):
    w_distance: float = Field(0.25, ge=0)
    w_time: float = Field(0.25, ge=0)
    w_fuel: float = Field(0.25, ge=0)
    w_delay: float = Field(0.25, ge=0)
    order_ids: List[str] = Field(default_factory=list)
    vehicle_ids: List[str] = Field(default_factory=list)
    risk_lambda: float = Field(0.25, ge=0.0, le=1.0)
    max_runtime_s: float = Field(6.0, gt=0.0, le=30.0)
    commit: bool = False


class DisruptRequest(BaseModel):
    optimizer_run_id: Optional[str] = Field(None, description="Defaults to the latest completed run")
    event: DisruptionEvent


@router.post("/optimize", status_code=status.HTTP_202_ACCEPTED)
def start_optimization(req: OptimizeRequest, current_user: User = Depends(get_current_user)):
    if req.solver_type not in svc.SOLVERS:
        raise HTTPException(422, f"solver_type must be one of {svc.SOLVERS}")
    task = run_batch_optimization.delay(req.order_ids, req.vehicle_ids, req.solver_type, req.weight_config,
                                        req.risk_lambda, req.max_runtime_s)
    return {"job_id": task.id, "status": "pending"}


def _delta(new: dict, old: Optional[dict]) -> Optional[dict]:
    if not old:
        return None
    keys = ("total_distance", "total_time_min", "total_cost", "vehicles_used", "predicted_late", "orders_unassigned", "utilization_pct")
    return {k: round(new.get(k, 0) - old.get(k, 0), 3) for k in keys if old.get(k) is not None}


@router.post("/whatif")
def what_if(req: WhatIfRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Synchronous re-solve under new cost weights (PRD 11.5). Nothing is saved unless commit=true."""
    cfg = {"w_distance": req.w_distance, "w_time": req.w_time, "w_fuel": req.w_fuel, "w_delay": req.w_delay}
    if sum(cfg.values()) <= 0:
        raise HTTPException(422, "At least one weight must be positive.")
    try:
        out = svc.run_optimization(db, req.order_ids or None, req.vehicle_ids or None, "hgs", cfg, req.risk_lambda,
                                   req.max_runtime_s, persist=req.commit)
    except ValueError as e:
        raise HTTPException(422, str(e))
    current = svc.latest_run(db)
    plan = svc.serialize_plan(out["problem"], out["result"], out["preds"])
    return {
        "committed": req.commit, "weights": out["weights"].model_dump(), "plan": plan,
        "metrics": out["metrics"], "baseline": out["baseline"],
        "current_metrics": current.metrics if current and not req.commit else None,
        "delta_vs_current": _delta(out["metrics"], current.metrics) if current and not req.commit else None,
    }


@router.post("/disrupt", status_code=status.HTTP_202_ACCEPTED)
def disrupt_route(req: DisruptRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run_id = req.optimizer_run_id
    if run_id is None:
        latest = svc.latest_run(db)
        if latest is None:
            raise HTTPException(409, "No completed optimization run to disrupt. Run an optimization first.")
        run_id = latest.id
    elif db.get(DBOptimizerRun, run_id) is None:
        raise HTTPException(404, "Optimizer run not found")
    event = req.event.model_dump(mode="json")
    if isinstance(req.event, NewOrderEvent):  # the new order becomes real data immediately; the job then fits it into the plan
        if db.get(DBOrder, req.event.order.order_id) is None:
            db.add(to_db_order(req.event.order.model_copy(update={"status": OrderStatus.PENDING})))
            db.commit()
    task = run_incremental_reoptimization.delay(run_id, event)
    return {"job_id": task.id, "status": "pending", "parent_run_id": run_id}


@router.get("/{route_id}", response_model=Route)
def get_route(route_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_route = db.query(DBRoute).filter(DBRoute.route_id == route_id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")
    return from_db_route(db_route)


@router.get("", response_model=List[Route])
def list_routes(optimizer_run_id: Optional[str] = None, all_runs: bool = False, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    """Routes of the latest completed run by default; pass optimizer_run_id or all_runs=true for others."""
    query = db.query(DBRoute)
    if optimizer_run_id:
        query = query.filter(DBRoute.optimizer_run_id == optimizer_run_id)
    elif not all_runs:
        latest = svc.latest_run(db)
        if latest is None:
            return []
        query = query.filter(DBRoute.optimizer_run_id == latest.id)
    return [from_db_route(r) for r in query.all()]
