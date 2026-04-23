"""APScheduler-based periodic jobs for hr-service.

Run as a separate process:
    python -m app.workers.scheduler

Jobs:
- audit_log_compaction: weekly, retain only last 90d of audit_log rows.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete

from app.db import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

AUDIT_RETENTION_DAYS = 90


async def audit_log_compaction() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=AUDIT_RETENTION_DAYS)
    async with async_session_factory() as session:
        result = await session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        await session.commit()
        logger.info("audit_log_compaction removed %d rows older than %s", result.rowcount, cutoff)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler()
    # Sundays at 04:00 UTC.
    scheduler.add_job(
        audit_log_compaction,
        "cron",
        day_of_week="sun",
        hour=4,
        minute=0,
        id="audit_log_compaction",
    )
    scheduler.start()
    logger.info("hr-service scheduler started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
