# app/api/routes/foods.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from datetime import datetime
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.food import Food
from app.models.restaurant import Restaurant, RestaurantStatus
from app.schemas.food import FoodCreate, FoodUpdate, FoodResponse, FoodWithRestaurant
from app.core.security import get_current_active_user, require_role
from app.services.cloudinary_service import cloudinary_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(
    food_data: FoodCreate,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Create a new food item (restaurant only)"""
    try:
        # Verify restaurant ownership
        restaurant = db.query(Restaurant).filter(
            Restaurant.id == food_data.restaurant_id,
            Restaurant.owner_id == current_user.id
        ).first()

        if not restaurant:
            logger.warning(f"User {current_user.id} attempted to create food for restaurant {food_data.restaurant_id} without ownership")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create food items for your own restaurant"
            )

        if restaurant.status != RestaurantStatus.APPROVED:
            logger.warning(f"Attempt to create food for non-approved restaurant {restaurant.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Restaurant must be approved to create food items"
            )

        # Validate expiration date
        if food_data.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiration date must be in the future"
            )

        # Validate prices
        if food_data.price <= 0 or food_data.old_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prices must be greater than zero"
            )

        if food_data.price >= food_data.old_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discounted price must be less than original price"
            )

        # Create food item
        new_food = Food(**food_data.dict())
        db.add(new_food)
        db.commit()
        db.refresh(new_food)

        logger.info(f"Food item '{new_food.name}' created successfully by restaurant {restaurant.id}")
        return new_food

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating food: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the food item"
        )
    except Exception as e:
        logger.error(f"Unexpected error while creating food: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/", response_model=List[FoodWithRestaurant])
async def get_all_foods(
    restaurant_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all available food items with filters"""
    try:
        query = db.query(
            Food,
            Restaurant.name.label("restaurant_name"),
            Restaurant.address.label("restaurant_address")
        ).join(Restaurant)

        # Filter by restaurant
        if restaurant_id:
            query = query.filter(Food.restaurant_id == restaurant_id)

        # Filter by search term
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Food.name.ilike(search_term),
                    Food.description.ilike(search_term)
                )
            )

        # Only show food that hasn't expired and has quantity > 0
        query = query.filter(
            Food.expires_at > datetime.utcnow(),
            Food.quantity > 0
        ).filter(
            Restaurant.status == RestaurantStatus.APPROVED
        )

        # Apply pagination
        query = query.limit(limit).offset(offset)

        results = query.all()

        # Format response
        food_list = [
            FoodWithRestaurant(
                **food.__dict__,
                restaurant_name=restaurant_name,
                restaurant_address=restaurant_address
            )
            for food, restaurant_name, restaurant_address in results
        ]

        logger.info(f"Retrieved {len(food_list)} food items (limit: {limit}, offset: {offset})")
        return food_list

    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching foods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching food items"
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching foods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/me", response_model=List[FoodResponse])
async def get_my_foods(
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Get current restaurant's food items"""

    # Get restaurant
    restaurant = db.query(Restaurant).filter(
        Restaurant.owner_id == current_user.id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Get all foods for this restaurant
    foods = db.query(Food).filter(
        Food.restaurant_id == restaurant.id
    ).all()

    return foods


@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(food_id: int, db: Session = Depends(get_db)):
    """Get food item by ID"""

    food = db.query(Food).filter(Food.id == food_id).first()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )

    return food


@router.put("/{food_id}", response_model=FoodResponse)
async def update_food(
    food_id: int,
    food_data: FoodUpdate,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Update food item (restaurant only)"""

    # Get food
    food = db.query(Food).filter(Food.id == food_id).first()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )

    # Verify ownership
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == food.restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own food items"
        )

    # Update fields
    update_data = food_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(food, field, value)

    db.commit()
    db.refresh(food)

    return food


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: int,
    current_user: User = Depends(require_role(["restaurant"])),
    db: Session = Depends(get_db)
):
    """Delete food item (restaurant only)"""

    # Get food
    food = db.query(Food).filter(Food.id == food_id).first()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found"
        )

    # Verify ownership
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == food.restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own food items"
        )

    # Delete image from Cloudinary if exists
    if food.image:
        # Extract public_id from URL
        try:
            public_id = food.image.split('/')[-1].split('.')[0]
            cloudinary_service.delete_image(public_id)
        except:
            pass

    db.delete(food)
    db.commit()

    return None


@router.post("/upload-image")
async def upload_food_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["restaurant"]))
):
    """Upload food image to Cloudinary"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Validate file size (max 10MB)
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB
        max_size = 10 * 1024 * 1024  # 10MB

        # Read file in chunks to check size
        await file.seek(0)
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size must not exceed 10MB"
                )

        # Reset file pointer
        await file.seek(0)

        result = await cloudinary_service.upload_image(file, folder="arzaq/foods")

        logger.info(f"Image uploaded successfully by user {current_user.id}: {result['public_id']}")

        return {
            "success": True,
            "url": result["url"],
            "public_id": result["public_id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )
