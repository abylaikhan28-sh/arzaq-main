# app/schemas/restaurant.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from app.models.restaurant import RestaurantStatus


# Base schema
class RestaurantBase(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr
    description: Optional[str] = None
    latitude: float
    longitude: float


# Schema for creating restaurant
class RestaurantCreate(RestaurantBase):
    pass


# Schema for updating restaurant
class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# Schema for response
class RestaurantResponse(RestaurantBase):
    id: int
    owner_id: int
    status: RestaurantStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Schema for rejection
class RestaurantReject(BaseModel):
    reason: str
