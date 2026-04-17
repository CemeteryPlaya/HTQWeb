"""Task schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.task import Status, Priority, TaskType
from app.schemas.label import LabelResponse
from app.schemas.comment import CommentResponse
from app.schemas.attachment import AttachmentResponse
from app.schemas.activity import ActivityResponse
from app.schemas.link import LinkResponse
from app.schemas.common import DateWarning


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    summary: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    task_type: TaskType = Field(default=TaskType.TASK)
    priority: Priority = Field(default=Priority.MEDIUM)
    status: Status = Field(default=Status.OPEN)

    reporter_id: int | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    version_id: int | None = None
    parent_id: int | None = None

    label_ids: list[int] = Field(default=[])

    due_date: date | None = None
    start_date: date | None = None
    estimated_working_days: int | None = None

    @field_validator("summary")
    @classmethod
    def summary_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Summary cannot be blank")
        return v


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    summary: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    task_type: TaskType | None = None
    priority: Priority | None = None
    status: Status | None = None

    reporter_id: int | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    version_id: int | None = None
    parent_id: int | None = None

    label_ids: list[int] | None = None

    due_date: date | None = None
    start_date: date | None = None
    estimated_working_days: int | None = None


class TaskListResponse(BaseModel):
    """Compact task response for list views."""

    id: int
    key: str
    summary: str
    task_type: TaskType
    priority: Priority
    status: Status

    reporter_id: int | None = None
    reporter_name: str | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    version_id: int | None = None
    version_name: str | None = None
    parent_id: int | None = None
    parent_key: str | None = None

    labels: list[LabelResponse] = []
    due_date: date | None = None
    start_date: date | None = None
    effective_start_date: date | None = None
    effective_due_date: date | None = None
    date_warnings: list[DateWarning] = []
    completed_at: datetime | None = None

    subtask_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailResponse(BaseModel):
    """Detailed task response with nested data."""

    id: int
    key: str
    summary: str
    description: str
    task_type: TaskType
    priority: Priority
    status: Status

    reporter_id: int | None = None
    reporter_name: str | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    version_id: int | None = None
    version_name: str | None = None
    parent_id: int | None = None
    parent_key: str | None = None

    labels: list[LabelResponse] = []
    label_ids: list[int] = Field(default=[], description="Write-only label IDs")

    due_date: date | None = None
    start_date: date | None = None
    effective_start_date: date | None = None
    effective_due_date: date | None = None
    date_warnings: list[DateWarning] = []
    completed_at: datetime | None = None

    comments: list[CommentResponse] = []
    attachments: list[AttachmentResponse] = []
    subtasks: list["TaskListResponse"] = []
    activities: list[ActivityResponse] = []
    outgoing_links: list[LinkResponse] = []
    incoming_links: list[LinkResponse] = []

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskStats(BaseModel):
    """Task statistics."""

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_type: dict[str, int]
    by_department: list[dict]
    by_assignee: list[dict]
    created_per_day: list[dict]
    resolved_per_day: list[dict]
