import pytest

from src.cost_engine.config import CostWeights
from src.optimization.hgs_solver import solve_hgs
from src.optimization.incremental import reoptimize
from src.optimization.problem_builder import SOLOMON_COORD_SCALE, build_cvrptw_problem, parse_solomon_instance
from src.optimization.routing_metrics import evaluate_solution
from src.paths import BENCHMARK_DIR

WEIGHTS = CostWeights(w_distance=1.0, w_time=0.0, w_fuel=0.0, w_delay=0.0)


@pytest.fixture(scope="module")
def baseline():
    path = BENCHMARK_DIR / "solomon" / "RC101.txt"
    if not path.exists():
        pytest.skip("RC101 not found")
    orders, vehicles = parse_solomon_instance(str(path), num_customers=100)
    prob = build_cvrptw_problem(orders, vehicles, use_euclidean=True, coord_scale=SOLOMON_COORD_SCALE)
    return orders, prob, solve_hgs(prob, WEIGHTS, 5.0, 500, vehicle_fixed_cost=1000.0)


def _events(orders, base):
    extra = orders[5].model_copy(deep=True)
    extra.order_id = "NEW1"
    return [
        {"type": "new_order", "order": extra},
        {"type": "cancel_order", "order_id": orders[10].order_id},
        {"type": "vehicle_down", "vehicle_id": base.routes[0].vehicle_id},
        {"type": "traffic_change", "time_multiplier": 1.1},
    ]


def test_each_disruption_resolves_under_5s_without_violations(baseline):
    orders, prob, base = baseline
    for event in _events(orders, base):
        res, new_prob = reoptimize(prob, base.routes, event, WEIGHTS, max_runtime_seconds=3.0)
        assert res.runtime_s < 5.0, f"{event['type']} took {res.runtime_s:.2f}s"
        m = evaluate_solution(res.routes, new_prob, WEIGHTS, res.unassigned)
        assert m["violations"] == [], (event["type"], m["violations"][:3])


def test_new_order_is_served_and_vehicle_down_removes_vehicle(baseline):
    orders, prob, base = baseline
    ev = _events(orders, base)
    res, _ = reoptimize(prob, base.routes, ev[0], WEIGHTS, 3.0)
    assert "NEW1" in {s for r in res.routes for s in r.ordered_stops}
    down = ev[2]["vehicle_id"]
    res, _ = reoptimize(prob, base.routes, ev[2], WEIGHTS, 3.0)
    assert down not in {r.vehicle_id for r in res.routes}
    assert res.unassigned == []


def test_unknown_event_rejected(baseline):
    _, prob, base = baseline
    with pytest.raises(ValueError):
        reoptimize(prob, base.routes, {"type": "meteor"}, WEIGHTS)
