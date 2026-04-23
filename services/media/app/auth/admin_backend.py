"""sqladmin AuthenticationBackend."""

import jwt
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.settings import settings


COOKIE_NAME = "admin_session"


class JWTAdminAuthBackend(AuthenticationBackend):
    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key=secret_key)

    async def login(self, request: Request) -> bool:
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return False
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                options={"verify_exp": True},
            )
        except jwt.PyJWTError:
            return False
        return bool(payload.get("is_admin"))
