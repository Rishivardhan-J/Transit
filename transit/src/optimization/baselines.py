import time
import uuid
from datetime import timedelta
from typing import List

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from src.cost_engine.config import CostWeights, FUEL_PRICE
from src.data_processing.schemas import Route
from src.optimization.infeasibility import SolveResult, explain_unassigned
from src.optimization.routing_metrics import _rel, route_cost, simulate_route
from src.optimization.solution_adapter import create_route_object

SCALE = 100
COST_SCALE = 100


def _routes_from_nodes(problem, weights, per_vehicle_nodes, run_id) -> List[Route]:
    base = problem["base_time"]
    routes = []
    for vehicle, nodes in per_vehicle_nodes:
        if not nodes:
            continue
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


def _unassigned(problem, routes) -> List[dict]:
    served = {s for r in routes for s in r.ordered_stops}
    return [
        {"order_id": o.order_id, "reason": explain_unassigned(problem, i)}
        for i, o in enumerate(problem["orders"]) if o.order_id not in served
    ]


def solve_nn(problem: dict, weights: CostWeights) -> SolveResult:
    """Nearest-neighbour construction: each vehicle repeatedly drives to the nearest order it can
    still serve within capacity, time window and its own availability window."""
    t0 = time.time()
    orders, D, T = problem["orders"], problem["dist_matrix"], problem["time_matrix"]
    unvisited = set(range(1, len(orders) + 1))
    assignments = []
    for vehicle in problem["vehicles"]:
        if not unvisited:
            break
        v_start, v_end = _rel(problem, vehicle.available_from), _rel(problem, vehicle.available_until)
        node, t, load, nodes = 0, v_start, 0.0, []
        while True:
            best, best_d = None, float("inf")
            for n in unvisited:
                o = orders[n - 1]
                if load + o.demand_weight > vehicle.capacity:
                    continue
                start = max(t + T[node][n], _rel(problem, o.time_window_start))
                if start > _rel(problem, o.time_window_end):
                    continue
                if start + o.service_time_minutes + T[n][0] > v_end:
                    continue
                if D[node][n] < best_d:
                    best, best_d = n, D[node][n]
            if best is None:
                break
            o = orders[best - 1]
            t = max(t + T[node][best], _rel(problem, o.time_window_start)) + o.service_time_minutes
            load += o.demand_weight
            nodes.append(best)
            unvisited.discard(best)
            node = best
        assignments.append((vehicle, nodes))
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    routes = _routes_from_nodes(problem, weights, assignments, run_id)
    return SolveResult(routes, _unassigned(problem, routes), run_id, "nn", time.time() - t0)


def solve_ortools(problem: dict, weights: CostWeights, max_runtime_seconds: float = 30.0,
                  vehicle_fixed_cost: float = 0.0) -> SolveResult:
    """OR-Tools routing with the same weighted objective as HGS: distance/fuel arc cost per vehicle,
    time as span cost, hard capacity + time windows, and optional nodes with a big drop penalty."""
    t0 = time.time()
    orders, vehicles, D, T = problem["orders"], problem["vehicles"], problem["dist_matrix"], problem["time_matrix"]
    nv, n = len(vehicles), len(orders) + 1
    manager = pywrapcp.RoutingIndexManager(n, nv, 0)
    routing = pywrapcp.RoutingModel(manager)

    def make_arc(vehicle):
        cpk = weights.w_distance + weights.w_fuel * FUEL_PRICE / vehicle.fuel_efficiency
        ucd = max(1, round(cpk * COST_SCALE)) if cpk > 0 else 1

        def cb(i, j):
            return int(round(D[manager.IndexToNode(i)][manager.IndexToNode(j)] * SCALE)) * ucd
        return routing.RegisterTransitCallback(cb)

    for k, v in enumerate(vehicles):
        routing.SetArcCostEvaluatorOfVehicle(make_arc(v), k)
        routing.SetFixedCostOfVehicle(int(vehicle_fixed_cost * SCALE * COST_SCALE), k)

    demand_cb = routing.RegisterUnaryTransitCallback(
        lambda i: 0 if manager.IndexToNode(i) == 0 else int(-(-orders[manager.IndexToNode(i) - 1].demand_weight // 1)))
    routing.AddDimensionWithVehicleCapacity(demand_cb, 0, [int(v.capacity) for v in vehicles], True, "Load")

    def time_cb(i, j):
        a, b = manager.IndexToNode(i), manager.IndexToNode(j)
        service = orders[a - 1].service_time_minutes if a > 0 else 0.0
        return int(-(-(float(T[a][b]) + service) * SCALE // 1))

    horizon = int(max(_rel(problem, v.available_until) for v in vehicles) * SCALE) + 1
    routing.AddDimension(routing.RegisterTransitCallback(time_cb), horizon, horizon, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for i, o in enumerate(orders):
        idx = manager.NodeToIndex(i + 1)
        early = int(-(-_rel(problem, o.time_window_start) * SCALE // 1))
        late = int(_rel(problem, o.time_window_end) * SCALE // 1)
        if late < early:
            routing.AddDisjunction([idx], 0)
            continue
        time_dim.CumulVar(idx).SetRange(early, late)
        routing.AddDisjunction([idx], 10 ** 9)
    for k, v in enumerate(vehicles):
        time_dim.CumulVar(routing.Start(k)).SetRange(
            int(-(-_rel(problem, v.available_from) * SCALE // 1)), int(_rel(problem, v.available_until) * SCALE // 1))
        time_dim.CumulVar(routing.End(k)).SetRange(
            int(-(-_rel(problem, v.available_from) * SCALE // 1)), int(_rel(problem, v.available_until) * SCALE // 1))
        ucu = round(weights.w_time * COST_SCALE)
        if ucu:
            time_dim.SetSpanCostCoefficientForVehicle(ucu, k)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(int(max_runtime_seconds * 1000))
    solution = routing.SolveWithParameters(params)

    assignments = []
    if solution:
        for k, v in enumerate(vehicles):
            idx, nodes = routing.Start(k), []
            while not routing.IsEnd(idx):
                idx = solution.Value(routing.NextVar(idx))
                node = manager.IndexToNode(idx)
                if node != 0:
                    nodes.append(node)
            assignments.append((v, nodes))
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    routes = _routes_from_nodes(problem, weights, assignments, run_id)
    return SolveResult(routes, _unassigned(problem, routes), run_id, "ortools", time.time() - t0)


def solve_with_nn(problem: dict, weights: CostWeights) -> List[Route]:
    return solve_nn(problem, weights).routes


def solve_with_ortools(problem: dict, weights: CostWeights, max_runtime_seconds: float = 30.0, **kw) -> List[Route]:
    return solve_ortools(problem, weights, max_runtime_seconds, **kw).routes
