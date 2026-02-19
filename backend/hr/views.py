from datetime import date
from django.utils import timezone
from django.utils.text import slugify

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Department, Position, Employee, Vacancy, Application,
    TimeTracking, Document, HRActionLog, PersonnelHistory,
    EmployeeAccount, _generate_password,
)
from .serializers import (
    DepartmentSerializer, PositionSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
    VacancySerializer, ApplicationSerializer,
    TimeTrackingSerializer, DocumentSerializer,
    HRActionLogSerializer, PersonnelHistorySerializer,
    EmployeeAccountSerializer,
)
from .permissions import (
    IsHRManagerOrSuperuser, IsSeniorHR, IsJuniorHR, IsJuniorHRReadOnly, DenyDelete, DenySROEdit,
)
from .roles import is_senior_hr, get_hr_level, _user_group_names, _is_privileged
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
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHRReadOnly, DenyDelete]
    pagination_class = None
    log_target_type = HRActionLog.TargetType.DEPARTMENT


class PositionViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для должностей."""
    queryset = Position.objects.select_related('department').all()
    serializer_class = PositionSerializer
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHRReadOnly, DenyDelete]
    pagination_class = None
    log_target_type = HRActionLog.TargetType.POSITION


class EmployeeViewSet(viewsets.ModelViewSet):
    """Список / детали / создание / редактирование сотрудников."""
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHRReadOnly, DenyDelete, DenySROEdit]
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
        # Detect financial field changes for explicit audit trail
        _FINANCIAL = {'salary', 'bonus', 'passport_data', 'bank_account'}
        changed_financial = []
        if serializer.instance:
            for field in _FINANCIAL:
                old_val = getattr(serializer.instance, field, None)
                new_val = serializer.validated_data.get(field, old_val)
                if new_val != old_val:
                    changed_financial.append(field)

        instance = serializer.save()

        base_detail = f'Обновлён сотрудник: {instance}'
        if changed_financial:
            base_detail += f' | Изменены финансовые поля: {", ".join(changed_financial)}'

        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.EMPLOYEE,
            target=instance,
            details=base_detail,
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

    @action(detail=False, methods=['get'], url_path='hr-level')
    def hr_level(self, request):
        """Возвращает текущий HR-уровень пользователя."""
        from .roles import get_hr_level
        level = get_hr_level(request.user)
        return Response({'level': level})


class VacancyViewSet(LoggingMixin, viewsets.ModelViewSet):
    """CRUD для вакансий + вложенные отклики."""
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHR, DenyDelete]
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
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHR, DenyDelete]
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

    @staticmethod
    def _build_unique_username(base: str) -> str:
        candidate = slugify(base or 'employee').replace('-', '_') or 'employee'
        candidate = candidate[:120]
        username = candidate
        idx = 1
        while User.objects.filter(username=username).exists():
            suffix = f'_{idx}'
            username = f'{candidate[:120-len(suffix)]}{suffix}'
            idx += 1
        return username

    def _get_or_create_employee_for_application(self, application: Application):
        user = User.objects.filter(email__iexact=application.email).first()
        raw_password = _generate_password()
        if not user:
            base_username = application.email.split('@')[0] if application.email else f"candidate_{application.id}"
            user = User.objects.create(
                username=self._build_unique_username(base_username),
                email=application.email,
                first_name=application.first_name,
                last_name=application.last_name,
                is_active=True,
            )
            user.set_password(raw_password)
            user.save(update_fields=['password'])
        else:
            # Existing user — set a new password so they can log in
            user.set_password(raw_password)
            user.save(update_fields=['password'])

        employee, created = Employee.objects.get_or_create(
            user=user,
            defaults={
                'phone': application.phone,
                'date_hired': timezone.localdate(),
                'status': Employee.Status.ACTIVE,
                'department': application.vacancy.department,
            },
        )

        changed = []
        if not created:
            if not employee.date_hired:
                employee.date_hired = timezone.localdate()
                changed.append('date_hired')
            if employee.status != Employee.Status.ACTIVE:
                employee.status = Employee.Status.ACTIVE
                changed.append('status')
            if not employee.phone and application.phone:
                employee.phone = application.phone
                changed.append('phone')
            if not employee.department and application.vacancy.department:
                employee.department = application.vacancy.department
                changed.append('department')
            if changed:
                employee.save(update_fields=changed)

        # Create or update EmployeeAccount with generated credentials
        account, acc_created = EmployeeAccount.objects.update_or_create(
            employee=employee,
            defaults={
                'username': user.username,
                'initial_password': raw_password,
                'is_active': True,
            },
        )

        return employee

    def _ensure_hiring_documents(self, application: Application, employee: Employee):
        from .pdf import build_contract_pdf, build_hiring_order_pdf

        today = timezone.localdate()
        full_name = f'{application.first_name} {application.last_name}'.strip()
        dept_name = (application.vacancy.department.name
                     if application.vacancy.department else '—')

        pdf_kwargs = dict(
            candidate_name=full_name,
            candidate_email=application.email,
            vacancy_title=application.vacancy.title,
            department_name=dept_name,
            hire_date=today,
            application_id=application.id,
        )

        docs_payload = [
            {
                'doc_type': Document.DocType.CONTRACT,
                'title': f'Трудовой договор — {full_name}',
                'description': f'Автоматически создано при приёме кандидата по заявке #{application.id}.',
                'filename': f'contract_application_{application.id}.pdf',
                'content': build_contract_pdf(**pdf_kwargs),
            },
            {
                'doc_type': Document.DocType.ORDER,
                'title': f'Приказ о приёме — {full_name}',
                'description': f'Автоматически создано при подтверждении оффера по заявке #{application.id}.',
                'filename': f'hiring_order_application_{application.id}.pdf',
                'content': build_hiring_order_pdf(**pdf_kwargs),
            },
        ]

        for item in docs_payload:
            exists = Document.objects.filter(
                application=application,
                employee=employee,
                doc_type=item['doc_type'],
                title=item['title'],
            ).exists()
            if exists:
                continue

            document = Document(
                employee=employee,
                application=application,
                title=item['title'],
                doc_type=item['doc_type'],
                description=item['description'],
                uploaded_by=self.request.user,
            )
            document.file.save(
                item['filename'],
                ContentFile(item['content']),
                save=True,
            )

    def _delete_hiring_documents(self, application: Application):
        docs = Document.objects.filter(
            application=application,
            doc_type__in=[Document.DocType.CONTRACT, Document.DocType.ORDER],
        )
        for doc in docs:
            if doc.file:
                doc.file.delete(save=False)
        docs.delete()

    def perform_update(self, serializer):
        previous_status = serializer.instance.status if serializer.instance else None
        instance = serializer.save()

        if previous_status != Application.AppStatus.HIRED and instance.status == Application.AppStatus.HIRED:
            employee = self._get_or_create_employee_for_application(instance)
            self._ensure_hiring_documents(instance, employee)
        elif (
            previous_status in {Application.AppStatus.HIRED, Application.AppStatus.REJECTED}
            and instance.status == Application.AppStatus.OFFERED
        ):
            self._delete_hiring_documents(instance)

        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.APPLICATION,
            target=instance,
            details=f'Обновлён отклик: {instance}',
        )

    @action(detail=False, methods=['get'], url_path='archive')
    def archive(self, request):
        archived_statuses = [Application.AppStatus.HIRED, Application.AppStatus.REJECTED]

        apps_qs = Application.objects.select_related('vacancy').filter(
            status__in=archived_statuses,
        ).order_by('-updated_at', '-created_at')

        docs_qs = Document.objects.select_related(
            'employee__user', 'uploaded_by', 'application'
        ).filter(
            application__status__in=archived_statuses,
        ).order_by('-created_at')

        return Response({
            'applications': ApplicationSerializer(apps_qs, many=True, context={'request': request}).data,
            'documents': DocumentSerializer(docs_qs, many=True, context={'request': request}).data,
        })


class TimeTrackingViewSet(viewsets.ModelViewSet):
    """Учёт отпусков и больничных."""
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHR, DenyDelete]
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
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHRReadOnly, DenyDelete]
    serializer_class = DocumentSerializer
    pagination_class = None
    log_target_type = HRActionLog.TargetType.DOCUMENT

    def get_queryset(self):
        qs = Document.objects.select_related(
            'employee__user', 'uploaded_by', 'application__vacancy__department',
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

    @action(detail=True, methods=['get'], url_path='pdf-fields')
    def pdf_fields(self, request, pk=None):
        """Вернуть текущие значения полей PDF для редактирования."""
        document = self.get_object()
        app = document.application
        if not app:
            return Response(
                {'detail': 'Документ не привязан к заявке.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        full_name = f'{app.first_name} {app.last_name}'.strip()
        dept_name = app.vacancy.department.name if app.vacancy and app.vacancy.department else '—'
        hire_date = document.employee.date_hired or timezone.localdate()

        return Response({
            'candidate_name': full_name,
            'candidate_email': app.email,
            'vacancy_title': app.vacancy.title if app.vacancy else '—',
            'department_name': dept_name,
            'hire_date': hire_date.strftime('%Y-%m-%d'),
            'work_conditions': 'Основное место работы',
            'work_type': 'Постоянная',
            'probation_period': '3 (три) месяца',
            'work_schedule': '5/2, с 09:00 до 18:00',
        })

    @action(detail=True, methods=['post'], url_path='regenerate')
    def regenerate(self, request, pk=None):
        """Перегенерировать PDF-документ из данных связанной заявки (с опциональными правками)."""
        document = self.get_object()
        app = document.application
        if not app:
            return Response(
                {'detail': 'Документ не привязан к заявке — перегенерация невозможна.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .pdf import build_contract_pdf, build_hiring_order_pdf

        data = request.data or {}

        full_name = data.get('candidate_name') or f'{app.first_name} {app.last_name}'.strip()
        candidate_email = data.get('candidate_email') or app.email
        dept_name = data.get('department_name') or (
            app.vacancy.department.name if app.vacancy and app.vacancy.department else '—'
        )
        vacancy_title = data.get('vacancy_title') or (app.vacancy.title if app.vacancy else '—')

        hire_date_str = data.get('hire_date')
        if hire_date_str:
            from datetime import datetime as _dt
            try:
                hire_date = _dt.strptime(hire_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                hire_date = document.employee.date_hired or timezone.localdate()
        else:
            hire_date = document.employee.date_hired or timezone.localdate()

        # Дополнительные поля (используются только в приказе/договоре)
        work_conditions = data.get('work_conditions', 'Основное место работы')
        work_type = data.get('work_type', 'Постоянная')
        probation_period = data.get('probation_period', '3 (три) месяца')
        work_schedule = data.get('work_schedule', '5/2, с 09:00 до 18:00')

        pdf_kwargs = dict(
            candidate_name=full_name,
            candidate_email=candidate_email,
            vacancy_title=vacancy_title,
            department_name=dept_name,
            hire_date=hire_date,
            application_id=app.id,
            work_conditions=work_conditions,
            work_type=work_type,
            probation_period=probation_period,
            work_schedule=work_schedule,
        )

        if document.doc_type == Document.DocType.CONTRACT:
            content = build_contract_pdf(**pdf_kwargs)
            filename = f'contract_application_{app.id}.pdf'
        elif document.doc_type == Document.DocType.ORDER:
            content = build_hiring_order_pdf(**pdf_kwargs)
            filename = f'hiring_order_application_{app.id}.pdf'
        else:
            return Response(
                {'detail': 'Перегенерация поддерживается только для договоров и приказов.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Удалить старый файл и сохранить новый
        if document.file:
            document.file.delete(save=False)
        document.file.save(filename, ContentFile(content), save=True)

        log_action(
            request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.DOCUMENT,
            target=document,
            details=f'Перегенерирован PDF: {document.title}',
        )

        return Response(DocumentSerializer(document, context={'request': request}).data)


class HRActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр журнала действий (только чтение).
    Senior HR может видеть логи для контроля Junior-сотрудников.
    """
    permission_classes = [IsSeniorHR]
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
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHR, DenyDelete]
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


