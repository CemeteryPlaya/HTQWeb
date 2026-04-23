"""OAuth API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.email import OAuthToken
from app.schemas.email import OAuthTokenRead

router = APIRouter(tags=["oauth"])


@router.get("/accounts", response_model=list[OAuthTokenRead])
async def list_accounts(
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """List connected email accounts."""
    stmt = select(OAuthToken).where(OAuthToken.user_id == user.user_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/connect/{provider}")
async def connect_account(
    provider: str,
    # In reality, needs code/state from OAuth flow
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """Initiate or complete OAuth connection."""
    # Stub implementation
    return {"status": "redirect", "url": f"https://{provider}.com/oauth/v2/auth..."}
