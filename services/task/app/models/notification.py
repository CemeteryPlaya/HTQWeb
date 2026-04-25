"""Notification model for task-related alerts."""

from typing import ClassVar, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from .task import Task


class Notification(BaseModel):
    """System notification for task events."""

    __tablename__ = "notifications"

    recipient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task_users.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task_users.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    verb: Mapped[str] = mapped_column(String(200), nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])
    task: Mapped["Task | None"] = relationship("Task")

    # Denormalized fields for API responses
    actor_name: ClassVar[str | None] = None
    task_key: ClassVar[str | None] = None
