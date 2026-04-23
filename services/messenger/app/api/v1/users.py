"""User Replica API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user, require_admin
from app.db import get_db_session
from app.models.domain import ChatUserReplica
from app.schemas.messenger import UserReplicaRead

router = APIRouter(tags=["users"])


@router.post("/ingest", response_model=UserReplicaRead, status_code=status.HTTP_201_CREATED)
async def ingest_user_replica(
    data: UserReplicaRead,
    session: AsyncSession = Depends(get_db_session),
    # In a real system, this should be secured by an internal service-to-service auth token
    # For now, require admin
    admin: TokenPayload = Depends(require_admin),
):
    """Ingest user data from the central user-service."""
    replica = await session.get(ChatUserReplica, data.id)
    if replica:
        # Update existing
        for k, v in data.model_dump().items():
            setattr(replica, k, v)
    else:
        # Create new
        replica = ChatUserReplica(**data.model_dump())
        session.add(replica)

    await session.commit()
    await session.refresh(replica)
    return replica
