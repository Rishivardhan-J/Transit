"""Optimization service: DB <-> solver glue shared by the Celery tasks and the synchronous what-if endpoint.

Everything here is plain functions on a SQLAlchemy session, so it runs identically in a worker,
in an API request, and in tests.
"""
import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models_db.converters import from_db_order, from_db_route, from_db_vehicle, to_db_route
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.order import DBOrder
from backend.models_db.prediction import DBPrediction
from backend.models_db.replay import DBReplayEvent
from backend.models_db.route import DBRoute
from backend.models_db.vehicle import DBVehicle
from src.cost_engine.config import PRESETS, CostWeights
from src.cost_engine.travel_time import MLTravelTime, SpeedProfileTime
from src.data_processing.schemas import Order, OrderStatus, Route, Vehicle
from src.optimization.baselines import solve_nn, solve_ortools
from src.optimization.hgs_solver import solve_hgs
from src.optimization.incremental import reoptimize
from src.optimization.infeasibility import SolveResult
from src.optimization.problem_builder import build_cvrptw_problem
from src.optimization.routing_metrics import _rel, evaluate_solution, node_index, simulate_route

logger = logging.getLogger(__name__)
Progress = Callable[[str, int], None]
SOLVERS = ("hgs", "ortools", "nn")
ACTIVE_STATUSES = (OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.LATE)


# ---------------------------------------------------------------------------- config helpers
def weights_from_config(cfg: Optional[dict]) -> CostWeights:
    """Accepts {"preset": name} or any of w_distance/w_time/w_fuel/w_delay (or distance/time/fuel/delay); auto-normalizes."""
    cfg = cfg or {}
    if cfg.get("preset") in PRESETS:
        return PRESETS[cfg["preset"]]
    g = lambda k: float(cfg.get(f"w_{k}", cfg.get(k, 0.0)) or 0.0)
    if sum(g(k) for k in ("distance", "time", "fuel", "delay")) == 0:
        return PRESETS["balanced"]
    return CostWeights.auto_normalize(g("distance"), g("time"), g("fuel"), g("delay"))


def make_time_provider(risk_lambda: float):
    """ML leg model when a bundle exists, otherwise the speed-profile fallback (recorded on the run)."""
    try:
        provider = MLTravelTime(settings.STATION_CODE, risk_lambda)
        return provider, provider.bundle.version
    except FileNotFoundError:
        logger.warning("No leg model bundle found; falling back to the speed-profile travel times.")
        return SpeedProfileTime(), "speed-profile"


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------- loading
def load_entities(db: Session, order_ids: Optional[List[str]], vehicle_ids: Optional[List[str]]) -> Tuple[List[Order], List[Vehicle]]:
    oq = db.query(DBOrder)
    oq = oq.filter(DBOrder.order_id.in_(order_ids)) if order_ids else oq.filter(DBOrder.status.in_(ACTIVE_STATUSES))
    vq = db.query(DBVehicle).filter(DBVehicle.is_active.is_(True))
    if vehicle_ids:
        vq = vq.filter(DBVehicle.vehicle_id.in_(vehicle_ids))
    orders = [from_db_order(o) for o in oq.order_by(DBOrder.order_id).all()]
    vehicles = [from_db_vehicle(v) for v in vq.order_by(DBVehicle.vehicle_id).all()]
    orders = [o.model_copy(update={k: _utc(getattr(o, k)) for k in ("time_window_start", "time_window_end", "created_at")}) for o in orders]
    vehicles = [v.model_copy(update={k: _utc(getattr(v, k)) for k in ("available_from", "available_until")}) for v in vehicles]
    if not orders:
        raise ValueError("No orders to optimize (none pending, assigned or late).")
    if not vehicles:
        raise ValueError("No active vehicles available.")
    return orders, vehicles


