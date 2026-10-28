"""Solver-independent route simulation and evaluation.

Every solver's output is re-simulated here from the problem matrices, so capacity
and time-window correctness (SC-05/SC-06) never depends on a solver's own report.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.cost_engine.config import CostWeights
from src.cost_engine.cost_function import compute_delay_penalty, compute_fuel_cost
from src.data_processing.schemas import Route

EPS = 1e-6


@dataclass
class RouteSim:
    nodes: List[int]
    arrivals_min: List[float] = field(default_factory=list)   # service start, minutes from base_time
    slack_min: List[float] = field(default_factory=list)      # window end - service start
    depart_min: float = 0.0
    end_min: float = 0.0
    distance: float = 0.0
    travel_min: float = 0.0
    wait_min: float = 0.0
    load: float = 0.0
    violations: List[str] = field(default_factory=list)


def _rel(problem: dict, dt) -> float:
    return (dt - problem["base_time"]).total_seconds() / 60.0


def simulate_route(problem: dict, vehicle, nodes: List[int]) -> RouteSim:
    """Earliest-start forward simulation of one vehicle visiting `nodes` (1-based order nodes)."""
    D, T, orders = problem["dist_matrix"], problem["time_matrix"], problem["orders"]
    sim = RouteSim(nodes=list(nodes))
    v_start, v_end = _rel(problem, vehicle.available_from), _rel(problem, vehicle.available_until)
    if not nodes:
        sim.depart_min = sim.end_min = v_start
        return sim

    first = orders[nodes[0] - 1]
    sim.depart_min = max(v_start, _rel(problem, first.time_window_start) - T[0][nodes[0]])
    t, prev = sim.depart_min, 0
    for n in nodes:
        o = orders[n - 1]
        travel = float(T[prev][n])
        arrive = t + travel
        start = max(arrive, _rel(problem, o.time_window_start))
        tw_end = _rel(problem, o.time_window_end)
        if start > tw_end + EPS:
            sim.violations.append(f"time_window:{o.order_id} start {start:.2f} > due {tw_end:.2f}")
        sim.wait_min += start - arrive
        sim.travel_min += travel
        sim.distance += float(D[prev][n])
        sim.load += o.demand_weight
        sim.arrivals_min.append(start)
        sim.slack_min.append(tw_end - start)
        t = start + o.service_time_minutes
        prev = n
    sim.travel_min += float(T[prev][0])
    sim.distance += float(D[prev][0])
    sim.end_min = t + float(T[prev][0])
    if sim.end_min > v_end + EPS:
        sim.violations.append(f"vehicle_window:{vehicle.vehicle_id} returns {sim.end_min:.2f} > {v_end:.2f}")
    if sim.load > vehicle.capacity + EPS:
        sim.violations.append(f"capacity:{vehicle.vehicle_id} load {sim.load:.2f} > {vehicle.capacity:.2f}")
    return sim


def route_cost(problem: dict, vehicle, sim: RouteSim, weights: CostWeights) -> float:
    """w_d*distance + w_f*fuel + w_t*route duration + w_delay*priority-weighted lateness."""
    orders = problem["orders"]
    delay = sum(
        compute_delay_penalty(a, _rel(problem, orders[n - 1].time_window_end), orders[n - 1].priority.value)
        for n, a in zip(sim.nodes, sim.arrivals_min)
    )
    return (
        weights.w_distance * sim.distance
        + weights.w_fuel * compute_fuel_cost(sim.distance, vehicle.fuel_efficiency)
        + weights.w_time * (sim.end_min - sim.depart_min)
        + weights.w_delay * delay
    )


def node_index(problem: dict) -> Dict[str, int]:
    if "_order_index" not in problem:
        problem["_order_index"] = {o.order_id: i + 1 for i, o in enumerate(problem["orders"])}
    return problem["_order_index"]


def build_route_sim(problem: dict, route: Route):
    idx = node_index(problem)
    vehicle = next((v for v in problem["vehicles"] if v.vehicle_id == route.vehicle_id), None)
    if vehicle is None:
        return None, None, [f"unknown_vehicle:{route.vehicle_id}"]
    missing = [s for s in route.ordered_stops if s not in idx]
    if missing:
        return vehicle, None, [f"unknown_order:{m}" for m in missing]
    return vehicle, simulate_route(problem, vehicle, [idx[s] for s in route.ordered_stops]), []


def evaluate_solution(
    routes: List[Route],
    problem: dict,
    weights: Optional[CostWeights] = None,
    unassigned: Optional[List[dict]] = None,
) -> dict:
    """Re-simulate `routes` and report metrics plus every constraint violation found."""
    weights = weights or CostWeights(w_distance=1.0, w_time=0.0, w_fuel=0.0, w_delay=0.0)
    violations: List[str] = []
    seen: Dict[str, int] = {}
    dist = time = cost = load = cap = 0.0
    late = 0
    for r in routes:
        vehicle, sim, errs = build_route_sim(problem, r)
        violations += errs
        if sim is None:
            continue
        violations += sim.violations
        late += sum(1 for s in sim.slack_min if s < -EPS)
        for s in r.ordered_stops:
            seen[s] = seen.get(s, 0) + 1
        dist += sim.distance
        time += sim.end_min - sim.depart_min
        cost += route_cost(problem, vehicle, sim, weights)
        load += sim.load
        cap += vehicle.capacity
    violations += [f"duplicate_order:{k}" for k, c in seen.items() if c > 1]
    reported = {u["order_id"] for u in (unassigned or [])}
    all_ids = {o.order_id for o in problem["orders"]}
    violations += [f"silently_dropped:{o}" for o in sorted(all_ids - set(seen) - reported)]
    return {
        "total_distance": dist,
        "total_time_min": time,
        "total_cost": cost,
        "vehicles_used": sum(1 for r in routes if r.ordered_stops),
        "late_deliveries": late,
        "utilization_pct": 100.0 * load / cap if cap else 0.0,
        "orders_assigned": len(seen),
        "orders_unassigned": len(reported),
        "violations": violations,
        "feasible": not violations,
    }
