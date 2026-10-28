"""Order-level ETA inference (p10/p50/p90 minutes + SHAP) on the latest 'order' model bundle."""
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src.data_processing.schemas import Order, Prediction, Vehicle
from src.feature_engineering.feature_pipeline import haversine_km
from src.models.serving import explain, get_bundle, predict_quantiles

logger = logging.getLogger(__name__)

_VEHICLE_MAP = {"bike": "Bike", "car": "Car", "van": "Car", "truck": "Car"}


def _time_of_day(hour: int) -> str:
    return "Morning" if 5 <= hour < 12 else "Afternoon" if 12 <= hour < 17 else "Evening" if 17 <= hour < 21 else "Night"


def _traffic_level(hour: int) -> str:
    """Synthetic traffic proxy (PRD 9.1: no paid feed): rush hours are High, daytime Medium, night Low."""
    return "High" if (7 <= hour < 10 or 16 <= hour < 20) else "Low" if (hour >= 21 or hour < 5) else "Medium"


def order_to_raw(order: Order, vehicle: Optional[Vehicle], bundle, weather: str = "Clear",
                 traffic_level: Optional[str] = None) -> pd.DataFrame:
    hour = order.time_window_start.hour
    d = bundle.metadata["defaults"]
    km = float(haversine_km(order.pickup_lat, order.pickup_lng, order.delivery_lat, order.delivery_lng))
    vtype = vehicle.vehicle_type.value if vehicle is not None else "car"
    return pd.DataFrame([{
        "distance_km": max(km, 0.1), "weather": weather, "traffic_level": traffic_level or _traffic_level(hour),
        "time_of_day": _time_of_day(hour), "vehicle_type": _VEHICLE_MAP.get(vtype, "Car"),
        "prep_time_min": d["prep_time_min"], "courier_exp_yrs": d["courier_exp_yrs"],
    }])


def predict_delivery_time(order: Order, vehicle: Optional[Vehicle] = None, as_of_timestamp: Optional[str] = None,
                          pipeline_path: Optional[str] = None, **conditions) -> Prediction:
    """Raises FileNotFoundError when no model has been trained (the API turns this into a 503)."""
    bundle = get_bundle("order")
    raw = order_to_raw(order, vehicle, bundle, **conditions)
    q = predict_quantiles(bundle, raw).iloc[0]
    top = explain(bundle, raw, top_k=5)[0]
    return Prediction(
        order_id=order.order_id,
        predicted_time_p10=float(q.p10), predicted_time_p50=float(q.p50), predicted_time_p90=float(q.p90),
        model_version=bundle.version,
        shap_top_features=[{"feature": t["feature"], "value": t["value"], "impact_minutes": t["impact"], "text": t["text"]}
                           for t in top],
    )
