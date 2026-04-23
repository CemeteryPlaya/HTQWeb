"""sqladmin admin panel for messenger-service."""

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

from app.admin.views import (
    ChatUserReplicaAdmin,
    MessageAdmin,
    RoomAdmin,
    RoomParticipantAdmin,
    UserKeyAdmin,
)
from app.auth.admin_backend import JWTAdminAuthBackend
from app.core.settings import settings


def create_admin(app: FastAPI, engine: AsyncEngine) -> Admin:
    admin = Admin(
        app=app,
        engine=engine,
        base_url="/admin",
        title=f"{settings.service_name} admin",
        authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret),
    )

    admin.add_view(ChatUserReplicaAdmin)
    admin.add_view(RoomAdmin)
    admin.add_view(RoomParticipantAdmin)
    admin.add_view(MessageAdmin)
    admin.add_view(UserKeyAdmin)

    return admin
