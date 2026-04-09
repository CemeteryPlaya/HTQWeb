from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Item(models.Model):
    """Универсальный элемент контента, привязанный к пользователю.

    Используется как базовая сущность для хранения пользовательских записей
    (заметки, черновики и т.д.). Каждый Item принадлежит одному владельцу.
    """

    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Владелец',
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Элемент'
        verbose_name_plural = 'Элементы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Profile(models.Model):
    """Расширенный профиль пользователя.

    Создаётся автоматически при регистрации нового User через сигнал post_save.
    Хранит дополнительные данные: ФИО, аватар, телефон, персональные настройки.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    display_name = models.CharField('Отображаемое имя', max_length=100, blank=True)
    bio = models.TextField('О себе', max_length=1000, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    patronymic = models.CharField('Отчество', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    settings = models.JSONField('Настройки', default=dict, blank=True)
    must_change_password = models.BooleanField(
        'Требуется смена пароля',
        default=False,
        help_text='Флаг устанавливается при создании пользователя через HR-модуль.',
    )

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f"Профиль: {self.user.username}"


# ---------------------------------------------------------------------------
# Сигналы: автоматическое создание профиля при регистрации пользователя
# ---------------------------------------------------------------------------

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Создаёт пустой Profile сразу после создания нового User."""
    if created:
        Profile.objects.create(user=instance)
