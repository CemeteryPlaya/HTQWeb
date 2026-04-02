import secrets
import string

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
#  Soft-delete infrastructure
# ---------------------------------------------------------------------------


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet, который по умолчанию скрывает «удалённые» записи."""

    def delete(self):
        """Мягкое удаление всего queryset."""
        return self.update(is_deleted=True)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Менеджер, возвращающий только «живые» записи."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteAllManager(models.Manager):
    """Менеджер, который включает удалённые записи (для администрирования)."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    """
    Абстрактный миксин для мягкого удаления.
    Вместо физического удаления выставляется флаг ``is_deleted = True``.
    Менеджер ``objects`` по умолчанию скрывает такие записи.
    ``all_objects`` — менеджер, показывающий всё (для Senior HR / Admin).
    """
    is_deleted = models.BooleanField('Удалён', default=False, db_index=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Мягкое удаление."""
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])

    def hard_delete(self, using=None, keep_parents=False):
        """Физическое удаление (использовать осторожно)."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Восстановить запись."""
        self.is_deleted = False
        self.save(update_fields=['is_deleted'])


class Department(SoftDeleteMixin, models.Model):
    """Отдел компании."""
    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    index = models.PositiveIntegerField(
        'Индекс', unique=True, editable=False, null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'
        ordering = ['index', 'name']

    def save(self, *args, **kwargs):
        if self.index is None:
            max_idx = (
                Department.all_objects
                .aggregate(models.Max('index'))['index__max']
            ) or 0
            self.index = max_idx + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.index}. {self.name}'


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
    index = models.CharField(
        'Индекс', max_length=20, unique=True, editable=False,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['index', 'title']

    def save(self, *args, **kwargs):
        if not self.index and self.department_id:
            dept_index = self.department.index or 0
            max_sub = (
                Position.objects
                .filter(department=self.department)
                .exclude(pk=self.pk)
                .aggregate(models.Max('index'))['index__max']
            )
            if max_sub:
                # Extract the sub-number after the dot
                try:
                    sub = int(max_sub.rsplit('.', 1)[-1])
                except (ValueError, IndexError):
                    sub = 0
            else:
                sub = 0
            self.index = f'{dept_index}.{sub + 1}'
        super().save(*args, **kwargs)

    def __str__(self):
        prefix = f'{self.index} ' if self.index else ''
        return f'{prefix}{self.title}'


class Employee(SoftDeleteMixin, models.Model):
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

    # ---- Финансовые / конфиденциальные поля (видны только Senior HR) ----
    salary = models.DecimalField(
        'Зарплата', max_digits=12, decimal_places=2, null=True, blank=True,
    )
    bonus = models.DecimalField(
        'Премия', max_digits=12, decimal_places=2, null=True, blank=True,
    )
    passport_data = models.TextField('Паспортные данные', blank=True)
    bank_account = models.CharField('Банковский счёт', max_length=100, blank=True)

    # ---- СРО и охрана труда (промышленная специфика) ----
    sro_permit_number = models.CharField(
        'Номер допуска СРО', max_length=100, blank=True,
    )
    sro_permit_expiry = models.DateField(
        'Срок действия допуска СРО', null=True, blank=True,
    )
    safety_cert_number = models.CharField(
        'Номер сертификата ОТ', max_length=100, blank=True,
    )
    safety_cert_expiry = models.DateField(
        'Срок действия сертификата ОТ', null=True, blank=True,
    )

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
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name='Заявка',
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


class PersonnelHistory(models.Model):
    """Кадровая история — записи о приёме, увольнении, перемещениях сотрудников."""

    class EventType(models.TextChoices):
        HIRED = 'hired', 'Приём на работу'
        DISMISSED = 'dismissed', 'Увольнение'
        TRANSFER = 'transfer', 'Перемещение'
        PROMOTION = 'promotion', 'Повышение'
        DEMOTION = 'demotion', 'Понижение'
        OTHER = 'other', 'Другое'

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='personnel_history',
        verbose_name='Сотрудник',
    )
    event_type = models.CharField(
        'Тип события',
        max_length=20,
        choices=EventType.choices,
        db_index=True,
    )
    event_date = models.DateField('Дата события')
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_from',
        verbose_name='Из отдела',
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_to',
        verbose_name='В отдел',
    )
    from_position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_from',
        verbose_name='Из должности',
    )
    to_position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_to',
        verbose_name='В должность',
    )
    order_number = models.CharField('Номер приказа', max_length=100, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_personnel_history',
        verbose_name='Создал',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Кадровая история'
        verbose_name_plural = 'Кадровая история'
        ordering = ['-event_date', '-created_at']

    def __str__(self):
        return f'{self.get_event_type_display()} — {self.employee}'


class HRActionLog(models.Model):
    """Журнал действий всех пользователей."""

    class ActionType(models.TextChoices):
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Редактирование'
        DELETE = 'delete', 'Удаление'
        APPROVE = 'approve', 'Одобрение'
        REJECT = 'reject', 'Отклонение'
        STATUS_CHANGE = 'status_change', 'Смена статуса'
        LOGIN = 'login', 'Вход'
        LOGOUT = 'logout', 'Выход'
        VIEW = 'view', 'Просмотр'
        UPLOAD = 'upload', 'Загрузка'
        OTHER = 'other', 'Другое'

    class TargetType(models.TextChoices):
        EMPLOYEE = 'employee', 'Сотрудник'
        DEPARTMENT = 'department', 'Отдел'
        POSITION = 'position', 'Должность'
        VACANCY = 'vacancy', 'Вакансия'
        APPLICATION = 'application', 'Отклик'
        TIME_TRACKING = 'time_tracking', 'Учёт времени'
        DOCUMENT = 'document', 'Документ'
        # General types
        NEWS = 'news', 'Новость'
        PROFILE = 'profile', 'Профиль'
        CONTACT_REQUEST = 'contact_request', 'Обращение'
        USER = 'user', 'Пользователь'
        AUTH = 'auth', 'Авторизация'
        OTHER = 'other', 'Другое'

    class Module(models.TextChoices):
        HR = 'hr', 'HR'
        NEWS = 'news', 'Новости'
        PROFILE = 'profile', 'Профиль'
        CONTACTS = 'contacts', 'Обращения'
        AUTH = 'auth', 'Авторизация'
        ADMIN = 'admin', 'Администрирование'
        OTHER = 'other', 'Другое'

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
    url = models.CharField('URL', max_length=500, blank=True, default='')
    module = models.CharField(
        'Модуль',
        max_length=30,
        choices=Module.choices,
        default=Module.OTHER,
        db_index=True,
    )
    created_at = models.DateTimeField('Дата/время', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Журнал действий'
        verbose_name_plural = 'Журнал действий'
        ordering = ['-created_at']

    def __str__(self):
        user_name = self.user.get_full_name() if self.user else 'Система'
        return f'{user_name} — {self.get_action_display()} — {self.target_repr}'


# ---------------------------------------------------------------------------
#  Employee Account — auto-generated credentials for hired candidates
# ---------------------------------------------------------------------------

def _generate_password(length: int = 12) -> str:
    """Generate a random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class EmployeeAccount(models.Model):
    """
    Учётная запись сотрудника, автоматически создаваемая при приёме
    кандидата (статус «Принят»). Хранит начальный пароль, чтобы HR мог
    передать его сотруднику.
    """
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='account',
        verbose_name='Сотрудник',
    )
    username = models.CharField('Логин', max_length=150)
    initial_password = models.CharField(
        'Начальный пароль', max_length=128,
        help_text='Пароль, сгенерированный при создании аккаунта. '
                  'Сотрудник должен сменить его при первом входе.',
    )
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Аккаунт сотрудника'
        verbose_name_plural = 'Аккаунты сотрудников'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.employee} — {self.username}'
