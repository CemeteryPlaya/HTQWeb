from datetime import date

from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from hr.permissions import IsHRManagerOrSuperuser

from .models import Label, ProjectVersion, Task, TaskComment, TaskAttachment
from .serializers import (
    LabelSerializer, ProjectVersionSerializer,
    TaskListSerializer, TaskDetailSerializer,
    TaskCommentSerializer, TaskAttachmentSerializer,
)


# ---------------------------------------------------------------------------
#   Task-management ViewSets
# ---------------------------------------------------------------------------


class LabelViewSet(viewsets.ModelViewSet):
    """CRUD для меток задач."""
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    permission_classes = [IsHRManagerOrSuperuser]


class ProjectVersionViewSet(viewsets.ModelViewSet):
    """CRUD для версий / релизов."""
    serializer_class = ProjectVersionSerializer
    permission_classes = [IsHRManagerOrSuperuser]

    def get_queryset(self):
        qs = ProjectVersion.objects.annotate(
            task_count=Count('tasks', filter=Q(tasks__is_deleted=False)),
            done_count=Count(
                'tasks',
                filter=Q(tasks__is_deleted=False, tasks__status__in=['done', 'closed']),
            ),
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=['get'], url_path='tasks')
    def version_tasks(self, request, pk=None):
        """Задачи конкретной версии."""
        version = self.get_object()
        tasks = Task.objects.filter(version=version, is_deleted=False)
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)


from rest_framework.permissions import IsAuthenticated
from hr.roles import has_hr_group, is_senior_hr, is_junior_hr, _is_privileged

class TaskViewSet(viewsets.ModelViewSet):
    """CRUD для задач (Jira-like issues)."""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        return TaskDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.select_related(
            'reporter', 'assignee', 'department', 'version', 'parent',
        ).prefetch_related('labels').annotate(
            subtask_count=Count('subtasks', filter=Q(subtasks__is_deleted=False)),
        ).filter(is_deleted=False)

        # Access Control
        if _is_privileged(user) or has_hr_group(user):
            # HR/Superuser see all
            pass
        else:
            # Regular users:
            # 1. Assigned to them
            # 2. Reported by them
            # 3. Belonging to their department (if they are an Employee)
            filters = Q(assignee=user) | Q(reporter=user)
            
            if hasattr(user, 'employee') and user.employee.department:
                filters |= Q(department=user.employee.department)
            
            qs = qs.filter(filters)

        # Различные фильтры API
        params = self.request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('priority'):
            qs = qs.filter(priority=params['priority'])
        if params.get('task_type'):
            qs = qs.filter(task_type=params['task_type'])
        if params.get('assignee'):
            qs = qs.filter(assignee_id=params['assignee'])
        if params.get('reporter'):
            qs = qs.filter(reporter_id=params['reporter'])
        if params.get('department'):
            qs = qs.filter(department_id=params['department'])
        if params.get('version'):
            qs = qs.filter(version_id=params['version'])
        if params.get('parent'):
            qs = qs.filter(parent_id=params['parent'])
        if params.get('label'):
            qs = qs.filter(labels__id=params['label'])
        if params.get('search'):
            q = params['search']
            qs = qs.filter(Q(summary__icontains=q) | Q(key__icontains=q) | Q(description__icontains=q))
        return qs.distinct()

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

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Статистика задач для отчётов."""
        qs = Task.objects.filter(is_deleted=False)

        # Фильтр по датам
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        by_status = dict(qs.values_list('status').annotate(c=Count('id')).order_by('status'))
        by_priority = dict(qs.values_list('priority').annotate(c=Count('id')).order_by('priority'))
        by_type = dict(qs.values_list('task_type').annotate(c=Count('id')).order_by('task_type'))

        by_department = list(
            qs.filter(department__isnull=False)
            .values('department__id', 'department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        by_assignee = list(
            qs.filter(assignee__isnull=False)
            .values('assignee__id', 'assignee__first_name', 'assignee__last_name', 'assignee__username')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Created vs Resolved по дням (последние 30 дней)
        from datetime import timedelta
        today = date.today()
        period_start = today - timedelta(days=30)

        created_per_day = list(
            qs.filter(created_at__date__gte=period_start)
            .extra({'day': "date(created_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        resolved_per_day = list(
            qs.filter(
                completed_at__isnull=False,
                completed_at__date__gte=period_start,
            )
            .extra({'day': "date(completed_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        return Response({
            'total': qs.count(),
            'by_status': by_status,
            'by_priority': by_priority,
            'by_type': by_type,
            'by_department': by_department,
            'by_assignee': by_assignee,
            'created_per_day': created_per_day,
            'resolved_per_day': resolved_per_day,
        })


class TaskCommentViewSet(viewsets.ModelViewSet):
    """CRUD комментариев (также доступно через task/{id}/comments)."""
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TaskComment.objects.select_related('author', 'task')
        
        # Filter comments based on task visibility
        user = self.request.user
        if not (_is_privileged(user) or has_hr_group(user)):
             # Regular users: see comments only for tasks they can see
            filters = Q(task__assignee=user) | Q(task__reporter=user)
            if hasattr(user, 'employee') and user.employee.department:
                filters |= Q(task__department=user.employee.department)
            qs = qs.filter(filters)

        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """CRUD вложений."""
    serializer_class = TaskAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TaskAttachment.objects.select_related('uploaded_by', 'task')
        
        # Filter attachments based on task visibility
        user = self.request.user
        if not (_is_privileged(user) or has_hr_group(user)):
             # Regular users: see attachments only for tasks they can see
            filters = Q(task__assignee=user) | Q(task__reporter=user)
            if hasattr(user, 'employee') and user.employee.department:
                filters |= Q(task__department=user.employee.department)
            qs = qs.filter(filters)

        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
