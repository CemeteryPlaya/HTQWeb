import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
import datetime

from hr.models import SoftDeleteMixin, Department


# ---------------------------------------------------------------------------
#  Task-management models
# ---------------------------------------------------------------------------


class Label(models.Model):
    """Метка (тег) для задач."""
    name = models.CharField('Название', max_length=100, unique=True)
    color = models.CharField(
        'Цвет (hex)', max_length=7, default='#6366f1',
        help_text='Цвет метки в формате #RRGGBB',
    )

    class Meta:
        verbose_name = 'Метка'
        verbose_name_plural = 'Метки'
        ordering = ['name']
        db_table = 'hr_label'

    def __str__(self):
        return self.name


class ProjectVersion(models.Model):
    """Версия / релиз для дорожной карты."""

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Запланирована'
        IN_PROGRESS = 'in_progress', 'В работе'
        RELEASED = 'released', 'Выпущена'
        ARCHIVED = 'archived', 'В архиве'

    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True, default='')
    status = models.CharField(
        'Статус', max_length=20,
        choices=Status.choices, default=Status.PLANNED,
    )
    start_date = models.DateField('Дата начала', null=True, blank=True)
    release_date = models.DateField('Дата релиза', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Версия (релиз)'
        verbose_name_plural = 'Версии (релизы)'
        ordering = ['-release_date', '-created_at']
        db_table = 'hr_projectversion'

    def __str__(self):
        return self.name


class TaskSequence(models.Model):
    """
    Атомарный счетчик для генерации уникальных ключей задач (TASK-X).
    Использует блокировку строки для предотвращения race condition.
    """
    project_prefix = models.CharField(max_length=10, unique=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'hr_tasksequence'

    @classmethod
    def get_next_value(cls, prefix='TASK'):
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(project_prefix=prefix)
            seq.last_value += 1
            seq.save(update_fields=['last_value'])
            return seq.last_value


class ProductionDay(models.Model):
    """
    Производственный календарь.
    Хранит типы дней (рабочий, выходной, праздник) для расчета дедлайнов.
    """
    class DayType(models.TextChoices):
        WORKING = 'working', 'Рабочий'
        WEEKEND = 'weekend', 'Выходной'
        HOLIDAY = 'holiday', 'Праздник'
        SHORT = 'short', 'Сокращённый'

    date = models.DateField('Дата', primary_key=True)
    day_type = models.CharField(
        'Тип дня', max_length=20,
        choices=DayType.choices, default=DayType.WORKING,
    )
    # Накопительный итог рабочих дней для алгоритма O(1)
    working_days_since_epoch = models.IntegerField(
        'Рабочих дней с начала эпохи', default=0, db_index=True,
        help_text='Используется для математического расчета разницы в рабочих днях за O(1)'
    )

    class Meta:
        verbose_name = 'Производственный день'
        verbose_name_plural = 'Производственный календарь'
        ordering = ['date']
        db_table = 'hr_production_day'

    def __str__(self):
        return f"{self.date} ({self.get_day_type_display()})"


class CalendarEvent(models.Model):
    """
    Событие календаря (встречи, общие события, вехи).
    Использует RFC 5545 (RRULE) для регулярных событий.
    """
    class EventType(models.TextChoices):
        COMMON = 'common', 'Общее'
        DEPARTMENT = 'department', 'Отдел'
        PERSONAL = 'personal', 'Личное'
        CONFERENCE = 'conference', 'Конференция'

    title = models.CharField('Заголовок', max_length=500)
    description = models.TextField('Описание', blank=True, default='')
    event_type = models.CharField(
        'Тип события', max_length=20,
        choices=EventType.choices, default=EventType.COMMON,
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_events',
        verbose_name='Создатель'
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='events',
        verbose_name='Отдел'
    )
    
    start_at = models.DateTimeField('Начало')
    end_at = models.DateTimeField('Конец')
    is_all_day = models.BooleanField('Весь день', default=False)
    
    # RFC 5545 RRULE
    rrule = models.CharField(
        'Правило повторения (RRULE)', max_length=255, blank=True,
        help_text='Например: FREQ=WEEKLY;BYDAY=MO,WE,FR'
    )

    conference_room_id = models.CharField(
        'ID комнаты ВКС', max_length=50, blank=True, default='',
        help_text='Автоматически заполняется при создании события с типом «Конференция»',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Событие календаря'
        verbose_name_plural = 'События календаря'
        ordering = ['start_at']
        db_table = 'hr_calendar_event'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.event_type == self.EventType.CONFERENCE and not self.conference_room_id:
            parts = str(uuid.uuid4()).split('-')
            self.conference_room_id = f'{parts[0]}-{parts[1]}'
        super().save(*args, **kwargs)


class EventException(models.Model):
    """
    Исключение для регулярного события (отмена или перенос конкретного дня).
    """
    event = models.ForeignKey(
        CalendarEvent, on_delete=models.CASCADE,
        related_name='exceptions', verbose_name='Событие'
    )
    original_date = models.DateField('Исходная дата вхождения')
    is_cancelled = models.BooleanField('Отменено', default=False)
    
    # Новые даты, если это перенос, а не просто отмена
    new_start_at = models.DateTimeField('Новое начало', null=True, blank=True)
    new_end_at = models.DateTimeField('Новый конец', null=True, blank=True)

    class Meta:
        verbose_name = 'Исключение события'
        verbose_name_plural = 'Исключения событий'
        unique_together = ('event', 'original_date')
        db_table = 'hr_event_exception'


class Task(SoftDeleteMixin):
    """
    Задача — основная единица работы.
    """

    class Priority(models.TextChoices):
        CRITICAL = 'critical', 'Критический'
        HIGH = 'high', 'Высокий'
        MEDIUM = 'medium', 'Средний'
        LOW = 'low', 'Низкий'
        TRIVIAL = 'trivial', 'Тривиальный'

    class Status(models.TextChoices):
        OPEN = 'open', 'Открыта'
        IN_PROGRESS = 'in_progress', 'В работе'
        IN_REVIEW = 'in_review', 'На ревью'
        DONE = 'done', 'Готова'
        CLOSED = 'closed', 'Закрыта'

    class TaskType(models.TextChoices):
        TASK = 'task', 'Задача'
        BUG = 'bug', 'Баг'
        STORY = 'story', 'История'
        EPIC = 'epic', 'Эпик'
        SUBTASK = 'subtask', 'Подзадача'

    # Допустимые переходы статусов (State Machine)
    TRANSITIONS = {
        Status.OPEN: {Status.IN_PROGRESS, Status.CLOSED},
        Status.IN_PROGRESS: {Status.IN_REVIEW, Status.DONE, Status.OPEN},
        Status.IN_REVIEW: {Status.DONE, Status.IN_PROGRESS},
        Status.DONE: {Status.CLOSED, Status.IN_PROGRESS},
        Status.CLOSED: {Status.OPEN},
    }

    # --- key ---
    key = models.CharField(
        'Ключ', max_length=20, unique=True, blank=True,
        help_text='Автогенерируемый ключ вида TASK-123',
    )

    # --- core fields ---
    summary = models.CharField('Заголовок', max_length=500)
    description = models.TextField('Описание', blank=True, default='')
    task_type = models.CharField(
        'Тип', max_length=20,
        choices=TaskType.choices, default=TaskType.TASK,
    )
    priority = models.CharField(
        'Приоритет', max_length=20,
        choices=Priority.choices, default=Priority.MEDIUM,
    )
    status = models.CharField(
        'Статус', max_length=20,
        choices=Status.choices, default=Status.OPEN,
    )

    # --- people ---
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reported_tasks',
        verbose_name='Автор',
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks',
        verbose_name='Исполнитель',
    )

    # --- organisation ---
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks',
        verbose_name='Отдел',
    )
    version = models.ForeignKey(
        ProjectVersion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks',
        verbose_name='Версия / релиз',
    )
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subtasks',
        verbose_name='Родительская задача',
    )
    labels = models.ManyToManyField(
        Label, blank=True, related_name='tasks',
        verbose_name='Метки',
    )

    # --- dates ---
    due_date = models.DateField('Срок', null=True, blank=True)
    start_date = models.DateField('Дата начала', null=True, blank=True)
    estimated_working_days = models.PositiveIntegerField(
        'Оценка (раб. дни)', null=True, blank=True,
        help_text='Если указано, дедлайн будет рассчитан автоматически с учетом календаря.'
    )
    completed_at = models.DateTimeField('Завершена', null=True, blank=True)

    # --- meta ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
        db_table = 'hr_task'
        indexes = [
            models.Index(fields=['status', 'assignee']),
            models.Index(fields=['status', 'department']),
            models.Index(fields=['version', 'status']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]

    def __str__(self):
        return f'{self.key} {self.summary}'

    def save(self, *args, **kwargs):
        if not self.key:
            next_num = TaskSequence.get_next_value('TASK')
            self.key = f'TASK-{next_num}'
            
        # Автоматический расчет дедлайна (Phase 5)
        if self.start_date and self.estimated_working_days:
            self._calculate_due_date()
            
        super().save(*args, **kwargs)

    def _calculate_due_date(self):
        """
        O(1) расчет дедлайна через таблицу ProductionDay.
        Логика:
        1. Находим начальный рабочий день (snap to future if weekend).
        2. Рассчитываем целевой накопитель: W + duration - 1.
        """
        try:
            # Находим запись для текущей даты
            day_entry = ProductionDay.objects.get(date=self.start_date)
            
            # Если это выходной, "перепрыгиваем" на первый рабочий день
            if day_entry.day_type not in [ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]:
                start_working_day = ProductionDay.objects.filter(
                    date__gt=self.start_date,
                    day_type__in=[ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]
                ).order_by('date').first()
                if not start_working_day:
                    return
                base_cumulative = start_working_day.working_days_since_epoch
            else:
                base_cumulative = day_entry.working_days_since_epoch
                
            target_cumulative = base_cumulative + self.estimated_working_days - 1
            
            target_day = ProductionDay.objects.filter(
                working_days_since_epoch=target_cumulative,
                day_type__in=[ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]
            ).order_by('date').first()
            
            if target_day:
                self.due_date = target_day.date
        except ProductionDay.DoesNotExist:
            pass


class TaskComment(models.Model):
    """Комментарий к задаче."""
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='comments', verbose_name='Задача',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='task_comments',
        verbose_name='Автор',
    )
    body = models.TextField('Текст')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Комментарий задачи'
        verbose_name_plural = 'Комментарии задач'
        ordering = ['created_at']
        db_table = 'hr_taskcomment'

    def __str__(self):
        return f'Comment #{self.id} on {self.task.key}'


