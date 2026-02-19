from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Department, Position, Employee, Vacancy, Application,
    TimeTracking, Document, HRActionLog, PersonnelHistory,
    EmployeeAccount, _generate_password,
)
from .roles import is_senior_hr

User = get_user_model()


# ---------------------------------------------------------------------------
#   Sensitive-field constants
# ---------------------------------------------------------------------------

# Финансовые / конфиденциальные поля — физически не отдаются Junior HR.
EMPLOYEE_SENSITIVE_FIELDS = frozenset({
    'salary', 'bonus', 'passport_data', 'bank_account',
})

# СРО-поля: Junior может видеть (read-only), но не может редактировать.
EMPLOYEE_SRO_FIELDS = frozenset({
    'sro_permit_number', 'sro_permit_expiry',
    'safety_cert_number', 'safety_cert_expiry',
})

# Зарплатные поля вакансий — скрыты от Junior.
VACANCY_SALARY_FIELDS = frozenset({
    'salary_min', 'salary_max',
})


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class PositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Position
        fields = ['id', 'title', 'department', 'department_name']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Краткая сериализация для списка сотрудников."""
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'full_name', 'username', 'email',
            'position_title', 'department_name',
            'phone', 'date_hired', 'status',
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    # ALL model fields — sensitive ones will be stripped dynamically.
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'full_name', 'username', 'email',
            'position', 'position_title',
            'department', 'department_name',
            'phone', 'date_hired', 'date_dismissed',
            'status', 'notes',
            # Sensitive (Senior-only)
            'salary', 'bonus', 'passport_data', 'bank_account',
            # SRO (read-only for Junior)
            'sro_permit_number', 'sro_permit_expiry',
            'safety_cert_number', 'safety_cert_expiry',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    # ---- Dynamic field stripping ----
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and not is_senior_hr(request.user):
            # Junior HR: физически убираем конфиденциальные поля из ответа
            for field_name in EMPLOYEE_SENSITIVE_FIELDS:
                fields.pop(field_name, None)
            # СРО-поля оставляем, но делаем read-only
            for field_name in EMPLOYEE_SRO_FIELDS:
                if field_name in fields:
                    fields[field_name].read_only = True
        return fields

    def validate(self, attrs):
        """Предотвратить Junior от записи в конфиденциальные/SRO поля."""
        attrs = super().validate(attrs)
        request = self.context.get('request')
        if request and not is_senior_hr(request.user):
            # Удалить любые чувствительные поля, если Junior как-то их прислал
            for field_name in EMPLOYEE_SENSITIVE_FIELDS | EMPLOYEE_SRO_FIELDS:
                attrs.pop(field_name, None)
        return attrs


class VacancySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    applications_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Vacancy
        fields = [
            'id', 'title', 'department', 'department_name',
            'description', 'requirements',
            'salary_min', 'salary_max',
            'status', 'created_by', 'created_by_name',
            'applications_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and not is_senior_hr(request.user):
            # Junior HR не видит зарплатные диапазоны вакансий
            for f in VACANCY_SALARY_FIELDS:
                fields.pop(f, None)
        return fields


class ApplicationSerializer(serializers.ModelSerializer):
    vacancy_title = serializers.CharField(source='vacancy.title', read_only=True)

    STATUS_TRANSITIONS = {
        Application.AppStatus.NEW: {Application.AppStatus.REVIEWED},
        Application.AppStatus.REVIEWED: {Application.AppStatus.NEW, Application.AppStatus.INTERVIEW},
        Application.AppStatus.INTERVIEW: {Application.AppStatus.REVIEWED, Application.AppStatus.OFFERED},
        Application.AppStatus.OFFERED: {
            Application.AppStatus.INTERVIEW,
            Application.AppStatus.HIRED,
            Application.AppStatus.REJECTED,
        },
        Application.AppStatus.HIRED: set(),
        Application.AppStatus.REJECTED: set(),
    }

    class Meta:
        model = Application
        fields = [
            'id', 'vacancy', 'vacancy_title',
            'first_name', 'last_name', 'email', 'phone',
            'resume', 'cover_letter',
            'status', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        new_status = attrs.get('status')

        if self.instance is None:
            if new_status and new_status != Application.AppStatus.NEW:
                raise serializers.ValidationError({
                    'status': 'Новая заявка может быть создана только со статусом new.'
                })
            return attrs

        request = self.context.get('request')
        if request and not is_senior_hr(request.user):
            allowed_fields = {'status'}
            extra_fields = set(attrs.keys()) - allowed_fields
            if extra_fields:
                raise serializers.ValidationError({
                    'detail': 'Junior HR может менять только статус заявки.'
                })

        if not new_status:
            return attrs

        current_status = self.instance.status
        if new_status == current_status:
            return attrs

        allowed = self.STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            request = self.context.get('request')
            is_senior = request and is_senior_hr(request.user)
            can_revert_offer = (
                is_senior
                and current_status in {
                    Application.AppStatus.HIRED,
                    Application.AppStatus.REJECTED,
                }
                and new_status == Application.AppStatus.OFFERED
            )
            if not can_revert_offer:
                raise serializers.ValidationError({
                    'status': 'Статус можно менять только на соседний шаг иерархии.'
                })

        # Junior HR не может ставить статус «Принят в штат»
        request = self.context.get('request')
        if request and not is_senior_hr(request.user):
            if new_status == Application.AppStatus.HIRED:
                raise serializers.ValidationError({
                    'status': 'Только Senior HR может утвердить приём в штат.'
                })

        return attrs


class TimeTrackingSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    duration_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = TimeTracking
        fields = [
            'id', 'employee', 'employee_name',
            'leave_type', 'start_date', 'end_date', 'duration_days',
            'status', 'comment',
            'approved_by', 'approved_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['approved_by', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None


class DocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    application_status = serializers.CharField(source='application.status', read_only=True)
    application_candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'employee', 'employee_name',
            'application', 'application_status', 'application_candidate_name',
            'title', 'doc_type', 'file', 'description',
            'uploaded_by', 'uploaded_by_name',
            'created_at',
        ]
        read_only_fields = ['uploaded_by', 'created_at']

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None

    def get_application_candidate_name(self, obj):
        if not obj.application:
            return None
        return f'{obj.application.first_name} {obj.application.last_name}'.strip()


class PersonnelHistorySerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    from_department_name = serializers.CharField(source='from_department.name', read_only=True)
    to_department_name = serializers.CharField(source='to_department.name', read_only=True)
    from_position_title = serializers.CharField(source='from_position.title', read_only=True)
    to_position_title = serializers.CharField(source='to_position.title', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PersonnelHistory
        fields = [
            'id', 'employee', 'employee_name',
            'event_type', 'event_date',
            'from_department', 'from_department_name',
            'to_department', 'to_department_name',
            'from_position', 'from_position_title',
            'to_position', 'to_position_title',
            'order_number', 'comment',
            'created_by', 'created_by_name',
            'created_at',
        ]
        read_only_fields = ['created_by', 'created_at']

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def create(self, validated_data):
        employee = validated_data['employee']

        if not validated_data.get('from_department'):
            validated_data['from_department'] = employee.department
        if not validated_data.get('from_position'):
            validated_data['from_position'] = employee.position

        instance = super().create(validated_data)

        if instance.event_type in {
            PersonnelHistory.EventType.TRANSFER,
            PersonnelHistory.EventType.PROMOTION,
            PersonnelHistory.EventType.DEMOTION,
            PersonnelHistory.EventType.HIRED,
        }:
            update_fields = []
            if instance.to_department and instance.to_department != employee.department:
                employee.department = instance.to_department
                update_fields.append('department')
            if instance.to_position and instance.to_position != employee.position:
                employee.position = instance.to_position
                update_fields.append('position')
            if update_fields:
                employee.save(update_fields=update_fields)

        return instance


class HRActionLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    position_title = serializers.SerializerMethodField()

    class Meta:
        model = HRActionLog
        fields = [
            'id', 'user', 'user_name',
            'employee', 'employee_name',
            'department', 'department_name',
            'position', 'position_title',
            'action', 'target_type', 'target_id', 'target_repr',
            'details', 'ip_address', 'url', 'module', 'created_at',
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'Система'

    def get_employee_name(self, obj):
        if obj.employee:
            return obj.employee.user.get_full_name() or obj.employee.user.username
        return None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_position_title(self, obj):
        return obj.position.title if obj.position else None


class EmployeeAccountSerializer(serializers.ModelSerializer):
    """Сериализация аккаунтов сотрудников."""
    employee_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    position_title = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeAccount
        fields = [
            'id', 'employee', 'employee_name', 'email',
            'department_name', 'position_title',
            'username', 'initial_password',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['employee', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username

    def get_email(self, obj):
        return obj.employee.user.email

    def get_department_name(self, obj):
        return obj.employee.department.name if obj.employee.department else None

    def get_position_title(self, obj):
        return obj.employee.position.title if obj.employee.position else None
