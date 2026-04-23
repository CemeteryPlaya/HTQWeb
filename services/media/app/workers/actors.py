"""Dramatiq actors for media service."""

import logging
from uuid import UUID

import dramatiq

from app.workers import broker  # noqa: F401

logger = logging.getLogger(__name__)


@dramatiq.actor
def generate_thumbnail(file_id: str) -> None:
    """Generate thumbnail for an image.
    
    Stub: To be implemented with Pillow.
    """
    logger.info("generate_thumbnail started: file_id=%s", file_id)
    # TODO: Implement thumbnail generation
    logger.info("generate_thumbnail completed: file_id=%s", file_id)


@dramatiq.actor
def cleanup_orphan_files() -> None:
    """Clean up files from storage that have no DB record.
    
    Stub: To be implemented.
    """
    logger.info("cleanup_orphan_files started")
    # TODO: Implement orphan cleanup
    logger.info("cleanup_orphan_files completed")
