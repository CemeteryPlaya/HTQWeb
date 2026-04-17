"""
__service_name__ Service — FastAPI microservice for HTQWeb platform.

This service handles __service_description__.
Part of the Strangler Fig migration pattern.
"""

import contextlib
import logging

import structlog
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.config import settings
from app.core.health import health_check, readiness_check
from app.middleware.request_id import RequestIDMiddleware
from app.routers import health as health_router


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
        title=settings.service_name,
        version="0.1.0",
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

    # Lifecycle events
    @app.on_event("startup")
    async def startup():
        logging.info("service_startup", service=settings.service_name, port=settings.service_port)

    @app.on_event("shutdown")
    async def shutdown():
        logging.info("service_shutdown", service=settings.service_name)

    return app


app = get_application()
