"""sqladmin admin panel for messenger-service."""

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.admin_backend import JWTAdminAuthBackend
from app.core.settings import settings
from app.admin.views import (
    ChatUserReplicaAdmin, RoomAdmin, RoomParticipantAdmin,
    MessageAdmin, UserKeyAdmin, ChatAttachmentAdmin,
)

def create_admin(app, engine):
    admin = Admin(app=app, engine=engine, base_url="/admin",
                  authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret))
    for view in (ChatUserReplicaAdmin, RoomAdmin, RoomParticipantAdmin,
                 MessageAdmin, UserKeyAdmin, ChatAttachmentAdmin):
        admin.add_view(view)
    return admin
