from sqlalchemy import Column, String, Float, Integer, DateTime
from .base import Base

class DBReplayEvent(Base):
    """Simulated outcome of a planned stop (v1 has no live GPS; actuals are drawn from the leg model's p10/p50/p90)."""
    __tablename__ = "replay_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    optimizer_run_id = Column(String, nullable=False, index=True)
    route_id = Column(String, nullable=False)
    vehicle_id = Column(String, nullable=False)
    order_id = Column(String, nullable=False)
    stop_index = Column(Integer, nullable=False)
    planned_arrival = Column(DateTime(timezone=True), nullable=False)
    actual_arrival = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    late = Column(Integer, nullable=False)   # 1 if actual_arrival > window_end
