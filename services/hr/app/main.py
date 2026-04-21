"""
HR Service — FastAPI microservice for HTQWeb platform.

Handles: employees, departments, positions, vacancies, applications,
         time tracking, documents, audit log.
Part of the Strangler Fig migration pattern (Phase 1b).
"""

import logging

import structlog
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.settings import settings
from app.middleware.request_id import RequestIDMiddleware
from app.api.health import router as health_router
from app.api.v1.employees import router as employees_router
from app.api.v1.departments import router as departments_router
from app.api.v1.positions import router as positions_router
from app.api.v1.vacancies import router as vacancies_router
from app.api.v1.applications import router as applications_router
from app.api.v1.time import router as time_router
from app.api.v1.documents import router as documents_router
from app.api.v1.audit import router as audit_router
from app.api.v1.org import router as org_router
from app.api.v1.pmo import router as pmo_router
from app.api.v1.share_links import router as share_links_router
from app.api.public.org import router as public_org_router, limiter  # limiter attached to app below

API_PREFIX = settings.api_prefix  # /api/hr/v1


def get_application() -> FastAPI:
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
        title="HR Service",
        version="1.0.0",
        description="HR management microservice for HTQWeb enterprise platform",
        docs_url="/docs" if settings.service_env != "production" else None,
        redoc_url="/redoc" if settings.service_env != "production" else None,
        openapi_url="/openapi.json" if settings.service_env != "production" else None,
    )

    # Middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SlowAPIMiddleware)

    # Rate limiter state (required by slowapi)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

    # Health (no prefix — required by Docker healthcheck and gateway)
    app.include_router(health_router)

    # API v1 routes
    app.include_router(employees_router, prefix=API_PREFIX)
    app.include_router(departments_router, prefix=API_PREFIX)
    app.include_router(positions_router, prefix=API_PREFIX)
    app.include_router(vacancies_router, prefix=API_PREFIX)
    app.include_router(applications_router, prefix=API_PREFIX)
    app.include_router(time_router, prefix=API_PREFIX)
    app.include_router(documents_router, prefix=API_PREFIX)
    app.include_router(audit_router, prefix=API_PREFIX)
    app.include_router(org_router, prefix=API_PREFIX)
    app.include_router(pmo_router, prefix=API_PREFIX)
    app.include_router(share_links_router, prefix=API_PREFIX)

    # Public routes (no auth, rate-limited)
    app.include_router(public_org_router, prefix=API_PREFIX)

    @app.on_event("startup")
    async def startup():
        logging.info("service_startup", extra={"service": settings.service_name, "port": settings.service_port})

    @app.on_event("shutdown")
    async def shutdown():
        logging.info("service_shutdown", extra={"service": settings.service_name})

    return app


app = get_application()
