"""Position service — weight system, level computation, CRUD."""

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.level_threshold import LevelThreshold
from app.models.position import Position
from app.repositories.base_repo import BaseRepository
from app.schemas.position import PositionCreate, PositionUpdate, LevelThresholdUpdate

logger = structlog.get_logger()

_DEFAULT_LEVEL = 5  # fallback if weight exceeds all configured thresholds


class PositionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BaseRepository(Position, session)
        self.threshold_repo = BaseRepository(LevelThreshold, session)

    # ── Level computation ──────────────────────────────────────────────

    async def _compute_level(self, weight: int) -> int:
        """Return level_number for given weight using hr_level_thresholds."""
        stmt = (
            select(LevelThreshold)
            .where(LevelThreshold.weight_from <= weight)
            .where(LevelThreshold.weight_to >= weight)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        threshold = result.scalar_one_or_none()
        return threshold.level_number if threshold else _DEFAULT_LEVEL

    async def _assert_weight_free(self, weight: int, exclude_id: int | None = None) -> None:
        """Warn (not block) if weight already taken; raise 409 only on exact collision."""
        stmt = select(Position).where(Position.weight == weight)
        if exclude_id:
            stmt = stmt.where(Position.id != exclude_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Weight {weight} is already taken by position '{existing.title}' (id={existing.id}). "
                       "Choose a different weight or update the existing position first.",
            )

    # ── CRUD ───────────────────────────────────────────────────────────

    async def list_positions(
        self, *, page: int = 1, limit: int = 20
    ) -> tuple[list[Position], int]:
        offset = (page - 1) * limit
        items, total = await self.repo.list(offset=offset, limit=limit, order_by="weight")
        return list(items), total

    async def get_position(self, id: int) -> Position:
        pos = await self.repo.get(id)
        if not pos:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        return pos

    async def create_position(self, data: PositionCreate) -> Position:
        await self._assert_weight_free(data.weight)
        level = await self._compute_level(data.weight)
        payload = data.model_dump()
        payload["level"] = level
        pos = await self.repo.create(payload)
        logger.info("position_created", position_id=pos.id, weight=pos.weight, level=pos.level)
        return pos

    async def update_position(self, id: int, data: PositionUpdate) -> Position:
        pos = await self.get_position(id)
        patch = data.model_dump(exclude_none=True)
        if "weight" in patch:
            await self._assert_weight_free(patch["weight"], exclude_id=id)
            patch["level"] = await self._compute_level(patch["weight"])
        updated = await self.repo.update(pos, patch)
        logger.info("position_updated", position_id=id)
        return updated

    async def delete_position(self, id: int) -> None:
        pos = await self.get_position(id)
        await self.repo.delete(pos)
        logger.info("position_deleted", position_id=id)

    # ── Weight endpoint ────────────────────────────────────────────────

    async def update_weight(self, id: int, weight: int) -> Position:
        pos = await self.get_position(id)
        await self._assert_weight_free(weight, exclude_id=id)
        level = await self._compute_level(weight)
        updated = await self.repo.update(pos, {"weight": weight, "level": level})
        logger.info("position_weight_updated", position_id=id, weight=weight, level=level)
        return updated

    # ── Level thresholds ───────────────────────────────────────────────

    async def list_thresholds(self) -> list[LevelThreshold]:
        items, _ = await self.threshold_repo.list(limit=100, order_by="level_number")
        return list(items)

    async def update_threshold(self, level_number: int, data: LevelThresholdUpdate) -> LevelThreshold:
        stmt = select(LevelThreshold).where(LevelThreshold.level_number == level_number)
        result = await self.session.execute(stmt)
        threshold = result.scalar_one_or_none()
        if not threshold:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Level threshold {level_number} not found",
            )
        if data.weight_from > data.weight_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="weight_from must be <= weight_to",
            )
        updated = await self.threshold_repo.update(threshold, data.model_dump(exclude_none=True))
        # Recompute level for all positions affected by this threshold change
        await self._recompute_levels_in_range(data.weight_from, data.weight_to)
        logger.info("level_threshold_updated", level_number=level_number)
        return updated

    async def _recompute_levels_in_range(self, weight_from: int, weight_to: int) -> None:
        """Recompute cached level for positions whose weight falls in the changed range."""
        stmt = select(Position).where(
            Position.weight >= weight_from,
            Position.weight <= weight_to,
        )
        result = await self.session.execute(stmt)
        positions = result.scalars().all()
        for pos in positions:
            new_level = await self._compute_level(pos.weight)
            if new_level != pos.level:
                pos.level = new_level
                self.session.add(pos)
        if positions:
            await self.session.flush()
