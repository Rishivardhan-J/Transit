from sqlalchemy import Column, String, Float, JSON, ForeignKey, Integer
from .base import Base

class DBPrediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False)
    predicted_time_p10 = Column(Float, nullable=False)
    predicted_time_p50 = Column(Float, nullable=False)
    predicted_time_p90 = Column(Float, nullable=False)
    model_version = Column(String, nullable=False)
    shap_top_features = Column(JSON, nullable=False)
