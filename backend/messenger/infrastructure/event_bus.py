"""
Event Bus — bridges external Django signals to the messenger domain.

Listens for ``post_save`` on:
- ``auth.User``       → sync username, full_name
- ``mainView.Profile`` → sync avatar_url
- ``hr.Employee``     → sync department_path, position_title

All handlers create or update ``ChatUserReplica`` rows WITHOUT making
any reverse imports or FK references to the source models. The data
flows one-way: external app → signal → event_bus → ChatUserReplica.

Usage:
    Called from ``MessengerConfig.ready()`` to register signal handlers.
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _build_department_path(employee) -> str:
    """
    Build a materialized path from the employee's department chain.

    Since the current Department model is flat (no parent FK), we build
    a simple path: ``{department_index}.{department_name_slug}``.

    If the Department model acquires a ``parent`` FK in the future,
    this function should walk up the chain to build a full path like
    ``Global.Engineering.Backend``.
    """
    if not employee.department:
        return ''

    dept = employee.department
    # Sanitise name for ltree: replace spaces/dots with underscores
    safe_name = (dept.name or '').replace(' ', '_').replace('.', '_')
    # Use the department index as a prefix for ordering
    dept_index = dept.index or 0
    return f'Dept{dept_index}.{safe_name}'


def _get_avatar_url(user) -> str:
    """Extract avatar URL from the user's Profile, if it exists."""
    try:
        profile = user.profile
        if profile.avatar:
            return profile.avatar.url
    except Exception:
        pass
    return ''


def _sync_user_replica(user) -> None:
    """
    Create or update ChatUserReplica from the given auth.User instance.

    Pulls data from:
    - auth.User: username, first_name, last_name
    - mainView.Profile: avatar (if exists)
    - hr.Employee: department, position (if exists)
    """
    from messenger.domain.models import ChatUserReplica

    full_name = user.get_full_name() or user.username

    # Extract profile data
    avatar_url = _get_avatar_url(user)

    # Extract employee/department data
    department_path = ''
    department_name = ''
    position_title = ''
    try:
        emp = user.employee
        department_path = _build_department_path(emp)
        department_name = emp.department.name if emp.department else ''
        position_title = emp.position.title if emp.position else ''
    except Exception:
        pass

    ChatUserReplica.objects.update_or_create(
        user_id=user.pk,
        defaults={
            'username': user.username,
            'full_name': full_name,
            'avatar_url': avatar_url,
            'department_path': department_path,
            'department_name': department_name,
            'position_title': position_title,
        },
    )
    logger.debug('ChatUserReplica synced for user_id=%s', user.pk)


def connect_signals():
    """
    Register post_save signal handlers.

    Must be called from ``MessengerConfig.ready()`` — NOT at module
    import time — to avoid AppRegistryNotReady errors.
    """
    User = settings.AUTH_USER_MODEL

    @receiver(post_save, sender=User)
    def on_user_save(sender, instance, **kwargs):
        _sync_user_replica(instance)

    # Profile model (mainView app)
    try:
        from mainView.models import Profile  # noqa: lazy import

        @receiver(post_save, sender=Profile)
        def on_profile_save(sender, instance, **kwargs):
            _sync_user_replica(instance.user)
    except ImportError:
        logger.warning('mainView.Profile not found — avatar sync disabled.')

    # Employee model (hr app)
    try:
        from hr.models import Employee  # noqa: lazy import

        @receiver(post_save, sender=Employee)
        def on_employee_save(sender, instance, **kwargs):
            _sync_user_replica(instance.user)
    except ImportError:
        logger.warning('hr.Employee not found — department sync disabled.')

    # Department model (hr app) — when a department is renamed, update all replicas
    try:
        from hr.models import Department  # noqa: lazy import

        @receiver(post_save, sender=Department)
        def on_department_save(sender, instance, **kwargs):
            from hr.models import Employee as Emp
            from messenger.domain.models import ChatUserReplica

            # Re-sync all employees in this department
            for emp in Emp.objects.filter(department=instance).select_related('user'):
                _sync_user_replica(emp.user)
    except ImportError:
        logger.warning('hr.Department not found — department rename sync disabled.')

    logger.info('Messenger event bus: signal handlers connected.')
