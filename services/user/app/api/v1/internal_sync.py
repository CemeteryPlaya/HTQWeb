"""
Internal sync endpoints — for dual-write migration from Django.

These endpoints are NOT exposed through the API Gateway.
They are only accessible from within the Docker network.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models.user import User, UserStatus
from app.services.auth_service import hash_password


router = APIRouter(prefix="/api/users/v1/internal", tags=["internal-sync"])


class ProfileSyncData(BaseModel):
    display_name: str = ""
    bio: str = ""
    patronymic: str = ""
    phone: str = ""
    avatar_url: str | None = None
    settings: dict = {}
    must_change_password: bool = False


class UserSyncRequest(BaseModel):
    """Data from Django for dual-write sync."""
    django_id: int
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = False
    is_staff: bool = False
    is_superuser: bool = False
    date_joined: str
    last_login: str | None = None
    profile: ProfileSyncData


@router.post("/sync-user/", status_code=201)
async def sync_user(
    request: UserSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Create or update a user from Django dual-write sync.

    If user with django_id exists → update.
    If not → create with a placeholder password (will be set on first login).
    """
    # Check if user already exists by django_id
    result = await db.execute(select(User).where(User.id == request.django_id))
    existing_user = result.scalar_one_or_none()

    status = UserStatus.ACTIVE if request.is_active else UserStatus.PENDING

    if existing_user:
        # Update existing user
        existing_user.username = request.username
        existing_user.email = request.email.lower()
        existing_user.first_name = request.first_name
        existing_user.last_name = request.last_name
        existing_user.is_staff = request.is_staff
        existing_user.is_superuser = request.is_superuser
        existing_user.status = status
        existing_user.display_name = request.profile.display_name or existing_user.display_name
        existing_user.bio = request.profile.bio or existing_user.bio
        existing_user.patronymic = request.profile.patronymic or existing_user.patronymic
        existing_user.phone = request.profile.phone or existing_user.phone
        existing_user.avatar_url = request.profile.avatar_url or existing_user.avatar_url
        existing_user.settings = request.profile.settings or existing_user.settings
        existing_user.must_change_password = request.profile.must_change_password

        if request.last_login:
            existing_user.last_login = datetime.fromisoformat(request.last_login)

        await db.commit()
        return {"status": "updated", "id": existing_user.id}

    # Create new user with placeholder password
    # The actual password hash will be synced when user first logs in
    # (the password verification will trigger a re-sync with the real hash)
    user = User(
        id=request.django_id,
        username=request.username,
        email=request.email.lower(),
        password_hash=hash_password("__placeholder_sync__"),  # Will be updated on login
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=request.profile.display_name or f"{request.first_name} {request.last_name}".strip(),
        bio=request.profile.bio,
        patronymic=request.profile.patronymic,
        phone=request.profile.phone,
        avatar_url=request.profile.avatar_url,
        settings=request.profile.settings,
        status=status,
        is_staff=request.is_staff,
        is_superuser=request.is_superuser,
        must_change_password=request.profile.must_change_password,
        date_joined=datetime.fromisoformat(request.date_joined),
        last_login=datetime.fromisoformat(request.last_login) if request.last_login else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(user)
    await db.commit()

    return {"status": "created", "id": user.id}


@router.put("/sync-user/{user_id}/", status_code=200)
async def update_synced_user(
    user_id: int,
    request: UserSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Update an already-synced user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in User Service",
        )

    user.username = request.username
    user.email = request.email.lower()
    user.first_name = request.first_name
    user.last_name = request.last_name
    user.status = UserStatus.ACTIVE if request.is_active else UserStatus.PENDING
    user.is_staff = request.is_staff
    user.is_superuser = request.is_superuser
    user.display_name = request.profile.display_name or user.display_name
    user.bio = request.profile.bio or user.bio
    user.patronymic = request.profile.patronymic or user.patronymic
    user.phone = request.profile.phone or user.phone
    user.avatar_url = request.profile.avatar_url or user.avatar_url
    user.settings = request.profile.settings or user.settings
    user.must_change_password = request.profile.must_change_password

    if request.last_login:
        user.last_login = datetime.fromisoformat(request.last_login)

    await db.commit()
    return {"status": "updated", "id": user.id}
