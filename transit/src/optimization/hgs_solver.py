import math
import time
import uuid
from collections import OrderedDict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from pyvrp import Model, Route as PyRoute, Solution
from pyvrp.stop import MaxRuntime, MultipleCriteria, NoImprovement

from src.cost_engine.config import (
    CostWeights, FUEL_PRICE, PRIORITY_MULTIPLIERS, PRIORITY_WINDOW_BUFFER,
)
from src.data_processing.schemas import Route
from src.optimization.infeasibility import SolveResult, explain_unassigned
from src.optimization.repair import repair_plan
from src.optimization.routing_metrics import _rel, route_cost, simulate_route
from src.optimization.solution_adapter import create_route_object

SCALE = 100            # distances (0.01 unit) and durations (0.01 min) become integers
COST_SCALE = 100       # integer cost per scaled unit = weight * COST_SCALE
PRIZE_BASE = 10 ** 9   # large enough that serving an order always beats skipping it


def _ceil(x: float) -> int:
    return int(math.ceil(x * SCALE - 1e-9))


def _floor(x: float) -> int:
    return int(math.floor(x * SCALE + 1e-9))


def _fleet_groups(vehicles) -> "OrderedDict[tuple, list]":
    """One PyVRP vehicle type per (capacity, fuel efficiency, availability window)."""
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for v in vehicles:
        groups.setdefault((v.capacity, v.fuel_efficiency, v.available_from, v.available_until), []).append(v)
    return groups


def _window(problem: dict, order, weights: CostWeights):
    """Order time window in minutes from base_time, tightened for urgent/high priority by w_delay."""
    start, end = _rel(problem, order.time_window_start), _rel(problem, order.time_window_end)
    frac = PRIORITY_WINDOW_BUFFER.get(order.priority.value, 0.0) * weights.w_delay
    return start, max(start, end - frac * (end - start))


def build_hgs_model(problem: Dict[str, Any], weights: CostWeights, vehicle_fixed_cost: float = 0.0):
    """Builds the PyVRP model. Returns (model, meta) where meta maps solver indices back to our entities.

    Objective mapping (all integers, cost unit = 1/(SCALE*COST_SCALE)):
      * edge distance  = true distance, edge duration = predicted minutes (ML/speed/Euclidean matrix)
      * unit_distance_cost = w_distance + w_fuel * FUEL_PRICE / fuel_efficiency   (per vehicle type)
      * unit_duration_cost = w_time                                               (per vehicle type)
      * w_delay: urgent/high orders get their window end pulled in by PRIORITY_WINDOW_BUFFER * w_delay
        of the window width, and every order's prize scales with its priority multiplier.
    Clients are optional with a huge prize, so the solver always returns a feasible solution and
    orders that cannot be served come back as an explicit unassigned set.
    """
    orders, vehicles = problem["orders"], problem["vehicles"]
    D, T = problem["dist_matrix"], problem["time_matrix"]
    max_cap = max(v.capacity for v in vehicles)
    horizon = max(_rel(problem, v.available_until) for v in vehicles)

    m = Model()
    depot_loc = m.add_location(x=problem["coords"][0][0], y=problem["coords"][0][1])
    m.add_depot(location=depot_loc, tw_early=0, tw_late=_floor(horizon))

    groups = _fleet_groups(vehicles)
    types = []
    for (cap, eff, avail_from, avail_until), members in groups.items():
        cpk = weights.w_distance + weights.w_fuel * FUEL_PRICE / eff
        ucd = max(1, round(cpk * COST_SCALE)) if cpk > 0 else 1
        ucu = round(weights.w_time * COST_SCALE)
        m.add_vehicle_type(
            len(members),
            capacity=int(cap),
            start_depot=m.depots[0],
            end_depot=m.depots[0],
            fixed_cost=int(vehicle_fixed_cost * SCALE * COST_SCALE),
            tw_early=_ceil(_rel(problem, avail_from)),
            tw_late=_floor(_rel(problem, avail_until)),
            unit_distance_cost=ucd,
            unit_duration_cost=ucu,
        )
        types.append(members)

    nodes = [0]          # problem node index per PyVRP location
    client_nodes = []    # problem node index per client
    locs = [depot_loc]
    unassigned = []
    for i, o in enumerate(orders):
        if o.demand_weight > max_cap:
            unassigned.append({"order_id": o.order_id, "reason": explain_unassigned(problem, i)})
            continue
        early, late = _window(problem, o, weights)
        loc = m.add_location(x=problem["coords"][i + 1][0], y=problem["coords"][i + 1][1])
        m.add_client(
            location=loc,
            delivery=int(math.ceil(o.demand_weight)),
            service_duration=_ceil(o.service_time_minutes),
            tw_early=_ceil(early),
            tw_late=_floor(late),
            prize=int(PRIZE_BASE * PRIORITY_MULTIPLIERS.get(o.priority.value, 1.0)),
            required=False,
        )
        locs.append(loc)
        nodes.append(i + 1)
        client_nodes.append(i + 1)

    for a, na in zip(locs, nodes):
        for b, nb in zip(locs, nodes):
            if a is not b:
                m.add_edge(a, b, distance=int(round(D[na][nb] * SCALE)), duration=_ceil(float(T[na][nb])))

    meta = {"types": types, "client_nodes": client_nodes, "excluded": unassigned}
    return m, meta


