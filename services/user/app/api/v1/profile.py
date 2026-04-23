"""
User profile endpoints — read/update own profile.

Replaces Django's ProfileViewSet.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db_session
from app.models.user import User


router = APIRouter(prefix="/api/users/v1/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    patronymic: str
    display_name: str
    bio: str
    phone: str
    avatar_url: str | None
    must_change_password: bool
    date_joined: str
    last_login: str | None


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    display_name: str | None = None
    bio: str | None = None
    phone: str | None = None
    settings: dict | None = None


@router.get("/me", response_model=ProfileResponse)
@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Get the current user's profile.

    Replaces ProfileViewSet.retrieve().
    Exposed at both `/profile/` and `/profile/me` (frontend uses `/me`).
    """
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return ProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        patronymic=user.patronymic,
        display_name=user.display_name,
        bio=user.bio,
        phone=user.phone,
        avatar_url=user.avatar_url,
        must_change_password=user.must_change_password,
        date_joined=user.date_joined.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Update the current user's profile fields.

    Replaces ProfileViewSet.partial_update().
    """
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return ProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        patronymic=user.patronymic,
        display_name=user.display_name,
        bio=user.bio,
        phone=user.phone,
        avatar_url=user.avatar_url,
        must_change_password=user.must_change_password,
        date_joined=user.date_joined.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )
