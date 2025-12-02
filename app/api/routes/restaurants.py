# app/api/routes/restaurants.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from datetime import datetime
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.restaurant import Restaurant, RestaurantStatus
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantResponse,
    RestaurantReject
)
from app.core.security import get_current_active_user, require_role

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant_data: RestaurantCreate,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Create a new restaurant (restaurant role only)"""
    try:
        # Check if user already has a restaurant
        existing = db.query(Restaurant).filter(
            Restaurant.owner_id == current_user.id
        ).first()

        if existing:
            logger.warning(f"User {current_user.id} attempted to create duplicate restaurant")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a restaurant registered"
            )

        # Validate coordinates
        if not (-90 <= restaurant_data.latitude <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude must be between -90 and 90"
            )

        if not (-180 <= restaurant_data.longitude <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Longitude must be between -180 and 180"
            )

        # Create restaurant
        new_restaurant = Restaurant(
            **restaurant_data.dict(),
            owner_id=current_user.id,
            status=RestaurantStatus.PENDING
        )

        db.add(new_restaurant)
        db.commit()
        db.refresh(new_restaurant)

        logger.info(f"Restaurant '{new_restaurant.name}' created by user {current_user.id}, status: PENDING")
        return new_restaurant

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating restaurant: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the restaurant"
        )
    except Exception as e:
        logger.error(f"Unexpected error while creating restaurant: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/", response_model=List[RestaurantResponse])
async def get_all_restaurants(
    status_filter: Optional[RestaurantStatus] = Query(None, alias="status"),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(10.0, ge=1.0, le=50.0),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all restaurants with optional filters"""
    try:
        # Validate coordinates if provided
        if latitude is not None and not (-90 <= latitude <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude must be between -90 and 90"
            )

        if longitude is not None and not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Longitude must be between -180 and 180"
            )

        query = db.query(Restaurant)

        # Filter by status
        if status_filter:
            query = query.filter(Restaurant.status == status_filter)
        else:
            # By default, only show approved restaurants
            query = query.filter(Restaurant.status == RestaurantStatus.APPROVED)

        # Filter by location (if provided)
        if latitude and longitude:
            # Simple distance calculation using Pythagorean theorem
            # For production, use PostGIS for accurate geospatial queries
            lat_diff = func.abs(Restaurant.latitude - latitude)
            lng_diff = func.abs(Restaurant.longitude - longitude)
            distance = func.sqrt(lat_diff * lat_diff + lng_diff * lng_diff)

            # Rough conversion: 1 degree ≈ 111 km
            query = query.filter(distance <= (radius_km / 111.0))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        restaurants = query.all()

        logger.info(f"Retrieved {len(restaurants)} restaurants (limit: {limit}, offset: {offset})")
        return restaurants

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching restaurants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching restaurants"
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching restaurants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/pending", response_model=List[RestaurantResponse])
async def get_pending_restaurants(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Get all pending restaurants (admin only)"""

    restaurants = db.query(Restaurant).filter(
        Restaurant.status == RestaurantStatus.PENDING
    ).all()

    return restaurants


@router.get("/me", response_model=RestaurantResponse)
async def get_my_restaurant(
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Get current user's restaurant"""

    restaurant = db.query(Restaurant).filter(
        Restaurant.owner_id == current_user.id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    return restaurant


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Get restaurant by ID"""

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    return restaurant


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    restaurant_data: RestaurantUpdate,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Update restaurant (owner only)"""

    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found or you don't have permission"
        )

    # Update fields
    update_data = restaurant_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(restaurant, field, value)

    db.commit()
    db.refresh(restaurant)

    return restaurant


@router.post("/{restaurant_id}/approve", response_model=RestaurantResponse)
async def approve_restaurant(
    restaurant_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Approve restaurant (admin only)"""

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    if restaurant.status != RestaurantStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is not in pending status"
        )

    restaurant.status = RestaurantStatus.APPROVED
    restaurant.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(restaurant)

    return restaurant


@router.post("/{restaurant_id}/reject", response_model=RestaurantResponse)
async def reject_restaurant(
    restaurant_id: int,
    reject_data: RestaurantReject,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Reject restaurant (admin only)"""

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    if restaurant.status != RestaurantStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is not in pending status"
        )

    restaurant.status = RestaurantStatus.REJECTED
    restaurant.rejection_reason = reject_data.reason

    db.commit()
    db.refresh(restaurant)

    return restaurant


@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant(
    restaurant_id: int,
    current_user: User = Depends(require_role(["admin", "restaurant"])),
    db: Session = Depends(get_db)
):
    """Delete restaurant (admin or owner)"""

    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Check permissions
    if current_user.role != "admin" and restaurant.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this restaurant"
        )

    db.delete(restaurant)
    db.commit()

    return None
