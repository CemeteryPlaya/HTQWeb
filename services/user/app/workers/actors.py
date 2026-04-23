"""Dramatiq actors for user-service.

Discovered by the worker entrypoint:
    dramatiq app.workers.actors

Enqueue from a route:
    from app.workers.actors import email_confirmation_send
    email_confirmation_send.send({"to": user.email, "token": token})
"""

import logging

import dramatiq

from app.workers import broker  # noqa: F401  ensures broker is set first

logger = logging.getLogger(__name__)


@dramatiq.actor(max_retries=5, min_backoff=1_000, max_backoff=60_000)
def email_confirmation_send(payload: dict) -> None:
    """Send a registration-confirmation email.

    payload: {"to": str, "token": str, "display_name": str | None}
    Real SMTP/transactional-email integration is wired by the email-service;
    here we hand the message off via HTTP or log it during local dev.
    """
    to = payload.get("to")
    token = payload.get("token")
    if not to or not token:
        logger.warning("email_confirmation_send missing fields: %s", payload)
        return
    # TODO: POST to email-service /api/email/v1/send when that service lands.
    logger.info("email_confirmation_send queued for %s", to)
