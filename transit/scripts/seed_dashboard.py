"""Seed the demo city: Solomon RC101 geography placed on real Los Angeles coordinates (PRD 9.3), a van fleet,
and one real HGS plan with ML travel times, so the ML model and the router operate on the same map.

Deterministic (seeded), and dated ~1 year ahead so the late-order sweep can never flip demo orders to 'late'.
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models_db.base import SessionLocal  # noqa: E402
from backend.models_db.converters import to_db_order, to_db_vehicle  # noqa: E402
from backend.models_db.optimizer_run import DBOptimizerRun  # noqa: E402
from backend.models_db.order import DBOrder  # noqa: E402
from backend.models_db.prediction import DBPrediction  # noqa: E402
from backend.models_db.replay import DBReplayEvent  # noqa: E402
from backend.models_db.route import DBRoute  # noqa: E402
from backend.models_db.vehicle import DBVehicle  # noqa: E402
from backend.services import optimization as svc  # noqa: E402
from src.data_processing.schemas import Order, Priority, Vehicle, VehicleType  # noqa: E402
from src.optimization.problem_builder import parse_solomon_instance  # noqa: E402
from src.paths import BENCHMARK_DIR  # noqa: E402

DEPOT = (34.0407, -118.2468)                     # downtown LA
BBOX = {"lat": (33.99, 34.12), "lng": (-118.34, -118.18)}
N_ORDERS, N_VEHICLES = 60, 8


def build_entities(base: datetime):
    rng = random.Random(42)
    solomon, _ = parse_solomon_instance(str(BENCHMARK_DIR / "solomon" / "RC101.txt"), num_customers=N_ORDERS)
    xs, ys = [o.delivery_lat for o in solomon], [o.delivery_lng for o in solomon]
    scale = lambda v, lo, hi, a, b: a + (v - lo) / (hi - lo) * (b - a)

    orders = []
    for i, s in enumerate(solomon):
        start = base + timedelta(minutes=rng.randint(0, 180))
        orders.append(Order(
            order_id=f"ORD-{5000 + i}", pickup_lat=DEPOT[0], pickup_lng=DEPOT[1],
            delivery_lat=scale(s.delivery_lat, min(xs), max(xs), *BBOX["lat"]),
            delivery_lng=scale(s.delivery_lng, min(ys), max(ys), *BBOX["lng"]),
            demand_weight=float(max(2, round(s.demand_weight / 2))),
            priority=rng.choices(list(Priority), weights=[2, 12, 4, 2])[0],
            time_window_start=start, time_window_end=start + timedelta(minutes=rng.randint(120, 300)),
            service_time_minutes=float(rng.randint(5, 12)), created_at=base - timedelta(hours=2),
        ))
    # Deliberate edge cases so the unassigned-with-reason and late-risk paths are visible in the demo.
    far = (34.115, -118.185)
    orders.append(orders[0].model_copy(update={
        "order_id": "ORD-9001", "delivery_lat": far[0], "delivery_lng": far[1], "priority": Priority.URGENT,
        "time_window_start": base, "time_window_end": base + timedelta(minutes=14)}))   # tight window, far away
    orders.append(orders[1].model_copy(update={"order_id": "ORD-9002", "demand_weight": 150.0}))  # exceeds van capacity

    vehicles = [Vehicle(
        vehicle_id=f"V-{1000 + k}", capacity=100.0, vehicle_type=VehicleType.VAN, fuel_efficiency=12.5,
        available_from=base - timedelta(minutes=30), available_until=base + timedelta(hours=9),
        current_lat=DEPOT[0], current_lng=DEPOT[1]) for k in range(N_VEHICLES)]
    return orders, vehicles


def seed_db():
    db = SessionLocal()
    try:
        for model in (DBReplayEvent, DBPrediction, DBRoute, DBOptimizerRun, DBOrder, DBVehicle):
            db.query(model).delete()
        base = (datetime.now(timezone.utc) + timedelta(days=365)).replace(hour=8, minute=0, second=0, microsecond=0)
        orders, vehicles = build_entities(base)
        for v in vehicles:
            db.add(to_db_vehicle(v))
        for o in orders:
            db.add(to_db_order(o))
        db.commit()

        out = svc.run_optimization(db, None, None, "hgs", {"preset": "balanced"}, risk_lambda=0.25,
                                   max_runtime_s=15.0, run_id="RUN-DEMO-1")
        m = out["metrics"]
        print(f"Seeded {len(orders)} orders, {len(vehicles)} vehicles. Plan RUN-DEMO-1: {len(out['result'].routes)} routes, "
              f"{m['orders_assigned']} assigned, {m['orders_unassigned']} unassigned, predicted late {m['predicted_late']}, "
              f"time model {out['problem']['time_model']}, violations {len(m['violations'])}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
