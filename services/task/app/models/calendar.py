"""Calendar event models."""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CalendarEvent(BaseModel):
    """Event in the production calendar."""
    __tablename__ = "calendar_events"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    exceptions: Mapped[list["EventException"]] = relationship(
        "EventException", back_populates="event", cascade="all, delete-orphan"
    )


class EventException(BaseModel):
    """Exceptions to recurring calendar events."""
    __tablename__ = "event_exceptions"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    event: Mapped["CalendarEvent"] = relationship("CalendarEvent", back_populates="exceptions")
