"""
OAuth-based email connector.

Sends external emails through Gmail API or Microsoft Graph API using
per-user OAuth 2.0 tokens.  Replaces the old Gmail SMTP + App Password approach.

Security features:
- select_for_update() prevents race conditions during token refresh
- CRLF injection protection on all MIME header fields
- Automatic access_token refresh when expired
"""

import base64
import json
import logging
import re
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from django.db import transaction
from django.utils import timezone

from .models import EmailOAuthToken
from .oauth import (
    refresh_google_token,
    refresh_microsoft_token,
)

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
#  CRLF sanitization
# ---------------------------------------------------------------------------

def _sanitize_header(value: str) -> str:
    """
    Strip CR/LF characters from a header value to prevent
    Email Header Injection (CRLF injection of hidden Bcc, etc.).
    """
    if not value:
        return ''
    return re.sub(r'[\r\n]+', ' ', value).strip()


def _sanitize_email_address(addr: str) -> str:
    """Sanitize an email address — strip CRLF and angle brackets."""
    return re.sub(r'[\r\n<>]+', '', addr).strip()


# ---------------------------------------------------------------------------
#  Token refresh with DB-level concurrency lock
# ---------------------------------------------------------------------------

def _ensure_valid_token(user) -> EmailOAuthToken:
    """
    Load the user's OAuth token with a row-level lock.
    If the access token is expired, refresh it atomically.

    Uses select_for_update() so that concurrent Celery workers
    won't race to refresh the same token simultaneously (which
    would invalidate the refresh token chain).
    """
    with transaction.atomic():
        try:
            token_obj = (
                EmailOAuthToken.objects
                .select_for_update()
                .get(user=user)
            )
        except EmailOAuthToken.DoesNotExist:
            raise ValueError(
                f'У пользователя {user} нет подключённой OAuth-почты. '
                'Подключите почту в настройках.'
            )

        if not token_obj.is_token_expired():
            return token_obj

        # --- Refresh ---
        logger.info(f'Refreshing OAuth token for {user} ({token_obj.provider})')
        try:
            if token_obj.provider == EmailOAuthToken.Provider.GOOGLE:
                data = refresh_google_token(token_obj.refresh_token)
            elif token_obj.provider == EmailOAuthToken.Provider.MICROSOFT:
                data = refresh_microsoft_token(token_obj.refresh_token)
            else:
                raise ValueError(f'Unknown provider: {token_obj.provider}')
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else 0
            if status_code in (400, 401):
                # Refresh token was revoked or expired
                logger.error(
                    f'OAuth token revoked for {user}. '
                    f'Provider responded {status_code}. Deleting token record.'
                )
                token_obj.delete()
                raise ValueError(
                    'Доступ к почте был отозван провайдером. '
                    'Пожалуйста, подключите почту заново.'
                ) from exc
            raise

        # Update tokens
        token_obj.access_token = data['access_token']
        # Microsoft may rotate refresh tokens
        if 'refresh_token' in data:
            token_obj.refresh_token = data['refresh_token']
        token_obj.token_expires_at = (
            timezone.now() + timedelta(seconds=data.get('expires_in', 3600))
        )
        token_obj.save()

        logger.info(f'OAuth token refreshed successfully for {user}')
        return token_obj


# ---------------------------------------------------------------------------
#  MIME message builder
# ---------------------------------------------------------------------------

def _build_mime_message(
    sender_email: str,
    sender_name: str,
    recipients: list[str],
    subject: str,
    body_html: str,
) -> MIMEMultipart:
    """
    Build an RFC 2822 MIME message with CRLF-safe headers.
    """
    msg = MIMEMultipart('alternative')

    safe_subject = _sanitize_header(subject)
    safe_sender_name = _sanitize_header(sender_name)
    safe_sender_email = _sanitize_email_address(sender_email)
    safe_recipients = [_sanitize_email_address(r) for r in recipients]

    msg['Subject'] = safe_subject
    msg['From'] = f'{safe_sender_name} <{safe_sender_email}>'
    msg['To'] = ', '.join(safe_recipients)

    # Attach HTML body
    html_part = MIMEText(body_html, 'html', 'utf-8')
    msg.attach(html_part)

    return msg


# ---------------------------------------------------------------------------
#  Gmail API sender
# ---------------------------------------------------------------------------

