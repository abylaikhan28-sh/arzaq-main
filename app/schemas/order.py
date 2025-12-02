# app/schemas/order.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.models.order import OrderStatus


# Order Item schemas
class OrderItemBase(BaseModel):
    food_id: int
    quantity: int


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    price: float
    created_at: datetime

    class Config:
        from_attributes = True


# Order schemas
class OrderBase(BaseModel):
    pickup_time: datetime


class OrderCreate(OrderBase):
    restaurant_id: int
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(OrderBase):
    id: int
    customer_id: int
    restaurant_id: int
    status: OrderStatus
    total_amount: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderWithItems(OrderResponse):
    items: List[OrderItemResponse]


# Impact stats schema
class ImpactStats(BaseModel):
    meals_rescued: int
    co2_saved: float  # kg
    meals_goal: int = 30
    co2_goal: float = 10.0
