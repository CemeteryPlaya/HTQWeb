from __future__ import annotations

from rest_framework.exceptions import ValidationError


def validate_task_link_cycle(*, source, target, link_type: str) -> None:
    """Protect `blocks` graph from cycles before saving a link."""
    if link_type != 'blocks':
        return

    visited: set[int] = set()

    def has_cycle(current_task) -> bool:
        if current_task.id == source.id:
            return True
        if current_task.id in visited:
            return False

        visited.add(current_task.id)
        for outgoing_link in current_task.outgoing_links.filter(link_type='blocks'):
            if has_cycle(outgoing_link.target):
                return True

        return False

    if has_cycle(target):
        raise ValidationError('Создание связи приведёт к циклической блокировке.')
