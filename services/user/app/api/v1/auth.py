"""
Authentication endpoints — JWT token issuance.

Replaces Django's SafeTokenObtainPairView and TokenRefreshView.
This is the entry point for all platform authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models.user import User, UserStatus
from app.services.auth_service import (
    TokenPair,
    create_token_pair,
    decode_token,
    verify_password,
)


router = APIRouter(prefix="/api/token", tags=["auth"])


class TokenObtainRequest(BaseModel):
    """Login request — email or username + password."""
    email: str  # Primary login identifier (was 'username' in Django)
    password: str


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""
    refresh: str


class TokenResponse(BaseModel):
    access: str
    refresh: str
    token_type: str = "Bearer"


class TokenRefreshResponse(BaseModel):
    access: str
    token_type: str = "Bearer"


@router.post("/", response_model=TokenResponse)
async def obtain_token(
    request: TokenObtainRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Authenticate user and return JWT pair.

    Replaces Django's SafeTokenObtainPairView.
    Supports login by email (was EmailTokenObtainPairSerializer).
    """
    # Find user by email or username
    result = await db.execute(
        select(User).where(
            (User.email == request.email.lower()) |
            (User.username == request.email)
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not activated",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create JWT pair with custom claims
    tokens = create_token_pair(
        user_id=user.id,
        username=user.username,
        email=user.email,
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
    )

    return TokenResponse(
        access=tokens.access,
        refresh=tokens.refresh,
    )


@router.post("/refresh/", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Refresh an access token using a valid refresh token.

    Replaces Django's TokenRefreshView.
    """
    try:
        payload = decode_token(request.refresh, require_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == payload.user_id))
    user = result.scalar_one_or_none()

    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Issue new token pair
    tokens = create_token_pair(
        user_id=user.id,
        username=user.username,
        email=user.email,
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
    )

    return TokenRefreshResponse(access=tokens.access)
