from django.contrib import admin

from .models import Label, ProjectVersion, Task, TaskComment, TaskAttachment


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(ProjectVersion)
class ProjectVersionAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'release_date')
    list_filter = ('status',)
    search_fields = ('name',)


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ('author', 'created_at')


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ('uploaded_by', 'created_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('key', 'summary', 'task_type', 'status', 'priority', 'assignee', 'created_at')
    list_filter = ('status', 'priority', 'task_type', 'department')
    search_fields = ('key', 'summary', 'description')
    inlines = [TaskCommentInline, TaskAttachmentInline]
    raw_id_fields = ('reporter', 'assignee', 'parent')
