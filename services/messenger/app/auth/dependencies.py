"""Authentication dependencies for Messenger service."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.settings import settings


security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT claims emitted by user-service.

    Mirrors `services.user.app.services.auth_service.TokenPayload`. We only
    need user_id + is_admin here, but accept the full claim set so a single
    Pydantic call validates the wire shape.
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


def get_optional_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> TokenPayload | None:
    if not auth:
        return None
    try:
        payload = jwt.decode(
            auth.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"verify_exp": True},
        )
        return TokenPayload(**payload)
    except jwt.PyJWTError:
        return None


def get_current_user(
    user: Annotated[TokenPayload | None, Depends(get_optional_user)]
) -> TokenPayload:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    user: Annotated[TokenPayload, Depends(get_current_user)]
) -> TokenPayload:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return user
