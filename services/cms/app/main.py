"""
__service_name__ Service — FastAPI microservice for HTQWeb platform.

This service handles __service_description__.
Each service owns its data, its admin (sqladmin), and its background workers (Dramatiq).
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.settings import settings
from app.core.health import router as health_router
from app.middleware.request_id import RequestIDMiddleware


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
        title=settings.service_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.service_env != "production" else None,
        redoc_url="/redoc" if settings.service_env != "production" else None,
        openapi_url="/openapi.json" if settings.service_env != "production" else None,
    )

    app.add_middleware(RequestIDMiddleware)

    # Health (no prefix — gateway and Docker healthcheck hit /health/)
    app.include_router(health_router)

    # API v1 — register routers from app.api.v1.*
    # from app.api.v1 import example
    # app.include_router(example.router, prefix="/api/__service_name__/v1")

    # Admin (sqladmin) — wires JWT auth backend and ModelView registrations
    # from app.admin import create_admin
    # from app.db import engine
    # create_admin(app, engine)

    return app


app = create_app()
