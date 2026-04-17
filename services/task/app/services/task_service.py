"""Task service layer with business logic."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, Status, TaskType
from app.models.sequence import TaskSequence, ProductionDay
from app.repositories.task_repo import TaskRepository
from app.repositories import (
    CommentRepository,
    AttachmentRepository,
    LinkRepository,
    ActivityRepository,
    LabelRepository,
    NotificationRepository,
)
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskListResponse,
    TaskDetailResponse,
    TaskStats,
)


class TaskService:
    """Business logic for task management."""

    TRACKED_FIELDS = [
        "summary",
        "description",
        "task_type",
        "priority",
        "status",
        "assignee_id",
        "due_date",
        "start_date",
        "estimated_working_days",
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)
        self.comment_repo = CommentRepository(session)
        self.attachment_repo = AttachmentRepository(session)
        self.link_repo = LinkRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.label_repo = LabelRepository(session)
        self.notification_repo = NotificationRepository(session)

    async def create_task(
        self,
        data: TaskCreate,
        user_id: int | None = None,
    ) -> Task:
        """Create a new task with auto-generated key."""
        # Generate unique key
        next_val = await TaskSequence.get_next_value(self.session, "TASK")
        key = f"TASK-{next_val}"

        # Calculate due_date if estimated_working_days provided
        due_date = data.due_date
        if data.estimated_working_days and data.start_date:
            due_date = await self._calculate_due_date(
                data.start_date, data.estimated_working_days
            )

        # Create task
        task = await self.task_repo.create(
            key=key,
            summary=data.summary,
            description=data.description,
            task_type=data.task_type,
            priority=data.priority,
            status=data.status,
            reporter_id=data.reporter_id or user_id,
            assignee_id=data.assignee_id,
            department_id=data.department_id,
            version_id=data.version_id,
            parent_id=data.parent_id,
            due_date=due_date,
            start_date=data.start_date,
            estimated_working_days=data.estimated_working_days,
        )

        # Associate labels
        if data.label_ids:
            labels = await self._get_labels_by_ids(data.label_ids)
            task.labels = labels

        await self.session.flush()

        # Create notification for assignee
        if task.assignee_id:
            await self._create_notification(
                recipient_id=task.assignee_id,
                actor_id=user_id,
                task_id=task.id,
                verb=f"task_assigned:{task.key}",
            )

        return task

    async def update_task(
        self,
        task_id: int,
        data: TaskUpdate,
        user_id: int | None = None,
    ) -> Task:
        """Update task with activity logging and validation."""
        task = await self.task_repo.get_with_relations(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        label_ids = update_data.pop("label_ids", None)

        # Validate status transition
        if "status" in update_data:
            new_status = Status(update_data["status"])
            task.apply_transition(new_status)

            # Notify on status change
            if task.assignee_id:
                await self._create_notification(
                    recipient_id=task.assignee_id,
                    actor_id=user_id,
                    task_id=task.id,
                    verb=f"status_changed:{task.key}",
                )

        # Log activity for tracked fields
        for field_name in self.TRACKED_FIELDS:
            if field_name in update_data:
                old_value = getattr(task, field_name)
                new_value = update_data[field_name]
                if old_value != new_value:
                    await self.activity_repo.create(
                        task_id=task.id,
                        actor_id=user_id,
                        field_name=field_name,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                    )

        # Update task
        await self.task_repo.update(task, **update_data)

        # Update labels if provided
        if label_ids is not None:
            labels = await self._get_labels_by_ids(label_ids)
            task.labels = labels

        # Notify on assignee change
        if "assignee_id" in update_data and update_data["assignee_id"]:
            await self._create_notification(
                recipient_id=update_data["assignee_id"],
                actor_id=user_id,
                task_id=task.id,
                verb=f"task_assigned:{task.key}",
            )

        await self.session.flush()
        return task

    async def delete_task(self, task_id: int) -> None:
        """Soft delete a task."""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.is_deleted = True
        await self.session.flush()

    async def get_available_transitions(self, task_id: int) -> list[Status]:
        """Get available status transitions for a task."""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        from app.models.task import TRANSITIONS

        return list(TRANSITIONS.get(task.status, set()))

    async def _calculate_due_date(
        self, start_date: date, working_days: int
    ) -> date | None:
        """Calculate due date using production calendar."""
        return await ProductionDay.get_date_by_workingDays(
            self.session, start_date, working_days
        )

    async def _get_labels_by_ids(self, label_ids: list[int]):
        """Get labels by IDs."""
        if not label_ids:
            return []
        from sqlalchemy import select
        from app.models.label import Label

        result = await self.session.execute(
            select(Label).where(Label.id.in_(label_ids))
        )
        return list(result.scalars().all())

    async def _create_notification(
        self,
        recipient_id: int,
        actor_id: int | None,
        task_id: int,
        verb: str,
    ) -> None:
        """Create a notification (non-blocking)."""
        try:
            await self.notification_repo.create(
                recipient_id=recipient_id,
                actor_id=actor_id,
                task_id=task_id,
                verb=verb,
            )
        except Exception:
            # Don't fail task creation on notification failure
            pass
