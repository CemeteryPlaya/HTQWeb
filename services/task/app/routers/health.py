"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "task-service"}


@router.get("/health/ready/")
async def readiness_check():
    """Readiness check - verifies DB connection."""
    # TODO: Add actual DB connection check
    return {"status": "ready", "service": "task-service"}
