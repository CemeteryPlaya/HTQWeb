"""
Messenger Service — FastAPI microservice for HTQWeb platform.

Handles chat, rooms, E2EE keys, and real-time Socket.IO communication.
"""


from contextlib import asynccontextmanager


from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.api.socket import sio_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    log.info("service_startup", extra={"service": settings.service_name, "port": settings.service_port})
    yield
    log.info("service_shutdown", extra={"service": settings.service_name})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="Messenger Service",
        version="0.1.0",
        description="Real-time chat and messaging for HTQWeb",
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

    # Health (no prefix — gateway and Docker healthcheck hit /health/)
    @app.get("/health/", include_in_schema=False)
    async def health_check():
        return {"status": "ok", "service": "messenger"}

    # Mount Socket.IO app
    app.mount("/ws", sio_app)

    # API v1 routers
    from app.api.v1 import rooms as rooms_router
    from app.api.v1 import messages as messages_router
    from app.api.v1 import keys as keys_router
    from app.api.v1 import users as users_router
    from app.api.v1 import read as read_router
    from app.api.v1 import attachments as attachments_router
    from app.api.v1 import admin as admin_router
    
    app.include_router(rooms_router.router, prefix="/api/messenger/v1/rooms")
    app.include_router(messages_router.router, prefix="/api/messenger/v1/messages")
    app.include_router(keys_router.router, prefix="/api/messenger/v1/keys")
    app.include_router(users_router.router, prefix="/api/messenger/v1/users")
    app.include_router(read_router.router, prefix="/api/messenger/v1")
    app.include_router(attachments_router.router, prefix="/api/messenger/v1/attachments")
    app.include_router(admin_router.router, prefix="/api/messenger/v1/admin")

    # Admin (sqladmin)
    from app.admin import create_admin
    from app.db import engine
    create_admin(app, engine)

    return app


app = create_app()
