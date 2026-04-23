"""APScheduler jobs for messenger-service.

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

async def archive_old_messages() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with async_session_factory() as s:
        # MVP: только лог. TODO перенос в cold storage.
        log.info("archive_old_messages_run", cutoff=cutoff.isoformat())

async def cleanup_presence() -> None:
    # Redis TTL handling — noop (presence хранится в Redis с TTL).
    log.info("cleanup_presence_run")

async def audit_log_compaction() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
    async with async_session_factory() as s:
        result = await s.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await s.commit()
        log.info("audit_log_compaction_run", deleted=result.rowcount)

def main() -> None:
    configure_logging()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(archive_old_messages, "cron", hour=3, minute=15, id="archive_old_messages")
    scheduler.add_job(cleanup_presence, "cron", minute="*/5", id="cleanup_presence")
    scheduler.add_job(audit_log_compaction, "cron", hour=3, minute=30, id="audit_log_compaction")
    scheduler.start()
    log.info("apscheduler_started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
