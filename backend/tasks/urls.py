from rest_framework.routers import DefaultRouter

from .viewsets import (
    LabelViewSet, ProjectVersionViewSet, TaskViewSet,
    TaskCommentViewSet, TaskAttachmentViewSet,
    TaskLinkViewSet, NotificationViewSet,
    ProductionDayViewSet, CalendarEventViewSet, CalendarTimelineViewSet
)

app_name = 'tasks'

router = DefaultRouter()
router.register(r'labels', LabelViewSet, basename='label')
router.register(r'versions', ProjectVersionViewSet, basename='version')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-comments', TaskCommentViewSet, basename='task-comment')
router.register(r'task-attachments', TaskAttachmentViewSet, basename='task-attachment')
router.register(r'task-links', TaskLinkViewSet, basename='task-link')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'production-calendar', ProductionDayViewSet, basename='production-day')
router.register(r'calendar-events', CalendarEventViewSet, basename='calendar-event')
router.register(r'calendar-timeline', CalendarTimelineViewSet, basename='calendar-timeline')

urlpatterns = router.urls
