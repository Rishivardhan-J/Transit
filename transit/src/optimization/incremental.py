"""Warm-start re-optimization for live disruption events (PRD 6.2 / SC-12).

Pipeline: apply the event to the problem -> repair the existing routes with cheapest feasible
insertion -> hand the repaired plan to HGS as `initial_solution` for a short improvement pass.
HGS keeps the best solution seen, so the result is never worse than the repaired plan.
"""
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.cost_engine.config import CostWeights
from src.data_processing.schemas import Order, Route

from src.optimization.hgs_solver import build_hgs_model, solution_from_plan, solve_hgs
from src.optimization.infeasibility import SolveResult
from src.optimization.problem_builder import build_cvrptw_problem
from src.optimization.repair import repair_plan

EVENT_TYPES = ("new_order", "cancel_order", "vehicle_down", "traffic_change")


def apply_event(problem: dict, event: dict) -> Tuple[dict, List[str]]:
    """Return (new_problem, order_ids_to_unroute). Matrices are rebuilt only when geometry changes."""
    kind = event.get("type")
    orders, vehicles = list(problem["orders"]), list(problem["vehicles"])
    args = dict(problem["_build_args"])
    if kind == "new_order":
        order = event["order"]
        if isinstance(order, dict):
            order = Order(**order)
        if any(o.order_id == order.order_id for o in orders):
            raise ValueError(f"order {order.order_id} already exists")
        return build_cvrptw_problem(orders + [order], vehicles, **args), []
    if kind == "cancel_order":
        oid = event["order_id"]
        if all(o.order_id != oid for o in orders):
            raise ValueError(f"unknown order {oid}")
        return build_cvrptw_problem([o for o in orders if o.order_id != oid], vehicles, **args), [oid]
    if kind == "vehicle_down":
        vid = event["vehicle_id"]
        if all(v.vehicle_id != vid for v in vehicles):
            raise ValueError(f"unknown vehicle {vid}")
        remaining = [v for v in vehicles if v.vehicle_id != vid]
        if not remaining:
            raise ValueError("no vehicles left")
        return build_cvrptw_problem(orders, remaining, **args), []
    if kind == "traffic_change":
        factor = float(event.get("time_multiplier", 1.0))
        new = dict(problem)
        new["time_matrix"] = np.asarray(problem["time_matrix"], dtype=float) * factor
        return new, []
    raise ValueError(f"unknown event type {kind!r}; expected one of {EVENT_TYPES}")


def reoptimize(
    problem: dict,
    prev_routes: List[Route],
    event: dict,
    weights: CostWeights,
    max_runtime_seconds: float = 3.0,
    seed: int = 42,
) -> Tuple[SolveResult, dict]:
    """Apply `event`, repair, then warm-start HGS. Returns (result, updated_problem)."""
    t0 = time.time()
    new_problem, _ = apply_event(problem, event)
    idx = {o.order_id: i + 1 for i, o in enumerate(new_problem["orders"])}
    prev_plan = {r.vehicle_id: [idx[s] for s in r.ordered_stops if s in idx] for r in prev_routes}
    plan, unplaced = repair_plan(new_problem, prev_plan)
    repaired_s = time.time() - t0

    model, meta = build_hgs_model(new_problem, weights)
    initial = solution_from_plan(model, meta, plan)
    remaining = max(0.5, max_runtime_seconds - (time.time() - t0))
    res = solve_hgs(new_problem, weights, max_runtime_seconds=remaining, max_iterations_no_improvement=500,
                    seed=seed, initial_solution=initial, model_and_meta=(model, meta))
    res.solver = "hgs-incremental"
    res.runtime_s = time.time() - t0
    res.stats.update({"event": event.get("type"), "repair_unplaced": len(unplaced), "repair_s": round(repaired_s, 3)})
    return res, new_problem