def build_problem(orders: List[Order], vehicles: List[Vehicle], risk_lambda: float):
    provider, version = make_time_provider(risk_lambda)
    # Depot = first vehicle's start position; fall back to the centroid of deliveries.
    if vehicles[0].current_lat is None or vehicles[0].current_lng is None:
        lat = float(np.mean([o.delivery_lat for o in orders])); lng = float(np.mean([o.delivery_lng for o in orders]))
        vehicles = [v.model_copy(update={"current_lat": lat, "current_lng": lng}) for v in vehicles]
    problem = build_cvrptw_problem(orders, vehicles, time_provider=provider)
    problem["time_model"] = version
    problem["risk_lambda"] = risk_lambda
    return problem


# ---------------------------------------------------------------------------- uncertainty per stop
def _leg_quantiles(problem: dict) -> Dict[str, np.ndarray]:
    """p10/p50/p90 leg-time matrices in minutes. Speed-profile fallback uses a fixed -20%/+30% band."""
    provider = problem["_build_args"]["time_provider"]
    if isinstance(provider, MLTravelTime):
        return provider.quantile_matrices(problem["coords"], _hour(problem))
    base = np.asarray(problem["time_matrix"], dtype=float)
    return {"p10": base * 0.8, "p50": base, "p90": base * 1.3}


def _hour(problem: dict) -> float:
    b = problem["base_time"]
    return b.hour + b.minute / 60.0


def stop_predictions(problem: dict, routes: List[Route], with_shap: bool = True) -> Dict[str, dict]:
    """Per-stop arrival distribution for a plan (minutes from base_time), keyed by order_id.

    p50 arrival replays the route on median leg times (the plan itself may use risk-adjusted times).
    Leg errors are treated as independent, so the spread at stop k is sqrt(sum of squared leg half-widths)
    - an approximation, but monotone in route length, which is what the late-risk flag needs.
    """
    q = _leg_quantiles(problem)
    median_problem = {**problem, "time_matrix": q["p50"]}
    idx = node_index(problem)
    vehicles = {v.vehicle_id: v for v in problem["vehicles"]}
    out: Dict[str, dict] = {}
    shap_rows = []
    for r in routes:
        nodes = [idx[s] for s in r.ordered_stops]
        sim = simulate_route(median_problem, vehicles[r.vehicle_id], nodes)
        lo2 = hi2 = 0.0
        prev = 0
        for k, n in enumerate(nodes):
            o = problem["orders"][n - 1]
            lo, mid, hi = q["p10"][prev][n], q["p50"][prev][n], q["p90"][prev][n]
            lo2 += (mid - lo) ** 2
            hi2 += (hi - mid) ** 2
            start = _rel(problem, o.time_window_start)
            end = _rel(problem, o.time_window_end)
            a50 = sim.arrivals_min[k]
            a10, a90 = max(a50 - lo2 ** 0.5, start), a50 + hi2 ** 0.5
            out[o.order_id] = {
                "route_id": r.route_id, "stop_index": k, "n_stops": len(nodes),
                "p10": a10, "p50": a50, "p90": a90, "window_start": start, "window_end": end,
                "late_risk": bool(a90 > end), "likely_late": bool(a50 > end),
                "leg": {"p10": lo, "p50": mid, "p90": hi}, "shap": [],
            }
            shap_rows.append((o.order_id, prev, n, k, len(nodes)))
            prev = n
    if with_shap and shap_rows and isinstance(problem["_build_args"]["time_provider"], MLTravelTime):
        try:
            provider = problem["_build_args"]["time_provider"]
            from src.models.serving import explain
            ii = [r[1] for r in shap_rows]; jj = [r[2] for r in shap_rows]
            raw = provider.raw_frame(problem["coords"], ii, jj, _hour(problem),
                                     stop_idx=[r[3] for r in shap_rows], n_stops=[r[4] for r in shap_rows])
            for (oid, *_), ex in zip(shap_rows, explain(provider.bundle, raw, top_k=5)):
                out[oid]["shap"] = ex
        except Exception as e:  # explanations are best-effort; the plan itself must not fail on them
            logger.warning("SHAP explanation skipped: %s", e)
    return out


