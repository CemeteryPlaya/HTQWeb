from __future__ import annotations

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Notification, Task, TaskAttachment, TaskComment, TaskLink
from ..serializers import (
    NotificationSerializer,
    TaskAttachmentSerializer,
    TaskCommentSerializer,
    TaskDetailSerializer,
    TaskLinkSerializer,
    TaskListSerializer,
)
from ..services import (
    build_task_stats,
    filter_related_tasks_for_user,
    get_task_queryset_for_request,
    validate_task_link_cycle,
)
from ..services.notifications import create_task_comment_notifications


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD для задач."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        return TaskDetailSerializer

    def get_queryset(self):
        return get_task_queryset_for_request(
            user=self.request.user,
            params=self.request.query_params,
        )

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['post'], url_path='comments')
    def add_comment(self, request, pk=None):
        """Добавить комментарий к задаче."""
        task = self.get_object()
        serializer = TaskCommentSerializer(data={**request.data, 'task': task.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='attachments')
    def add_attachment(self, request, pk=None):
        """Прикрепить файл к задаче."""
        task = self.get_object()
        serializer = TaskAttachmentSerializer(
            data={**request.data, 'task': task.id},
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='transitions')
    def transitions(self, request, pk=None):
        """Получить список доступных статусов для перехода."""
        task = self.get_object()
        allowed = Task.TRANSITIONS.get(task.status, set())

        # Include current status to avoid UI dropdown edge-cases.
        result = list(allowed) + [task.status]
        return Response(list(set(result)))

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Статистика задач для отчётов."""
        return Response(build_task_stats(request.query_params))


class TaskCommentViewSet(viewsets.ModelViewSet):
    """CRUD комментариев (также доступно через task/{id}/comments)."""

    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TaskComment.objects.select_related('author', 'task')
        queryset = filter_related_tasks_for_user(
            queryset,
            self.request.user,
            task_prefix='task__',
        )

        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)

        return queryset

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        create_task_comment_notifications(comment=comment, actor=self.request.user)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """CRUD вложений."""

    serializer_class = TaskAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TaskAttachment.objects.select_related('uploaded_by', 'task')
        queryset = filter_related_tasks_for_user(
            queryset,
            self.request.user,
            task_prefix='task__',
        )

        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class TaskLinkViewSet(viewsets.ModelViewSet):
    """CRUD для связей задач (блокирует, относится к и т.д.)."""

    serializer_class = TaskLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TaskLink.objects.select_related('source', 'target', 'created_by')
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(Q(source_id=task_id) | Q(target_id=task_id))
        return queryset

    def perform_create(self, serializer):
        source = serializer.validated_data['source']
        target = serializer.validated_data['target']
        link_type = serializer.validated_data['link_type']

        validate_task_link_cycle(source=source, target=target, link_type=link_type)
        serializer.save(created_by=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Список уведомлений текущего пользователя."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})
