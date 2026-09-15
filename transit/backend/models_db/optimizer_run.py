from sqlalchemy import Column, String, Float, JSON, DateTime
from datetime import datetime
from .base import Base

class DBOptimizerRun(Base):
    __tablename__ = "optimizer_runs"
    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    solver_type = Column(String, nullable=False)
    weight_config = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)