# ---------------------------------------------------------------------------- metrics
def plan_metrics(problem: dict, result: SolveResult, weights: CostWeights, preds: Dict[str, dict]) -> dict:
    m = evaluate_solution(result.routes, problem, weights, result.unassigned)
    m["predicted_late"] = sum(1 for p in preds.values() if p["late_risk"])
    m["predicted_late_ids"] = [oid for oid, p in preds.items() if p["late_risk"]]
    m["runtime_s"] = round(result.runtime_s, 3)
    m["base_time"] = problem["base_time"].isoformat()
    m["cost_per_order"] = m["total_cost"] / m["orders_assigned"] if m["orders_assigned"] else None
    return m


def solve(problem: dict, solver: str, weights: CostWeights, max_runtime_s: float, seed: int = 42) -> SolveResult:
    if solver == "hgs":
        return solve_hgs(problem, weights, max_runtime_s, 500, seed=seed)
    if solver == "ortools":
        return solve_ortools(problem, weights, max_runtime_s)
    if solver == "nn":
        return solve_nn(problem, weights)
    raise ValueError(f"unknown solver {solver!r}; expected one of {SOLVERS}")


# ---------------------------------------------------------------------------- serialization
def serialize_plan(problem: dict, result: SolveResult, preds: Dict[str, dict]) -> dict:
    """JSON plan for the map: routes with per-stop coordinates, prediction interval and late-risk flag."""
    base = problem["base_time"]
    idx = node_index(problem)
    stops_by_route = []
    for r in result.routes:
        stops = []
        for k, oid in enumerate(r.ordered_stops):
            o = problem["orders"][idx[oid] - 1]
            p = preds.get(oid, {})
            stops.append({
                "order_id": oid, "lat": o.delivery_lat, "lng": o.delivery_lng, "priority": o.priority.value,
                "planned_arrival": r.predicted_arrival_times[k].isoformat(),
                "p10": (base + timedelta(minutes=p["p10"])).isoformat() if p else None,
                "p50": (base + timedelta(minutes=p["p50"])).isoformat() if p else None,
                "p90": (base + timedelta(minutes=p["p90"])).isoformat() if p else None,
                "window_end": o.time_window_end.isoformat(), "window_start": o.time_window_start.isoformat(),
                "slack_min": r.stop_slack_min[k] if k < len(r.stop_slack_min) else None,
                "status": "late" if p.get("likely_late") else "at_risk" if p.get("late_risk") else "on_time",
            })
        stops_by_route.append({
            "route_id": r.route_id, "vehicle_id": r.vehicle_id, "total_distance_km": r.total_distance_km,
            "total_time_min": r.total_predicted_time_min, "total_cost": r.total_cost, "stops": stops,
        })
    return {
        "run_id": result.run_id, "solver": result.solver, "time_model": problem.get("time_model"),
        "depot": {"lat": problem["depot_lat"], "lng": problem["depot_lng"]},
        "routes": stops_by_route, "unassigned": result.unassigned,
    }


# ---------------------------------------------------------------------------- persistence
def persist_run(db: Session, problem: dict, result: SolveResult, weights: CostWeights, weight_cfg: dict, preds: Dict[str, dict],
                metrics: dict, baseline: Optional[dict], parent_run_id: Optional[str] = None, event: Optional[dict] = None) -> DBOptimizerRun:
    run = db.get(DBOptimizerRun, result.run_id) or DBOptimizerRun(id=result.run_id, solver_type=result.solver, weight_config=weight_cfg)
    run.solver_type, run.weight_config, run.status = result.solver, {**weight_cfg, "_risk_lambda": problem.get("risk_lambda", 0.0)}, "completed"
    run.parent_run_id, run.event = parent_run_id, event
    run.metrics, run.baseline_metrics, run.unassigned = _jsonable(metrics), _jsonable(baseline), result.unassigned
    run.runtime_s, run.time_model = result.runtime_s, problem.get("time_model")
    db.add(run)
    db.flush()  # routes/predictions reference the run id
    version = problem.get("time_model") or "speed-profile"
    served = set()
    for r in result.routes:
        db.add(to_db_route(r))
        served.update(r.ordered_stops)
    db.flush()
    for oid, p in preds.items():
        db.add(DBPrediction(
            order_id=oid, predicted_time_p10=p["p10"], predicted_time_p50=p["p50"], predicted_time_p90=p["p90"],
            model_version=version, shap_top_features=_jsonable(p["shap"]), optimizer_run_id=result.run_id,
            route_id=p["route_id"], stop_index=p["stop_index"],
            meta=_jsonable({k: p[k] for k in ("n_stops", "window_start", "window_end", "late_risk", "likely_late", "leg")}),
        ))
    for o in db.query(DBOrder).filter(DBOrder.order_id.in_(list(served))).all():
        if o.status in (OrderStatus.PENDING, OrderStatus.LATE):
            o.status = OrderStatus.ASSIGNED
    db.commit()
    return run


