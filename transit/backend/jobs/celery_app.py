from celery import Celery
from backend.config import settings

celery_app = Celery(
    "transit_jobs",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.jobs.optimization_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Time limits to prevent runaway tasks while allowing legitimate 30s solves
    task_soft_time_limit=120,
    task_time_limit=150,
)
