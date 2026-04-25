"""JWT authentication dependencies — inject into route handlers."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.settings import settings


class TokenPayload(BaseModel):
    """Decoded JWT payload from user-service.

    Mirrors `services.user.app.services.auth_service.TokenPayload` — the
    actual claim set emitted on login. `role` is derived from `is_admin`
    for back-compat with code that still expects it.
    """

    user_id: int
    username: str | None = None
    email: str | None = None
    is_staff: bool = False
    is_superuser: bool = False
    is_admin: bool = False
    token_type: str = "access"
    exp: int
    iat: int | None = None
    iss: str | None = None
    role: str = "employee"  # legacy alias — resolved in get_current_user


security = HTTPBearer()

# RBAC — roles that can do full HR operations.
# `admin` covers anyone with `is_superuser` OR `is_staff` (derived in
# get_current_user); `hr_admin`/`hr_manager` are reserved for future
# fine-grained per-employee ACLs.
HR_WRITE_ROLES = {"hr_admin", "hr_manager", "admin"}
HR_READ_ROLES = {"hr_admin", "hr_manager", "recruiter", "employee", "admin"}


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenPayload:
    """Validate JWT issued by User Service and extract user context."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"verify_exp": True},
        )
        token = TokenPayload(**payload)
        # Synthesize a coarse role for back-compat. is_admin = is_staff OR is_superuser
        # (set by user-service); fall through to "employee" for plain users.
        if token.is_admin or token.is_superuser or token.is_staff:
            token.role = "admin"
        return token
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_hr_write(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Require hr_admin, hr_manager, or admin role."""
    if current_user.role not in HR_WRITE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return current_user
