"""Task repository with specialized queries."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, Status
from app.repositories.base_repo import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Specialized repository for Task model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Task, session)

    async def get_by_key(self, key: str) -> Task | None:
        """Get task by unique key (e.g., TASK-123)."""
        result = await self.session.execute(
            select(Task)
            .where(Task.key == key, Task.is_deleted == False)
            .options(
                selectinload(Task.comments),
                selectinload(Task.attachments),
                selectinload(Task.labels),
                selectinload(Task.activities),
                selectinload(Task.outgoing_links),
                selectinload(Task.incoming_links),
                selectinload(Task.subtasks),
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, id: int) -> Task | None:
        """Get task with all related data loaded."""
        return await self.session.get(
            Task,
            id,
            options=[
                selectinload(Task.comments),
                selectinload(Task.attachments),
                selectinload(Task.labels),
                selectinload(Task.activities),
                selectinload(Task.outgoing_links),
                selectinload(Task.incoming_links),
                selectinload(Task.subtasks),
            ],
        )

    async def get_list(
        self,
        offset: int = 0,
        limit: int = 100,
        status: Status | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        assignee_id: int | None = None,
        reporter_id: int | None = None,
        department_id: int | None = None,
        version_id: int | None = None,
        parent_id: int | None = None,
        label_id: int | None = None,
        search: str | None = None,
    ) -> list[Task]:
        """Get filtered task list."""
        query = (
            select(Task)
            .where(Task.is_deleted == False)
            .options(
                selectinload(Task.labels),
            )
            .order_by(Task.created_at.desc())
        )

        # Apply filters
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if task_type:
            query = query.where(Task.task_type == task_type)
        if assignee_id is not None:
            query = query.where(Task.assignee_id == assignee_id)
        if reporter_id is not None:
            query = query.where(Task.reporter_id == reporter_id)
        if department_id is not None:
            query = query.where(Task.department_id == department_id)
        if version_id is not None:
            query = query.where(Task.version_id == version_id)
        if parent_id is not None:
            query = query.where(Task.parent_id == parent_id)
        if label_id is not None:
            query = query.where(Task.labels.any(id=label_id))
        if search:
            query = query.where(
                Task.summary.ilike(f"%{search}%")
                | Task.description.ilike(f"%{search}%")
                | Task.key.ilike(f"%{search}%")
            )

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        department_id: int | None = None,
        version_id: int | None = None,
    ) -> dict:
        """Get task statistics."""
        base_filter = Task.is_deleted == False
        if department_id:
            base_filter = base_filter & (Task.department_id == department_id)
        if version_id:
            base_filter = base_filter & (Task.version_id == version_id)

        # Total count
        total_result = await self.session.execute(
            select(func.count(Task.id)).where(base_filter)
        )
        total = total_result.scalar_one()

        # By status
        status_result = await self.session.execute(
            select(Task.status, func.count(Task.id))
            .where(base_filter)
            .group_by(Task.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By priority
        priority_result = await self.session.execute(
            select(Task.priority, func.count(Task.id))
            .where(base_filter)
            .group_by(Task.priority)
        )
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        # By type
        type_result = await self.session.execute(
            select(Task.task_type, func.count(Task.id))
            .where(base_filter)
            .group_by(Task.task_type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        # Created per day (last 30 days)
        thirty_days_ago = datetime.utcnow().date() - date.resolution * 30
        created_daily_result = await self.session.execute(
            select(
                func.date(Task.created_at).label("day"),
                func.count(Task.id),
            )
            .where(base_filter & (Task.created_at >= thirty_days_ago))
            .group_by(func.date(Task.created_at))
            .order_by(func.date(Task.created_at))
        )
        created_per_day = [
            {"day": str(row[0]), "count": row[1]} for row in created_daily_result.all()
        ]

        # Resolved per day (last 30 days)
        resolved_daily_result = await self.session.execute(
            select(
                func.date(Task.completed_at).label("day"),
                func.count(Task.id),
            )
            .where(
                base_filter
                & (Task.completed_at.isnot(None))
                & (Task.completed_at >= thirty_days_ago)
            )
            .group_by(func.date(Task.completed_at))
            .order_by(func.date(Task.completed_at))
        )
        resolved_per_day = [
            {"day": str(row[0]), "count": row[1]} for row in resolved_daily_result.all()
        ]

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_type": by_type,
            "by_department": [],  # Requires GROUP BY department
            "by_assignee": [],  # Requires GROUP BY assignee with user data
            "created_per_day": created_per_day,
            "resolved_per_day": resolved_per_day,
        }
