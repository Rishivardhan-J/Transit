from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.api.deps import get_db, get_current_user
from backend.models_db.user import User
from backend.models_db.vehicle import DBVehicle
from backend.models_db.converters import to_db_vehicle, from_db_vehicle
from src.data_processing.schemas import Vehicle

router = APIRouter()

@router.post("", response_model=Vehicle, status_code=201)
def create_vehicle(vehicle: Vehicle, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_vehicle = db.query(DBVehicle).filter(DBVehicle.vehicle_id == vehicle.vehicle_id).first()
    if db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle ID already exists")
    new_db_vehicle = to_db_vehicle(vehicle)
    db.add(new_db_vehicle)
    db.commit()
    db.refresh(new_db_vehicle)
    return from_db_vehicle(new_db_vehicle)

@router.get("", response_model=List[Vehicle])
def list_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_vehicles = db.query(DBVehicle).offset(skip).limit(limit).all()
    return [from_db_vehicle(v) for v in db_vehicles]

@router.get("/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_vehicle = db.query(DBVehicle).filter(DBVehicle.vehicle_id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return from_db_vehicle(db_vehicle)
