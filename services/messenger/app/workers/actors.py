"""Dramatiq actors for messenger service."""

import logging
from app.workers import broker  # noqa: F401

import dramatiq

logger = logging.getLogger(__name__)


@dramatiq.actor
def push_notification(user_id: int, message_preview: str) -> None:
    """Send push notification to user devices.
    
    Stub: to be implemented using Firebase Cloud Messaging / APNs.
    """
    logger.info("push_notification sent to user %d: %s", user_id, message_preview)
