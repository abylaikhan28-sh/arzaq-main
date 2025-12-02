# app/schemas/post.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# Post schemas
class PostBase(BaseModel):
    text: str
    image: Optional[str] = None
    location: Optional[str] = None
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    restaurant_address: Optional[str] = None


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None


class PostResponse(PostBase):
    id: int
    author_id: int
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0

    class Config:
        from_attributes = True


# Like schemas
class LikeResponse(BaseModel):
    success: bool
    is_liked: bool
    likes_count: int


# Comment schemas
class CommentBase(BaseModel):
    text: str


class CommentCreate(CommentBase):
    pass


class CommentResponse(CommentBase):
    id: int
    post_id: int
    author_id: int
    author_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Post with details
class PostWithDetails(PostResponse):
    author_name: str
    is_liked: bool = False
    comments: List[CommentResponse] = []
