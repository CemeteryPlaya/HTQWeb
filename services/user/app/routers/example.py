"""
Example router — demonstrates JWT auth, DB access, and circuit breaker pattern.
Replace this with your actual service endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session


router = APIRouter(prefix="/api/user", tags=["user"])


class ExampleResponse(BaseModel):
    id: int
    name: str
    owner_id: int


@router.get("/", response_model=list[ExampleResponse])
async def list_items(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    List all items owned by the current user.
    Demonstrates: JWT auth + DB session injection.
    """
    # TODO: Replace with actual query
    # result = await db.execute(
    #     select(Item).where(Item.owner_id == current_user.user_id)
    # )
    # items = result.scalars().all()
    return []


@router.post("/", response_model=ExampleResponse, status_code=201)
async def create_item(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Create a new item.
    Demonstrates: JWT auth + DB session + POST handling.
    """
    # TODO: Replace with actual creation logic
    return ExampleResponse(id=1, name="example", owner_id=current_user.user_id)
