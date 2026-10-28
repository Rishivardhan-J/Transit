from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.models_db.user import User
from backend.services import optimization as svc

router = APIRouter()


@router.get("/{run_id}")
def replay(run_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Planned vs simulated-actual arrivals for a run (the evaluation view). Actuals are simulated: v1 has no GPS feed."""
    try:
        events = svc.ensure_replay(db, run_id)
        plan = svc.plan_from_db(db, run_id)
    except ValueError:
        raise HTTPException(404, "Optimizer run not found")
    coords = {s["order_id"]: (s["lat"], s["lng"]) for r in plan["routes"] for s in r["stops"]}
    by_route = defaultdict(list)
    for e in events:
        lat, lng = coords.get(e.order_id, (None, None))
        by_route[e.route_id].append({
            "order_id": e.order_id, "stop_index": e.stop_index, "lat": lat, "lng": lng,
            "planned": e.planned_arrival.isoformat(), "actual": e.actual_arrival.isoformat(),
            "window_end": e.window_end.isoformat(), "late": bool(e.late),
            "error_min": round((e.actual_arrival - e.planned_arrival).total_seconds() / 60.0, 2),
        })
    errors = [abs(s["error_min"]) for stops in by_route.values() for s in stops]
    n = len(errors)
    vehicle = {r["route_id"]: r["vehicle_id"] for r in plan["routes"]}
    return {
        "run_id": run_id, "simulated": True, "depot": plan["depot"],
        "routes": [{"route_id": rid, "vehicle_id": vehicle.get(rid), "stops": sorted(s, key=lambda x: x["stop_index"])}
                   for rid, s in by_route.items()],
        "summary": {
            "stops": n, "mae_min": round(sum(errors) / n, 2) if n else None,
            "planned_late": sum(1 for r in plan["routes"] for s in r["stops"] if s["planned_arrival"] > s["window_end"]),
            "actual_late": sum(1 for e in events if e.late),
        },
    }
