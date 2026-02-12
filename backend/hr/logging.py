from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import AnonymousUser

from .models import (
    HRActionLog, Employee, Department, Position,
    TimeTracking, Document, Vacancy, Application,
)


def _get_client_ip(request) -> Optional[str]:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _apply_target_context(target, employee, department, position):
    if isinstance(target, Employee):
        employee = target
        department = target.department
        position = target.position
    elif isinstance(target, Department):
        department = target
    elif isinstance(target, Position):
        position = target
        department = target.department
    elif isinstance(target, TimeTracking):
        employee = target.employee
        if employee:
            department = employee.department
            position = employee.position
    elif isinstance(target, Document):
        employee = target.employee
        if employee:
            department = employee.department
            position = employee.position
    elif isinstance(target, Vacancy):
        department = target.department
    elif isinstance(target, Application):
        if target.vacancy:
            department = target.vacancy.department

    return employee, department, position


def log_action(
    request,
    action: str,
    target_type: str,
    *,
    target=None,
    target_id: Optional[int] = None,
    target_repr: str = '',
    details: str = '',
    employee: Optional[Employee] = None,
    department: Optional[Department] = None,
    position: Optional[Position] = None,
):
    user = request.user if request and getattr(request, 'user', None) else None
    if isinstance(user, AnonymousUser):
        user = None

    if target is None and user and target_type == HRActionLog.TargetType.EMPLOYEE:
        if hasattr(user, 'employee'):
            target = user.employee

    if target is not None:
        if target_id is None:
            target_id = getattr(target, 'pk', None)
        if not target_repr:
            target_repr = str(target)

    employee, department, position = _apply_target_context(
        target, employee, department, position
    )

    if not employee and user and hasattr(user, 'employee'):
        employee = user.employee
        department = employee.department
        position = employee.position

    HRActionLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_repr=str(target_repr)[:500],
        details=str(details)[:2000],
        ip_address=_get_client_ip(request),
        employee=employee,
        department=department,
        position=position,
    )
