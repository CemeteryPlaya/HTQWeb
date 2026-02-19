from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Department, Position, Employee, Vacancy, Application,
    TimeTracking, Document, HRActionLog, PersonnelHistory,
)
from .serializers import (
    DepartmentSerializer, PositionSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
    VacancySerializer, ApplicationSerializer,
    TimeTrackingSerializer, DocumentSerializer,
    HRActionLogSerializer, PersonnelHistorySerializer,
)
from .permissions import IsHRManagerOrSuperuser
from .logging import log_action

User = get_user_model()


class LoggingMixin:
    """
    Миксин для автоматического логирования create / update / destroy в HR ViewSet.
    Требует атрибут `log_target_type` на ViewSet.
    """
    log_target_type: str = ''

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            self.request,
            HRActionLog.ActionType.CREATE,
            self.log_target_type,
            target=instance,
            details=f'Создано: {str(instance)}',
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request,
            HRActionLog.ActionType.UPDATE,
            self.log_target_type,
            target=instance,
            details=f'Обновлено: {str(instance)}',
        )

    def perform_destroy(self, instance):
        pk = instance.pk
        repr_str = str(instance)
        instance.delete()
        log_action(
            self.request,
            HRActionLog.ActionType.DELETE,
            self.log_target_type,
            target_id=pk,
            target_repr=repr_str,
            details=f'Удалено: {repr_str}',
        )


class DepartmentViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для отделов."""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRManagerOrSuperuser]
    pagination_class = None
    log_target_type = HRActionLog.TargetType.DEPARTMENT


class PositionViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для должностей."""
    queryset = Position.objects.select_related('department').all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRManagerOrSuperuser]
    pagination_class = None
    log_target_type = HRActionLog.TargetType.POSITION


