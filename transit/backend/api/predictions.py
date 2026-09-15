from fastapi import APIRouter, Depends, HTTPException
from backend.api.deps import get_current_user
from backend.models_db.user import User
from src.data_processing.schemas import Prediction, Order, Vehicle
# from src.models.predict import predict_delivery_time
# Phase 3 predict not fully implemented here as mock for now
from pydantic import BaseModel

router = APIRouter()

class PredictRequest(BaseModel):
    order: Order
    vehicle: Vehicle

@router.post("/eta", response_model=Prediction)
def get_eta(req: PredictRequest, current_user: User = Depends(get_current_user)):
    # Mocking prediction call since we don't have the fully trained models on disk for the test
    # In a real setup, we would call `predict_delivery_time(req.order, req.vehicle)`
    return Prediction(
        order_id=req.order.order_id,
        predicted_time_p10=10.0,
        predicted_time_p50=15.0,
        predicted_time_p90=25.0,
        model_version="v1.0",
        shap_top_features={"distance": 0.5, "priority": 0.2}
    )

@router.get("/{order_id}/explain")
def explain_eta(order_id: str, current_user: User = Depends(get_current_user)):
    return {"shap_top_features": {"distance": 0.5, "priority": 0.2}}
