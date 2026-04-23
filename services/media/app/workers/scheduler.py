"""APScheduler jobs for media-service.

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

async def cleanup_orphan_files() -> None:
    """Check storage for files without metadata and delete them."""
    log.info("cleanup_orphan_files_run")
    # TODO: implement storage-specific cleanup

async def audit_log_compaction() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
    async with async_session_factory() as s:
        result = await s.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await s.commit()
        log.info("audit_log_compaction_run", deleted=result.rowcount)

def main() -> None:
    configure_logging()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_orphan_files, "cron", day_of_week="sun", hour=4, id="cleanup_orphan_files")
    scheduler.add_job(audit_log_compaction, "cron", hour=3, minute=30, id="audit_log_compaction")
    scheduler.start()
    log.info("apscheduler_started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
