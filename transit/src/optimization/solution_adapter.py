import uuid
from typing import List, Optional
from datetime import datetime
from src.data_processing.schemas import Route, Order, Vehicle

def create_route_object(
    vehicle: Vehicle,
    ordered_stops: List[str],
    predicted_arrival_times: List[datetime],
    total_distance_km: float,
    total_predicted_time_min: float,
    total_cost: float,
    run_id: Optional[str] = None,
    stop_slack_min: Optional[List[float]] = None,
) -> Route:
    """
    Parses solver-specific output into a valid Route Pydantic schema instance.
    Generates and populates a unique optimizer_run_id linking the route to the solver run.
    """
    return Route(
        route_id=f"rt_{uuid.uuid4().hex[:8]}",
        vehicle_id=vehicle.vehicle_id,
        ordered_stops=ordered_stops,
        predicted_arrival_times=predicted_arrival_times,
        total_distance_km=total_distance_km,
        total_predicted_time_min=total_predicted_time_min,
        total_cost=total_cost,
        optimizer_run_id=run_id or f"run_{uuid.uuid4().hex[:8]}",
        stop_slack_min=stop_slack_min or [],
    )
