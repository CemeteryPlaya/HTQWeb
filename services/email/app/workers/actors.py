"""Dramatiq actors for email service."""

import logging
from app.workers import broker  # noqa: F401

import dramatiq

logger = logging.getLogger(__name__)


@dramatiq.actor
def sync_emails_from_provider(account_id: int) -> None:
    """Background task to sync IMAP/Graph emails into local DB."""
    logger.info("Syncing emails for account %d", account_id)


@dramatiq.actor
def check_delivery_status(message_id: str) -> None:
    """Check for bounces or delivery receipts."""
    logger.info("Checking delivery status for message %s", message_id)
