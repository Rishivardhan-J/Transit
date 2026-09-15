from src.data_processing.schemas import Order, Vehicle, Route, Prediction
from .order import DBOrder
from .vehicle import DBVehicle
from .route import DBRoute
from .prediction import DBPrediction
from datetime import datetime

def to_db_order(order: Order) -> DBOrder:
    return DBOrder(
        order_id=order.order_id,
        pickup_lat=order.pickup_lat,
        pickup_lng=order.pickup_lng,
        delivery_lat=order.delivery_lat,
        delivery_lng=order.delivery_lng,
        demand_weight=order.demand_weight,
        priority=order.priority,
        time_window_start=order.time_window_start,
        time_window_end=order.time_window_end,
        service_time_minutes=order.service_time_minutes,
        created_at=order.created_at,
        status=order.status
    )

def from_db_order(db_order: DBOrder) -> Order:
    return Order(
        order_id=db_order.order_id,
        pickup_lat=db_order.pickup_lat,
        pickup_lng=db_order.pickup_lng,
        delivery_lat=db_order.delivery_lat,
        delivery_lng=db_order.delivery_lng,
        demand_weight=db_order.demand_weight,
        priority=db_order.priority,
        time_window_start=db_order.time_window_start,
        time_window_end=db_order.time_window_end,
        service_time_minutes=db_order.service_time_minutes,
        created_at=db_order.created_at,
        status=db_order.status
    )

def to_db_vehicle(vehicle: Vehicle) -> DBVehicle:
    return DBVehicle(
        vehicle_id=vehicle.vehicle_id,
        capacity=vehicle.capacity,
        vehicle_type=vehicle.vehicle_type,
        fuel_efficiency=vehicle.fuel_efficiency,
        available_from=vehicle.available_from,
        available_until=vehicle.available_until,
        current_lat=vehicle.current_lat,
        current_lng=vehicle.current_lng
    )

def from_db_vehicle(db_vehicle: DBVehicle) -> Vehicle:
    return Vehicle(
        vehicle_id=db_vehicle.vehicle_id,
        capacity=db_vehicle.capacity,
        vehicle_type=db_vehicle.vehicle_type,
        fuel_efficiency=db_vehicle.fuel_efficiency,
        available_from=db_vehicle.available_from,
        available_until=db_vehicle.available_until,
        current_lat=db_vehicle.current_lat,
        current_lng=db_vehicle.current_lng
    )

def to_db_route(route: Route) -> DBRoute:
    # Convert datetimes to isoformat strings for JSON serialization
    predicted_arrival_times = [t.isoformat() for t in route.predicted_arrival_times]
    return DBRoute(
        route_id=route.route_id,
        vehicle_id=route.vehicle_id,
        ordered_stops=route.ordered_stops,
        predicted_arrival_times=predicted_arrival_times,
        total_distance_km=route.total_distance_km,
        total_predicted_time_min=route.total_predicted_time_min,
        total_cost=route.total_cost,
        optimizer_run_id=route.optimizer_run_id
    )

def from_db_route(db_route: DBRoute) -> Route:
    predicted_arrival_times = [datetime.fromisoformat(t) for t in db_route.predicted_arrival_times]
    return Route(
        route_id=db_route.route_id,
        vehicle_id=db_route.vehicle_id,
        ordered_stops=db_route.ordered_stops,
        predicted_arrival_times=predicted_arrival_times,
        total_distance_km=db_route.total_distance_km,
        total_predicted_time_min=db_route.total_predicted_time_min,
        total_cost=db_route.total_cost,
        optimizer_run_id=db_route.optimizer_run_id
    )

def to_db_prediction(pred: Prediction) -> DBPrediction:
    return DBPrediction(
        order_id=pred.order_id,
        predicted_time_p10=pred.predicted_time_p10,
        predicted_time_p50=pred.predicted_time_p50,
        predicted_time_p90=pred.predicted_time_p90,
        model_version=pred.model_version,
        shap_top_features=pred.shap_top_features
    )

def from_db_prediction(db_pred: DBPrediction) -> Prediction:
    return Prediction(
        order_id=db_pred.order_id,
        predicted_time_p10=db_pred.predicted_time_p10,
        predicted_time_p50=db_pred.predicted_time_p50,
        predicted_time_p90=db_pred.predicted_time_p90,
        model_version=db_pred.model_version,
        shap_top_features=db_pred.shap_top_features
    )
