from sqlalchemy import Column, String, Float, Enum, DateTime, Boolean, true
from src.data_processing.schemas import VehicleType
from .base import Base

class DBVehicle(Base):
    __tablename__ = "vehicles"
    vehicle_id = Column(String, primary_key=True, index=True)
    capacity = Column(Float, nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    fuel_efficiency = Column(Float, nullable=False)
    available_from = Column(DateTime(timezone=True), nullable=False)
    available_until = Column(DateTime(timezone=True), nullable=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())  # False after a vehicle_down event
