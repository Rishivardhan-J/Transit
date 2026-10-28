import json
import logging
import time
from typing import List, Optional

import redis

from backend.config import settings
from backend.jobs.celery_app import celery_app
from backend.models_db.base import SessionLocal
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.services import optimization as svc

logger = logging.getLogger(__name__)
_redis = None
_down_until = 0.0   # circuit breaker: after a failed publish, skip Redis for a while instead of stalling every progress update
_COOLDOWN_S = 30.0


def _client():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    return _redis


def publish(channel: str, payload: dict) -> None:
    """Best-effort pub/sub: clients fall back to polling GET /jobs/{id} if Redis is unavailable."""
    global _down_until
    if settings.CELERY_EAGER or time.monotonic() < _down_until:
        return
    try:
        _client().publish(channel, json.dumps(payload, default=str))
    except Exception as e:
        _down_until = time.monotonic() + _COOLDOWN_S
        logger.debug("redis publish skipped (%s)", e)


def publish_status(job_id: str, status: str, result: Optional[dict] = None, stage: Optional[str] = None, pct: Optional[int] = None):
    msg = {"job_id": job_id, "status": status}
    if result:
        msg["result"] = result
    if stage:
        msg["stage"] = stage
    if pct is not None:
        msg["progress"] = pct
    publish(f"job_updates:{job_id}", msg)


def _finish(job_id: str, out: dict) -> dict:
    result, metrics = out["result"], out["metrics"]
    summary = {"optimizer_run_id": result.run_id, "routes": len(result.routes), "unassigned": len(result.unassigned),
               "total_distance": metrics["total_distance"], "total_cost": metrics["total_cost"],
               "predicted_late": metrics["predicted_late"], "feasible": metrics["feasible"]}
    publish(f"route_updates:{result.run_id}", {"optimizer_run_id": result.run_id, **summary})
    publish_status(job_id, "completed", summary, stage="done", pct=100)
    return {"status": "completed", **summary}


def _fail(db, job_id: str, run_id: str, solver: str, cfg: dict, e: Exception):
    db.rollback()
    run = db.get(DBOptimizerRun, run_id) or DBOptimizerRun(id=run_id, solver_type=solver, weight_config=cfg)
    run.status, run.error = "failed", str(e)[:500]
    db.add(run)
    db.commit()
    publish_status(job_id, "failed", {"error": str(e)})


@celery_app.task(bind=True)
def run_batch_optimization(self, order_ids: List[str], vehicle_ids: List[str], solver_type: str, weight_config: dict,
                           risk_lambda: float = 0.25, max_runtime_s: float = 20.0):
    job_id = self.request.id or "eager"
    publish_status(job_id, "running", stage="starting", pct=0)
    db = SessionLocal()
    try:
        out = svc.run_optimization(db, order_ids or None, vehicle_ids or None, solver_type, weight_config, risk_lambda,
                                   max_runtime_s, run_id=job_id,
                                   progress=lambda stage, pct: publish_status(job_id, "running", stage=stage, pct=pct))
        return _finish(job_id, out)
    except Exception as e:
        logger.exception("optimization failed")
        _fail(db, job_id, job_id, solver_type, weight_config, e)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, soft_time_limit=60, time_limit=90)
def run_incremental_reoptimization(self, optimizer_run_id: str, disruption_event: dict, max_runtime_s: float = 3.0):
    job_id = self.request.id or "eager"
    publish_status(job_id, "running", stage="starting", pct=0)
    db = SessionLocal()
    try:
        out = svc.run_disruption(db, optimizer_run_id, disruption_event, max_runtime_s, run_id=job_id,
                                 progress=lambda stage, pct: publish_status(job_id, "running", stage=stage, pct=pct))
        return _finish(job_id, out)
    except Exception as e:
        logger.exception("incremental re-optimization failed")
        _fail(db, job_id, job_id, "hgs-incremental", {}, e)
        raise
    finally:
        db.close()
