from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.models_db.user import User, Role
from backend.security.rbac import require_role
import pandas as pd
import json

router = APIRouter()

@router.get("/summary")
def get_eda_summary(current_user: User = Depends(require_role(Role.researcher))):
    """
    Provides mock EDA summary stats for Phase 5 visualization.
    In a real app, this would query a data warehouse or load pre-computed JSON from Phase 1.
    """
    return {
        "distributions": {
            "demand_weight": [
                {"bin": "0-10", "count": 120},
                {"bin": "10-20", "count": 340},
                {"bin": "20-30", "count": 210},
                {"bin": "30-40", "count": 80},
                {"bin": "40+", "count": 20}
            ],
            "priority": [
                {"category": "standard", "count": 500},
                {"category": "high", "count": 200},
                {"category": "low", "count": 70}
            ]
        },
        "feature_importance": [
            {"feature": "distance", "importance": 0.45},
            {"feature": "demand_weight", "importance": 0.25},
            {"feature": "priority_high", "importance": 0.15},
            {"feature": "service_time", "importance": 0.10},
            {"feature": "time_window_length", "importance": 0.05}
        ],
        "correlation": [
            {"x": "distance", "y": "duration", "value": 0.85},
            {"x": "distance", "y": "demand", "value": 0.12},
            {"x": "duration", "y": "demand", "value": 0.14}
        ]
    }
