# app/db/base.py
# Import all models here for Alembic to detect them
from app.db.session import Base
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.food import Food
from app.models.order import Order, OrderItem
from app.models.post import Post, PostLike, PostComment
