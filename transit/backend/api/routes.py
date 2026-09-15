from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from backend.api.deps import get_db, get_current_user
from backend.models_db.user import User, Role
from backend.models_db.route import DBRoute
from backend.models_db.converters import from_db_route
from src.data_processing.schemas import Route
from backend.jobs.optimization_tasks import run_batch_optimization, run_incremental_reoptimization

router = APIRouter()

class OptimizeRequest(BaseModel):
    order_ids: List[str]
    vehicle_ids: List[str]
    solver_type: str = "hgs"
    weight_config: Dict[str, Any] = {"preset": "balanced"}

@router.post("/optimize", status_code=status.HTTP_202_ACCEPTED)
def start_optimization(req: OptimizeRequest, current_user: User = Depends(get_current_user)):
    task = run_batch_optimization.delay(req.order_ids, req.vehicle_ids, req.solver_type, req.weight_config)
    return {"job_id": task.id, "status": "pending"}

@router.post("/disrupt", status_code=status.HTTP_202_ACCEPTED)
def disrupt_route(optimizer_run_id: str, event: dict, current_user: User = Depends(get_current_user)):
    task = run_incremental_reoptimization.delay(optimizer_run_id, event)
    return {"job_id": task.id, "status": "pending"}

@router.get("/{route_id}", response_model=Route)
def get_route(route_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_route = db.query(DBRoute).filter(DBRoute.route_id == route_id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")
    return from_db_route(db_route)

@router.get("", response_model=List[Route])
def list_routes(optimizer_run_id: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(DBRoute)
    if optimizer_run_id:
        query = query.filter(DBRoute.optimizer_run_id == optimizer_run_id)
    db_routes = query.all()
    return [from_db_route(r) for r in db_routes]
