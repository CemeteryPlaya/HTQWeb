"""ShareableLink — one-time/time-limited public org access links."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShareableLink(Base):
    __tablename__ = "hr_shareable_links"
    __table_args__ = (
        CheckConstraint(
            "link_type IN ('one_time','time_limited','permanent_with_expiry')",
            name="ck_link_type",
        ),
        CheckConstraint("max_level >= 1", name="ck_link_max_level"),
        Index("ix_shareable_links_token", "token", unique=True),
        Index("ix_shareable_links_user", "created_by_user_id"),
        Index("ix_shareable_links_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200))
    max_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    visible_units: Mapped[list | None] = mapped_column(JSON)
    link_type: Mapped[str] = mapped_column(String(30), nullable=False, default="one_time")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_by_ip: Mapped[str | None] = mapped_column(String(45))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<ShareableLink(token='{self.token[:8]}…', type='{self.link_type}', active={self.is_active})>"
