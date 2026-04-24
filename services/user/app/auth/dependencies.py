"""JWT authentication dependencies — inject into route handlers."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.settings import settings


class TokenPayload(BaseModel):
    """Decoded JWT payload.

    Mirrors the claims emitted by ``auth_service.create_token_pair``. Extra
    claims are tolerated so adding a new field to the token doesn't require
    touching this schema.
    """

    model_config = {"extra": "ignore"}

    user_id: int
    token_type: str
    exp: int
    username: str | None = None
    email: str | None = None
    is_staff: bool = False
    is_superuser: bool = False
    is_admin: bool = False


security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenPayload:
    """
    Validate JWT and extract user context.
    Called by every protected route handler.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"verify_exp": True},
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