class EmployeeViewSet(viewsets.ModelViewSet):
    """Список / детали / создание / редактирование сотрудников."""
    permission_classes = [IsHRManagerOrSuperuser]
    pagination_class = None
    log_target_type = HRActionLog.TargetType.EMPLOYEE

    @staticmethod
    def _sync_employee_statuses():
        """
        Синхронизация статусов сотрудников с одобренными отпусками.
        Вызывается при загрузке списка и статистики.
        """
        today = date.today()

        # Сотрудники, у которых сейчас есть одобренный отпуск → on_leave
        on_leave_ids = set(
            TimeTracking.objects.filter(
                status=TimeTracking.LeaveStatus.APPROVED,
                start_date__lte=today,
                end_date__gte=today,
            ).values_list('employee_id', flat=True)
        )

        # Перевести в on_leave тех, кто active, но имеет активный отпуск
        Employee.objects.filter(
            id__in=on_leave_ids,
            status=Employee.Status.ACTIVE,
        ).update(status=Employee.Status.ON_LEAVE)

        # Вернуть в active тех, кто on_leave, но активных отпусков нет
        Employee.objects.filter(
            status=Employee.Status.ON_LEAVE,
        ).exclude(
            id__in=on_leave_ids,
        ).update(status=Employee.Status.ACTIVE)

    def get_queryset(self):
        self._sync_employee_statuses()

        qs = Employee.objects.select_related(
            'user', 'position', 'department',
        ).order_by('-date_hired')
        # Фильтры по query-параметрам
        dept = self.request.query_params.get('department')
        emp_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if dept:
            qs = qs.filter(department_id=dept)
        if emp_status:
            qs = qs.filter(status=emp_status)
        if search:
            qs = qs.filter(
                user__first_name__icontains=search
            ) | qs.filter(
                user__last_name__icontains=search
            ) | qs.filter(
                user__username__icontains=search
            )
        return qs

    def get_serializer_class(self):
        return EmployeeDetailSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, HRActionLog.ActionType.CREATE,
            HRActionLog.TargetType.EMPLOYEE,
            target=instance,
            details=f'Создан сотрудник: {instance}',
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.EMPLOYEE,
            target=instance,
            details=f'Обновлён сотрудник: {instance}',
        )

    def perform_destroy(self, instance):
        pk, repr_str = instance.pk, str(instance)
        instance.delete()
        log_action(
            self.request, HRActionLog.ActionType.DELETE,
            HRActionLog.TargetType.EMPLOYEE,
            target_id=pk, target_repr=repr_str,
            details=f'Удалён сотрудник: {repr_str}',
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по сотрудникам."""
        self._sync_employee_statuses()

        qs = Employee.objects.all()
        return Response({
            'total': qs.count(),
            'active': qs.filter(status=Employee.Status.ACTIVE).count(),
            'on_leave': qs.filter(status=Employee.Status.ON_LEAVE).count(),
            'dismissed': qs.filter(status=Employee.Status.DISMISSED).count(),
        })

    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request):
        """Список пользователей для создания сотрудника (без привязки Employee)."""
        search = request.query_params.get('search', '').strip()
        qs = User.objects.filter(is_active=True).exclude(employee__isnull=False)
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
            )
        qs = qs.order_by('first_name', 'last_name', 'username')
        data = []
        for user in qs:
            full_name = user.get_full_name() or user.username
            data.append({
                'id': user.id,
                'full_name': full_name,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
        return Response(data)


class VacancyViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для вакансий + вложенные отклики."""
    permission_classes = [IsHRManagerOrSuperuser]
    serializer_class = VacancySerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.VACANCY

    def get_queryset(self):
        return Vacancy.objects.select_related(
            'department', 'created_by',
        ).annotate(
            applications_count=Count('applications'),
        ).order_by('-created_at')

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(
            self.request, HRActionLog.ActionType.CREATE,
            HRActionLog.TargetType.VACANCY,
            target=instance,
            details=f'Создана вакансия: {instance}',
        )


class ApplicationViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для откликов кандидатов."""
    permission_classes = [IsHRManagerOrSuperuser]
    serializer_class = ApplicationSerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.APPLICATION

    def get_queryset(self):
        qs = Application.objects.select_related('vacancy').order_by('-created_at')
        vacancy_id = self.request.query_params.get('vacancy')
        app_status = self.request.query_params.get('status')
        if vacancy_id:
            qs = qs.filter(vacancy_id=vacancy_id)
        if app_status:
            qs = qs.filter(status=app_status)
        return qs


class TimeTrackingViewSet(viewsets.ModelViewSet):
    """Учёт отпусков и больничных."""
    permission_classes = [IsHRManagerOrSuperuser]
    serializer_class = TimeTrackingSerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.TIME_TRACKING

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, HRActionLog.ActionType.CREATE,
            HRActionLog.TargetType.TIME_TRACKING,
            target=instance,
            details=f'Создана запись: {instance}',
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.TIME_TRACKING,
            target=instance,
            details=f'Обновлена запись: {instance}',
        )

    def get_queryset(self):
        qs = TimeTracking.objects.select_related(
            'employee__user', 'approved_by',
        ).order_by('-start_date')
        employee_id = self.request.query_params.get('employee')
        leave_type = self.request.query_params.get('leave_type')
        tt_status = self.request.query_params.get('status')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if leave_type:
            qs = qs.filter(leave_type=leave_type)
        if tt_status:
            qs = qs.filter(status=tt_status)
        return qs

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Одобрить заявку на отпуск/больничный."""
        record = self.get_object()
        record.status = TimeTracking.LeaveStatus.APPROVED
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by', 'updated_at'])

        log_action(
            request, HRActionLog.ActionType.APPROVE,
            HRActionLog.TargetType.TIME_TRACKING,
            target=record,
            details=f'Одобрена заявка: {record}',
        )

        # Автоматически обновить статус сотрудника
        today = date.today()
        employee = record.employee
        if record.start_date <= today <= record.end_date:
            # Период отпуска покрывает сегодня — ставим «в отпуске»
            if employee.status != Employee.Status.DISMISSED:
                old_status = employee.status
                employee.status = Employee.Status.ON_LEAVE
                employee.save(update_fields=['status', 'updated_at'])
                log_action(
                    request, HRActionLog.ActionType.STATUS_CHANGE,
                    HRActionLog.TargetType.EMPLOYEE,
                    target=employee,
                    details=f'Статус изменён: {old_status} → on_leave (одобрен отпуск)',
                )

        return Response(TimeTrackingSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Отклонить заявку."""
        record = self.get_object()
        record.status = TimeTracking.LeaveStatus.REJECTED
        record.approved_by = request.user
        record.save(update_fields=['status', 'approved_by', 'updated_at'])

        log_action(
            request, HRActionLog.ActionType.REJECT,
            HRActionLog.TargetType.TIME_TRACKING,
            target=record,
            details=f'Отклонена заявка: {record}',
        )

        # Если сотрудник сейчас «в отпуске» и других активных отпусков нет — вернуть «активен»
        employee = record.employee
        if employee.status == Employee.Status.ON_LEAVE:
            today = date.today()
            has_other_active_leave = TimeTracking.objects.filter(
                employee=employee,
                status=TimeTracking.LeaveStatus.APPROVED,
                start_date__lte=today,
                end_date__gte=today,
            ).exclude(pk=record.pk).exists()
            if not has_other_active_leave:
                employee.status = Employee.Status.ACTIVE
                employee.save(update_fields=['status', 'updated_at'])
                log_action(
                    request, HRActionLog.ActionType.STATUS_CHANGE,
                    HRActionLog.TargetType.EMPLOYEE,
                    target=employee,
                    details=f'Статус изменён: on_leave → active (отпуск отклонён)',
                )

        return Response(TimeTrackingSerializer(record).data)

    def perform_destroy(self, instance):
        """При удалении записи — обновить статус сотрудника."""
        employee = instance.employee
        was_approved = instance.status == TimeTracking.LeaveStatus.APPROVED
        pk, repr_str = instance.pk, str(instance)
        instance.delete()

        log_action(
            self.request, HRActionLog.ActionType.DELETE,
            HRActionLog.TargetType.TIME_TRACKING,
            target_id=pk, target_repr=repr_str,
            details=f'Удалена запись: {repr_str}',
        )

        if was_approved and employee.status == Employee.Status.ON_LEAVE:
            today = date.today()
            has_other_active_leave = TimeTracking.objects.filter(
                employee=employee,
                status=TimeTracking.LeaveStatus.APPROVED,
                start_date__lte=today,
                end_date__gte=today,
            ).exists()
            if not has_other_active_leave:
                employee.status = Employee.Status.ACTIVE
                employee.save(update_fields=['status', 'updated_at'])
                log_action(
                    self.request, HRActionLog.ActionType.STATUS_CHANGE,
                    HRActionLog.TargetType.EMPLOYEE,
                    target=employee,
                    details=f'Статус изменён: on_leave → active (запись удалена)',
                )


class DocumentViewSet(viewsets.ModelViewSet):
    """Управление трудовыми документами."""
    permission_classes = [IsHRManagerOrSuperuser]
    serializer_class = DocumentSerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.DOCUMENT

    def get_queryset(self):
        qs = Document.objects.select_related(
            'employee__user', 'uploaded_by',
        ).order_by('-created_at')
        employee_id = self.request.query_params.get('employee')
        doc_type = self.request.query_params.get('doc_type')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(uploaded_by=self.request.user)
        log_action(
            self.request, HRActionLog.ActionType.CREATE,
            HRActionLog.TargetType.DOCUMENT,
            target=instance,
            details=f'Загружен документ: {instance}',
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.DOCUMENT,
            target=instance,
            details=f'Обновлён документ: {instance}',
        )

    def perform_destroy(self, instance):
        pk, repr_str = instance.pk, str(instance)
        instance.delete()
        log_action(
            self.request, HRActionLog.ActionType.DELETE,
            HRActionLog.TargetType.DOCUMENT,
            target_id=pk, target_repr=repr_str,
            details=f'Удалён документ: {repr_str}',
        )


class HRActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр журнала действий (только чтение, только админы)."""
    permission_classes = [IsAdminUser]
    serializer_class = HRActionLogSerializer
    pagination_class = None

    def get_queryset(self):
        qs = HRActionLog.objects.select_related(
            'user', 'employee__user', 'department', 'position'
        ).order_by('-created_at')
        # Фильтры
        action_type = self.request.query_params.get('action')
        target_type = self.request.query_params.get('target_type')
        module = self.request.query_params.get('module')
        user_id = self.request.query_params.get('user')
        employee_id = self.request.query_params.get('employee')
        department_id = self.request.query_params.get('department')
        position_id = self.request.query_params.get('position')
        search = self.request.query_params.get('search')
        if action_type:
            qs = qs.filter(action=action_type)
        if target_type:
            qs = qs.filter(target_type=target_type)
        if module:
            qs = qs.filter(module=module)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if department_id:
            qs = qs.filter(department_id=department_id)
        if position_id:
            qs = qs.filter(position_id=position_id)
        if search:
            qs = qs.filter(
                Q(target_repr__icontains=search)
                | Q(details__icontains=search)
            )
        return qs[:500]  # Ограничение — последние 500 записей


class PersonnelHistoryViewSet(LoggingMixin, viewsets.ModelViewSet):
    """Кадровая история сотрудников."""
    permission_classes = [IsHRManagerOrSuperuser]
    serializer_class = PersonnelHistorySerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.EMPLOYEE

    def get_queryset(self):
        qs = PersonnelHistory.objects.select_related(
            'employee__user', 'from_department', 'to_department',
            'from_position', 'to_position', 'created_by',
        ).order_by('-event_date', '-created_at')
        employee_id = self.request.query_params.get('employee')
        event_type = self.request.query_params.get('event_type')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
