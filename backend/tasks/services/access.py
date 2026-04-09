from __future__ import annotations

from django.db.models import Q, QuerySet

from hr.roles import _is_privileged, has_hr_group

from ..models import CalendarEvent


def has_global_task_access(user) -> bool:
    """Return True when a user may browse all tasks without per-task filtering."""
    return bool(getattr(user, 'is_authenticated', False)) and (
        _is_privileged(user) or has_hr_group(user)
    )


def get_user_department(user):
    """Safely extract related employee department if present."""
    employee = getattr(user, 'employee', None)
    return getattr(employee, 'department', None)


def build_task_visibility_filter(user, *, prefix: str = '') -> Q:
    """Build visibility Q for task model or relations that point to task fields."""
    q_filter = Q(**{f'{prefix}assignee': user}) | Q(**{f'{prefix}reporter': user})
    department = get_user_department(user)
    if department:
        q_filter |= Q(**{f'{prefix}department': department})
    return q_filter


def filter_tasks_for_user(queryset: QuerySet, user) -> QuerySet:
    """Apply standard task visibility rules to queryset."""
    if has_global_task_access(user):
        return queryset
    return queryset.filter(build_task_visibility_filter(user))


def filter_related_tasks_for_user(queryset: QuerySet, user, *, task_prefix: str) -> QuerySet:
    """Apply task visibility rules to querysets related through a task foreign key."""
    if has_global_task_access(user):
        return queryset
    return queryset.filter(build_task_visibility_filter(user, prefix=task_prefix))


def filter_timeline_tasks_for_user(queryset: QuerySet, user) -> QuerySet:
    """
    Timeline intentionally stays personal:
    even privileged users see only tasks directly relevant to them.
    """
    if not getattr(user, 'is_authenticated', False):
        return queryset.none()
    return queryset.filter(build_task_visibility_filter(user)).distinct()


def filter_calendar_events_for_user(queryset: QuerySet, user) -> QuerySet:
    """Apply calendar ABAC rules for common/department/personal events."""
    if not getattr(user, 'is_authenticated', False):
        return queryset.filter(event_type=CalendarEvent.EventType.COMMON)

    if has_global_task_access(user):
        return queryset

    visibility_filter = Q(event_type=CalendarEvent.EventType.COMMON)
    visibility_filter |= Q(creator=user)

    department = get_user_department(user)
    if department:
        visibility_filter |= Q(
            department=department,
            event_type=CalendarEvent.EventType.DEPARTMENT,
        )

    return queryset.filter(visibility_filter).distinct()
