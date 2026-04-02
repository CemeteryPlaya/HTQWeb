from __future__ import annotations

from ..models import Notification


def create_task_comment_notifications(*, comment, actor) -> int:
    """Create notifications for task assignee/reporter when a new comment appears."""
    task = comment.task

    recipient_ids: set[int] = set()
    recipients = []

    for candidate in (task.assignee, task.reporter):
        if not candidate or candidate == actor:
            continue
        if candidate.id in recipient_ids:
            continue
        recipient_ids.add(candidate.id)
        recipients.append(candidate)

    notifications = [
        Notification(
            recipient=recipient,
            actor=actor,
            task=task,
            verb='оставил(а) новый комментарий в задаче',
        )
        for recipient in recipients
    ]

    if notifications:
        Notification.objects.bulk_create(notifications)

    return len(notifications)
