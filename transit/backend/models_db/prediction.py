from sqlalchemy import Column, String, Float, JSON, ForeignKey, Integer
from .base import Base

class DBPrediction(Base):
    """Arrival-time prediction for one stop of one optimizer run.

    predicted_time_* are minutes from the run's base time to arrival (planned arrival plus the
    accumulated uncertainty of the legs driven so far); `meta` carries the per-leg quantiles used
    by the replay simulation and the late-risk flag.
    """
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, index=True)
    predicted_time_p10 = Column(Float, nullable=False)
    predicted_time_p50 = Column(Float, nullable=False)
    predicted_time_p90 = Column(Float, nullable=False)
    model_version = Column(String, nullable=False)
    shap_top_features = Column(JSON, nullable=False)
    optimizer_run_id = Column(String, nullable=True, index=True)
    route_id = Column(String, nullable=True)
    stop_index = Column(Integer, nullable=True)
    meta = Column(JSON, nullable=True)
