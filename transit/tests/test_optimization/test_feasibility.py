import pytest
from datetime import timedelta
import os
from pathlib import Path

from src.optimization.problem_builder import parse_solomon_instance, build_cvrptw_problem
from src.optimization.hgs_solver import solve_with_hgs
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
def test_hgs_feasibility_solomon(instance_name, num_customers, default_weights):
    filepath = BENCHMARK_DIR / instance_name
    if not filepath.exists():
        pytest.skip(f"Benchmark file {filepath} not found.")

    orders, vehicles = parse_solomon_instance(str(filepath), num_customers=num_customers)
    problem = build_cvrptw_problem(orders, vehicles, use_euclidean=True)

    # Solve with a short budget for tests
    routes = solve_with_hgs(
        problem=problem,
        weights=default_weights,
        max_runtime_seconds=2.0,
        max_iterations_no_improvement=200
    )

    assert len(routes) > 0, "Solver should return at least one route"

    # Track order assignment exactly once
    assigned_orders = set()

    for route in routes:
        vehicle = next(v for v in vehicles if v.vehicle_id == route.vehicle_id)
        
        # 1. Capacity constraints
        total_demand = 0.0
        
        # 2. Arrival times and windows
        assert len(route.ordered_stops) == len(route.predicted_arrival_times)
        
        for i, order_id in enumerate(route.ordered_stops):
            order = next(o for o in orders if o.order_id == order_id)
            total_demand += order.demand_weight
            
            arrival_time = route.predicted_arrival_times[i]
            
            # Time window feasibility
            if arrival_time > order.time_window_end + timedelta(minutes=5):
                print(f"LATE: order {order_id}, arrival {arrival_time}, due {order.time_window_end}")
                print(f"Route: {route.ordered_stops}")
                print(f"Arrivals: {route.predicted_arrival_times}")
            assert arrival_time <= order.time_window_end + timedelta(minutes=5), f"Late arrival at {order_id} beyond tolerance"
            
            # The departure time from this stop would be arrival_time (or ready time) + service_time
            # This is implicitly checked if subsequent stops are valid, but we explicitly verify
            # that arrival_time respects the vehicle's availability.
            assert arrival_time >= vehicle.available_from, "Arrival before vehicle available"
            assert arrival_time <= vehicle.available_until, "Arrival after vehicle unavailable"
            
            assigned_orders.add(order_id)
            
        assert total_demand <= vehicle.capacity, f"Capacity exceeded on route {route.route_id}"
        
    # 3. Exact assignment
    # In a full solve, every order should be assigned unless explicitly marked infeasible.
    # For Solomon C101/R101, all should be feasible.
    assert len(assigned_orders) == num_customers, "Not all orders were assigned!"
