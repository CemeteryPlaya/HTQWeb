from django.contrib import admin
from .models import (
    Department, Position, Employee, Vacancy, Application,
    TimeTracking, Document, HRActionLog,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department')
    list_filter = ('department',)
    search_fields = ('title',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'department', 'status', 'date_hired')
    list_filter = ('status', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    list_select_related = ('user', 'position', 'department')


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'department')
    search_fields = ('title',)
    raw_id_fields = ('created_by',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'vacancy', 'status', 'created_at')
    list_filter = ('status', 'vacancy')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(TimeTracking)
class TimeTrackingAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status')
    raw_id_fields = ('employee', 'approved_by')
    list_select_related = ('employee__user', 'approved_by')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'doc_type', 'uploaded_by', 'created_at')
    list_filter = ('doc_type',)
    search_fields = ('title',)
    raw_id_fields = ('employee', 'uploaded_by')
    list_select_related = ('employee__user', 'uploaded_by')


@admin.register(HRActionLog)
class HRActionLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'target_type', 'target_repr', 'ip_address')
    list_filter = ('action', 'target_type', 'created_at')
    search_fields = ('target_repr', 'details', 'user__username', 'user__first_name', 'user__last_name')
    list_select_related = ('user',)
    readonly_fields = (
        'user', 'action', 'target_type', 'target_id',
        'target_repr', 'details', 'ip_address', 'created_at',
    )
    date_hierarchy = 'created_at'
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
