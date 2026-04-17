"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.tasks import router as tasks_router
from app.api.v1.labels import router as labels_router
from app.api.v1.versions import router as versions_router
from app.api.v1.links import router as links_router
from app.api.v1.notifications import router as notifications_router

router = APIRouter(prefix="/api/tasks/v1")

router.include_router(tasks_router)
router.include_router(labels_router)
router.include_router(versions_router)
router.include_router(links_router)
router.include_router(notifications_router)
