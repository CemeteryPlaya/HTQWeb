"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin import create_admin
from app.api import v1_router
from app.core.settings import settings
from app.db import engine
from app.core.health import router as health_router
from app.middleware import RequestIDMiddleware
from app.workers import actors as _actors  # noqa: F401  ensures broker is configured

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Task service starting up...")
    # TODO: Run DB migrations on startup
    # TODO: Initialize Redis connection
    yield
    logger.info("Task service shutting down...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Task Service",
        description="Task tracking and project management microservice",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestIDMiddleware)

    app.include_router(health_router)
    app.include_router(v1_router)

    create_admin(app, engine)

    return app


app = create_app()
