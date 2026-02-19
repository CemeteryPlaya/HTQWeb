from django.conf import settings
from django.db import models

from hr.models import SoftDeleteMixin, Department


# ---------------------------------------------------------------------------
#  Task-management models (Jira-like)
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
    completed_at = models.DateTimeField('Завершена', null=True, blank=True)

    # --- meta ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']
        db_table = 'hr_task'

    def __str__(self):
        return f'{self.key} {self.summary}'

    def save(self, *args, **kwargs):
        if not self.key:
            last = Task.all_objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.key = f'TASK-{next_num}'
        super().save(*args, **kwargs)


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
