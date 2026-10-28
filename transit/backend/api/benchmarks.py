from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models_db.user import Role, User
from backend.security.rbac import require_role
from backend.services import optimization as svc
from src.optimization.routing_metrics import evaluate_solution
from src.paths import RESULTS_DIR

router = APIRouter()


@router.get("/solver-comparison")
def get_solver_comparison(current_user: User = Depends(get_current_user)):
    """Solomon benchmark results (HGS vs OR-Tools vs Nearest Neighbour vs best-known)."""
    path = RESULTS_DIR / "benchmark_summary.csv"
    if not path.exists():
        raise HTTPException(404, "Benchmark results not found. Run `python -m scripts.run_benchmarks`.")
    return pd.read_csv(path).to_dict(orient="records")


class CompareRequest(BaseModel):
    w_distance: float = Field(0.25, ge=0)
    w_time: float = Field(0.25, ge=0)
    w_fuel: float = Field(0.25, ge=0)
    w_delay: float = Field(0.25, ge=0)
    max_runtime_s: float = Field(10.0, gt=0, le=60)
    risk_lambda: float = Field(0.25, ge=0, le=1)


@router.post("/compare-live")
def compare_live(req: CompareRequest, db: Session = Depends(get_db), user: User = Depends(require_role(Role.researcher))):
    """Run Nearest Neighbour, OR-Tools and HGS on the current orders under the same weights; nothing is saved."""
    cfg = {"w_distance": req.w_distance, "w_time": req.w_time, "w_fuel": req.w_fuel, "w_delay": req.w_delay}
    weights = svc.weights_from_config(cfg)
    try:
        orders, vehicles = svc.load_entities(db, None, None)
    except ValueError as e:
        raise HTTPException(422, str(e))
    problem = svc.build_problem(orders, vehicles, req.risk_lambda)
    rows = []
    for solver in ("nn", "ortools", "hgs"):
        res = svc.solve(problem, solver, weights, req.max_runtime_s)
        preds = svc.stop_predictions(problem, res.routes, with_shap=False)
        m = svc.plan_metrics(problem, res, weights, preds)
        rows.append({"solver": solver, **{k: m[k] for k in (
            "total_distance", "total_time_min", "total_cost", "vehicles_used", "predicted_late", "late_deliveries",
            "utilization_pct", "orders_assigned", "orders_unassigned", "runtime_s", "feasible")}})
    return {"orders": len(orders), "vehicles": len(vehicles), "time_model": problem["time_model"],
            "weights": weights.model_dump(), "solvers": rows}
