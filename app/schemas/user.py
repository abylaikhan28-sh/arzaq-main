# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from app.models.user import UserRole


# Base schema
class UserBase(BaseModel):
    email: EmailStr
    full_name: str


# Schema for user registration
class UserRegister(UserBase):
    password: str
    role: UserRole = UserRole.CLIENT


# Schema for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Schema for response
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Schema for current user (with more details)
class UserMe(UserResponse):
    google_id: Optional[str] = None


# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
