"""
User profile endpoints — read/update own profile.

Replaces Django's ProfileViewSet. The response shape matches what the
React SPA expects (camelCase aliases, `roles`, `fio`, etc.), so no frontend
changes are needed to light up the post-login page.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db_session
from app.models.user import User


router = APIRouter(prefix="/api/users/v1/profile", tags=["profile"])


def _roles_for(user: User) -> list[str]:
    roles: list[str] = []
    if user.is_superuser:
        roles.append("admin")
    if user.is_staff and not user.is_superuser:
        roles.append("staff")
    if not roles:
        roles.append("user")
    return roles


def _build_response(user: User) -> "ProfileResponse":
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    patronymic = user.patronymic or ""
    fio_parts = [p for p in (last_name, first_name, patronymic) if p]
    fio = " ".join(fio_parts)
    return ProfileResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        first_name=first_name,
        last_name=last_name,
        firstName=first_name,
        lastName=last_name,
        patronymic=patronymic,
        display_name=user.display_name or "",
        fio=fio,
        bio=user.bio or "",
        phone=user.phone or "",
        avatar_url=user.avatar_url,
        avatarUrl=user.avatar_url,
        settings=user.settings or {},
        roles=_roles_for(user),
        department=None,
        department_id=None,
        position=None,
        must_change_password=bool(user.must_change_password),
        date_joined=user.date_joined.isoformat() if user.date_joined else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


class ProfileResponse(BaseModel):
    # Identity
    id: str
    username: str
    email: str

    # Name fields — both snake_case (DB) and camelCase (frontend) on the wire.
    first_name: str
    last_name: str
    firstName: str
    lastName: str
    patronymic: str
    display_name: str
    fio: str

    # Profile content
    bio: str
    phone: str
    avatar_url: str | None
    avatarUrl: str | None
    settings: dict

    # Roles + org
    roles: list[str]
    department: str | None
    department_id: int | None
    position: str | None

    # Flags + timestamps
    must_change_password: bool
    date_joined: str | None
    last_login: str | None
    created_at: str | None
    updated_at: str | None


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    firstName: str | None = None
    lastName: str | None = None
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
    """Return the current user's profile (frontend-compatible shape)."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _build_response(user)


@router.patch("/me", response_model=ProfileResponse)
@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Patch the current user's profile. Accepts both snake_case and camelCase keys."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    payload = request.model_dump(exclude_unset=True)
    # Coalesce camelCase aliases into the underlying column names.
    if "firstName" in payload:
        payload["first_name"] = payload.pop("firstName")
    if "lastName" in payload:
        payload["last_name"] = payload.pop("lastName")

    for field, value in payload.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return _build_response(user)
