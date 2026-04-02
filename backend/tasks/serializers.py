from rest_framework import serializers

from .models import (
    Label, ProjectVersion, Task, TaskComment, TaskAttachment,
    TaskActivity, TaskLink, Notification,
    ProductionDay, CalendarEvent, EventException
)


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
    effective_release_date = serializers.SerializerMethodField()

    class Meta:
        model = ProjectVersion
        fields = [
            'id', 'name', 'description', 'status',
            'start_date', 'release_date', 'effective_release_date',
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

    def get_effective_release_date(self, obj):
        dates = [t.due_date for t in obj.tasks.exclude(is_deleted=True) if t.due_date]
        return max(dates) if dates else obj.release_date


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


class TaskActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskActivity
        fields = ['id', 'task', 'actor', 'actor_name', 'field_name',
                  'old_value', 'new_value', 'created_at']
        read_only_fields = ['actor', 'created_at']

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None


class TaskLinkSerializer(serializers.ModelSerializer):
    source_key = serializers.CharField(source='source.key', read_only=True)
    source_summary = serializers.CharField(source='source.summary', read_only=True)
    target_key = serializers.CharField(source='target.key', read_only=True)
    target_summary = serializers.CharField(source='target.summary', read_only=True)

    class Meta:
        model = TaskLink
        fields = [
            'id', 'source', 'target', 'link_type', 
            'source_key', 'source_summary', 'target_key', 'target_summary',
            'created_by', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    task_key = serializers.CharField(source='task.key', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'actor', 'actor_name', 'verb', 
            'task', 'task_key', 'is_read', 'created_at'
        ]
        read_only_fields = ['recipient', 'actor', 'created_at']


class ProductionDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionDay
        fields = ['date', 'day_type', 'working_days_since_epoch']


class EventExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventException
        fields = ['id', 'event', 'original_date', 'is_cancelled', 'new_start_at', 'new_end_at']


class CalendarEventSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    exceptions = EventExceptionSerializer(many=True, read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'event_type',
            'creator', 'creator_name', 'department', 'department_name',
            'start_at', 'end_at', 'is_all_day', 'rrule',
            'conference_room_id',
            'exceptions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['creator', 'conference_room_id', 'created_at', 'updated_at']


class TaskListSerializer(serializers.ModelSerializer):
    """Компактный сериализатор для списка задач."""
    reporter_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    version_name = serializers.SerializerMethodField()
    labels = LabelSerializer(many=True, read_only=True)
    subtask_count = serializers.IntegerField(read_only=True, default=0)
    effective_start_date = serializers.SerializerMethodField()
    effective_due_date = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'key', 'summary', 'task_type', 'priority', 'status',
            'reporter', 'reporter_name', 'assignee', 'assignee_name',
            'department', 'department_name', 'version', 'version_name',
            'parent', 'labels', 'subtask_count',
            'due_date', 'start_date', 'estimated_working_days',
            'effective_start_date', 'effective_due_date', 'completed_at',
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

    def get_effective_start_date(self, obj):
        if obj.task_type == 'epic':
            dates = [t.start_date for t in obj.subtasks.exclude(is_deleted=True) if t.start_date]
            return min(dates) if dates else obj.start_date
        return obj.start_date

    def get_effective_due_date(self, obj):
        if obj.task_type == 'epic':
            dates = [t.due_date for t in obj.subtasks.exclude(is_deleted=True) if t.due_date]
            return max(dates) if dates else obj.due_date
        return obj.due_date


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
    activities = TaskActivitySerializer(many=True, read_only=True)
    
    outgoing_links = TaskLinkSerializer(many=True, read_only=True)
    incoming_links = TaskLinkSerializer(many=True, read_only=True)
    
    effective_start_date = serializers.SerializerMethodField()
    effective_due_date = serializers.SerializerMethodField()
    date_warnings = serializers.SerializerMethodField()

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
            'due_date', 'start_date', 'estimated_working_days',
            'effective_start_date', 'effective_due_date', 'date_warnings', 'completed_at',
            'comments', 'attachments', 'subtasks', 'activities',
            'outgoing_links', 'incoming_links',
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

    def get_effective_start_date(self, obj):
        if obj.task_type == 'epic':
            dates = [t.start_date for t in obj.subtasks.exclude(is_deleted=True) if t.start_date]
            return min(dates) if dates else obj.start_date
        return obj.start_date

    def get_effective_due_date(self, obj):
        if obj.task_type == 'epic':
            dates = [t.due_date for t in obj.subtasks.exclude(is_deleted=True) if t.due_date]
            return max(dates) if dates else obj.due_date
        return obj.due_date

    def get_date_warnings(self, obj):
        warnings = []
        if obj.parent and obj.parent.due_date and obj.due_date:
            if obj.due_date > obj.parent.due_date:
                warnings.append({
                    "code": "date_conflict",
                    "message": f"Срок подзадачи выходит за рамки родительского эпика ({obj.parent.due_date.strftime('%d.%m.%Y')})"
                })
        return warnings

    def validate_status(self, value):
        if self.instance and self.instance.status != value:
            # FSM validation
            allowed = Task.TRANSITIONS.get(self.instance.status, set())
            if value not in allowed:
                raise serializers.ValidationError(
                    f"Недопустимый переход статуса: {self.instance.status} -> {value}"
                )
            if value in ('done', 'closed'):
                from django.utils import timezone
                self.context['_completed_at'] = timezone.now()
        elif not self.instance and value in ('done', 'closed'):
            from django.utils import timezone
            self.context['_completed_at'] = timezone.now()
        return value

    def update(self, instance, validated_data):
        completed_at = self.context.pop('_completed_at', None)
        if completed_at:
            validated_data['completed_at'] = completed_at
            
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None
        
        changes = []
        tracked_fields = ['summary', 'description', 'task_type', 'priority', 'status', 'assignee', 'department', 'version', 'due_date', 'start_date']
        
        for field in tracked_fields:
            if field in validated_data:
                old_val = getattr(instance, field)
                new_val = validated_data[field]
                
                # Check for ForeignKeys
                if field == 'assignee':
                    old_str = old_val.username if old_val else 'None'
                    new_str = new_val.username if new_val else 'None'
                elif field == 'department':
                    old_str = old_val.name if old_val else 'None'
                    new_str = new_val.name if new_val else 'None'
                elif field == 'version':
                    old_str = old_val.name if old_val else 'None'
                    new_str = new_val.name if new_val else 'None'
                else:
                    old_str = str(old_val) if old_val is not None else ''
                    new_str = str(new_val) if new_val is not None else ''

                if old_str != new_str:
                    changes.append({
                        'task': instance,
                        'actor': actor,
                        'field_name': field,
                        'old_value': old_str,
                        'new_value': new_str
                    })

        updated_instance = super().update(instance, validated_data)
        
        for change in changes:
            TaskActivity.objects.create(**change)
            
            # Trigger notifications for specific events
            if change['field_name'] == 'status':
                # Notify assignee (if any) and reporter (if not the actor)
                recipients = set()
                if updated_instance.assignee and updated_instance.assignee != actor:
                    recipients.add(updated_instance.assignee)
                if updated_instance.reporter and updated_instance.reporter != actor:
                    recipients.add(updated_instance.reporter)
                    
                for rec in recipients:
                    Notification.objects.create(
                        recipient=rec,
                        actor=actor,
                        task=updated_instance,
                        verb=f"изменил(а) статус задачи на «{updated_instance.get_status_display() or updated_instance.status}»"
                    )
            elif change['field_name'] == 'assignee':
                if updated_instance.assignee and updated_instance.assignee != actor:
                    Notification.objects.create(
                        recipient=updated_instance.assignee,
                        actor=actor,
                        task=updated_instance,
                        verb="назначил(а) эту задачу на вас"
                    )
                # If someone was unassigned, we could notify them too if old_val was a user object,
                # but we'll stick to notifying the new assignee for now.

        return updated_instance

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and not validated_data.get('reporter'):
            validated_data['reporter'] = request.user
        return super().create(validated_data)
