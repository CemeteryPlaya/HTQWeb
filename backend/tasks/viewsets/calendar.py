from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from hr.permissions import IsSeniorHR

from ..models import CalendarEvent, ProductionDay
from ..serializers import CalendarEventSerializer, ProductionDaySerializer, TaskListSerializer
from ..services import (
    apply_timeline_date_window,
    filter_calendar_events_for_user,
    get_visible_calendar_events,
    get_visible_timeline_tasks,
    inject_production_day_notes,
)


class ProductionDayViewSet(viewsets.ModelViewSet):
    """API для управления производственным календарем."""

    queryset = ProductionDay.objects.all()
    serializer_class = ProductionDaySerializer
    permission_classes = [IsSeniorHR]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()

        date_from = self.request.query_params.get('date__gte')
        date_to = self.request.query_params.get('date__lte')

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        data = [dict(item) for item in serializer.data]
        inject_production_day_notes(data)

        return Response(data)


class CalendarEventViewSet(viewsets.ModelViewSet):
    """API для событий календаря с ABAC-фильтрацией."""

    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = CalendarEvent.objects.select_related('creator', 'department').prefetch_related('exceptions')
        return filter_calendar_events_for_user(queryset, self.request.user)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class CalendarTimelineViewSet(viewsets.ViewSet):
    """Агрегированный endpoint календаря (задачи + события)."""

    permission_classes = [AllowAny]

    def list(self, request):
        tasks = get_visible_timeline_tasks(request.user)
        events = get_visible_calendar_events(request.user)

        date_from = request.query_params.get('start')
        date_to = request.query_params.get('end')
        tasks, events = apply_timeline_date_window(
            tasks,
            events,
            date_from=date_from,
            date_to=date_to,
        )

        return Response(
            {
                'tasks': TaskListSerializer(tasks, many=True).data,
                'events': CalendarEventSerializer(events, many=True).data,
            }
        )
