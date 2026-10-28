from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.models_db.user import User, Role
from backend.security.rbac import require_role

router = APIRouter()

@router.get("/performance")
def get_model_performance(current_user: User = Depends(require_role(Role.researcher))):
    # Stub reading MLflow run history
    return {
        "runs": [
            {"run_id": "8fa2143b1234", "model_type": "lightgbm", "metrics": {"r2": 0.74, "mae": 4.5}, "timestamp": "2026-09-15T00:00:00Z"}
        ]
    }

@router.get("/")
def get_models_metadata(current_user: User = Depends(require_role(Role.researcher))):
    return {
        "models": {
            "p50": "lightgbm_p50 (latest)",
            "p10": "lightgbm_p10 (latest)",
            "p90": "lightgbm_p90 (latest)"
        },
        "pipeline": "feature_pipeline_latest"
    }
