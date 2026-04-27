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
from app.workers.actors import user_deactivated, user_upserted


def _replica_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "display_name": user.display_name or "",
        "avatar_url": user.avatar_url,
        "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        "is_active": user.status == UserStatus.ACTIVE,
    }


router = APIRouter(prefix="/api/users/v1/admin/users", tags=["admin-users"])


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    # Name fields — both snake_case (DB) and camelCase (frontend wire format).
    first_name: str
    last_name: str
    firstName: str
    lastName: str
    patronymic: str
    display_name: str
    bio: str
    phone: str
    avatar_url: str | None
    avatarUrl: str | None
    settings: dict
    roles: list[str]
    status: str
    is_staff: bool
    is_superuser: bool
    must_change_password: bool
    date_joined: str
    last_login: str | None
    created_at: str | None
    updated_at: str | None


class AdminUserUpdateRequest(BaseModel):
    # Role / status flags
    is_staff: bool | None = None
    is_superuser: bool | None = None
    status: str | None = None
    must_change_password: bool | None = None
    # Profile fields — admins can edit on a user's behalf (HR /hr/profiles).
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    bio: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    settings: dict | str | None = None  # JSON object or stringified JSON


def _admin_user_response(user: User) -> "AdminUserResponse":
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    roles: list[str] = []
    if user.is_superuser:
        roles.append("admin")
    if user.is_staff and not user.is_superuser:
        roles.append("staff")
    if not roles:
        roles.append("user")
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=first_name,
        last_name=last_name,
        firstName=first_name,
        lastName=last_name,
        patronymic=user.patronymic or "",
        display_name=user.display_name or "",
        bio=user.bio or "",
        phone=user.phone or "",
        avatar_url=user.avatar_url,
        avatarUrl=user.avatar_url,
        settings=user.settings or {},
        roles=roles,
        status=user.status.value if isinstance(user.status, UserStatus) else str(user.status),
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
        must_change_password=bool(user.must_change_password),
        date_joined=user.date_joined.isoformat() if user.date_joined else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


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

    return [_admin_user_response(u) for u in users]


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

    import json as _json

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(user, field, UserStatus(value))
        elif field == "settings" and value is not None:
            # Accept either a dict or a JSON-encoded string for forward-compat
            # with the HR profile editor that posts the field as a string.
            if isinstance(value, str):
                try:
                    parsed = _json.loads(value) if value else {}
                except _json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="settings must be valid JSON")
                if not isinstance(parsed, dict):
                    raise HTTPException(status_code=400, detail="settings must be a JSON object")
                user.settings = parsed
            else:
                user.settings = value
        else:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    if user.status == UserStatus.ACTIVE:
        user_upserted.send(_replica_payload(user))
    else:
        user_deactivated.send({"id": user.id})

    return _admin_user_response(user)
