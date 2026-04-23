"""Dramatiq actors for hr-service.

Discovered by:
    dramatiq app.workers.actors

Enqueue from a route:
    from app.workers.actors import vacancy_application_notify
    vacancy_application_notify.send({"vacancy_id": v.id, "candidate_email": ...})
"""

import logging

import dramatiq

from app.workers import broker  # noqa: F401  ensures broker is set first

logger = logging.getLogger(__name__)


@dramatiq.actor(max_retries=3, min_backoff=2_000, max_backoff=60_000)
def vacancy_application_notify(payload: dict) -> None:
    """Notify recruiter of a new application.

    payload: {"vacancy_id": int, "application_id": int, "candidate_email": str}
    Sends through email-service /api/email/v1/send when wired; logs locally otherwise.
    """
    if not payload.get("vacancy_id") or not payload.get("application_id"):
        logger.warning("vacancy_application_notify missing fields: %s", payload)
        return
    logger.info("vacancy_application_notify queued: %s", payload)
