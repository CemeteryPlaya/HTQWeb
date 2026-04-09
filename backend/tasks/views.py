"""Compatibility module for task viewsets.

The implementation now lives in ``tasks.viewsets`` to keep each domain focused
and easier to maintain.
"""

from .viewsets import (
    CalendarEventViewSet,
    CalendarTimelineViewSet,
    LabelViewSet,
    NotificationViewSet,
    ProductionDayViewSet,
    ProjectVersionViewSet,
    TaskAttachmentViewSet,
    TaskCommentViewSet,
    TaskLinkViewSet,
    TaskViewSet,
)

__all__ = [
    'CalendarEventViewSet',
    'CalendarTimelineViewSet',
    'LabelViewSet',
    'NotificationViewSet',
    'ProductionDayViewSet',
    'ProjectVersionViewSet',
    'TaskAttachmentViewSet',
    'TaskCommentViewSet',
    'TaskLinkViewSet',
    'TaskViewSet',
]
