"""Shareable links API — authenticated management endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, TokenPayload
from app.services.share_link_service import ShareLinkService

router = APIRouter(prefix="/share-links", tags=["share-links"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> ShareLinkService:
    return ShareLinkService(db)


class LinkCreate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    max_level: int = Field(default=3, ge=1, le=10)
    visible_units: list[int] | None = None
    link_type: Literal["one_time", "time_limited", "permanent_with_expiry"] = "one_time"
    expires_at: datetime | None = None


class LinkOut(BaseModel):
    id: uuid.UUID
    token: str
    label: str | None
    max_level: int
    link_type: str
    expires_at: datetime | None
    opened_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(
    body: LinkCreate,
    svc: ShareLinkService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    return await svc.create_link(current_user.user_id, body.model_dump())


@router.get("/", response_model=list[LinkOut])
async def list_links(
    svc: ShareLinkService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    return await svc.list_links(current_user.user_id)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_link(
    link_id: uuid.UUID,
    svc: ShareLinkService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    await svc.revoke_link(link_id, current_user.user_id)
