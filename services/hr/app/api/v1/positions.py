"""Positions API router."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, TokenPayload
from app.models.position import Position
from app.repositories.base_repo import BaseRepository
from app.schemas.position import PositionCreate, PositionUpdate, PositionOut
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/positions", tags=["positions"])


def _repo(db: AsyncSession = Depends(get_db_session)) -> BaseRepository[Position]:
    return BaseRepository(Position, db)


@router.get("/", response_model=PaginatedResponse[PositionOut])
async def list_positions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    repo: BaseRepository[Position] = Depends(_repo),
    _: TokenPayload = Depends(get_current_user),
):
    offset = (page - 1) * limit
    items, total = await repo.list(offset=offset, limit=limit, order_by="title")
    pages = (total + limit - 1) // limit
    return PaginatedResponse(items=list(items), total=total, page=page, pages=pages, limit=limit)


@router.post("/", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def create_position(
    body: PositionCreate,
    repo: BaseRepository[Position] = Depends(_repo),
    _: TokenPayload = Depends(get_current_user),
):
    return await repo.create(body.model_dump())


@router.get("/{id}/", response_model=PositionOut)
async def get_position(
    id: int,
    repo: BaseRepository[Position] = Depends(_repo),
    _: TokenPayload = Depends(get_current_user),
):
    from fastapi import HTTPException
    pos = await repo.get(id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return pos


@router.put("/{id}/", response_model=PositionOut)
async def update_position(
    id: int,
    body: PositionUpdate,
    repo: BaseRepository[Position] = Depends(_repo),
    _: TokenPayload = Depends(get_current_user),
):
    from fastapi import HTTPException
    pos = await repo.get(id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return await repo.update(pos, body.model_dump(exclude_none=True))


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    id: int,
    repo: BaseRepository[Position] = Depends(_repo),
    _: TokenPayload = Depends(get_current_user),
):
    from fastapi import HTTPException
    pos = await repo.get(id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    await repo.delete(pos)
