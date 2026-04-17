"""
User/Identity Service — FastAPI microservice for HTQWeb platform.

This service handles user identity, authentication, registration,
and JWT token issuance. It is the JWT authority for the entire platform.
Part of the Strangler Fig migration pattern.
"""

import contextlib
import logging

import structlog
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.settings import settings
from app.core.health import health_check, readiness_check
from app.middleware.request_id import RequestIDMiddleware
from app.routers import (
    admin,
    auth,
    health as health_router,
    internal_sync,
    profile,
    registration,
)


def get_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Configure structured logging
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
        title="User/Identity Service",
        version="0.1.0",
        description="JWT authority and user management for HTQWeb platform",
        docs_url="/docs" if settings.service_env != "production" else None,
        redoc_url="/redoc" if settings.service_env != "production" else None,
        openapi_url="/openapi.json" if settings.service_env != "production" else None,
    )

    # Middleware (order matters: last added = first executed)
    app.add_middleware(RequestIDMiddleware)

    # OpenTelemetry instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # Routers
    app.include_router(health_router.router)
    app.include_router(auth.router)
    app.include_router(registration.router)
    app.include_router(profile.router)
    app.include_router(admin.router)
    app.include_router(internal_sync.router)

    # Lifecycle events
    @app.on_event("startup")
    async def startup():
        logging.info(
            "service_startup",
            service="user-identity",
            port=settings.service_port,
        )

    @app.on_event("shutdown")
    async def shutdown():
        logging.info("service_shutdown", service="user-identity")

    return app


app = get_application()
