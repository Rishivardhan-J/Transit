"""Property tests (SC-06): random small instances never produce a silent violation."""
from datetime import datetime, timedelta

from hypothesis import HealthCheck, given, settings, strategies as st

from src.cost_engine.config import CostWeights
from src.data_processing.schemas import Order, Priority, Vehicle, VehicleType
from src.optimization.baselines import solve_nn, solve_ortools
from src.optimization.hgs_solver import solve_hgs
from src.optimization.problem_builder import build_cvrptw_problem
from src.optimization.routing_metrics import evaluate_solution

BASE = datetime(2025, 1, 6, 8, 0)
WEIGHTS = CostWeights(w_distance=0.4, w_time=0.3, w_fuel=0.1, w_delay=0.2)


@st.composite
def instances(draw):
    n = draw(st.integers(3, 10))
    orders = []
    for i in range(n):
        start = draw(st.integers(0, 240))
        width = draw(st.integers(15, 300))
        orders.append(Order(
            order_id=f"o{i}",
            pickup_lat=37.77, pickup_lng=-122.41,
            delivery_lat=37.77 + draw(st.floats(-0.08, 0.08)), delivery_lng=-122.41 + draw(st.floats(-0.08, 0.08)),
            demand_weight=draw(st.floats(1, 40)),
            priority=draw(st.sampled_from(list(Priority))),
            time_window_start=BASE + timedelta(minutes=start),
            time_window_end=BASE + timedelta(minutes=start + width),
            service_time_minutes=draw(st.floats(0, 15)),
            created_at=BASE - timedelta(hours=1),
        ))
    vehicles = [
        Vehicle(vehicle_id=f"v{k}", capacity=draw(st.sampled_from([60.0, 100.0])), vehicle_type=VehicleType.VAN,
                fuel_efficiency=draw(st.sampled_from([8.0, 12.0])), available_from=BASE,
                available_until=BASE + timedelta(hours=draw(st.integers(5, 10))),
                current_lat=37.77, current_lng=-122.41)
        for k in range(draw(st.integers(1, 3)))
    ]
    return build_cvrptw_problem(orders, vehicles)


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(instances())
def test_hgs_never_violates_or_drops_silently(problem):
    res = solve_hgs(problem, WEIGHTS, 1.0, 100)
    m = evaluate_solution(res.routes, problem, WEIGHTS, res.unassigned)
    assert m["violations"] == []


@settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(instances())
def test_baselines_never_violate_or_drop_silently(problem):
    for res in (solve_nn(problem, WEIGHTS), solve_ortools(problem, WEIGHTS, 1.0)):
        m = evaluate_solution(res.routes, problem, WEIGHTS, res.unassigned)
        assert m["violations"] == []