def _jsonable(x):
    import json
    return json.loads(json.dumps(x, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))) if x is not None else None


def latest_run(db: Session) -> Optional[DBOptimizerRun]:
    return db.query(DBOptimizerRun).filter(DBOptimizerRun.status == "completed").order_by(DBOptimizerRun.created_at.desc()).first()


def stored_routes(db: Session, run_id: str) -> List[Route]:
    return [from_db_route(r) for r in db.query(DBRoute).filter(DBRoute.optimizer_run_id == run_id).all()]


# ---------------------------------------------------------------------------- entry points
def run_optimization(db: Session, order_ids: Optional[List[str]], vehicle_ids: Optional[List[str]], solver: str,
                     weight_cfg: dict, risk_lambda: float = 0.25, max_runtime_s: float = 20.0, persist: bool = True,
                     run_id: Optional[str] = None, progress: Optional[Progress] = None) -> dict:
    progress = progress or (lambda stage, pct: None)
    weights = weights_from_config(weight_cfg)
    progress("loading orders and vehicles", 10)
    orders, vehicles = load_entities(db, order_ids, vehicle_ids)
    progress("building the travel-time matrix", 30)
    problem = build_problem(orders, vehicles, risk_lambda)
    progress(f"solving with {solver}", 50)
    result = solve(problem, solver, weights, max_runtime_s)
    if run_id:
        result.run_id = run_id
        for r in result.routes:
            r.optimizer_run_id = run_id
    progress("scoring arrival-time uncertainty", 80)
    preds = stop_predictions(problem, result.routes)
    metrics = plan_metrics(problem, result, weights, preds)
    baseline = None
    if solver != "nn":  # nearest-neighbour shadow run on the identical problem: the live "vs baseline" number
        nn = solve_nn(problem, weights)
        baseline = evaluate_solution(nn.routes, problem, weights, nn.unassigned)
        baseline["cost_per_order"] = baseline["total_cost"] / baseline["orders_assigned"] if baseline["orders_assigned"] else None
    if metrics["violations"]:
        logger.error("Solver %s produced violations: %s", solver, metrics["violations"][:5])
    if persist:
        progress("saving the plan", 90)
        persist_run(db, problem, result, weights, weight_cfg, preds, metrics, baseline)
    return {"problem": problem, "result": result, "preds": preds, "metrics": metrics, "baseline": baseline, "weights": weights}