def plan_from_solution(meta: dict, solution) -> Dict[str, List[int]]:
    """PyVRP solution -> {vehicle_id: [order nodes]}."""
    pools = [list(members) for members in meta["types"]]
    plan = {}
    for pr in solution.routes():
        nodes = [meta["client_nodes"][a.idx] for a in pr if a.is_client()]
        if nodes:
            plan[pools[pr.vehicle_type()].pop(0).vehicle_id] = nodes
    return plan


def solution_from_plan(model, meta: dict, plan: Dict[str, List[int]]) -> Solution:
    """{vehicle_id: [order nodes]} -> PyVRP Solution for warm starts."""
    data = model.data()
    client_of = {node: k for k, node in enumerate(meta["client_nodes"])}
    type_of = {v.vehicle_id: t for t, members in enumerate(meta["types"]) for v in members}
    routes = [
        PyRoute(data, [client_of[n] for n in nodes if n in client_of], type_of[vid])
        for vid, nodes in plan.items() if any(n in client_of for n in nodes)
    ]
    return Solution(data, routes)


def result_to_routes(problem: dict, weights: CostWeights, meta: dict, solution, run_id: str, prefix: str = "rt") -> List[Route]:
    """Convert a PyVRP solution into Route objects with float-simulated schedules and per-route cost."""
    pools = [list(members) for members in meta["types"]]
    base = problem["base_time"]
    routes = []
    for pr in solution.routes():
        nodes = [meta["client_nodes"][a.idx] for a in pr if a.is_client()]
        if not nodes:
            continue
        vehicle = pools[pr.vehicle_type()].pop(0)
        sim = simulate_route(problem, vehicle, nodes)
        routes.append(create_route_object(
            vehicle=vehicle,
            ordered_stops=[problem["orders"][n - 1].order_id for n in nodes],
            predicted_arrival_times=[base + timedelta(minutes=a) for a in sim.arrivals_min],
            total_distance_km=sim.distance,
            total_predicted_time_min=sim.end_min - sim.depart_min,
            total_cost=route_cost(problem, vehicle, sim, weights),
            run_id=run_id,
            stop_slack_min=sim.slack_min,
        ))
    return routes


def unassigned_report(problem: dict, meta: dict, routes: List[Route]) -> List[dict]:
    served = {s for r in routes for s in r.ordered_stops}
    out = list(meta["excluded"])
    for n in meta["client_nodes"]:
        o = problem["orders"][n - 1]
        if o.order_id not in served:
            out.append({"order_id": o.order_id, "reason": explain_unassigned(problem, n - 1)})
    return out


def solve_hgs(
    problem: Dict[str, Any],
    weights: CostWeights,
    max_runtime_seconds: float = 30.0,
    max_iterations_no_improvement: int = 2000,
    seed: int = 42,
    vehicle_fixed_cost: float = 0.0,
    initial_solution: Optional[Solution] = None,
    model_and_meta=None,
) -> SolveResult:
    """Solve with PyVRP's Hybrid Genetic Search. Always returns a feasible SolveResult."""
    t0 = time.time()
    m, meta = model_and_meta or build_hgs_model(problem, weights, vehicle_fixed_cost)
    res = m.solve(
        stop=MultipleCriteria([MaxRuntime(max_runtime_seconds), NoImprovement(max_iterations_no_improvement)]),
        seed=seed,
        display=False,
        initial_solution=initial_solution,
    )
    best = res.best
    repaired = False
    if not best.is_feasible():
        # Optional clients with large prizes can leave PyVRP with an infeasible best after a short run.
        # Strip violating stops, re-insert what fits, and polish from that feasible plan.
        plan, _ = repair_plan(problem, plan_from_solution(meta, best))
        warm = solution_from_plan(m, meta, plan)
        left = max(0.5, max_runtime_seconds - (time.time() - t0))
        res = m.solve(stop=MultipleCriteria([MaxRuntime(left), NoImprovement(max_iterations_no_improvement)]),
                      seed=seed, display=False, initial_solution=warm)
        best = res.best if res.best.is_feasible() else warm
        repaired = True
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    routes = result_to_routes(problem, weights, meta, best, run_id)
    return SolveResult(
        routes=routes,
        unassigned=unassigned_report(problem, meta, routes),
        run_id=run_id,
        solver="hgs",
        runtime_s=time.time() - t0,
        stats={"iterations": res.num_iterations, "pyvrp_feasible": bool(best.is_feasible()), "repaired": repaired},
    )


def solve_with_hgs(problem: Dict[str, Any], weights: CostWeights, max_runtime_seconds: float = 30.0,
                   max_iterations_no_improvement: int = 2000, seed: int = 42, **kw) -> List[Route]:
    """Backwards-compatible wrapper returning only the routes."""
    return solve_hgs(problem, weights, max_runtime_seconds, max_iterations_no_improvement, seed, **kw).routes