class TaskAttachment(models.Model):
    """Вложение к задаче."""
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='attachments', verbose_name='Задача',
    )
    file = models.FileField('Файл', upload_to='hr/task_attachments/%Y/%m/')
    filename = models.CharField('Имя файла', max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='task_attachments',
        verbose_name='Загрузил',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение задачи'
        verbose_name_plural = 'Вложения задач'
        ordering = ['-created_at']
        db_table = 'hr_taskattachment'

    def __str__(self):
        return f'{self.filename or self.file.name} ({self.task.key})'

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)


class TaskActivity(models.Model):
    """Журнал истории изменений задачи (Activity Log)."""
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='activities', verbose_name='Задача',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='task_activities',
        verbose_name='Инициатор',
    )
    field_name = models.CharField('Поле', max_length=50)
    old_value = models.TextField('Старое значение', blank=True, null=True)
    new_value = models.TextField('Новое значение', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История изменений'
        verbose_name_plural = 'История изменений'
        ordering = ['-created_at']
        db_table = 'hr_taskactivity'
        indexes = [
            models.Index(fields=['task', '-created_at']),
        ]

    def __str__(self):
        return f'{self.field_name} changed on {self.task.key}'


class TaskLink(models.Model):
    """Связь между задачами (блокирует, относится к, дублирует)."""
    
    LINK_TYPES = (
        ('blocks', 'Блокирует'),
        ('is_blocked_by', 'Блокируется'),
        ('relates_to', 'Относится к'),
        ('duplicates', 'Дублирует'),
    )

    source = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='outgoing_links',
        verbose_name='Исходная задача',
    )
    target = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name='incoming_links',
        verbose_name='Целевая задача',
    )
    link_type = models.CharField(
        'Тип связи', max_length=20, choices=LINK_TYPES,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Кто связал',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Связь задач'
        verbose_name_plural = 'Связи задач'
        db_table = 'hr_tasklink'
        unique_together = ('source', 'target', 'link_type')

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.source == self.target:
            raise ValidationError("Задача не может ссылаться сама на себя.")
            
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.source.key} {self.link_type} {self.target.key}'


class Notification(models.Model):
    """Системные уведомления."""
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Получатель'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='notifications_sent', 
        verbose_name='Инициатор'
    )
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications',
        verbose_name='Задача'
    )
    verb = models.CharField('Действие', max_length=255)
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        db_table = 'hr_notification'
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'Notif for {self.recipient.username}: {self.verb}'