class EmployeeAccountViewSet(viewsets.ModelViewSet):
    """Управление аккаунтами сотрудников (автоматически созданными при приёме)."""
    permission_classes = [IsHRManagerOrSuperuser, IsJuniorHRReadOnly]
    serializer_class = EmployeeAccountSerializer
    pagination_class = None

    def get_queryset(self):
        qs = EmployeeAccount.objects.select_related(
            'employee__user', 'employee__department', 'employee__position',
        ).order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(employee__user__first_name__icontains=search)
                | Q(employee__user__last_name__icontains=search)
                | Q(employee__user__email__icontains=search)
            )
        return qs

    def perform_update(self, serializer):
        instance = serializer.save()
        # Sync username / password / active status to the actual User
        user = instance.employee.user
        changed = []
        if user.username != instance.username:
            user.username = instance.username
            changed.append('username')
        if instance.initial_password:
            user.set_password(instance.initial_password)
            changed.append('password')
        if user.is_active != instance.is_active:
            user.is_active = instance.is_active
            changed.append('is_active')
        if changed:
            user.save(update_fields=changed)

        log_action(
            self.request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.EMPLOYEE,
            target=instance.employee,
            details=f'Обновлён аккаунт сотрудника: {instance.username}',
        )

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """Сбросить пароль аккаунта — сгенерировать новый."""
        account = self.get_object()
        new_password = _generate_password()
        account.initial_password = new_password
        account.save(update_fields=['initial_password', 'updated_at'])

        user = account.employee.user
        user.set_password(new_password)
        user.save(update_fields=['password'])

        log_action(
            request, HRActionLog.ActionType.UPDATE,
            HRActionLog.TargetType.EMPLOYEE,
            target=account.employee,
            details=f'Сброшен пароль аккаунта: {account.username}',
        )

        return Response(EmployeeAccountSerializer(account).data)


# ---------------------------------------------------------------------------
#  Diagnostic endpoint — helps debug 403 / permission issues
# ---------------------------------------------------------------------------
from rest_framework.decorators import api_view, permission_classes as perm_classes_dec
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@perm_classes_dec([IsAuthenticated])
def whoami(request):
    """Return current user's auth & HR-role info.

    Accessible by any authenticated user — useful for debugging 403 errors.
    Response example::

        {
          "id": 1,
          "username": "admin",
          "is_superuser": true,
          "is_staff": true,
          "groups": ["senior_hr", "staff"],
          "hr_level": "senior",
          "privileged": true
        }
    """
    user = request.user
    return Response({
        'id': user.pk,
        'username': getattr(user, 'username', ''),
        'email': getattr(user, 'email', ''),
        'is_superuser': getattr(user, 'is_superuser', False),
        'is_staff': getattr(user, 'is_staff', False),
        'groups': sorted(_user_group_names(user)),
        'hr_level': get_hr_level(user),
        'privileged': _is_privileged(user),
    })
