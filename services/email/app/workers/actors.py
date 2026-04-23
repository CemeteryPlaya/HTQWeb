"""Dramatiq actors for email service."""
import dramatiq
from app.workers import broker  # noqa: F401
from app.core.logging import get_logger

log = get_logger(__name__)

@dramatiq.actor(max_retries=5, min_backoff=1000, max_backoff=30000)
def deliver_email(message_id: int) -> None:
    """Deliver email message via SMTP/OAuth."""
    log.info("delivering_email", message_id=message_id)
    # TODO: real delivery logic

@dramatiq.actor(max_retries=3)
def dlp_scan_attachment(attachment_id: int) -> None:
    """Scan attachment for sensitive data."""
    log.info("dlp_scanning_attachment", attachment_id=attachment_id)
    # TODO: real DLP scan logic
