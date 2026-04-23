"""Dramatiq actors for CMS service.

Worker process command (docker-compose):
    dramatiq app.workers.actors --processes 2 --threads 4

Every @dramatiq.actor function is auto-registered with the broker initialised
in app/workers/__init__.py.
"""

import logging

import dramatiq
import httpx

# Ensure the broker is set up before any @dramatiq.actor declarations.
from app.workers import broker  # noqa: F401

logger = logging.getLogger(__name__)


@dramatiq.actor(max_retries=3, min_backoff=1000)
def translate_news(news_id: int, target_lang: str) -> None:
    """Translate a news article to target_lang via external API.

    TODO: Wire up a real translation provider (Google Translate API / DeepL)
    via ``settings.translation_api_key``. Currently returns a stub response
    and logs the request.
    """
    from app.core.settings import settings

    logger.info(
        "translate_news started: news_id=%d target=%s provider=%s",
        news_id,
        target_lang,
        settings.translation_provider,
    )

    if not settings.translation_api_key:
        logger.warning(
            "translate_news: no translation_api_key set — skipping. "
            "Set TRANSLATION_API_KEY env to enable."
        )
        return

    # TODO: implement actual translation call
    # Example flow:
    # 1. Fetch news from DB (sync session for dramatiq)
    # 2. Call translation API
    # 3. Store translated content (new field or separate table)
    logger.info(
        "translate_news completed (stub): news_id=%d target=%s",
        news_id,
        target_lang,
    )


@dramatiq.actor(max_retries=3, min_backoff=2000)
def notify_admins_on_contact_request(contact_request_id: int) -> None:
    """Notify administrators about a new contact request via email-service.

    Makes an HTTP call to the email-service to dispatch the notification.
    Fails silently (logs error) if email-service is unavailable.
    """
    from app.core.settings import settings

    logger.info(
        "notify_admins_on_contact_request: id=%d", contact_request_id
    )

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{settings.email_service_url}/api/email/v1/internal/notify",
                json={
                    "event": "contact_request_submitted",
                    "contact_request_id": contact_request_id,
                },
            )
            if resp.status_code < 300:
                logger.info(
                    "notify_admins_on_contact_request: email-service accepted id=%d",
                    contact_request_id,
                )
            else:
                logger.warning(
                    "notify_admins_on_contact_request: email-service returned %d for id=%d",
                    resp.status_code,
                    contact_request_id,
                )
    except httpx.HTTPError as exc:
        logger.error(
            "notify_admins_on_contact_request: email-service unreachable for id=%d: %s",
            contact_request_id,
            exc,
        )
