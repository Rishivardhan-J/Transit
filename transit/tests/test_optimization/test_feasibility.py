"""SC-05/SC-06/SC-07: every solver's routes are re-simulated by an independent evaluator."""
import pytest

from src.cost_engine.config import CostWeights
from src.optimization.baselines import solve_nn, solve_ortools
from src.optimization.hgs_solver import solve_hgs
from src.optimization.problem_builder import SOLOMON_COORD_SCALE, build_cvrptw_problem, parse_solomon_instance
from src.optimization.routing_metrics import evaluate_solution
from src.paths import BENCHMARK_DIR

SOLOMON = BENCHMARK_DIR / "solomon"
WEIGHTS = CostWeights(w_distance=1.0, w_time=0.0, w_fuel=0.0, w_delay=0.0)


def load(inst, n):
    path = SOLOMON / f"{inst}.txt"
    if not path.exists():
        pytest.skip(f"{path} not found")
    orders, vehicles = parse_solomon_instance(str(path), num_customers=n)
    return build_cvrptw_problem(orders, vehicles, use_euclidean=True, coord_scale=SOLOMON_COORD_SCALE)


def run(solver, problem):
    if solver == "HGS":
        return solve_hgs(problem, WEIGHTS, 5.0, 300)
    if solver == "OR-Tools":
        return solve_ortools(problem, WEIGHTS, 5.0)
    return solve_nn(problem, WEIGHTS)


@pytest.mark.parametrize("inst", ["C101", "R101", "RC101"])
@pytest.mark.parametrize("solver", ["HGS", "OR-Tools", "NN"])
def test_no_constraint_violations(inst, solver):
    problem = load(inst, 25)
    res = run(solver, problem)
    m = evaluate_solution(res.routes, problem, WEIGHTS, res.unassigned)
    assert res.routes, "solver should return at least one route"
    assert m["violations"] == [], f"{solver} violated constraints: {m['violations'][:3]}"
    assert m["orders_assigned"] + m["orders_unassigned"] == 25


@pytest.mark.parametrize("inst", ["C101", "R101", "RC101"])
def test_hgs_assigns_all_feasible_orders(inst):
    problem = load(inst, 25)
    res = run("HGS", problem)
    assert res.unassigned == []


def test_unassigned_orders_are_reported_with_reason():
    problem = load("C101", 10)
    problem["orders"][0].demand_weight = 10_000.0  # larger than any vehicle
    res = run("HGS", problem)
    reported = {u["order_id"]: u["reason"] for u in res.unassigned}
    assert problem["orders"][0].order_id in reported
    assert "capacity" in reported[problem["orders"][0].order_id]
    assert evaluate_solution(res.routes, problem, WEIGHTS, res.unassigned)["violations"] == []


def test_evaluator_catches_violations():
    """The checker itself must flag a capacity breach and a silently dropped order."""
    problem = load("C101", 10)
    res = run("HGS", problem)
    bad = res.routes[0].model_copy(deep=True)
    dropped = bad.ordered_stops.pop()
    bad.predicted_arrival_times.pop()
    problem["vehicles"][0].capacity = 1.0
    m = evaluate_solution([bad], problem, WEIGHTS, [])
    assert f"silently_dropped:{dropped}" in m["violations"]
    assert any(v.startswith("capacity") for v in m["violations"])


@pytest.mark.slow
def test_hgs_c101_within_one_percent_of_best_known():
    problem = load("C101", 100)
    res = solve_hgs(problem, WEIGHTS, 20.0, 3000, vehicle_fixed_cost=1000.0)
    m = evaluate_solution(res.routes, problem, WEIGHTS, res.unassigned)
    assert m["violations"] == []
    assert m["vehicles_used"] == 10
    assert m["total_distance"] <= 828.94 * 1.01


@pytest.mark.slow
def test_hgs_beats_both_baselines_on_r101():
    problem = load("R101", 100)
    h = solve_hgs(problem, WEIGHTS, 15.0, 3000, vehicle_fixed_cost=1000.0)
    o = solve_ortools(problem, WEIGHTS, 15.0, vehicle_fixed_cost=1000.0)
    n = solve_nn(problem, WEIGHTS)
    mh, mo, mn = (evaluate_solution(r.routes, problem, WEIGHTS, r.unassigned) for r in (h, o, n))
    assert not mh["violations"] and not mo["violations"] and not mn["violations"]
    assert (mh["orders_unassigned"], mh["vehicles_used"], mh["total_distance"]) <= \
           (mo["orders_unassigned"], mo["vehicles_used"], mo["total_distance"])
    assert (mh["orders_unassigned"], mh["vehicles_used"], mh["total_distance"]) < \
           (mn["orders_unassigned"], mn["vehicles_used"], mn["total_distance"])
