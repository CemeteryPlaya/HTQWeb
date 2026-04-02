from __future__ import annotations

import datetime

from django.db.models import Q, QuerySet

from ..models import CalendarEvent
from ..utils.calendar import generate_calendar_days
from .access import filter_calendar_events_for_user, filter_timeline_tasks_for_user
from .task_queries import build_base_task_queryset


def inject_production_day_notes(serialized_days: list[dict]) -> list[dict]:
    """Enrich serialized production-calendar days with configured holiday notes."""
    if not serialized_days:
        return serialized_days

    years = {
        datetime.datetime.strptime(day['date'], '%Y-%m-%d').year
        for day in serialized_days
        if day.get('date')
    }

    holiday_maps: dict[int, dict[str, str]] = {}
    for year in years:
        days_info = generate_calendar_days(year)
        holiday_maps[year] = {
            entry['date'].strftime('%Y-%m-%d'): entry['note']
            for entry in days_info
            if entry.get('note')
        }

    for day in serialized_days:
        day_date = day.get('date')
        if not day_date:
            continue

        year = int(day_date.split('-')[0])
        note = holiday_maps.get(year, {}).get(day_date)
        if note:
            day['note'] = note

    return serialized_days


def get_visible_timeline_tasks(user) -> QuerySet:
    """Return timeline tasks using personal relevance rules."""
    queryset = build_base_task_queryset()
    return filter_timeline_tasks_for_user(queryset, user)


def get_visible_calendar_events(user) -> QuerySet:
    """Return calendar events visible to current user according to ABAC."""
    queryset = CalendarEvent.objects.select_related('creator', 'department').prefetch_related('exceptions')
    return filter_calendar_events_for_user(queryset, user)


def apply_timeline_date_window(tasks: QuerySet, events: QuerySet, *, date_from, date_to):
    """Apply shared [start, end] window to tasks and calendar events."""
    if date_from:
        tasks = tasks.filter(Q(due_date__gte=date_from) | Q(start_date__gte=date_from))
        events = events.filter(start_at__date__gte=date_from)

    if date_to:
        tasks = tasks.filter(Q(due_date__lte=date_to) | Q(start_date__lte=date_to))
        events = events.filter(start_at__date__lte=date_to)

    return tasks, events
