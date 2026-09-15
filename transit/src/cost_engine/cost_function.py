from typing import Optional, Dict
from src.cost_engine.config import CostWeights, PRIORITY_MULTIPLIERS

def compute_delay_penalty(
    arrival_time_minutes: float, 
    time_window_end: float, 
    priority: str
) -> float:
    """
    Computes penalty if arrival time exceeds the time window end.
    Delay is scaled by priority multiplier.
    """
    if arrival_time_minutes <= time_window_end:
        return 0.0
    
    delay_minutes = arrival_time_minutes - time_window_end
    multiplier = PRIORITY_MULTIPLIERS.get(priority.lower(), 1.0)
    return delay_minutes * multiplier

def compute_fuel_cost(distance_km: float, fuel_efficiency: float, fuel_price: float = 1.5) -> float:
    """
    Computes fuel cost.
    Fuel efficiency is e.g. km per liter. Fuel price is cost per liter.
    """
    if fuel_efficiency <= 0:
        return 0.0
    liters_used = distance_km / fuel_efficiency
    return liters_used * fuel_price

def compute_edge_cost(
    distance_km: float,
    predicted_time_min: float, # Pre-selected p50 or risk_adjusted blend
    fuel_efficiency: float,
    priority: str,
    arrival_time_min: float,
    time_window_end: float,
    weights: CostWeights,
    is_infeasible: bool = False
) -> float:
    """
    Computes the total dynamic weighted cost for traversing an edge between two nodes.
    
    `is_infeasible` can be set to True by the solver if evaluating a route that violates 
    hard constraints (capacity, strict time window). This applies the w_constraint penalty.
    """
    cost_dist = distance_km * weights.w_distance
    cost_time = predicted_time_min * weights.w_time
    
    fuel_val = compute_fuel_cost(distance_km, fuel_efficiency)
    cost_fuel = fuel_val * weights.w_fuel
    
    delay_val = compute_delay_penalty(arrival_time_min, time_window_end, priority)
    cost_delay = delay_val * weights.w_delay
    
    cost_penalty = weights.w_constraint if is_infeasible else 0.0
    
    total_cost = cost_dist + cost_time + cost_fuel + cost_delay + cost_penalty
    return total_cost
