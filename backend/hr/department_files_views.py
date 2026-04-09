"""
API views for department folders and files.

Access rules:
- superuser / staff → see ALL folders, manage ALL files
- regular employee  → see only their own department folder / files
- unauthenticated   → 403
"""
import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .department_files import DepartmentFolder, DepartmentFile
from .department_files_serializers import (
    DepartmentFolderSerializer,
    DepartmentFileSerializer,
)

logger = logging.getLogger('hr.department_files')


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_employee_department(user):
    """Return the Department instance for the user, or None."""
    if not user or not user.is_authenticated:
        return None
    emp = getattr(user, 'employee', None)
    if emp is None:
        return None
    return emp.department


def _is_privileged(user):
    return bool(
        getattr(user, 'is_superuser', False)
        or getattr(user, 'is_staff', False)
    )


def _ensure_folder(department):
    """Get-or-create a folder for the department."""
    folder, _ = DepartmentFolder.objects.get_or_create(department=department)
    return folder


# ---------------------------------------------------------------------------
#  Permissions
# ---------------------------------------------------------------------------

class IsSameDepartmentOrAdmin(permissions.BasePermission):
    """
    Allow access only if the user belongs to the same department as the
    folder/file, or is superuser/staff.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if _is_privileged(request.user):
            return True
        dept = _get_employee_department(request.user)
        return dept is not None

    def has_object_permission(self, request, view, obj):
        if _is_privileged(request.user):
            return True
        dept = _get_employee_department(request.user)
        if dept is None:
            return False
        # obj can be DepartmentFolder or DepartmentFile
        if isinstance(obj, DepartmentFolder):
            return obj.department_id == dept.id
        if isinstance(obj, DepartmentFile):
            return obj.folder.department_id == dept.id
        return False


# ---------------------------------------------------------------------------
#  Folder ViewSet
# ---------------------------------------------------------------------------

class DepartmentFolderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/hr/department-folders/       → list (filtered by user dept)
    GET /api/hr/department-folders/<id>/   → detail
    """
    serializer_class = DepartmentFolderSerializer
    permission_classes = [IsSameDepartmentOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if _is_privileged(user):
            return DepartmentFolder.objects.select_related('department').all()
        dept = _get_employee_department(user)
        if dept is None:
            return DepartmentFolder.objects.none()
        # Ensure the folder exists
        _ensure_folder(dept)
        return DepartmentFolder.objects.select_related('department').filter(
            department=dept,
        )


# ---------------------------------------------------------------------------
#  File ViewSet
# ---------------------------------------------------------------------------

class DepartmentFileViewSet(viewsets.ModelViewSet):
    """
    CRUD for files inside department folders.

    GET    /api/hr/department-files/?folder=<id>   → list
    POST   /api/hr/department-files/               → upload (multipart)
    DELETE /api/hr/department-files/<id>/           → delete
    """
    serializer_class = DepartmentFileSerializer
    permission_classes = [IsSameDepartmentOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = DepartmentFile.objects.select_related(
            'folder__department', 'uploaded_by',
        )
        if _is_privileged(user):
            pass  # no filter — admin sees all
        else:
            dept = _get_employee_department(user)
            if dept is None:
                return qs.none()
            qs = qs.filter(folder__department=dept)

        # Optional folder filter
        folder_id = self.request.query_params.get('folder')
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        return qs

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get('file')
        file_size = uploaded_file.size if uploaded_file else 0
        name = self.request.data.get('name') or (
            uploaded_file.name if uploaded_file else 'Без имени'
        )

        folder_id = self.request.data.get('folder')

        # Security: verify the user has access to this folder
        try:
            folder = DepartmentFolder.objects.select_related('department').get(
                pk=folder_id,
            )
        except DepartmentFolder.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Папка не найдена')

        if not _is_privileged(self.request.user):
            dept = _get_employee_department(self.request.user)
            if dept is None or folder.department_id != dept.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Нет доступа к этой папке')

        serializer.save(
            uploaded_by=self.request.user,
            file_size=file_size,
            name=name,
            folder=folder,
        )
        logger.info(
            '[DepartmentFile] user=%s uploaded file=%s to folder=%s',
            self.request.user.username, name, folder,
        )

    def perform_destroy(self, instance):
        logger.info(
            '[DepartmentFile] user=%s deleted file=%s from folder=%s',
            self.request.user.username, instance.name, instance.folder,
        )
        # Delete the physical file as well
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
