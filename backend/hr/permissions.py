from rest_framework.permissions import BasePermission


class IsHRManagerOrSuperuser(BasePermission):
    """
    Доступ разрешён только superuser или участникам группы HR_Manager.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='HR_Manager').exists()
