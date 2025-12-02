# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse, UserMe, Token, GoogleAuthRequest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user
)

router = APIRouter()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


async def verify_google_token(token: str) -> dict:
    """Verify Google OAuth token and return user info"""
    try:
        # For access tokens, we need to make a request to Google's userinfo endpoint
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token"
                )

            user_info = response.json()

            return {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "google_id": user_info.get("sub"),
                "email_verified": user_info.get("email_verified", False)
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to verify Google token: {str(e)}"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with email and password"""

    # Find user by email (form_data.username contains email)
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserMe)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.post("/google/login", response_model=Token)
async def google_login(google_data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Login with Google OAuth"""

    # Verify Google token and get user info
    user_info = await verify_google_token(google_data.token)

    # Find user by email or google_id
    user = db.query(User).filter(
        (User.email == user_info["email"]) | (User.google_id == user_info["google_id"])
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first."
        )

    # Update google_id if not set
    if not user.google_id:
        user.google_id = user_info["google_id"]
        db.commit()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def google_register(google_data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Register a new user with Google OAuth"""

    # Verify Google token and get user info
    user_info = await verify_google_token(google_data.token)

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_info["email"]) | (User.google_id == user_info["google_id"])
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or Google account already exists"
        )

    # Create new user with Google OAuth
    new_user = User(
        email=user_info["email"],
        full_name=user_info["name"],
        google_id=user_info["google_id"],
        hashed_password=None,  # No password for Google OAuth users
        role=google_data.role,
        is_verified=user_info["email_verified"]  # Trust Google's email verification
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token = create_access_token(data={"sub": new_user.id})

    return {"access_token": access_token, "token_type": "bearer"}
