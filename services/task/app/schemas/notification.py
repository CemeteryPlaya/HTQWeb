"""Notification schemas."""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    recipient_id: int
    actor_id: int | None = None
    actor_name: str | None = None
    verb: str
    task_id: int | None = None
    task_key: str | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
