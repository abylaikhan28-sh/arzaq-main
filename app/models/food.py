# app/models/food.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    # Basic Info
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(String, nullable=True)  # Cloudinary URL

    # Pricing
    price = Column(Float, nullable=False)  # Discounted price
    old_price = Column(Float, nullable=True)  # Original price
    discount = Column(Integer, nullable=True)  # Discount percentage

    # Availability
    quantity = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # When the food expires

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="foods")
    order_items = relationship("OrderItem", back_populates="food")

    def __repr__(self):
        return f"<Food {self.name}>"
