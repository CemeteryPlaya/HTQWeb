"""APScheduler-based periodic jobs for task-service.

Run as a separate process:
    python -m app.workers.scheduler

Jobs:
- task_deadline_reminder: hourly, finds tasks due within 24h and enqueues notifications.
"""

import asyncio
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, select

from app.db import async_session_factory
from app.models.task import Status, Task
from app.workers.actors import notification_dispatch

logger = logging.getLogger(__name__)


async def task_deadline_reminder() -> None:
    today = date.today()
    horizon = today + timedelta(days=1)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Task).where(
                and_(
                    Task.due_date.is_not(None),
                    Task.due_date <= horizon,
                    Task.status.notin_([Status.DONE, Status.CLOSED]),
                    Task.is_deleted.is_(False),
                )
            )
        )
        tasks = result.scalars().all()

    for task in tasks:
        if not task.assignee_id:
            continue
        notification_dispatch.send(
            {
                "recipient_id": task.assignee_id,
                "actor_id": None,
                "task_id": task.id,
                "verb": f"task_due_{(task.due_date - today).days}d",
            }
        )
    logger.info("task_deadline_reminder enqueued %d notifications", len(tasks))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        task_deadline_reminder,
        "cron",
        minute=0,
        id="task_deadline_reminder",
    )
    scheduler.start()
    logger.info("task-service scheduler started")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
