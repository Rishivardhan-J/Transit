from fastapi import APIRouter, Depends, HTTPException
from backend.api.deps import get_current_user, get_db
from sqlalchemy.orm import Session
from backend.models_db.user import User
from src.data_processing.schemas import Prediction, Order, Vehicle
from src.models.predict import predict_delivery_time
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class PredictRequest(BaseModel):
    order: Order
    vehicle: Vehicle

@router.post("/eta", response_model=Prediction)
def get_eta(req: PredictRequest, current_user: User = Depends(get_current_user)):
    try:
        prediction = predict_delivery_time(
            order=req.order,
            vehicle=req.vehicle,
            as_of_timestamp=req.order.time_window_start.isoformat(),
        )
        return prediction
    except Exception as e:
        logger.error(f"Failed to generate prediction: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Prediction models unavailable"
        )

def _persisted_explanation(db: Session, order_id: str):
    """Stop-level explanation stored by the latest optimizer run: arrival interval, window, leg SHAP."""
    from datetime import datetime, timedelta
    from backend.models_db.prediction import DBPrediction
    from backend.services.optimization import latest_run

    run = latest_run(db)
    if run is None:
        return None
    pred = db.query(DBPrediction).filter(DBPrediction.order_id == order_id, DBPrediction.optimizer_run_id == run.id).first()
    if pred is None or not (run.metrics or {}).get("base_time"):
        return None
    base = datetime.fromisoformat(run.metrics["base_time"])
    at = lambda minutes: (base + timedelta(minutes=minutes)).isoformat()
    meta = pred.meta or {}
    leg = meta.get("leg") or {}
    shap = [{"feature": f["feature"], "value": round(f["impact"] / 60.0 if f.get("unit") == "sec" else f["impact"], 3),
             "text": f.get("text", f["feature"])} for f in (pred.shap_top_features or [])]
    status = "late" if meta.get("likely_late") else "at_risk" if meta.get("late_risk") else "on_time"
    return {
        "order_id": order_id, "optimizer_run_id": run.id, "route_id": pred.route_id, "stop_index": pred.stop_index,
        "n_stops": meta.get("n_stops"), "status": status, "model_version": pred.model_version,
        "arrival": {"p10": at(pred.predicted_time_p10), "p50": at(pred.predicted_time_p50), "p90": at(pred.predicted_time_p90)},
        "window_end": at(meta["window_end"]) if "window_end" in meta else None,
        "leg_minutes": {k: round(v, 2) for k, v in leg.items()},
        "predicted_eta_mins": int(round(leg.get("p50", 0))),
        "p10_mins": round(leg.get("p10", 0), 1), "p50_mins": round(leg.get("p50", 0), 1), "p90_mins": round(leg.get("p90", 0), 1),
        "shap_values": shap,
    }


@router.get("/{order_id}/explain")
def explain_eta(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    persisted = _persisted_explanation(db, order_id)
    if persisted:
        return persisted
    from backend.models_db.order import DBOrder
    from backend.models_db.route import DBRoute
    from backend.models_db.vehicle import DBVehicle
    from backend.models_db.converters import from_db_order, from_db_vehicle

    # 1. Fetch Order
    db_order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Find Assigned Vehicle from Routes
    # We iterate routes in memory for simplicity (in a real app, this would be a normalized DB relation or JSON query)
    routes = db.query(DBRoute).all()
    vehicle_id = None
    for r in routes:
        if isinstance(r.ordered_stops, list) and order_id in r.ordered_stops:
            vehicle_id = r.vehicle_id
            break

    if not vehicle_id:
        raise HTTPException(status_code=404, detail="Order is not assigned to any vehicle")

    db_vehicle = db.query(DBVehicle).filter(DBVehicle.vehicle_id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="Assigned vehicle not found")

    try:
        order = from_db_order(db_order)
        vehicle = from_db_vehicle(db_vehicle)
        prediction = predict_delivery_time(
            order=order,
            vehicle=vehicle,
            as_of_timestamp=order.time_window_start.isoformat(),
        )
        # Format the response as requested: {"predicted_eta_mins": int, "shap_values": [{"feature": str, "value": float}]}
        # Prediction returns shap_top_features as: [{"feature": str, "value": any, "impact_minutes": float}]
        # We map 'impact_minutes' to 'value' for the frontend chart.
        formatted_shap = []
        for feat in prediction.shap_top_features:
            formatted_shap.append({
                "feature": feat["feature"],
                "value": feat["impact_minutes"],
                "text": feat.get("text", feat["feature"]),
            })

        return {
            "predicted_eta_mins": int(prediction.predicted_time_p50),
            "p10_mins": round(prediction.predicted_time_p10, 1),
            "p50_mins": round(prediction.predicted_time_p50, 1),
            "p90_mins": round(prediction.predicted_time_p90, 1),
            "model_version": prediction.model_version,
            "shap_values": formatted_shap
        }
    except Exception as e:
        logger.error(f"Failed to explain prediction: {str(e)}")
        raise HTTPException(status_code=503, detail="Prediction models unavailable")
