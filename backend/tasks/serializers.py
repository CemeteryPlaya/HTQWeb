from rest_framework import serializers

from .models import Label, ProjectVersion, Task, TaskComment, TaskAttachment


# ---------------------------------------------------------------------------
#   Task-management serializers
# ---------------------------------------------------------------------------


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'color']


class ProjectVersionSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True, default=0)
    done_count = serializers.IntegerField(read_only=True, default=0)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = ProjectVersion
        fields = [
            'id', 'name', 'description', 'status',
            'start_date', 'release_date',
            'task_count', 'done_count', 'progress',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_progress(self, obj):
        total = getattr(obj, 'task_count', 0) or 0
        done = getattr(obj, 'done_count', 0) or 0
        if total == 0:
            return 0
        return round(done / total * 100, 1)


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'body',
                  'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'file', 'filename', 'uploaded_by',
                  'uploaded_by_name', 'created_at']
        read_only_fields = ['uploaded_by', 'filename', 'created_at']

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None


class TaskListSerializer(serializers.ModelSerializer):
    """Компактный сериализатор для списка задач."""
    reporter_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    labels = LabelSerializer(many=True, read_only=True)
    subtask_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            'id', 'key', 'summary', 'task_type', 'priority', 'status',
            'reporter', 'reporter_name', 'assignee', 'assignee_name',
            'department', 'department_name', 'version', 'version_name',
            'parent', 'labels', 'subtask_count',
            'due_date', 'start_date', 'completed_at',
            'created_at', 'updated_at',
        ]

    def get_reporter_name(self, obj):
        if obj.reporter:
            return obj.reporter.get_full_name() or obj.reporter.username
        return None

    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.username
        return None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_version_name(self, obj):
        return obj.version.name if obj.version else None


class TaskDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор для просмотра/редактирования задачи."""
    reporter_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    parent_key = serializers.SerializerMethodField()
    labels = LabelSerializer(many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        queryset=Label.objects.all(), many=True,
        source='labels', write_only=True, required=False,
    )
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'key', 'summary', 'description', 'task_type',
            'priority', 'status',
            'reporter', 'reporter_name', 'assignee', 'assignee_name',
            'department', 'department_name',
            'version', 'version_name',
            'parent', 'parent_key',
            'labels', 'label_ids',
            'due_date', 'start_date', 'completed_at',
            'comments', 'attachments', 'subtasks',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['key', 'created_at', 'updated_at', 'completed_at']

    def get_reporter_name(self, obj):
        if obj.reporter:
            return obj.reporter.get_full_name() or obj.reporter.username
        return None

    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.username
        return None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_version_name(self, obj):
        return obj.version.name if obj.version else None

    def get_parent_key(self, obj):
        return obj.parent.key if obj.parent else None

    def get_subtasks(self, obj):
        qs = obj.subtasks.filter(is_deleted=False)
        return TaskListSerializer(qs, many=True).data

    def validate_status(self, value):
        if self.instance and value in ('done', 'closed') and self.instance.status not in ('done', 'closed'):
            from django.utils import timezone
            self.context['_completed_at'] = timezone.now()
        return value

    def update(self, instance, validated_data):
        completed_at = self.context.pop('_completed_at', None)
        if completed_at:
            validated_data['completed_at'] = completed_at
        return super().update(instance, validated_data)

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and not validated_data.get('reporter'):
            validated_data['reporter'] = request.user
        return super().create(validated_data)
