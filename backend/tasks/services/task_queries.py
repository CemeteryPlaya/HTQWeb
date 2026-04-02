from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from ..models import Task
from .access import filter_tasks_for_user


TASK_FILTER_LOOKUPS = {
    'status': 'status',
    'priority': 'priority',
    'task_type': 'task_type',
    'assignee': 'assignee_id',
    'reporter': 'reporter_id',
    'department': 'department_id',
    'version': 'version_id',
    'parent': 'parent_id',
    'label': 'labels__id',
}


def build_base_task_queryset() -> QuerySet:
    """Return shared base queryset for task list/detail APIs."""
    return (
        Task.objects.select_related(
            'reporter',
            'assignee',
            'department',
            'version',
            'parent',
        )
        .prefetch_related('labels')
        .annotate(
            subtask_count=Count('subtasks', filter=Q(subtasks__is_deleted=False)),
        )
        .filter(is_deleted=False)
    )


def apply_task_query_filters(queryset: QuerySet, params) -> QuerySet:
    """Apply standard query-parameter filters for task APIs."""
    for param_name, field_lookup in TASK_FILTER_LOOKUPS.items():
        value = params.get(param_name)
        if value:
            queryset = queryset.filter(**{field_lookup: value})

    search = params.get('search')
    if search:
        queryset = queryset.filter(
            Q(summary__icontains=search)
            | Q(key__icontains=search)
            | Q(description__icontains=search)
        )

    return queryset.distinct()


def get_task_queryset_for_request(user, params) -> QuerySet:
    """Build task queryset with access control + query filters."""
    queryset = build_base_task_queryset()
    queryset = filter_tasks_for_user(queryset, user)
    return apply_task_query_filters(queryset, params)
