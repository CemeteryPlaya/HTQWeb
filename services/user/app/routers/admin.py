"""
Admin endpoints — user management by admins.

Replaces Django's AdminUserViewSet.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db_session
from app.models.user import User, UserStatus


router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    display_name: str
    status: str
    is_staff: bool
    is_superuser: bool
    date_joined: str
    last_login: str | None


class AdminUserUpdateRequest(BaseModel):
    is_staff: bool | None = None
    is_superuser: bool | None = None
    status: str | None = None
    must_change_password: bool | None = None


@router.get("/", response_model=list[AdminUserResponse])
async def list_users(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    List all users (admin view).
    Requires: staff or superuser.
    """
    if not current_user.is_staff and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    result = await db.execute(select(User).order_by(User.date_joined.desc()))
    users = result.scalars().all()

    return [
        AdminUserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            display_name=u.display_name,
            status=u.status.value if isinstance(u.status, UserStatus) else u.status,
            is_staff=u.is_staff,
            is_superuser=u.is_superuser,
            date_joined=u.date_joined.isoformat(),
            last_login=u.last_login.isoformat() if u.last_login else None,
        )
        for u in users
    ]


@router.patch("/{user_id}/", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Update user admin settings.
    Requires: staff or superuser.
    """
    if not current_user.is_staff and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(user, field, UserStatus(value))
        else:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        status=user.status.value if isinstance(user.status, UserStatus) else user.status,
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
        date_joined=user.date_joined.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )
