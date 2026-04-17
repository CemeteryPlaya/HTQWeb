"""Project version (roadmap) model."""

import enum
from typing import ClassVar
from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class VersionStatus(enum.StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    RELEASED = "released"
    ARCHIVED = "archived"


class ProjectVersion(BaseModel):
    """Project version/release for roadmap management."""

    __tablename__ = "project_versions"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[VersionStatus] = mapped_column(
        PG_ENUM(VersionStatus, create_type=False),
        nullable=False,
        default=VersionStatus.PLANNED,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Denormalized fields for API responses
    task_count: ClassVar[int] = 0
    done_count: ClassVar[int] = 0
    progress: ClassVar[float] = 0.0
    effective_release_date: ClassVar[date | None] = None

    # Relationships
    tasks = relationship("Task", back_populates="version")
