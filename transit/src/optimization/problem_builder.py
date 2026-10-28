import os
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from src.data_processing.schemas import Order, Vehicle, Priority, VehicleType, OrderStatus
import numpy as np
from src.cost_engine.travel_time import TravelTimeProvider, EuclideanTime, SpeedProfileTime

def parse_solomon_instance(filepath: str, num_customers: int = 100) -> Tuple[List[Order], List[Vehicle]]:
    """
    Parses a Solomon benchmark instance into our internal Order and Vehicle schemas.
    """
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    # Solomon format:
    # 0: Name (e.g. C101)
    # 1: VEHICLE
    # 2: NUMBER CAPACITY
    # 3: [num] [cap]
    
    parts = lines[3].split()
    num_vehicles = int(parts[0])
    capacity = float(parts[1])

    # Find the CUSTOMER section
    cust_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("CUST NO."):
            cust_idx = i + 1
            break

    depot_line = lines[cust_idx].split()
    depot_x, depot_y = float(depot_line[1])/10.0, float(depot_line[2])/10.0
    depot_ready = float(depot_line[4])
    depot_due = float(depot_line[5])
    
    # We will use an arbitrary base date for datetime conversion
    base_date = datetime(2024, 1, 1, 8, 0, 0)

    vehicles = []
    for i in range(num_vehicles):
        v = Vehicle(
            vehicle_id=f"solomon_v_{i}",
            capacity=capacity,
            vehicle_type=VehicleType.TRUCK,
            fuel_efficiency=10.0,
            available_from=base_date + timedelta(minutes=depot_ready),
            available_until=base_date + timedelta(minutes=depot_due),
            current_lat=depot_x,  # Mapping X/Y directly to Lat/Lng for simplicity in benchmark
            current_lng=depot_y
        )
        vehicles.append(v)

    orders = []
    # Read customers up to num_customers
    for i in range(1, num_customers + 1):
        line = lines[cust_idx + i].split()
        cust_id = line[0]
        x, y = float(line[1])/10.0, float(line[2])/10.0
        demand = float(line[3])
        ready_time = float(line[4])
        due_date = float(line[5])
        service_time = float(line[6])

        order = Order(
            order_id=f"solomon_cust_{cust_id}",
            pickup_lat=depot_x,
            pickup_lng=depot_y,
            delivery_lat=x,
            delivery_lng=y,
            demand_weight=demand,
            priority=Priority.STANDARD,
            time_window_start=base_date + timedelta(minutes=ready_time),
            time_window_end=base_date + timedelta(minutes=due_date),
            service_time_minutes=service_time,
            created_at=base_date - timedelta(hours=1),
            status=OrderStatus.PENDING
        )
        orders.append(order)

    return orders, vehicles

SOLOMON_COORD_SCALE = 10.0  # parse_solomon_instance divides raw x/y by 10 to satisfy lat/lng bounds


def pairwise_distance(coords: List[Tuple[float, float]], euclidean: bool = False, scale: float = 1.0) -> np.ndarray:
    """NxN distance matrix. Haversine km for lat/lng, or planar Euclidean (times `scale`)."""
    c = np.asarray(coords, dtype=float)
    if euclidean:
        d = np.sqrt(((c[:, None, :] - c[None, :, :]) ** 2).sum(-1)) * scale
    else:
        lat, lng = np.radians(c[:, 0]), np.radians(c[:, 1])
        dlat = lat[None, :] - lat[:, None]
        dlng = lng[None, :] - lng[:, None]
        a = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlng / 2) ** 2
        d = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    np.fill_diagonal(d, 0.0)
    return d


def build_cvrptw_problem(
    orders: List[Order],
    vehicles: List[Vehicle],
    use_euclidean: bool = False,
    coord_scale: float = 1.0,
    time_provider: Optional[TravelTimeProvider] = None,
    depart_hour: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Builds the single-depot CVRPTW problem dict shared by every solver.

    Node 0 is the depot (first vehicle's start coordinates); node i>0 is orders[i-1].
    Units: `dist_matrix` is km for lat/lng data (or raw instance units when
    `use_euclidean`, with `coord_scale` undoing any coordinate down-scaling);
    `time_matrix` is minutes from `time_provider` (default: Euclidean 1 unit = 1 min
    for planar data, speed profile for lat/lng).
    """
    if not vehicles:
        raise ValueError("Must provide at least one vehicle")

    v0 = vehicles[0]
    depot_lat = v0.current_lat if v0.current_lat is not None else 0.0
    depot_lng = v0.current_lng if v0.current_lng is not None else 0.0
    coords = [(depot_lat, depot_lng)] + [(o.delivery_lat, o.delivery_lng) for o in orders]

    dist = pairwise_distance(coords, euclidean=use_euclidean, scale=coord_scale)
    base_time = min(v.available_from for v in vehicles)
    if time_provider is None:
        time_provider = EuclideanTime() if use_euclidean else SpeedProfileTime()
    hour = depart_hour if depart_hour is not None else base_time.hour + base_time.minute / 60.0
    time = time_provider.matrix(coords, dist, hour)

    return {
        "coords": coords,
        "dist_matrix": dist,
        "time_matrix": time,
        "orders": orders,
        "vehicles": vehicles,
        "depot_lat": depot_lat,
        "depot_lng": depot_lng,
        "base_time": base_time,
        "units": "planar" if use_euclidean else "km",
        "_build_args": {"use_euclidean": use_euclidean, "coord_scale": coord_scale,
                        "time_provider": time_provider, "depart_hour": depart_hour},
    }
