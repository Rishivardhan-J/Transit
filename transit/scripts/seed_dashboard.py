import sys
import os
import random
from datetime import datetime, timedelta, timezone

# Ensure we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.models_db.base import SessionLocal
from backend.models_db.order import DBOrder
from backend.models_db.vehicle import DBVehicle
from backend.models_db.route import DBRoute
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.prediction import DBPrediction
from src.data_processing.schemas import OrderStatus, Priority, VehicleType

def seed_db():
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(DBPrediction).delete()
        db.query(DBRoute).delete()
        db.query(DBOptimizerRun).delete()
        db.query(DBOrder).delete()
        db.query(DBVehicle).delete()
        
        now = datetime.now(timezone.utc)
        
        # Seed Vehicles
        vehicles = []
        for i in range(10):
            v = DBVehicle(
                vehicle_id=f"V-{1000+i}",
                capacity=100.0,
                vehicle_type=VehicleType.VAN,
                fuel_efficiency=12.5,
                available_from=now - timedelta(hours=1),
                available_until=now + timedelta(hours=8),
                current_lat=37.7749 + random.uniform(-0.05, 0.05),
                current_lng=-122.4194 + random.uniform(-0.05, 0.05)
            )
            vehicles.append(v)
            db.add(v)
            
        # Seed Orders
        orders = []
        for i in range(50):
            status = random.choice([OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED, OrderStatus.LATE])
            start_time = now + timedelta(minutes=random.randint(-30, 90))
            end_time = start_time + timedelta(hours=random.uniform(2, 6))
            
            o = DBOrder(
                order_id=f"ORD-{5000+i}",
                pickup_lat=37.7749 + random.uniform(-0.1, 0.1),
                pickup_lng=-122.4194 + random.uniform(-0.1, 0.1),
                delivery_lat=37.7749 + random.uniform(-0.1, 0.1),
                delivery_lng=-122.4194 + random.uniform(-0.1, 0.1),
                demand_weight=random.uniform(5.0, 20.0),
                priority=random.choice(list(Priority)),
                time_window_start=start_time,
                time_window_end=end_time,
                service_time_minutes=random.uniform(5, 15),
                created_at=start_time - timedelta(minutes=30),
                status=status
            )
            orders.append(o)
            db.add(o)
            
        # Seed Optimizer Run
        run = DBOptimizerRun(
            id="RUN-9999",
            solver_type="ortools",
            weight_config={"distance": 1.0},
            status="completed"
        )
        db.add(run)
        
        db.commit() # Commit vehicles, orders, and run to get them in DB
        
        # Seed Routes
        # Assign some orders to vehicles
        assigned_orders = [o for o in orders if o.status in (OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT)]
        
        chunk_size = 3
        for i in range(0, min(len(assigned_orders), 15), chunk_size):
            chunk = assigned_orders[i:i+chunk_size]
            if not chunk: break
            v = vehicles[i // chunk_size]
            
            r = DBRoute(
                route_id=f"RT-{8000+i}",
                vehicle_id=v.vehicle_id,
                ordered_stops=[o.order_id for o in chunk],
                predicted_arrival_times=[(now + timedelta(minutes=15*(j+1))).isoformat() for j in range(len(chunk))],
                total_distance_km=random.uniform(10.0, 30.0),
                total_predicted_time_min=random.uniform(30.0, 60.0),
                total_cost=random.uniform(15.0, 45.0),
                optimizer_run_id=run.id
            )
            db.add(r)
            
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