def run_disruption(db: Session, parent_run_id: str, event: dict, max_runtime_s: float = 3.0,
                   run_id: Optional[str] = None, progress: Optional[Progress] = None) -> dict:
    progress = progress or (lambda stage, pct: None)
    parent = db.get(DBOptimizerRun, parent_run_id)
    if parent is None:
        raise ValueError(f"unknown optimizer run {parent_run_id}")
    prev_routes = stored_routes(db, parent_run_id)
    parent_ids = [s for r in prev_routes for s in r.ordered_stops] + [u["order_id"] for u in (parent.unassigned or [])]
    cfg = dict(parent.weight_config or {})
    risk = float(cfg.pop("_risk_lambda", 0.25))
    weights = weights_from_config(cfg)
    progress("loading the previous plan", 15)
    orders, vehicles = load_entities(db, parent_ids, None)
    # a vehicle that is down but still referenced by the old plan must be present for the repair step
    problem = build_problem(orders, vehicles, risk)
    solver_event = dict(event)
    if event["type"] == "new_order":
        order = event["order"] if isinstance(event["order"], Order) else Order(**event["order"])
        order = order.model_copy(update={k: _utc(getattr(order, k)) for k in ("time_window_start", "time_window_end", "created_at")})
        if order.order_id in {o.order_id for o in orders}:  # already part of the plan: nothing to add
            solver_event = {"type": "traffic_change", "time_multiplier": 1.0}
        else:
            solver_event = {"type": "new_order", "order": order}
        event = {"type": "new_order", "order": order.model_dump(mode="json")}
    progress("re-optimizing from the previous plan", 45)
    result, new_problem = reoptimize(problem, prev_routes, solver_event, weights, max_runtime_seconds=max_runtime_s)
    new_problem["time_model"], new_problem["risk_lambda"] = problem["time_model"], risk
    if run_id:
        result.run_id = run_id
        for r in result.routes:
            r.optimizer_run_id = run_id
    progress("scoring arrival-time uncertainty", 80)
    preds = stop_predictions(new_problem, result.routes)
    metrics = plan_metrics(new_problem, result, weights, preds)
    nn = solve_nn(new_problem, weights)
    baseline = evaluate_solution(nn.routes, new_problem, weights, nn.unassigned)
    baseline["cost_per_order"] = baseline["total_cost"] / baseline["orders_assigned"] if baseline["orders_assigned"] else None
    persist_run(db, new_problem, result, weights, cfg, preds, metrics, baseline, parent_run_id=parent_run_id,
                event=event)
    # apply the disruption to operational data only after the new plan is safely stored
    if event["type"] == "cancel_order":
        o = db.get(DBOrder, event["order_id"])
        if o:
            o.status = OrderStatus.CANCELLED
    elif event["type"] == "vehicle_down":
        v = db.get(DBVehicle, event["vehicle_id"])
        if v:
            v.is_active = False
    db.commit()
    return {"problem": new_problem, "result": result, "preds": preds, "metrics": metrics, "baseline": baseline}


# ---------------------------------------------------------------------------- replay
def _sample_leg(rng, leg: dict) -> float:
    lo, mid, hi = leg["p10"], leg["p50"], leg["p90"]
    knots_u = [0.0, 0.1, 0.5, 0.9, 1.0]
    knots_v = [max(lo - 0.5 * (mid - lo), 0.0), lo, mid, hi, hi + 1.5 * (hi - mid)]
    return float(np.interp(rng.uniform(), knots_u, knots_v))


def ensure_replay(db: Session, run_id: str) -> List[DBReplayEvent]:
    """Simulated 'what actually happened' for a run: each leg is drawn from its calibrated p10/p50/p90
    distribution (seeded per run, so reproducible). v1 has no live GPS, so this is clearly simulated data."""
    existing = db.query(DBReplayEvent).filter(DBReplayEvent.optimizer_run_id == run_id).order_by(DBReplayEvent.planned_arrival).all()
    if existing:
        return existing
    run = db.get(DBOptimizerRun, run_id)
    if run is None:
        raise ValueError(f"unknown optimizer run {run_id}")
    routes = stored_routes(db, run_id)
    preds = {p.order_id: p for p in db.query(DBPrediction).filter(DBPrediction.optimizer_run_id == run_id).all()}
    orders = {o.order_id: from_db_order(o) for o in db.query(DBOrder).filter(DBOrder.order_id.in_(list(preds))).all()}
    rng = np.random.RandomState(int(hashlib.sha1(run_id.encode()).hexdigest()[:8], 16))
    for r in routes:
        t = None
        for k, oid in enumerate(r.ordered_stops):
            p, o = preds.get(oid), orders.get(oid)
            if p is None or o is None:
                continue
            leg = (p.meta or {}).get("leg") or {"p10": 5, "p50": 8, "p90": 12}
            planned = _utc(r.predicted_arrival_times[k])
            if t is None:
                t = planned - timedelta(minutes=leg["p50"])
            arrive = t + timedelta(minutes=_sample_leg(rng, leg))
            start = max(arrive, _utc(o.time_window_start))
            end = _utc(o.time_window_end)
            db.add(DBReplayEvent(
                optimizer_run_id=run_id, route_id=r.route_id, vehicle_id=r.vehicle_id, order_id=oid, stop_index=k,
                planned_arrival=planned, actual_arrival=start, window_end=end, late=int(start > end)))
            t = start + timedelta(minutes=o.service_time_minutes)
    db.commit()
    return db.query(DBReplayEvent).filter(DBReplayEvent.optimizer_run_id == run_id).order_by(DBReplayEvent.planned_arrival).all()


