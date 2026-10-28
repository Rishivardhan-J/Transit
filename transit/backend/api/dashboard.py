import csv
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models_db.order import DBOrder
from backend.models_db.route import DBRoute
from backend.models_db.user import User
from backend.models_db.vehicle import DBVehicle
from backend.services import optimization as svc
from src.data_processing.schemas import OrderStatus
from src.models.model_registry import load_bundle
from src.paths import RESULTS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)


def _benchmark_gap():
    """HGS vs OR-Tools total distance across the Solomon suite (a separate, offline number from the live baseline)."""
    path = RESULTS_DIR / "benchmark_summary.csv"
    try:
        with open(path) as f:
            rows = list(csv.DictReader(f))
        hgs, ort = sum(float(r["HGS_Dist"]) for r in rows), sum(float(r["ORT_Dist"]) for r in rows)
        return round((hgs - ort) / ort * 100, 1) if ort > 0 else None
    except Exception:
        return None


@router.get("/kpis")
def get_dashboard_kpis(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_vehicles = db.query(func.count(DBVehicle.vehicle_id)).filter(DBVehicle.is_active.is_(True)).scalar() or 0
    run = svc.latest_run(db)
    active_routes = vehicles_used = 0
    predicted_late = 0
    cost_vs_baseline = None
    baseline_name = "nearest neighbour"
    if run:
        active_routes = db.query(func.count(DBRoute.route_id)).filter(DBRoute.optimizer_run_id == run.id).scalar() or 0
        vehicles_used = db.query(func.count(func.distinct(DBRoute.vehicle_id))).filter(DBRoute.optimizer_run_id == run.id).scalar() or 0
        m, b = run.metrics or {}, run.baseline_metrics or {}
        predicted_late = m.get("predicted_late", 0)
        # compare cost per served order so a baseline that drops orders cannot look cheaper
        if m.get("cost_per_order") and b.get("cost_per_order"):
            cost_vs_baseline = round((m["cost_per_order"] - b["cost_per_order"]) / b["cost_per_order"] * 100, 1)
    late_now = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == OrderStatus.LATE).scalar() or 0

    model = {}
    for kind in ("leg", "order"):
        try:
            b = load_bundle(kind)
            model[kind] = {"version": b.version, "unit": b.metadata["unit"], "mae": round(b.metadata["metrics"]["test_MAE"], 2),
                           "r2": round(b.metadata["metrics"]["test_R2"], 3),
                           "coverage80": round(b.metadata["metrics"]["test_coverage80_cqr"], 3)}
        except FileNotFoundError:
            model[kind] = None

    return {
        "fleet_utilization_pct": round(vehicles_used / total_vehicles * 100, 1) if total_vehicles else 0,
        "active_routes": active_routes,
        "late_deliveries": late_now,
        "predicted_late": predicted_late,
        "cost_vs_baseline_pct": cost_vs_baseline,
        "baseline": baseline_name,
        "benchmark_hgs_vs_ortools_pct": _benchmark_gap(),
        "latest_run": {"id": run.id, "solver": run.solver_type, "time_model": run.time_model,
                       "created_at": run.created_at.isoformat() if run.created_at else None,
                       "unassigned": len(run.unassigned or [])} if run else None,
        "model": model,
    }
