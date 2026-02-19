from rest_framework.routers import DefaultRouter

from .views import (
    LabelViewSet, ProjectVersionViewSet, TaskViewSet,
    TaskCommentViewSet, TaskAttachmentViewSet,
)

app_name = 'tasks'

router = DefaultRouter()
router.register(r'labels', LabelViewSet, basename='label')
router.register(r'versions', ProjectVersionViewSet, basename='version')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-comments', TaskCommentViewSet, basename='task-comment')
router.register(r'task-attachments', TaskAttachmentViewSet, basename='task-attachment')

urlpatterns = router.urls