# ---------------------------------------------------------------------------- stored-plan view
def plan_from_db(db: Session, run_id: str) -> dict:
    """The same JSON shape as serialize_plan(), rebuilt from persisted routes + predictions."""
    run = db.get(DBOptimizerRun, run_id)
    if run is None:
        raise ValueError(f"unknown optimizer run {run_id}")
    routes = db.query(DBRoute).filter(DBRoute.optimizer_run_id == run_id).all()
    preds = {p.order_id: p for p in db.query(DBPrediction).filter(DBPrediction.optimizer_run_id == run_id).all()}
    ids = [s for r in routes for s in r.ordered_stops] + [u["order_id"] for u in (run.unassigned or [])]
    orders = {o.order_id: o for o in db.query(DBOrder).filter(DBOrder.order_id.in_(ids)).all()}
    base = _utc(datetime.fromisoformat(run.metrics["base_time"])) if run.metrics and run.metrics.get("base_time") else None
    out_routes = []
    for r in routes:
        stops = []
        for k, oid in enumerate(r.ordered_stops):
            o, p = orders.get(oid), preds.get(oid)
            if o is None:
                continue
            m = (p.meta or {}) if p else {}
            planned = _utc(datetime.fromisoformat(r.predicted_arrival_times[k].replace("Z", "+00:00")))
            def at(minutes):
                return (base + timedelta(minutes=minutes)).isoformat() if base is not None and minutes is not None else None
            stops.append({
                "order_id": oid, "lat": o.delivery_lat, "lng": o.delivery_lng, "priority": o.priority.value,
                "planned_arrival": planned.isoformat(), "p10": at(p.predicted_time_p10 if p else None),
                "p50": at(p.predicted_time_p50 if p else None), "p90": at(p.predicted_time_p90 if p else None),
                "window_start": _utc(o.time_window_start).isoformat(), "window_end": _utc(o.time_window_end).isoformat(),
                "slack_min": (r.stop_slack_min or [None] * (k + 1))[k] if r.stop_slack_min else None,
                "status": "late" if m.get("likely_late") else "at_risk" if m.get("late_risk") else "on_time",
            })
        out_routes.append({"route_id": r.route_id, "vehicle_id": r.vehicle_id, "total_distance_km": r.total_distance_km,
                           "total_time_min": r.total_predicted_time_min, "total_cost": r.total_cost, "stops": stops})
    vehicles = {v.vehicle_id: v for v in db.query(DBVehicle).all()}
    v0 = next((vehicles[r.vehicle_id] for r in routes if r.vehicle_id in vehicles), None)
    return {
        "run_id": run_id, "solver": run.solver_type, "time_model": run.time_model, "status": run.status,
        "depot": {"lat": v0.current_lat, "lng": v0.current_lng} if v0 else None,
        "routes": out_routes, "unassigned": run.unassigned or [],
        "metrics": run.metrics, "baseline_metrics": run.baseline_metrics, "parent_run_id": run.parent_run_id,
        "event": run.event, "weights": run.weight_config, "created_at": run.created_at.isoformat() if run.created_at else None,
    }
