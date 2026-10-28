"""Typed disruption events accepted by POST /routes/disrupt (PRD 6.2 feedback loop)."""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from src.data_processing.schemas import Order


class NewOrderEvent(BaseModel):
    type: Literal["new_order"]
    order: Order


class CancelOrderEvent(BaseModel):
    type: Literal["cancel_order"]
    order_id: str


class VehicleDownEvent(BaseModel):
    type: Literal["vehicle_down"]
    vehicle_id: str


class TrafficChangeEvent(BaseModel):
    type: Literal["traffic_change"]
    time_multiplier: float = Field(..., gt=0.2, le=5.0, description="1.3 = every leg takes 30% longer")


DisruptionEvent = Annotated[
    Union[NewOrderEvent, CancelOrderEvent, VehicleDownEvent, TrafficChangeEvent], Field(discriminator="type")
]
