from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate

from ..models import Task


def _build_stats_queryset(params):
    queryset = Task.objects.filter(is_deleted=False)

    date_from = params.get('date_from')
    date_to = params.get('date_to')

    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset


def _aggregate_counts(queryset, field_name: str) -> dict:
    return dict(
        queryset.values(field_name)
        .annotate(count=Count('id'))
        .order_by(field_name)
        .values_list(field_name, 'count')
    )


def build_task_stats(params) -> dict:
    """Compose response payload for task statistics endpoint."""
    queryset = _build_stats_queryset(params)

    by_status = _aggregate_counts(queryset, 'status')
    by_priority = _aggregate_counts(queryset, 'priority')
    by_type = _aggregate_counts(queryset, 'task_type')

    by_department = list(
        queryset.filter(department__isnull=False)
        .values('department__id', 'department__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    by_assignee = list(
        queryset.filter(assignee__isnull=False)
        .values(
            'assignee__id',
            'assignee__first_name',
            'assignee__last_name',
            'assignee__username',
        )
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )

    period_start = date.today() - timedelta(days=30)

    created_per_day = list(
        queryset.filter(created_at__date__gte=period_start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    resolved_per_day = list(
        queryset.filter(
            completed_at__isnull=False,
            completed_at__date__gte=period_start,
        )
        .annotate(day=TruncDate('completed_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    return {
        'total': queryset.count(),
        'by_status': by_status,
        'by_priority': by_priority,
        'by_type': by_type,
        'by_department': by_department,
        'by_assignee': by_assignee,
        'created_per_day': created_per_day,
        'resolved_per_day': resolved_per_day,
    }
