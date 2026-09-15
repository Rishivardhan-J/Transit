from backend.jobs.celery_app import celery_app
from src.optimization.problem_builder import build_cvrptw_problem
import time
import json
import redis
from backend.config import settings
from backend.models_db.base import SessionLocal
from backend.models_db.optimizer_run import DBOptimizerRun
from backend.models_db.route import DBRoute

redis_client = redis.from_url(settings.REDIS_URL)

def publish_status(job_id: str, status: str, result: dict = None):
    msg = {"job_id": job_id, "status": status}
    if result:
        msg["result"] = result
    redis_client.publish(f"job_updates:{job_id}", json.dumps(msg))

@celery_app.task(bind=True)
def run_batch_optimization(self, order_ids: list, vehicle_ids: list, solver_type: str, weight_config: dict):
    job_id = self.request.id
    publish_status(job_id, "running")
    
    db = SessionLocal()
    try:
        # Create an OptimizerRun row
        run_record = DBOptimizerRun(
            id=job_id,
            solver_type=solver_type,
            weight_config=weight_config,
            status="running"
        )
        db.add(run_record)
        db.commit()
        
        # Simulate optimization time
        time.sleep(2) # To be integrated with Phase 3 baselines/hgs
        
        run_record.status = "completed"
        db.commit()
        publish_status(job_id, "completed", {"routes": []})
        return {"status": "completed", "optimizer_run_id": job_id}
    except Exception as e:
        publish_status(job_id, "failed", {"error": str(e)})
        if run_record:
            run_record.status = "failed"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task(bind=True)
def run_incremental_reoptimization(self, optimizer_run_id: str, disruption_event: dict):
    job_id = self.request.id
    publish_status(job_id, "running")
    # Simulate re-optimization (Phase 3 incremental logic)
    time.sleep(1) 
    publish_status(job_id, "completed", {"status": "reoptimized"})
    return {"status": "completed"}
