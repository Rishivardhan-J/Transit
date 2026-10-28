from sqlalchemy import Column, String, Float, JSON, DateTime
from datetime import datetime, timezone
from .base import Base


def _now():
    return datetime.now(timezone.utc)


class DBOptimizerRun(Base):
    __tablename__ = "optimizer_runs"
    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    solver_type = Column(String, nullable=False)
    weight_config = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)
    parent_run_id = Column(String, nullable=True, index=True)   # set for incremental re-solves
    event = Column(JSON, nullable=True)                         # the disruption that produced this run
    metrics = Column(JSON, nullable=True)                       # evaluate_solution() output + predicted-late stats
    baseline_metrics = Column(JSON, nullable=True)              # nearest-neighbour shadow run on the same problem
    unassigned = Column(JSON, nullable=True)                    # [{order_id, reason}]
    runtime_s = Column(Float, nullable=True)
    time_model = Column(String, nullable=True)                  # leg-model bundle version or "speed-profile"
    error = Column(String, nullable=True)
