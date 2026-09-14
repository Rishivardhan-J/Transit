from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class Priority(str, Enum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    URGENT = "urgent"


class OrderStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    LATE = "late"
    CANCELLED = "cancelled"


class VehicleType(str, Enum):
    BIKE = "bike"
    CAR = "car"
    VAN = "van"
    TRUCK = "truck"


class Order(BaseModel):
    order_id: str = Field(..., description="Unique identifier for the order")
    pickup_lat: float = Field(..., ge=-90.0, le=90.0)
    pickup_lng: float = Field(..., ge=-180.0, le=180.0)
    delivery_lat: float = Field(..., ge=-90.0, le=90.0)
    delivery_lng: float = Field(..., ge=-180.0, le=180.0)
    demand_weight: float = Field(..., gt=0.0, description="Weight/volume demand of the order")
    priority: Priority = Field(default=Priority.STANDARD)
    time_window_start: datetime
    time_window_end: datetime
    service_time_minutes: float = Field(..., ge=0.0)
    created_at: datetime
    status: OrderStatus = Field(default=OrderStatus.PENDING)

    @model_validator(mode='after')
    def check_time_window(self) -> 'Order':
        if self.time_window_start >= self.time_window_end:
            raise ValueError("time_window_end must be strictly after time_window_start")
        if self.created_at > self.time_window_start:
            raise ValueError("created_at cannot be after time_window_start")
        return self


class Vehicle(BaseModel):
    vehicle_id: str = Field(..., description="Unique identifier for the vehicle")
    capacity: float = Field(..., gt=0.0, description="Maximum carrying capacity")
    vehicle_type: VehicleType
    fuel_efficiency: float = Field(..., gt=0.0, description="Fuel efficiency metric")
    available_from: datetime
    available_until: datetime
    current_lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    current_lng: Optional[float] = Field(default=None, ge=-180.0, le=180.0)

    @model_validator(mode='after')
    def check_availability_window(self) -> 'Vehicle':
        if self.available_from >= self.available_until:
            raise ValueError("available_until must be strictly after available_from")
        return self


class Route(BaseModel):
    route_id: str = Field(..., description="Unique identifier for the route")
    vehicle_id: str = Field(..., description="FK to Vehicle")
    ordered_stops: List[str] = Field(..., description="List of Order IDs in visitation order")
    predicted_arrival_times: List[datetime] = Field(..., description="Estimated arrival time at each stop")
    total_distance_km: float = Field(..., ge=0.0)
    total_predicted_time_min: float = Field(..., ge=0.0)
    total_cost: float = Field(..., ge=0.0)
    optimizer_run_id: str = Field(..., description="Identifier for the optimization run that produced this route")

    @model_validator(mode='after')
    def check_stops_match_predictions(self) -> 'Route':
        if len(self.ordered_stops) != len(self.predicted_arrival_times):
            raise ValueError("Length of ordered_stops must match predicted_arrival_times")
        return self


class Prediction(BaseModel):
    order_id: str = Field(..., description="FK to Order")
    predicted_time_p10: float = Field(..., ge=0.0, description="10th percentile predicted delivery time in minutes")
    predicted_time_p50: float = Field(..., ge=0.0, description="50th percentile (median) predicted delivery time")
    predicted_time_p90: float = Field(..., ge=0.0, description="90th percentile predicted delivery time")
    model_version: str = Field(..., description="Version identifier of the ML model used")
    shap_top_features: Dict[str, Any] = Field(default_factory=dict, description="JSON representing top SHAP features")

    @model_validator(mode='after')
    def check_percentiles_order(self) -> 'Prediction':
        if not (self.predicted_time_p10 <= self.predicted_time_p50 <= self.predicted_time_p90):
            raise ValueError("Predictions must be strictly ordered: p10 <= p50 <= p90")
        return self
