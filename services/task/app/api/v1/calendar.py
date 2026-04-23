"""Calendar API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.calendar import CalendarEvent, EventException
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    EventExceptionBase,
    EventExceptionResponse,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/", response_model=list[CalendarEventResponse])
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
    department_id: int | None = None,
):
    """List calendar events."""
    stmt = select(CalendarEvent).options(selectinload(CalendarEvent.exceptions))
    if department_id is not None:
        stmt = stmt.where(
            (CalendarEvent.department_id == department_id) | (CalendarEvent.is_global.is_(True))
        )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    data: CalendarEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Create a new calendar event."""
    event = CalendarEvent(**data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.patch("/{event_id}/", response_model=CalendarEventResponse)
async def update_event(
    event_id: int,
    data: CalendarEventUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Update a calendar event."""
    result = await db.execute(
        select(CalendarEvent).where(CalendarEvent.id == event_id).options(selectinload(CalendarEvent.exceptions))
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(event, k, v)
        
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}/", status_code=204)
async def delete_event(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Delete a calendar event."""
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await db.delete(event)
    await db.commit()


@router.post("/{event_id}/exceptions/", response_model=EventExceptionResponse, status_code=201)
async def create_event_exception(
    event_id: int,
    data: EventExceptionBase,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Add an exception to a calendar event."""
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Event not found")
        
    exc = EventException(event_id=event_id, **data.model_dump())
    db.add(exc)
    await db.commit()
    await db.refresh(exc)
    return exc


@router.delete("/exceptions/{exception_id}/", status_code=204)
async def delete_event_exception(
    exception_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Remove an exception from a calendar event."""
    result = await db.execute(select(EventException).where(EventException.id == exception_id))
    exc = result.scalar_one_or_none()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    await db.delete(exc)
    await db.commit()
