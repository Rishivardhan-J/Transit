from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.data_processing.schemas import Order


@dataclass
class SolveResult:
    """What every solver returns: routes, plus an explicit unassigned set (PRD 6.2 policy:
    orders that cannot be served feasibly are excluded and surfaced with a reason, never dropped silently)."""
    routes: List[Any]
    unassigned: List[Dict[str, Any]] = field(default_factory=list)
    run_id: str = ""
    solver: str = ""
    runtime_s: float = 0.0
    stats: Dict[str, Any] = field(default_factory=dict)


def explain_unassigned(problem: dict, order_idx: int) -> str:
    """Best-effort reason an order (0-based index into problem['orders']) is unservable."""
    o = problem["orders"][order_idx]
    node = order_idx + 1
    base = problem["base_time"]
    max_cap = max(v.capacity for v in problem["vehicles"])
    if o.demand_weight > max_cap:
        return f"demand {o.demand_weight:g} exceeds largest vehicle capacity {max_cap:g}"
    tw_end = (o.time_window_end - base).total_seconds() / 60.0
    tw_start = (o.time_window_start - base).total_seconds() / 60.0
    earliest = min((v.available_from - base).total_seconds() / 60.0 for v in problem["vehicles"])
    reach = earliest + problem["time_matrix"][0][node]
    if reach > tw_end:
        return "time window unreachable: fastest arrival from the depot is after the window closes"
    back = max(tw_start, reach) + o.service_time_minutes + problem["time_matrix"][node][0]
    latest_return = max((v.available_until - base).total_seconds() / 60.0 for v in problem["vehicles"])
    if back > latest_return:
        return "no vehicle can return to the depot within its availability window"
    return "fleet capacity or time exhausted (not enough vehicle-time to serve this order)"
