"""Admin-only: список всех комнат, сообщения в комнате (для moderation audit)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, require_admin
from app.db import get_db_session
from app.models.domain import Room, Message

router = APIRouter(tags=["admin"])

@router.get("/rooms")
async def list_all_rooms(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _admin: Annotated[TokenPayload, Depends(require_admin)],
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
): 
    result = await session.execute(select(Room).offset(offset).limit(limit))
    return result.scalars().all()

@router.get("/rooms/{room_id}/messages")
async def list_messages_in_room(
    room_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _admin: Annotated[TokenPayload, Depends(require_admin)],
): 
    result = await session.execute(select(Message).where(Message.room_id == room_id))
    return result.scalars().all()
