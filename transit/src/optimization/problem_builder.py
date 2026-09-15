import os
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta
import uuid

from src.data_processing.schemas import Order, Vehicle, Priority, VehicleType, OrderStatus
from src.cost_engine.distance_matrix import distance_matrix_service

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

def build_cvrptw_problem(orders: List[Order], vehicles: List[Vehicle], use_euclidean: bool = False) -> Dict[str, Any]:
    """
    Transforms Orders and Vehicles into a CVRPTW problem representation suitable 
    for PyVRP or OR-Tools solvers. Assumes single depot from the vehicles' start coords.
    """
    if not vehicles:
        raise ValueError("Must provide at least one vehicle")
        
    depot_lat = vehicles[0].current_lat if vehicles[0].current_lat else 0.0
    depot_lng = vehicles[0].current_lng if vehicles[0].current_lng else 0.0

    # Build coordinates array: index 0 is depot, 1..N are customers
    coords = [(depot_lat, depot_lng)]
    for o in orders:
        coords.append((o.delivery_lat, o.delivery_lng))
        
    # Pre-build distance matrix
    dist_matrix = distance_matrix_service.build_matrix(coords, use_euclidean=use_euclidean)
    
    # We will compute the time matrix simply as distance / speed (e.g. 60km/h = 1km/min)
    # This is a naive translation for baseline/benchmark when ML predictions aren't directly injected
    time_matrix = dist_matrix  # 1 km = 1 min
    
    # Return standard dictionary representation
    return {
        "coords": coords,
        "dist_matrix": dist_matrix,
        "time_matrix": time_matrix,
        "orders": orders,
        "vehicles": vehicles,
        "depot_lat": depot_lat,
        "depot_lng": depot_lng,
    }
