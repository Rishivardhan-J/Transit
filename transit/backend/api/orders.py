from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd

from backend.api.deps import get_db, get_current_user
from backend.models_db.user import User, Role
from backend.models_db.order import DBOrder
from backend.models_db.route import DBRoute
from backend.models_db.converters import to_db_order, from_db_order
from src.data_processing.schemas import Order, OrderStatus
from src.data_processing.processor import DataProcessor, anonymize_coordinates
from backend.jobs.optimization_tasks import run_incremental_reoptimization

router = APIRouter()
processor = DataProcessor()

@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order: Order, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validate using DataProcessor (Phase 1 logic)
    df = pd.DataFrame([order.model_dump()])
    report = processor.validate_batch(df, Order)
    if not report.is_valid():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[err.model_dump() for err in report.errors]
        )
    
    db_order = db.query(DBOrder).filter(DBOrder.order_id == order.order_id).first()
    if db_order:
        raise HTTPException(status_code=400, detail="Order ID already exists")
    
    new_db_order = to_db_order(order)
    db.add(new_db_order)
    db.commit()
    db.refresh(new_db_order)
    return from_db_order(new_db_order)

@router.get("/export", response_model=List[Order])
def export_orders(
    skip: int = 0, limit: int = 100, status_filter: Optional[OrderStatus] = None, 
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    query = db.query(DBOrder)
    if status_filter:
        query = query.filter(DBOrder.status == status_filter)
    db_orders = query.offset(skip).limit(limit).all()
    
    orders = [from_db_order(db_o) for db_o in db_orders]
    
    # RBAC: Anonymize coordinates for non-researchers on export only
    if current_user.role != Role.researcher and orders:
        df = pd.DataFrame([o.model_dump() for o in orders])
        df_anon = anonymize_coordinates(df)
        orders = [Order(**{str(k): v for k, v in record.items()}) for record in df_anon.to_dict(orient="records")]
        
    return orders

@router.get("", response_model=List[Order])
def list_orders(
    skip: int = 0, limit: int = 100, status_filter: Optional[OrderStatus] = None, 
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    query = db.query(DBOrder)
    if status_filter:
        query = query.filter(DBOrder.status == status_filter)
    db_orders = query.offset(skip).limit(limit).all()
    
    return [from_db_order(db_o) for db_o in db_orders]

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return from_db_order(db_order)

@router.patch("/{order_id}", response_model=Order)
def update_order_status(order_id: str, status_update: OrderStatus, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.status = status_update
    db.commit()
    db.refresh(db_order)
    return from_db_order(db_order)

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order was assigned to an active route
    if db_order.status == OrderStatus.ASSIGNED:
        # Find the route containing this order
        routes = db.query(DBRoute).all()
        for r in routes:
            if order_id in r.ordered_stops:
                # Trigger incremental re-optimization asynchronously
                run_incremental_reoptimization.delay(
                    r.optimizer_run_id, 
                    {"type": "cancellation", "order_id": order_id}
                )
                break
                
    db.delete(db_order)
    db.commit()
    return None
