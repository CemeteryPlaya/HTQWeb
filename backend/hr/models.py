from django.conf import settings
from django.db import models


class Department(models.Model):
    """Отдел компании."""
    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Position(models.Model):
    """Должность."""
    title = models.CharField('Название', max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='positions',
        verbose_name='Отдел',
    )

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['title']

    def __str__(self):
        return self.title


class Employee(models.Model):
    """Расширенный профиль сотрудника, привязанный к User."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активен'
        ON_LEAVE = 'on_leave', 'В отпуске'
        DISMISSED = 'dismissed', 'Уволен'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee',
        verbose_name='Пользователь',
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Должность',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Отдел',
    )
    phone = models.CharField('Телефон', max_length=30, blank=True)
    date_hired = models.DateField('Дата приёма', null=True, blank=True)
    date_dismissed = models.DateField('Дата увольнения', null=True, blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    notes = models.TextField('Заметки', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['-date_hired']
        permissions = [
            ('view_hr_section', 'Can access HR section'),
        ]

    def __str__(self):
        full = self.user.get_full_name() or self.user.username
        pos = self.position.title if self.position else '—'
        return f'{full} ({pos})'


class Vacancy(models.Model):
    """Вакансия."""

    class VacancyStatus(models.TextChoices):
        OPEN = 'open', 'Открыта'
        CLOSED = 'closed', 'Закрыта'
        ON_HOLD = 'on_hold', 'На удержании'

    title = models.CharField('Название', max_length=300)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vacancies',
        verbose_name='Отдел',
    )
    description = models.TextField('Описание', blank=True)
    requirements = models.TextField('Требования', blank=True)
    salary_min = models.DecimalField(
        'Зарплата от', max_digits=12, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        'Зарплата до', max_digits=12, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=VacancyStatus.choices,
        default=VacancyStatus.OPEN,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vacancies',
        verbose_name='Создал',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Application(models.Model):
    """Отклик кандидата на вакансию."""

    class AppStatus(models.TextChoices):
        NEW = 'new', 'Новый'
        REVIEWED = 'reviewed', 'Рассмотрен'
        INTERVIEW = 'interview', 'Интервью'
        OFFERED = 'offered', 'Оффер'
        REJECTED = 'rejected', 'Отклонён'
        HIRED = 'hired', 'Принят'

    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Вакансия',
    )
    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=30, blank=True)
    resume = models.FileField('Резюме', upload_to='hr/resumes/', blank=True, null=True)
    cover_letter = models.TextField('Сопроводительное письмо', blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=AppStatus.choices,
        default=AppStatus.NEW,
        db_index=True,
    )
    notes = models.TextField('Заметки рекрутера', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} → {self.vacancy.title}'


class TimeTracking(models.Model):
    """Учёт отпусков, больничных, отгулов."""

    class LeaveType(models.TextChoices):
        VACATION = 'vacation', 'Отпуск'
        SICK_LEAVE = 'sick_leave', 'Больничный'
        DAY_OFF = 'day_off', 'Отгул'
        BUSINESS_TRIP = 'business_trip', 'Командировка'
        UNPAID = 'unpaid', 'За свой счёт'

    class LeaveStatus(models.TextChoices):
        PENDING = 'pending', 'На рассмотрении'
        APPROVED = 'approved', 'Одобрен'
        REJECTED = 'rejected', 'Отклонён'
        CANCELLED = 'cancelled', 'Отменён'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='time_records',
        verbose_name='Сотрудник',
    )
    leave_type = models.CharField(
        'Тип',
        max_length=20,
        choices=LeaveType.choices,
        db_index=True,
    )
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
        db_index=True,
    )
    comment = models.TextField('Комментарий', blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves',
        verbose_name='Одобрил',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Учёт времени'
        verbose_name_plural = 'Учёт времени'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.employee} — {self.get_leave_type_display()} ({self.start_date} – {self.end_date})'

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0


class Document(models.Model):
    """Трудовые документы сотрудника."""

    class DocType(models.TextChoices):
        CONTRACT = 'contract', 'Трудовой договор'
        AMENDMENT = 'amendment', 'Допсоглашение'
        ORDER = 'order', 'Приказ'
        CERTIFICATE = 'certificate', 'Справка'
        OTHER = 'other', 'Прочее'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Сотрудник',
    )
    title = models.CharField('Название', max_length=300)
    doc_type = models.CharField(
        'Тип документа',
        max_length=20,
        choices=DocType.choices,
        default=DocType.OTHER,
        db_index=True,
    )
    file = models.FileField('Файл', upload_to='hr/documents/')
    description = models.TextField('Описание', blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_hr_docs',
        verbose_name='Загрузил',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.employee}'


class HRActionLog(models.Model):
    """Журнал действий пользователей в HR-модуле."""

    class ActionType(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Редактирование'
        DELETE = 'delete', 'Удаление'
        APPROVE = 'approve', 'Одобрение'
        REJECT = 'reject', 'Отклонение'
        STATUS_CHANGE = 'status_change', 'Смена статуса'

    class TargetType(models.TextChoices):
        EMPLOYEE = 'employee', 'Сотрудник'
        DEPARTMENT = 'department', 'Отдел'
        POSITION = 'position', 'Должность'
        VACANCY = 'vacancy', 'Вакансия'
        APPLICATION = 'application', 'Отклик'
        TIME_TRACKING = 'time_tracking', 'Учёт времени'
        DOCUMENT = 'document', 'Документ'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_action_logs',
        verbose_name='Пользователь',
    )
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs',
        verbose_name='Сотрудник',
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs',
        verbose_name='Отдел',
    )
    position = models.ForeignKey(
        'Position',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs',
        verbose_name='Должность',
    )
    action = models.CharField(
        'Действие',
        max_length=20,
        choices=ActionType.choices,
        db_index=True,
    )
    target_type = models.CharField(
        'Тип объекта',
        max_length=30,
        choices=TargetType.choices,
        db_index=True,
    )
    target_id = models.PositiveIntegerField('ID объекта', null=True, blank=True)
    target_repr = models.CharField('Описание объекта', max_length=500, blank=True)
    details = models.TextField('Детали', blank=True)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)
    created_at = models.DateTimeField('Дата/время', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Журнал действий HR'
        verbose_name_plural = 'Журнал действий HR'
        ordering = ['-created_at']

    def __str__(self):
        user_name = self.user.get_full_name() if self.user else 'Система'
        return f'{user_name} — {self.get_action_display()} — {self.target_repr}'
