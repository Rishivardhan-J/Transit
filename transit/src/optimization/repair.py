"""Feasibility repair: strip violating stops, then cheapest-feasible insertion of everything unrouted."""
from typing import Dict, List, Tuple

from src.optimization.routing_metrics import simulate_route


def repair_plan(problem: dict, plan: Dict[str, List[int]]) -> Tuple[Dict[str, List[int]], List[int]]:
    """`plan` maps vehicle_id -> ordered 1-based order nodes (stale/unknown nodes already removed).
    Returns (feasible plan, nodes that could not be placed anywhere)."""
    vehicles = {v.vehicle_id: v for v in problem["vehicles"]}
    n_orders = len(problem["orders"])
    plan = {vid: [n for n in plan.get(vid, []) if 1 <= n <= n_orders] for vid in vehicles}
    D = problem["dist_matrix"]
    max_cap = max(v.capacity for v in vehicles.values())

    for vid, nodes in plan.items():          # drop the stops that break a route, last first
        while nodes and simulate_route(problem, vehicles[vid], nodes).violations:
            nodes.pop()

    routed = {n for nodes in plan.values() for n in nodes}

    def dist(nodes):
        path = [0] + nodes + [0]
        return sum(D[a][b] for a, b in zip(path, path[1:]))

    unplaced: List[int] = []
    todo = sorted((n for n in range(1, n_orders + 1) if n not in routed),
                  key=lambda n: problem["orders"][n - 1].time_window_end)
    for n in todo:
        if problem["orders"][n - 1].demand_weight > max_cap:
            unplaced.append(n)
            continue
        best, best_delta = None, float("inf")
        for vid, nodes in plan.items():
            base_d = dist(nodes)
            for pos in range(len(nodes) + 1):
                cand = nodes[:pos] + [n] + nodes[pos:]
                if simulate_route(problem, vehicles[vid], cand).violations:
                    continue
                delta = dist(cand) - base_d + (1e6 if not nodes else 0.0)  # prefer vehicles already in use
                if delta < best_delta:
                    best, best_delta = (vid, pos), delta
        if best is None:
            unplaced.append(n)
        else:
            plan[best[0]].insert(best[1], n)
    return plan, unplaced
