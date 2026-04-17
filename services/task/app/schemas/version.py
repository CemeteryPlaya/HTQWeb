"""Project version schemas."""

import enum
from datetime import date

from pydantic import BaseModel, Field


class VersionStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    RELEASED = "released"
    ARCHIVED = "archived"


class VersionCreate(BaseModel):
    """Schema for creating a project version."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: VersionStatus = Field(default=VersionStatus.PLANNED)
    start_date: date | None = None
    release_date: date | None = None


class VersionUpdate(BaseModel):
    """Schema for updating a project version."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    status: VersionStatus | None = None
    start_date: date | None = None
    release_date: date | None = None


class VersionResponse(BaseModel):
    """Project version response schema."""

    id: int
    name: str
    description: str
    status: VersionStatus
    start_date: date | None
    release_date: date | None
    effective_release_date: date | None = None
    task_count: int = 0
    done_count: int = 0
    progress: float = 0.0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
