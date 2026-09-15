from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.models_db.user import User, Role
from backend.security.rbac import require_role
import pandas as pd
import os

router = APIRouter()

@router.get("/solver-comparison")
def get_solver_comparison(current_user: User = Depends(require_role(Role.researcher))):
    path = "results/benchmark_summary.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df.to_dict(orient="records")
    return {"error": "Benchmark data not found"}
