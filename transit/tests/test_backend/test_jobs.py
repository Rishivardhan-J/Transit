import pytest
from backend.jobs.optimization_tasks import run_batch_optimization
from backend.models_db.optimizer_run import DBOptimizerRun
import time
from unittest.mock import patch

def test_run_batch_optimization(db_session):
    with patch("backend.jobs.optimization_tasks.SessionLocal", return_value=db_session):
        # Call task synchronously
        result = run_batch_optimization.apply(
        args=(["ord-1"], ["veh-1"], "hgs", {"preset": "balanced"}),
        task_id="test-job-id"
        )
        assert result.status == "SUCCESS"
        assert result.result["status"] == "completed"
    
    # Verify DB state
    run_record = db_session.query(DBOptimizerRun).filter(DBOptimizerRun.id == "test-job-id").first()
    assert run_record is not None
    assert run_record.status == "completed"
    assert run_record.solver_type == "hgs"
