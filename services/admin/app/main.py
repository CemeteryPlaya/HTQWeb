"""Unified Admin Aggregator Service for HTQWeb platform."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.admin import create_admin

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
        title="Admin Aggregator Service",
        version="0.1.0",
        description="Unified sqladmin dashboard for HTQWeb",
        lifespan=lifespan,
        docs_url="/docs" if settings.service_env != "production" else None,
        redoc_url="/redoc" if settings.service_env != "production" else None,
        openapi_url="/openapi.json" if settings.service_env != "production" else None,
    )

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    @app.get("/health/", include_in_schema=False)
    async def health_check():
        return {"status": "ok", "service": "admin"}

    create_admin(app)
    return app

app = create_app()
