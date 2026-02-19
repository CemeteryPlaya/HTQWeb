from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Department, Position, Employee, Vacancy, Application,
    TimeTracking, Document, HRActionLog, PersonnelHistory,
)

User = get_user_model()


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

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'full_name', 'username', 'email',
            'position', 'position_title',
            'department', 'department_name',
            'phone', 'date_hired', 'date_dismissed',
            'status', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


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


class ApplicationSerializer(serializers.ModelSerializer):
    vacancy_title = serializers.CharField(source='vacancy.title', read_only=True)

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

    class Meta:
        model = Document
        fields = [
            'id', 'employee', 'employee_name',
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
