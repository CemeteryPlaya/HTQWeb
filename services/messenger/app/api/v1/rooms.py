"""Room API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.domain import Room, RoomParticipant
from app.schemas.messenger import RoomCreate, RoomRead
from app.services.messenger_service import MessengerService

router = APIRouter(tags=["rooms"])


@router.post("/", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    service = MessengerService(session)
    room = await service.create_room(data, creator_id=user.user_id)
    return room


@router.get("/", response_model=list[RoomRead])
async def list_user_rooms(
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """List rooms the current user is a participant of."""
    stmt = (
        select(Room)
        .join(RoomParticipant)
        .where(RoomParticipant.user_id == user.user_id)
        .options(selectinload(Room.participants).selectinload(RoomParticipant.user))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{room_id}", response_model=RoomRead)
async def get_room(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """Get details of a specific room."""
    # Check if user is in room
    rp = await session.get(RoomParticipant, (room_id, user.user_id))
    if not rp:
        raise HTTPException(status_code=403, detail="Not a participant")

    stmt = select(Room).where(Room.id == room_id).options(
        selectinload(Room.participants).selectinload(RoomParticipant.user)
    )
    result = await session.execute(stmt)
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    return room
