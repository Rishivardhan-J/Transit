from sqlalchemy import Column, String, Float, Enum, DateTime
from src.data_processing.schemas import Priority, OrderStatus
from .base import Base

class DBOrder(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True, index=True)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    delivery_lat = Column(Float, nullable=False)
    delivery_lng = Column(Float, nullable=False)
    demand_weight = Column(Float, nullable=False)
    priority = Column(Enum(Priority), default=Priority.STANDARD, nullable=False)
    time_window_start = Column(DateTime(timezone=True), nullable=False)
    time_window_end = Column(DateTime(timezone=True), nullable=False)
    service_time_minutes = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
