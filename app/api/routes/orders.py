# app/api/routes/orders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus
from app.models.food import Food
from app.models.restaurant import Restaurant
from app.schemas.order import OrderCreate, OrderResponse, OrderWithItems, OrderUpdate, ImpactStats
from app.core.security import get_current_active_user, require_role

router = APIRouter()


@router.post("/", response_model=OrderWithItems, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(require_role(["client"])),
    db: Session = Depends(get_db)
):
    """Create a new order (customers only)"""

    # Verify restaurant exists
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == order_data.restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Calculate total and verify food availability
    total_amount = 0.0
    order_items_data = []

    for item in order_data.items:
        food = db.query(Food).filter(Food.id == item.food_id).first()

        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food item {item.food_id} not found"
            )

        if food.restaurant_id != order_data.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Food item {item.food_id} does not belong to this restaurant"
            )

        if food.quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough quantity for {food.name}. Available: {food.quantity}"
            )

        if food.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{food.name} has expired"
            )

        item_total = food.price * item.quantity
        total_amount += item_total

        order_items_data.append({
            "food_id": food.id,
            "quantity": item.quantity,
            "price": food.price
        })

        # Decrease food quantity
        food.quantity -= item.quantity

    # Create order
    new_order = Order(
        customer_id=current_user.id,
        restaurant_id=order_data.restaurant_id,
        total_amount=total_amount,
        pickup_time=order_data.pickup_time,
        status=OrderStatus.PENDING
    )

    db.add(new_order)
    db.flush()  # Get order ID

    # Create order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            **item_data
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    return new_order


@router.get("/", response_model=List[OrderWithItems])
async def get_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get orders based on user role"""

    if current_user.role == "client":
        # Customers see their own orders
        orders = db.query(Order).filter(
            Order.customer_id == current_user.id
        ).order_by(Order.created_at.desc()).all()

    elif current_user.role == "restaurant":
        # Restaurants see orders for their restaurant
        restaurant = db.query(Restaurant).filter(
            Restaurant.owner_id == current_user.id
        ).first()

        if not restaurant:
            return []

        orders = db.query(Order).filter(
            Order.restaurant_id == restaurant.id
        ).order_by(Order.created_at.desc()).all()

    elif current_user.role == "admin":
        # Admins see all orders
        orders = db.query(Order).order_by(Order.created_at.desc()).all()

    else:
        orders = []

    return orders


@router.get("/{order_id}", response_model=OrderWithItems)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order by ID"""

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check permissions
    if current_user.role == "client" and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders"
        )

    if current_user.role == "restaurant":
        restaurant = db.query(Restaurant).filter(
            Restaurant.owner_id == current_user.id
        ).first()

        if not restaurant or order.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view orders for your restaurant"
            )

    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderUpdate,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Update order status (restaurant only)"""

    # Get order
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Verify restaurant ownership
    restaurant = db.query(Restaurant).filter(
        Restaurant.owner_id == current_user.id,
        Restaurant.id == order.restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update orders for your restaurant"
        )

    # Update status
    order.status = status_update.status

    if status_update.status == OrderStatus.COMPLETED:
        order.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(order)

    return order


@router.get("/impact/stats", response_model=ImpactStats)
async def get_impact_stats(
    current_user: User = Depends(require_role(["client"])),
    db: Session = Depends(get_db)
):
    """Get user's impact statistics"""

    # Count completed orders
    completed_orders = db.query(Order).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.COMPLETED
    ).count()

    # Calculate total items rescued
    total_items = db.query(func.sum(OrderItem.quantity)).join(Order).filter(
        Order.customer_id == current_user.id,
        Order.status == OrderStatus.COMPLETED
    ).scalar() or 0

    # Calculate CO2 saved (0.18 kg per meal)
    co2_saved = round(total_items * 0.18, 1)

    return {
        "meals_rescued": total_items,
        "co2_saved": co2_saved,
        "meals_goal": 30,
        "co2_goal": 10.0
    }
