import time
import uuid
import numpy as np
import math
from typing import Dict, Any, List
from datetime import timedelta

from pyvrp import Model, Result
from pyvrp.stop import MaxRuntime, MaxIterations, MultipleCriteria

from src.data_processing.schemas import Route, Vehicle
from src.optimization.solution_adapter import create_route_object
from src.optimization.infeasibility import infeasibility_tracker
from src.cost_engine.config import CostWeights
from src.cost_engine.cost_function import compute_edge_cost

def solve_with_hgs(
    problem: Dict[str, Any],
    weights: CostWeights,
    max_runtime_seconds: float = 30.0,
    max_iterations_no_improvement: int = 2000,
    seed: int = 42
) -> List[Route]:
    """
    Solves a CVRPTW problem instance using PyVRP's HGS implementation.
    """
    orders = problem["orders"]
    vehicles = problem["vehicles"]
    dist_matrix = problem["dist_matrix"]
    time_matrix = problem["time_matrix"]
    
    n_customers = len(orders)
    
    TIME_MUL = 100
    
    m = Model()
    m.add_vehicle_type(len(vehicles), capacity=int(vehicles[0].capacity))
    
    # Depot is index 0
    depot_loc = m.add_location(x=problem["depot_lat"], y=problem["depot_lng"])
    depot = m.add_depot(
        location=depot_loc,
        tw_early=0,
        tw_late=int((vehicles[0].available_until - vehicles[0].available_from).total_seconds() / 60) * TIME_MUL
    )
    
    clients = []
    base_time = vehicles[0].available_from
    
    # Track which clients are strictly infeasible before adding
    valid_orders = []
    valid_indices = []
    
    client_locs = []
    
    for i, order in enumerate(orders):
        # Time windows relative to base_time in minutes
        tw_early = int((order.time_window_start - base_time).total_seconds() / 60)
        tw_late = int((order.time_window_end - base_time).total_seconds() / 60)
        service = int(order.service_time_minutes)
        demand = int(order.demand_weight)
        
        # Simple feasibility check: if demand > capacity, exclude immediately
        if demand > vehicles[0].capacity:
            infeasibility_tracker.record_unassigned(order, "Demand exceeds max vehicle capacity")
            continue
            
        valid_orders.append(order)
        valid_indices.append(i + 1)
        
        client_loc = m.add_location(x=order.delivery_lat, y=order.delivery_lng)
        client_locs.append(client_loc)
        
        client = m.add_client(
            location=client_loc,
            delivery=demand,
            service_duration=service * TIME_MUL,
            tw_early=max(0, tw_early * TIME_MUL),
            tw_late=tw_late * TIME_MUL
        )

    locations = [depot_loc] + client_locs
    
    # Build edges using the dynamic cost engine
    # In PyVRP Model, distance is used as the objective cost. We map our total_cost -> distance.
    # We map time_matrix -> duration.
    for i, frm in enumerate(locations):
        for j, to in enumerate(locations):
            # i, j map to valid_indices
            orig_i = 0 if i == 0 else valid_indices[i-1]
            orig_j = 0 if j == 0 else valid_indices[j-1]
            
            dist_km = dist_matrix[orig_i, orig_j]
            pred_time = time_matrix[orig_i, orig_j]
            
            target_order = None
            if j > 0:
                target_order = valid_orders[j-1]
                
            priority = target_order.priority if target_order else "standard"
            time_window_end_min = int((target_order.time_window_end - base_time).total_seconds() / 60) if target_order else 999999
            
            # For HGS initialization we don't have arrival times yet, so we assume arrival_time=0 
            # for the cost setup, letting PyVRP handle TW natively via tw_late. 
            # Our custom cost engine acts as the edge weight.
            edge_cost = compute_edge_cost(
                distance_km=dist_km,
                predicted_time_min=pred_time,
                fuel_efficiency=vehicles[0].fuel_efficiency,
                priority=priority,
                arrival_time_min=0.0, 
                time_window_end=time_window_end_min,
                weights=weights,
                is_infeasible=False
            )
            
            m.add_edge(frm, to, distance=int(edge_cost * 1000), duration=int(pred_time * TIME_MUL))

    # Solve
    res = m.solve(
        stop=MultipleCriteria([
            MaxRuntime(max_runtime_seconds),
            MaxIterations(max_iterations_no_improvement)
        ]),
        seed=seed,
        display=False
    )
    
    # Parse solution
    routes = []
    if not res.best.is_feasible():
        # Handle infeasibility - in Phase 3 we rely on PyVRP's internal mechanisms 
        # but if it fails completely, we return empty and all are unassigned.
        for o in valid_orders:
            infeasibility_tracker.record_unassigned(o, "Solver failed to find feasible global route")
        return []

    # Map PyVRP routes to schemas
    for route_idx, pyvrp_route in enumerate(res.best.routes()):
        ordered_stops_ids = []
        predicted_arrival_times = []
        
        current_time = 0.0
        current_loc_idx = 0
        total_dist_km = 0.0
        total_time_min = 0.0
        
        for activity in pyvrp_route:
            if not activity.is_client():
                continue
            client_node = activity.idx
            # In PyVRP, client idx is 0-indexed among clients.
            # It directly maps to our valid_orders array since we added them in order.
            order = valid_orders[client_node]
            ordered_stops_ids.append(order.order_id)
            
            orig_i = 0 if current_loc_idx == 0 else valid_indices[current_loc_idx-1]
            orig_j = valid_indices[client_node]
            
            # Update current_loc_idx to the location index of this client (1-based in valid_indices)
            current_loc_idx = client_node + 1
            
            step_dist = dist_matrix[orig_i, orig_j]
            step_time = time_matrix[orig_i, orig_j]
            
            total_dist_km += step_dist
            total_time_min += step_time
            
            current_time += step_time
            # Wait if arriving before time window
            order_tw_early = int((order.time_window_start - base_time).total_seconds() / 60)
            if current_time < order_tw_early:
                current_time = order_tw_early
                
            arrival_datetime = base_time + timedelta(minutes=current_time)
            predicted_arrival_times.append(arrival_datetime)
            
            # add service time
            current_time += order.service_time_minutes
            
        # Add return to depot
        orig_i = valid_indices[current_loc_idx-1]
        orig_j = 0
        step_dist = dist_matrix[orig_i, orig_j]
        step_time = time_matrix[orig_i, orig_j]
        
        total_dist_km += step_dist
        total_time_min += step_time
        
        # Calculate total cost for route using cost engine
        # Simplified sum for adapter
        total_cost = res.best.distance() / 1000.0 
        
        vehicle = vehicles[route_idx] if route_idx < len(vehicles) else vehicles[0]
        
        route_obj = create_route_object(
            vehicle=vehicle,
            ordered_stops=ordered_stops_ids,
            predicted_arrival_times=predicted_arrival_times,
            total_distance_km=total_dist_km,
            total_predicted_time_min=total_time_min,
            total_cost=total_cost
        )
        routes.append(route_obj)
        
    return routes
