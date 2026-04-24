"""
User profile endpoints — read/update own profile.

Replaces Django's ProfileViewSet. The response shape matches what the
React SPA expects (camelCase aliases, `roles`, `fio`, etc.), so no frontend
changes are needed to light up the post-login page.
"""

import json
import logging
from typing import Annotated

import httpx
import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.db import get_db_session
from app.models.user import User
from app.services.auth_service import hash_password, verify_password
from app.services.service_tokens import issue_service_token


log = structlog.get_logger(__name__)


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


class ChangePasswordRequest(BaseModel):
    """Change-password payload.

    ``current_password`` is required for ordinary voluntary changes. When
    ``User.must_change_password`` is true (admin-forced reset), the current
    password check is relaxed so the blocked user can escape the force-screen.
    """

    new_password: str = Field(..., min_length=8)
    current_password: str | None = None


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
    log.info("profile_requested", user_id=user.id)
    return _build_response(user)


@router.patch("/me", response_model=ProfileResponse)
@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    # Profile fields — any combination may be present. Accept both snake_case
    # and camelCase aliases because the frontend mixes both.
    display_name: Annotated[str | None, Form()] = None,
    firstName: Annotated[str | None, Form(alias="firstName")] = None,
    first_name: Annotated[str | None, Form()] = None,
    lastName: Annotated[str | None, Form(alias="lastName")] = None,
    last_name: Annotated[str | None, Form()] = None,
    patronymic: Annotated[str | None, Form()] = None,
    bio: Annotated[str | None, Form()] = None,
    phone: Annotated[str | None, Form()] = None,
    settings_json: Annotated[str | None, Form(alias="settings")] = None,
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Patch the current user's profile.

    Content-Type: multipart/form-data (the frontend sends FormData so it can
    optionally attach an avatar file). When ``avatar`` is present, the file is
    forwarded to media-service via an S2S JWT (``SERVICE_JWT_SECRET``) and the
    returned download URL is persisted to ``user.avatar_url``.
    """
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes: dict = {}

    # Name fields — coalesce camelCase aliases, then diff against current values.
    effective_first = firstName if firstName is not None else first_name
    effective_last = lastName if lastName is not None else last_name

    for field, value in [
        ("display_name", display_name),
        ("first_name", effective_first),
        ("last_name", effective_last),
        ("patronymic", patronymic),
        ("bio", bio),
        ("phone", phone),
    ]:
        if value is not None and getattr(user, field, None) != value:
            changes[field] = {"from": getattr(user, field, None), "to": value}
            setattr(user, field, value)

    if settings_json is not None:
        try:
            parsed = json.loads(settings_json) if settings_json else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="settings must be valid JSON")
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="settings must be a JSON object")
        if parsed != (user.settings or {}):
            changes["settings"] = "updated"
            user.settings = parsed

    # Avatar upload: forward to media-service with an S2S JWT + X-User-Id header.
    if avatar is not None and avatar.filename:
        data = await avatar.read()
        token = issue_service_token()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.media_service_url}/api/media/v1/files/",
                    files={
                        "file": (
                            avatar.filename,
                            data,
                            avatar.content_type or "application/octet-stream",
                        ),
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-User-Id": str(user.id),
                    },
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.error(
                "avatar_upload_failed",
                user_id=user.id,
                error=repr(exc),
                status=getattr(getattr(exc, "response", None), "status_code", None),
            )
            raise HTTPException(
                status_code=502,
                detail="Avatar upload failed (media-service unavailable)",
            )

        body = resp.json()
        # media-service returns computed `url` plus `id`/`path`.
        new_url = body.get("url") or f"/api/media/v1/files/{body['id']}"
        changes["avatar_url"] = {"from": user.avatar_url, "to": new_url}
        user.avatar_url = new_url

    if changes:
        await db.flush()

    await db.commit()
    await db.refresh(user)

    log.info(
        "profile_updated",
        user_id=user.id,
        fields=list(changes.keys()),
        via_multipart=True,
    )
    return _build_response(user)


@router.post("/change-password", status_code=200)
@router.post("/change-password/", status_code=200)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Change the current user's password.

    If ``must_change_password`` flag is set (forced reset), ``current_password``
    is optional; otherwise it must match the stored hash.
    """
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.must_change_password:
        if not payload.current_password or not verify_password(
            payload.current_password, user.password_hash
        ):
            log.info("password_change_rejected", user_id=user.id, reason="wrong_current")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    await db.commit()

    log.info(
        "password_changed",
        user_id=user.id,
        forced=not bool(payload.current_password),
    )
    return {"detail": "Password changed successfully"}
