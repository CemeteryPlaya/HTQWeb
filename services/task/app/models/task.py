"""Task model with FSM status transitions and business logic."""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
    Table,
    Column,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from .activity import TaskActivity
    from .attachment import TaskAttachment
    from .comment import TaskComment
    from .link import TaskLink


class Status(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"


class Priority(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class TaskType(enum.StrEnum):
    TASK = "task"
    BUG = "bug"
    STORY = "story"
    EPIC = "epic"
    SUBTASK = "subtask"


# FSM transitions: from_state -> allowed target states
TRANSITIONS = {
    Status.OPEN: {Status.IN_PROGRESS, Status.CLOSED},
    Status.IN_PROGRESS: {Status.IN_REVIEW, Status.DONE, Status.OPEN},
    Status.IN_REVIEW: {Status.DONE, Status.IN_PROGRESS},
    Status.DONE: {Status.CLOSED, Status.IN_PROGRESS},
    Status.CLOSED: {Status.OPEN},
}


task_labels = Table(
    "task_labels",
    BaseModel.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Task(BaseModel):
    """Main task entity with lifecycle management."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR start_date <= due_date",
            name="ck_task_dates",
        ),
    )

    # Core fields
    key: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Classification
    task_type: Mapped[TaskType] = mapped_column(
        PG_ENUM(TaskType, create_type=False),
        nullable=False,
        default=TaskType.TASK,
    )
    priority: Mapped[Priority] = mapped_column(
        PG_ENUM(Priority, create_type=False),
        nullable=False,
        default=Priority.MEDIUM,
    )
    status: Mapped[Status] = mapped_column(
        PG_ENUM(Status, create_type=False),
        nullable=False,
        default=Status.OPEN,
        index=True,
    )

    # Assignments
    reporter_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_users.id", ondelete="SET NULL"), index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_users.id", ondelete="SET NULL"), index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_departments.id", ondelete="SET NULL"), index=True
    )
    version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project_versions.id", ondelete="SET NULL"), index=True
    )

    # Hierarchy
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )

    # Dates
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_working_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Soft delete (mirrors Django SoftDeleteMixin)
    is_deleted: Mapped[bool] = mapped_column(
        default=False, server_default="false", index=True
    )

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    department = relationship("Department")
    version = relationship("ProjectVersion")
    parent = relationship("Task", remote_side="Task.id", backref="subtasks")

    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="task", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["TaskAttachment"]] = relationship(
        "TaskAttachment", back_populates="task", cascade="all, delete-orphan"
    )
    activities: Mapped[list["TaskActivity"]] = relationship(
        "TaskActivity", back_populates="task", cascade="all, delete-orphan"
    )
    outgoing_links: Mapped[list["TaskLink"]] = relationship(
        "TaskLink",
        foreign_keys="TaskLink.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[list["TaskLink"]] = relationship(
        "TaskLink",
        foreign_keys="TaskLink.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    labels = relationship(
        "Label",
        secondary="task_labels",
        back_populates="tasks",
    )

    # FSM validation
    def can_transition_to(self, target: Status) -> bool:
        """Check if task can transition to target status."""
        return target in TRANSITIONS.get(self.status, set())

    def apply_transition(self, target: Status) -> None:
        """Apply status transition with validation."""
        if not self.can_transition_to(target):
            raise ValueError(
                f"Cannot transition from {self.status} to {target}. "
                f"Allowed: {TRANSITIONS.get(self.status, set())}"
            )
        self.status = target
        if target in (Status.DONE, Status.CLOSED) and not self.completed_at:
            self.completed_at = datetime.utcnow()
