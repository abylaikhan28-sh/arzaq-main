# app/schemas/food.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Base schema
class FoodBase(BaseModel):
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    price: float
    old_price: Optional[float] = None
    discount: Optional[int] = None
    quantity: int
    expires_at: datetime


# Schema for creating food
class FoodCreate(FoodBase):
    restaurant_id: int


# Schema for updating food
class FoodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = None
    old_price: Optional[float] = None
    discount: Optional[int] = None
    quantity: Optional[int] = None
    expires_at: Optional[datetime] = None


# Schema for response
class FoodResponse(FoodBase):
    id: int
    restaurant_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schema for food with restaurant info
class FoodWithRestaurant(FoodResponse):
    restaurant_name: str
    restaurant_address: str
