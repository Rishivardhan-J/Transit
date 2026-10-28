"""Celery tasks end to end (eager mode): solve, persist routes/predictions, mark orders assigned."""
from backend.jobs.optimization_tasks import run_batch_optimization
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.order import DBOrder
from backend.models_db.prediction import DBPrediction
from backend.models_db.route import DBRoute
from src.data_processing.schemas import OrderStatus


def test_batch_optimization_persists_a_real_plan(db_session, plan_data):
    res = run_batch_optimization.apply(args=([], [], "hgs", {"preset": "balanced"}, 0.25, 5.0), task_id="job-batch-1")
    assert res.status == "SUCCESS", res.traceback
    assert res.result["feasible"] is True

    run = db_session.get(DBOptimizerRun, "job-batch-1")
    assert run.status == "completed" and run.solver_type == "hgs"
    assert run.metrics["violations"] == []
    assert run.runtime_s > 0 and run.baseline_metrics is not None

    routes = db_session.query(DBRoute).filter_by(optimizer_run_id="job-batch-1").all()
    served = [s for r in routes for s in r.ordered_stops]
    assert len(served) == len(set(served)) > 0
    assert len(served) + len(run.unassigned) == len(plan_data["orders"])  # nothing silently dropped

    preds = db_session.query(DBPrediction).filter_by(optimizer_run_id="job-batch-1").all()
    assert len(preds) == len(served)
    for p in preds:
        assert p.predicted_time_p10 <= p.predicted_time_p50 <= p.predicted_time_p90
        assert p.meta["leg"]["p10"] <= p.meta["leg"]["p50"] <= p.meta["leg"]["p90"]

    db_session.expire_all()
    for oid in served:
        assert db_session.get(DBOrder, oid).status == OrderStatus.ASSIGNED


def test_failed_job_is_recorded(db_session, plan_data):
    res = run_batch_optimization.apply(args=([], [], "bogus-solver", {"preset": "balanced"}), task_id="job-bad-1", throw=False)
    assert res.status == "FAILURE"
    run = db_session.get(DBOptimizerRun, "job-bad-1")
    assert run.status == "failed" and "bogus-solver" in run.error
