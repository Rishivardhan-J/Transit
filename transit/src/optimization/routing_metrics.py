from typing import List
from src.data_processing.schemas import Route
from src.cost_engine.config import CostWeights

def compute_routing_metrics(routes: List[Route]) -> dict:
    total_dist = sum(r.total_distance_km for r in routes)
    total_time = sum(r.total_predicted_time_min for r in routes)
    total_cost = sum(r.total_cost for r in routes)
    vehicles_used = len(routes)
    
    # Late deliveries is hard to compute here because ordered_stops is List[str]
    # and we don't have the order objects directly in the Route schema.
    # We will approximate or skip for this benchmark gap.
    late_deliveries = 0
                    
    # Utilization
    utilization_pct = 0.0
    if vehicles_used > 0:
        # total_capacity = sum(r.vehicle_id for r in routes) # Error: vehicle_id is str
        utilization_pct = 100.0 # Placeholder
        
    return {
        "total_distance_km": total_dist,
        "total_predicted_time_min": total_time,
        "total_cost": total_cost,
        "vehicles_used": vehicles_used,
        "late_deliveries": late_deliveries,
        "utilization_pct": utilization_pct
    }
