"""Message API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.domain import Message, RoomParticipant
from app.schemas.messenger import MessageCreate, MessageRead
from app.services.messenger_service import MessengerService

router = APIRouter(tags=["messages"])


@router.post("/", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    service = MessengerService(session)
    try:
        msg = await service.send_message(data, sender_id=user.user_id)
        return msg
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/room/{room_id}", response_model=list[MessageRead])
async def list_messages(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    # Check if user is in room
    rp = await session.get(RoomParticipant, (room_id, user.user_id))
    if not rp:
        raise HTTPException(status_code=403, detail="Not a participant")

    stmt = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(Message.sender))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/room/{room_id}/read/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def mark_message_read(
    room_id: int,
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    service = MessengerService(session)
    try:
        await service.mark_read(room_id, message_id, user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/room/{room_id}/typing", status_code=status.HTTP_204_NO_CONTENT)
async def publish_typing(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    service = MessengerService(session)
    await service.publish_typing(room_id, user.user_id)
