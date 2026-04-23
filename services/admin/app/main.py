"""
Unified Admin Aggregator Service for HTQWeb platform.
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqladmin import Admin
from starlette.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.db import engine
from app.auth.backend import JWTAdminAuthBackend


# Add all services to PYTHONPATH dynamically so we can import their models and admin views
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logging.info("service_startup", extra={"service": settings.service_name, "port": settings.service_port})
    yield
    logging.info("service_shutdown", extra={"service": settings.service_name})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    app = FastAPI(
        title="Admin Aggregator Service",
        version="0.1.0",
        description="Unified sqladmin dashboard for HTQWeb",
        lifespan=lifespan,
        docs_url="/docs" if settings.service_env != "production" else None,
        redoc_url="/redoc" if settings.service_env != "production" else None,
        openapi_url="/openapi.json" if settings.service_env != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health/", include_in_schema=False)
    async def health_check():
        return {"status": "ok", "service": "admin"}

    # Initialize unified Admin
    admin = Admin(
        app=app,
        engine=engine,
        base_url="/admin",
        title="HTQWeb Central Admin",
        authentication_backend=JWTAdminAuthBackend(secret_key=settings.jwt_secret),
    )

    # Note: To avoid circular imports and schema conflicts, 
    # we dynamically import the admin views from each service here.
    
    try:
        from user.app.admin.views import UserAdmin
        admin.add_view(UserAdmin)
    except ImportError as e:
        logging.warning(f"Could not load user admin views: {e}")

    try:
        from cms.app.admin import NewsAdmin, ContactRequestAdmin
        admin.add_view(NewsAdmin)
        admin.add_view(ContactRequestAdmin)
    except ImportError as e:
        logging.warning(f"Could not load cms admin views: {e}")
        
    try:
        from media.app.admin.views import FileMetadataAdmin
        admin.add_view(FileMetadataAdmin)
    except ImportError as e:
        logging.warning(f"Could not load media admin views: {e}")
        
    try:
        from messenger.app.admin.views import (
            ChatUserReplicaAdmin, RoomAdmin, RoomParticipantAdmin, MessageAdmin, UserKeyAdmin
        )
        admin.add_view(ChatUserReplicaAdmin)
        admin.add_view(RoomAdmin)
        admin.add_view(RoomParticipantAdmin)
        admin.add_view(MessageAdmin)
        admin.add_view(UserKeyAdmin)
    except ImportError as e:
        logging.warning(f"Could not load messenger admin views: {e}")

    try:
        from email.app.admin.views import EmailMessageAdmin, OAuthTokenAdmin, RecipientStatusAdmin
        admin.add_view(EmailMessageAdmin)
        admin.add_view(OAuthTokenAdmin)
        admin.add_view(RecipientStatusAdmin)
    except ImportError as e:
        logging.warning(f"Could not load email admin views: {e}")

    return app


app = create_app()
