"""
Email Service — FastAPI microservice for HTQWeb platform.
"""


from contextlib import asynccontextmanager


from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


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
        title="Email Service",
        version="0.1.0",
        description="Encrypted email sending and sync for HTQWeb",
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
        return {"status": "ok", "service": "email"}

    # API v1 routers
    from app.api.v1 import emails as emails_router
    from app.api.v1 import oauth as oauth_router
    app.include_router(emails_router.router, prefix="/api/email/v1")
    app.include_router(oauth_router.router, prefix="/api/email/v1/oauth")

    # Admin (sqladmin)
    from app.admin import create_admin
    from app.db import engine
    create_admin(app, engine)

    return app


app = create_app()
