"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.tasks import router as tasks_router
from app.api.v1.labels import router as labels_router
from app.api.v1.versions import router as versions_router
from app.api.v1.links import router as links_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.comments import router as comments_router
from app.api.v1.attachments import router as attachments_router
from app.api.v1.activity import router as activity_router
from app.api.v1.sequences import router as sequences_router

router = APIRouter(prefix="/api/tasks/v1")

router.include_router(tasks_router)
router.include_router(labels_router)
router.include_router(versions_router)
router.include_router(links_router)
router.include_router(notifications_router)
router.include_router(calendar_router)
router.include_router(comments_router)
router.include_router(attachments_router)
router.include_router(activity_router)
router.include_router(sequences_router)
