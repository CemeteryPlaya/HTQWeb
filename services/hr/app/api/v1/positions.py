"""Positions API router — CRUD + weight system."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, require_hr_write, TokenPayload
from app.services.position_service import PositionService
from app.schemas.position import (
    PositionCreate, PositionUpdate, PositionOut,
    PositionWeightUpdate, LevelThresholdOut, LevelThresholdUpdate,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/positions", tags=["positions"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> PositionService:
    return PositionService(db)


# ── CRUD ──────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedResponse[PositionOut])
async def list_positions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    items, total = await svc.list_positions(page=page, limit=limit)
    pages = (total + limit - 1) // limit
    return PaginatedResponse(items=items, total=total, page=page, pages=pages, limit=limit)


@router.post("/", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def create_position(
    body: PositionCreate,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    return await svc.create_position(body)


@router.get("/{id}/", response_model=PositionOut)
async def get_position(
    id: int,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.get_position(id)


@router.put("/{id}/", response_model=PositionOut)
async def update_position(
    id: int,
    body: PositionUpdate,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    return await svc.update_position(id, body)


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    id: int,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    await svc.delete_position(id)


# ── Weight endpoint (HR_WRITE only) ───────────────────────────────────

@router.patch("/{id}/weight", response_model=PositionOut)
async def update_position_weight(
    id: int,
    body: PositionWeightUpdate,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    """Update position weight; recomputes level automatically."""
    return await svc.update_weight(id, body.weight)


# ── Level thresholds (read all, write admin only) ─────────────────────

@router.get("/levels/", response_model=list[LevelThresholdOut])
async def list_level_thresholds(
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.list_thresholds()


@router.put("/levels/{level_number}", response_model=LevelThresholdOut)
async def update_level_threshold(
    level_number: int,
    body: LevelThresholdUpdate,
    svc: PositionService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    """Update weight range for a level; recomputes affected positions' levels."""
    return await svc.update_threshold(level_number, body)
