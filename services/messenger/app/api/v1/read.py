"""Mark-read endpoint — REST counterpart of Socket.IO 'mark_read' event."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.domain import ChatMembership
from app.services.audit import record_action

router = APIRouter(tags=["read"])

@router.post("/rooms/{room_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    room_id: int,
    pts: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> None:
    stmt = (
        update(ChatMembership)
        .where(ChatMembership.room_id == room_id, ChatMembership.user_id == user.user_id)
        .values(
            local_pts=func.greatest(ChatMembership.local_pts, pts),
            last_read_at=func.now(),
            unread_count=0
        )
    )
    await session.execute(stmt)
    await session.commit()
    await record_action(session, user.user_id, "mark_read", "ChatMembership", str(room_id))
