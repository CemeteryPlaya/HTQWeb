"""
Authentication service — password hashing, JWT generation/validation.

This service is the JWT authority for the entire HTQWeb platform.
All other services validate tokens using the same secret.
"""

import datetime
import re
from typing import Optional

import bcrypt
import jwt
from pydantic import BaseModel

from app.core.settings import settings


# ─── Password hashing ───────────────────────────────────────────────────────
# Django uses PBKDF2-SHA256 with 600,000 iterations (Django 6.x).
# We support both Django PBKDF2 (for migration) and bcrypt (for new passwords).
# New passwords are hashed with bcrypt (faster verification).

# Regex to detect Django PBKDF2 hashes: pbkdf2_sha256$iterations$salt$hash
_DJANGO_PBKDF2_RE = re.compile(r'^pbkdf2_sha256\$\d+\$.+')


def _verify_django_pbkdf2(plain_password: str, hashed: str) -> bool:
    """
    Verify a Django PBKDF2-SHA256 hash.
    Django format: pbkdf2_sha256$iterations$salt$hash
    """
    from django.contrib.auth.hashers import check_password
    return check_password(plain_password, hashed)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    Supports both Django PBKDF2 and bcrypt — transparent migration.
    """
    if _DJANGO_PBKDF2_RE.match(hashed_password):
        return _verify_django_pbkdf2(plain_password, hashed_password)
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash should be upgraded to bcrypt."""
    # Django PBKDF2 hashes need rehashing
    if _DJANGO_PBKDF2_RE.match(hashed_password):
        return True
    # Check bcrypt rounds (if needed in the future)
    return False


class TokenPair(BaseModel):
    """JWT access + refresh token pair."""
    access: str
    refresh: str
    token_type: str = "Bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload with custom claims."""
    user_id: int
    username: str
    email: str
    is_staff: bool
    is_superuser: bool
    is_admin: bool = False
    token_type: str  # "access" or "refresh"
    exp: datetime.datetime
    iat: datetime.datetime
    iss: str


def create_token_pair(
    user_id: int,
    username: str,
    email: str,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> TokenPair:
    """
    Create JWT access + refresh token pair.

    Tokens contain custom claims (username, email, is_staff, is_superuser, is_admin)
    so downstream services can authorize without calling this service.
    The `is_admin` claim is derived from `is_staff or is_superuser` and is the
    single source of truth for sqladmin access across all services.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    is_admin = bool(is_staff or is_superuser)

    access_payload = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "is_staff": is_staff,
        "is_superuser": is_superuser,
        "is_admin": is_admin,
        "token_type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(hours=2),
        "iss": settings.jwt_issuer,
    }

    refresh_payload = {
        "user_id": user_id,
        "token_type": "refresh",
        "iat": now,
        "exp": now + datetime.timedelta(days=7),
        "iss": settings.jwt_issuer,
    }

    access_token = jwt.encode(
        access_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    refresh_token = jwt.encode(
        refresh_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return TokenPair(access=access_token, refresh=refresh_token)


def decode_token(token: str, require_type: Optional[str] = None) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string
        require_type: If set, verify token_type claim (e.g. "access" or "refresh")
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )

    if require_type and payload.get("token_type") != require_type:
        raise jwt.InvalidTokenError(
            f"Invalid token type: expected '{require_type}', got '{payload.get('token_type')}'"
        )

    return TokenPayload(**payload)
