from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hr.permissions import IsHRManagerOrSuperuser

from ..models import Label, ProjectVersion, Task
from ..serializers import LabelSerializer, ProjectVersionSerializer, TaskListSerializer


class AuthenticatedReadActionsMixin:
    """Allow public write-policy while keeping list/retrieve authenticated-only."""

    authenticated_read_actions: set[str] = {'list', 'retrieve'}

    def get_permissions(self):
        if self.action in self.authenticated_read_actions:
            return [IsAuthenticated()]
        return [permission() for permission in self.permission_classes]


class LabelViewSet(AuthenticatedReadActionsMixin, viewsets.ModelViewSet):
    """CRUD для меток задач."""

    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = [IsHRManagerOrSuperuser]


class ProjectVersionViewSet(AuthenticatedReadActionsMixin, viewsets.ModelViewSet):
    """CRUD для версий / релизов."""

    serializer_class = ProjectVersionSerializer
    permission_classes = [IsHRManagerOrSuperuser]
    authenticated_read_actions = {'list', 'retrieve', 'version_tasks'}

    def get_queryset(self):
        queryset = ProjectVersion.objects.annotate(
            task_count=Count('tasks', filter=Q(tasks__is_deleted=False)),
            done_count=Count(
                'tasks',
                filter=Q(tasks__is_deleted=False, tasks__status__in=['done', 'closed']),
            ),
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=['get'], url_path='tasks')
    def version_tasks(self, request, pk=None):
        """Задачи конкретной версии."""
        version = self.get_object()
        tasks = Task.objects.filter(version=version, is_deleted=False)
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)
