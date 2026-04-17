"""Notification API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.auth.dependencies import get_current_user
from app.repositories import NotificationRepository
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """List user notifications."""
    repo = NotificationRepository(db)
    user_id = current_user.get("id")
    notifications = await repo.get_all(recipient_id=user_id)
    return notifications


@router.post("/{notification_id}/mark_read/", status_code=204)
async def mark_notification_read(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    repo = NotificationRepository(db)
    notification = await repo.get_by_id(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    await db.commit()


@router.post("/mark-all-read/", status_code=204)
async def mark_all_notifications_read(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Mark all user notifications as read."""
    from sqlalchemy import update
    from app.models.notification import Notification
    
    user_id = current_user.get("id")
    await db.execute(
        update(Notification)
        .where(Notification.recipient_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
