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
            {"version": "v1.0", "metrics": {"r2": 0.74, "mae": 4.5}, "timestamp": "2026-09-15T00:00:00Z"}
        ]
    }
