"""
Email Service — FastAPI microservice for HTQWeb platform.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.settings import settings


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
