import logging

from rest_framework.permissions import BasePermission, SAFE_METHODS
from .roles import has_hr_group, is_senior_hr, is_junior_hr, _is_privileged

logger = logging.getLogger('hr.permissions')


def _safe_check(fn, request, view, *, label: str) -> bool:
    """Run a permission check wrapped in try/except.

    If the check itself raises an exception (e.g. DB error while loading
    groups), we log the error and DENY access rather than crashing the
    whole request.  However, superuser/staff are ALWAYS allowed through
    before the real check runs — so they can never be locked out.
    """
    user = getattr(request, 'user', None)
    # Fast-path: privileged users bypass ALL permission checks
    if user and _is_privileged(user):
        return True
    try:
        return fn(request, view)
    except Exception:
        logger.exception(
            '403 Permission check "%s" raised for user=%s path=%s method=%s',
            label,
            getattr(user, 'username', '?'),
            request.path,
            request.method,
        )
        return False


# ---------------------------------------------------------------------------
#  1.  General HR gate — any HR role (or superuser/staff) may enter.
# ---------------------------------------------------------------------------

class IsHRManagerOrSuperuser(BasePermission):
    """
    Доступ разрешён superuser, staff или участникам любой HR-роли.
    Используется как минимальный порог на уровне роутера.
    """
    def has_permission(self, request, view):
        def _check(req, v):
            if not req.user or not req.user.is_authenticated:
                return False
            return has_hr_group(req.user)
        return _safe_check(_check, request, view, label='IsHRManagerOrSuperuser')


# ---------------------------------------------------------------------------
#  2.  Granular HR permissions
# ---------------------------------------------------------------------------

class IsSeniorHR(BasePermission):
    """
    Полные права: CRUD + утверждение офферов + управление СРО + просмотр
    логов Junior. Superuser/staff автоматически считаются Senior.
    """
    def has_permission(self, request, view):
        def _check(req, v):
            return is_senior_hr(req.user)
        return _safe_check(_check, request, view, label='IsSeniorHR')


class IsJuniorHR(BasePermission):
    """
        Ограниченные права:
        • Просмотр данных в HR-модуле
        • Запись регулируется IsJuniorHRReadOnly (только SAFE_METHODS)
        • Запрет DELETE (soft или hard)
    • Поля salary, bonus, passport_data, bank_account ФИЗИЧЕСКИ не приходят
      (обеспечивается сериализатором, а не permission)
    • Не может менять статус кандидата на «hired» (обеспечивается сериализатором)
    • Может видеть, но не может редактировать поля СРО
    """
    def has_permission(self, request, view):
        def _check(req, v):
            if not req.user or not req.user.is_authenticated:
                return False
            return is_senior_hr(req.user) or is_junior_hr(req.user)
        return _safe_check(_check, request, view, label='IsJuniorHR')


class IsJuniorHRReadOnly(BasePermission):
    """
    Junior: только безопасные методы (GET, HEAD, OPTIONS).
    Используется там, где Junior не должен иметь доступа на запись
    (например, ActionLog — только чтение).
    """
    def has_permission(self, request, view):
        def _check(req, v):
            if not req.user or not req.user.is_authenticated:
                return False
            if is_senior_hr(req.user):
                return True
            if is_junior_hr(req.user) and req.method in SAFE_METHODS:
                return True
            return False
        return _safe_check(_check, request, view, label='IsJuniorHRReadOnly')


class DenyDelete(BasePermission):
    """
    Запрещает DELETE для пользователей без Senior-уровня.
    Должен идти вторым в списке permission_classes (после основного).
    """
    def has_permission(self, request, view):
        def _check(req, v):
            if req.method == 'DELETE':
                return is_senior_hr(req.user)
            return True
        return _safe_check(_check, request, view, label='DenyDelete')


class DenySROEdit(BasePermission):
    """
    Запрещает Junior HR изменять поля СРО и охраны труда.
    Проверяется на уровне has_permission (данные не достигнут save).
    """
    SRO_FIELDS = {
        'sro_permit_number', 'sro_permit_expiry',
        'safety_cert_number', 'safety_cert_expiry',
    }

    def has_permission(self, request, view):
        def _check(req, v):
            if req.method in SAFE_METHODS:
                return True
            if is_senior_hr(req.user):
                return True
            # Junior пытается записать?
            if req.data and isinstance(req.data, dict):
                if self.SRO_FIELDS & set(req.data.keys()):
                    return False
            return True
        return _safe_check(_check, request, view, label='DenySROEdit')
