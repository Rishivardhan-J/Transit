from backend.jobs.celery_app import celery_app
from backend.models_db.base import SessionLocal
from backend.models_db.order import DBOrder
from src.data_processing.schemas import OrderStatus
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def sweep_late_orders(self):
    """
    Periodically checks for orders whose time_window_end has passed
    and they are not delivered or cancelled. Marks them as 'late'.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Find orders that are past their delivery window and not finalized
        late_orders = db.query(DBOrder).filter(
            DBOrder.time_window_end < now,
            DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT])
        ).all()

        count = 0
        for order in late_orders:
            order.status = OrderStatus.LATE
            count += 1
            
        if count > 0:
            db.commit()
            logger.info(f"Marked {count} orders as late.")
            
        return {"updated_count": count}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to sweep late orders: {e}")
        raise
    finally:
        db.close()
