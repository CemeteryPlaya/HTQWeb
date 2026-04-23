"""APScheduler jobs for email-service.

Run as separate process:
    python -m app.workers.scheduler
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete

from app.core.logging import configure_logging, get_logger
from app.core.settings import settings
from app.db import async_session_factory
from app.models.audit_log import AuditLog

log = get_logger(__name__)

async def mta_inbound_poll() -> None:
    """Poll IMAP for new emails."""
    log.info("mta_inbound_poll_run")

async def oauth_token_refresh() -> None:
    """Refresh expiring OAuth tokens."""
    log.info("oauth_token_refresh_run")

async def audit_log_compaction() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
    async with async_session_factory() as s:
        result = await s.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await s.commit()
        log.info("audit_log_compaction_run", deleted=result.rowcount)

def main() -> None:
    configure_logging()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(mta_inbound_poll, "interval", seconds=60, id="mta_inbound_poll")
    scheduler.add_job(oauth_token_refresh, "interval", minutes=30, id="oauth_token_refresh")
    scheduler.add_job(audit_log_compaction, "cron", hour=3, minute=30, id="audit_log_compaction")
    scheduler.start()
    log.info("apscheduler_started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
