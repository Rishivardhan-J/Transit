from sqlalchemy import Column, String, Float, JSON, ForeignKey
from .base import Base

class DBRoute(Base):
    __tablename__ = "routes"
    route_id = Column(String, primary_key=True, index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.vehicle_id"), nullable=False)
    ordered_stops = Column(JSON, nullable=False)
    predicted_arrival_times = Column(JSON, nullable=False)
    total_distance_km = Column(Float, nullable=False)
    total_predicted_time_min = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    optimizer_run_id = Column(String, ForeignKey("optimizer_runs.id"), nullable=False)
