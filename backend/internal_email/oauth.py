"""
OAuth 2.0 Authorization Code Flow helpers for Google & Microsoft.

This module handles:
- Building the authorization URL (with state for CSRF)
- Exchanging an authorization code for tokens
- Refreshing an expired access token
"""

import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Timeouts & constants
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 15  # seconds

# Google endpoints
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
# STRICTLY gmail.send — no reading inbox, no restricted scopes (avoids CASA audit)
GOOGLE_SCOPES = 'https://www.googleapis.com/auth/gmail.send email'

# Microsoft endpoints (common tenant for multi-org, override via MICROSOFT_OAUTH_TENANT_ID)
MICROSOFT_TOKEN_URL_TEMPLATE = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
MICROSOFT_AUTH_URL_TEMPLATE = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize'
# Mail.Send = send only, offline_access = refresh token
MICROSOFT_SCOPES = 'Mail.Send offline_access User.Read'


# ═══════════════════════════════════════════════════════════════════════════
#  GOOGLE
# ═══════════════════════════════════════════════════════════════════════════

def get_google_auth_url(state: str) -> str:
    """
    Build the Google OAuth 2.0 authorization URL.
    ``state`` must be a cryptographically random string saved in the session.
    """
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': GOOGLE_SCOPES,
        'access_type': 'offline',       # request refresh_token
        'prompt': 'consent',            # force consent to always get refresh_token
        'state': state,
    }
    return f'{GOOGLE_AUTH_URL}?{urlencode(params)}'


def exchange_google_code(code: str) -> dict:
    """
    Exchange authorization code for tokens.
    Returns: {access_token, refresh_token, expires_in, scope, token_type}
    Raises requests.HTTPError on failure.
    """
    payload = {
        'code': code,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def refresh_google_token(refresh_token: str) -> dict:
    """
    Use a refresh token to obtain a new access token.
    Returns: {access_token, expires_in, scope, token_type}
    """
    payload = {
        'refresh_token': refresh_token,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'grant_type': 'refresh_token',
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_google_user_email(access_token: str) -> str:
    """Fetch the user's email from the Google userinfo endpoint."""
    resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get('email', '')


# ═══════════════════════════════════════════════════════════════════════════
#  MICROSOFT
# ═══════════════════════════════════════════════════════════════════════════

def _ms_tenant() -> str:
    return getattr(settings, 'MICROSOFT_OAUTH_TENANT_ID', 'common')


def get_microsoft_auth_url(state: str) -> str:
    """Build the Microsoft OAuth 2.0 authorization URL."""
    params = {
        'client_id': settings.MICROSOFT_OAUTH_CLIENT_ID,
        'redirect_uri': settings.MICROSOFT_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': MICROSOFT_SCOPES,
        'response_mode': 'query',
        'state': state,
    }
    base = MICROSOFT_AUTH_URL_TEMPLATE.format(tenant=_ms_tenant())
    return f'{base}?{urlencode(params)}'


def exchange_microsoft_code(code: str) -> dict:
    """
    Exchange authorization code for tokens.
    Returns: {access_token, refresh_token, expires_in, scope, token_type}
    """
    payload = {
        'code': code,
        'client_id': settings.MICROSOFT_OAUTH_CLIENT_ID,
        'client_secret': settings.MICROSOFT_OAUTH_CLIENT_SECRET,
        'redirect_uri': settings.MICROSOFT_OAUTH_REDIRECT_URI,
        'grant_type': 'authorization_code',
        'scope': MICROSOFT_SCOPES,
    }
    url = MICROSOFT_TOKEN_URL_TEMPLATE.format(tenant=_ms_tenant())
    resp = requests.post(url, data=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def refresh_microsoft_token(refresh_token: str) -> dict:
    """
    Use a refresh token to obtain a new access token.
    Returns: {access_token, refresh_token (rotated), expires_in, scope}
    """
    payload = {
        'refresh_token': refresh_token,
        'client_id': settings.MICROSOFT_OAUTH_CLIENT_ID,
        'client_secret': settings.MICROSOFT_OAUTH_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'scope': MICROSOFT_SCOPES,
    }
    url = MICROSOFT_TOKEN_URL_TEMPLATE.format(tenant=_ms_tenant())
    resp = requests.post(url, data=payload, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_microsoft_user_email(access_token: str) -> str:
    """Fetch the user's email from Microsoft Graph /me endpoint."""
    resp = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('mail') or data.get('userPrincipalName', '')
