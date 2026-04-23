"""Schemas for calendar models."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventExceptionBase(BaseModel):
    exception_date: date
    is_cancelled: bool = True


class EventExceptionResponse(EventExceptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int


class CalendarEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    color: Optional[str] = None
    is_global: bool = False
    department_id: Optional[int] = None


class CalendarEventCreate(CalendarEventBase):
    pass


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    color: Optional[str] = None
    is_global: Optional[bool] = None
    department_id: Optional[int] = None


class CalendarEventResponse(CalendarEventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    exceptions: list[EventExceptionResponse] = []
