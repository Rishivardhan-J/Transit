import pytest
from datetime import timedelta
import os
from pathlib import Path

from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
from src.optimization.baselines import solve_with_ortools, solve_with_nn
from src.cost_engine.config import CostWeights

# The extracted Solomon benchmark directory
BENCHMARK_DIR = Path("/home/rishi/Projects/Transit/transit/data/benchmark/solomon")

@pytest.fixture(scope="module")
def default_weights():
    return CostWeights.auto_normalize(1.0, 1.0, 0.0, 0.0)

@pytest.mark.parametrize("instance_name, num_customers", [
    ("C101.txt", 25),
    ("R101.txt", 25),
    ("RC101.txt", 25),
])
@pytest.mark.parametrize("solver_name", ["HGS", "OR-Tools", "NN"])
def test_feasibility_solomon(instance_name, num_customers, default_weights, solver_name):
    filepath = BENCHMARK_DIR / instance_name
    if not filepath.exists():
        pytest.skip(f"Benchmark file {filepath} not found.")

    orders, vehicles = parse_solomon_instance(str(filepath), num_customers=num_customers)
    problem = build_cvrptw_problem(orders, vehicles, use_euclidean=True)

    if solver_name == "HGS":
        routes = solve_with_hgs(
            problem=problem,
            weights=default_weights,
            max_runtime_seconds=5.0,
            max_iterations_no_improvement=200
        )
    elif solver_name == "OR-Tools":
        routes = solve_with_ortools(
            problem=problem,
            weights=default_weights,
            max_runtime_seconds=5.0
        )
    elif solver_name == "NN":
        routes = solve_with_nn(
            problem=problem,
            weights=default_weights
        )

    assert len(routes) > 0, "Solver should return at least one route"

    assigned_orders = set()

    for route in routes:
        vehicle = next((v for v in vehicles if v.vehicle_id == route.vehicle_id), None)
        assert vehicle is not None, f"Vehicle {route.vehicle_id} not found"
        
        # 1. Capacity constraints
        total_demand = 0.0
        
        # If solver doesn't predict arrival times, we simulate them to check feasibility
        # OR-Tools currently returns empty predicted_arrival_times, we should check it using our own accumulator
        
        current_time_min = 0.0
        curr_node = 0
        base_time = vehicle.available_from
        
        for i, order_id in enumerate(route.ordered_stops):
            order = next(o for o in orders if o.order_id == order_id)
            node_idx = problem["orders"].index(order) + 1
            
            total_demand += order.demand_weight
            
            travel_t = problem["time_matrix"][curr_node][node_idx]
            
            arrival_time_min = current_time_min + travel_t
            
            tw_start_min = (order.time_window_start - base_time).total_seconds() / 60
            tw_end_min = (order.time_window_end - base_time).total_seconds() / 60
            
            arrival_time_min = max(arrival_time_min, tw_start_min)
            
            assert arrival_time_min <= tw_end_min + 5, f"{solver_name} failed: Late arrival at {order_id}. Arrived {arrival_time_min}, Due {tw_end_min}"
            
            current_time_min = arrival_time_min + order.service_time_minutes
            curr_node = node_idx
            
            assigned_orders.add(order_id)
            
        assert total_demand <= vehicle.capacity, f"{solver_name} failed: Capacity exceeded on route {route.route_id}"
        
    # In a full solve, every order should be assigned unless explicitly marked infeasible.
    if solver_name in ["HGS", "OR-Tools"]:
        assert len(assigned_orders) == num_customers, f"{solver_name} failed: Not all orders were assigned!"
    else:
        # NN might leave some unassigned due to its greedy nature being unable to pack properly
        pass

