from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.api.deps import get_db, get_current_user
from backend.models_db.user import User
from backend.models_db.vehicle import DBVehicle
from backend.models_db.route import DBRoute
from backend.models_db.order import DBOrder
from src.data_processing.schemas import OrderStatus

router = APIRouter()

@router.get("/kpis")
def get_dashboard_kpis(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Total Registered Vehicles
    total_vehicles = db.query(func.count(DBVehicle.vehicle_id)).scalar()
    
    # 2. Active Routes & Vehicles used
    # Assuming the most recent optimizer run defines the active routes
    latest_run = db.query(DBRoute.optimizer_run_id).order_by(DBRoute.route_id.desc()).first()
    active_routes_count = 0
    vehicles_used = 0
    
    if latest_run:
        run_id = latest_run[0]
        active_routes_count = db.query(func.count(DBRoute.route_id)).filter(DBRoute.optimizer_run_id == run_id).scalar()
        # Each route corresponds to a vehicle, but some might be unassigned. We count active routes that have a vehicle_id
        vehicles_used = db.query(func.count(DBRoute.vehicle_id)).filter(
            DBRoute.optimizer_run_id == run_id,
            DBRoute.vehicle_id.isnot(None)
        ).scalar()
        
    fleet_utilization = (vehicles_used / total_vehicles * 100) if total_vehicles > 0 else 0
    
    # 3. Predicted late deliveries
    # For now, count orders flagged as LATE
    late_deliveries = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == OrderStatus.LATE).scalar()
    
    return {
        "fleet_utilization_pct": round(fleet_utilization, 1),
        "active_routes": active_routes_count,
        "late_deliveries": late_deliveries,
        "cost_vs_baseline_pct": -12.5 # Placeholder until Phase 6
    }