def _send_via_gmail(access_token: str, mime_message: MIMEMultipart) -> bool:
    """
    Send via Gmail API: POST users.messages.send
    https://developers.google.com/gmail/api/reference/rest/v1/users.messages/send
    """
    raw_message = base64.urlsafe_b64encode(
        mime_message.as_bytes()
    ).decode('ascii')

    resp = requests.post(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        json={'raw': raw_message},
        timeout=HTTP_TIMEOUT,
    )

    if resp.status_code == 401:
        logger.error('Gmail API 401: Access token invalid or expired.')
        raise requests.HTTPError(response=resp)
    if resp.status_code == 403:
        logger.error(f'Gmail API 403: Insufficient scope or quota. {resp.text}')
        raise requests.HTTPError(response=resp)
    if resp.status_code == 429:
        logger.warning('Gmail API 429: Rate limit exceeded.')
        raise requests.HTTPError(response=resp)

    resp.raise_for_status()
    logger.info(f'Gmail API: Message sent. ID={resp.json().get("id")}')
    return True


# ---------------------------------------------------------------------------
#  Microsoft Graph API sender
# ---------------------------------------------------------------------------

def _send_via_microsoft(access_token: str, mime_message: MIMEMultipart) -> bool:
    """
    Send via Microsoft Graph API: POST /me/sendMail
    Uses the raw MIME approach: PUT /me/messages (draft) then send,
    or the JSON approach for simpler payloads.
    We use the JSON /me/sendMail endpoint for reliability.
    """
    # Extract fields from MIME to build Graph JSON payload
    subject = mime_message['Subject'] or ''
    to_header = mime_message['To'] or ''
    recipients = [addr.strip() for addr in to_header.split(',') if addr.strip()]

    # Get HTML body from MIME parts
    body_html = ''
    for part in mime_message.walk():
        if part.get_content_type() == 'text/html':
            payload = part.get_payload(decode=True)
            if payload:
                body_html = payload.decode('utf-8', errors='replace')
            break

    graph_payload = {
        'message': {
            'subject': subject,
            'body': {
                'contentType': 'HTML',
                'content': body_html,
            },
            'toRecipients': [
                {'emailAddress': {'address': addr}} for addr in recipients
            ],
        },
        'saveToSentItems': 'true',
    }

    resp = requests.post(
        'https://graph.microsoft.com/v1.0/me/sendMail',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        json=graph_payload,
        timeout=HTTP_TIMEOUT,
    )

    if resp.status_code == 401:
        logger.error('Graph API 401: Access token invalid or expired.')
        raise requests.HTTPError(response=resp)
    if resp.status_code == 403:
        logger.error(f'Graph API 403: Insufficient permissions. {resp.text}')
        raise requests.HTTPError(response=resp)
    if resp.status_code == 429:
        logger.warning('Graph API 429: Rate limit exceeded.')
        raise requests.HTTPError(response=resp)

    resp.raise_for_status()
    logger.info('Graph API: Message sent successfully.')
    return True


# ═══════════════════════════════════════════════════════════════════════════
#  Public API — drop-in replacement for the old ExternalEmailAPIConnector
# ═══════════════════════════════════════════════════════════════════════════

class OAuthEmailConnector:
    """
    Sends email on behalf of the authenticated user via their
    connected OAuth provider (Google / Microsoft).
    """

    def send_external_email(
        self,
        subject: str,
        body: str,
        external_recipients: list[str],
        sender_user=None,
    ) -> bool:
        """
        Send an email to external recipients using the sender's OAuth token.

        Returns True on success, False on failure (logged).
        """
        if not external_recipients:
            return True

        if sender_user is None:
            logger.error('send_external_email called without sender_user.')
            return False

        try:
            token_obj = _ensure_valid_token(sender_user)
        except ValueError as exc:
            logger.error(f'OAuth token error: {exc}')
            return False

        # Build sender identity
        sender_name = (
            f'{sender_user.first_name} {sender_user.last_name}'.strip()
            or sender_user.username
        )
        sender_email = token_obj.user_email

        # Build MIME message with sanitized headers
        mime_msg = _build_mime_message(
            sender_email=sender_email,
            sender_name=sender_name,
            recipients=external_recipients,
            subject=subject,
            body_html=body,
        )

        try:
            if token_obj.provider == EmailOAuthToken.Provider.GOOGLE:
                return _send_via_gmail(token_obj.access_token, mime_msg)
            elif token_obj.provider == EmailOAuthToken.Provider.MICROSOFT:
                return _send_via_microsoft(token_obj.access_token, mime_msg)
            else:
                logger.error(f'Unknown provider: {token_obj.provider}')
                return False

        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else 0
            logger.error(
                f'Email send failed via {token_obj.provider}: '
                f'HTTP {status_code} — {exc}'
            )
            return False
        except requests.ConnectionError:
            logger.error(
                f'Connection error sending via {token_obj.provider} API.'
            )
            return False
        except Exception as exc:
            logger.error(f'Unexpected error sending email: {exc}')
            return False
