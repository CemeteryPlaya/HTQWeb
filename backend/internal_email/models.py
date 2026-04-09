from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator

class EmailMessage(models.Model):
    subject = models.CharField('Тема', max_length=255, blank=True)
    body = models.TextField('Текст письма', blank=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_emails',
        verbose_name='Отправитель'
    )
    is_draft = models.BooleanField('Черновик', default=False)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    sent_at = models.DateTimeField('Дата отправки', null=True, blank=True)
    external_recipients = models.JSONField(
        'Внешние получатели',
        default=list,
        blank=True,
        help_text='Список email-адресов внешних получателей'
    )
    
    class Meta:
        verbose_name = 'Письмо'
        verbose_name_plural = 'Письма'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} (от {self.sender})"


class EmailRecipientStatus(models.Model):
    class Folder(models.TextChoices):
        INBOX = 'inbox', 'Входящие'
        ARCHIVE = 'archive', 'Архив'
        TRASH = 'trash', 'Корзина'

    class RecipientType(models.TextChoices):
        TO = 'to', 'Кому'
        CC = 'cc', 'Копия'
        BCC = 'bcc', 'Скрытая копия'

    message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        related_name='recipient_statuses',
        verbose_name='Письмо'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_statuses',
        verbose_name='Пользователь'
    )
    recipient_type = models.CharField(
        'Тип получателя',
        max_length=10,
        choices=RecipientType.choices,
        default=RecipientType.TO
    )
    folder = models.CharField(
        'Папка',
        max_length=20,
        choices=Folder.choices,
        default=Folder.INBOX
    )
    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Дата прочтения', null=True, blank=True)

    class Meta:
        verbose_name = 'Статус получателя'
        verbose_name_plural = 'Статусы получателей'
        unique_together = ('message', 'user', 'recipient_type')

    def __str__(self):
        return f"{self.user} - {self.message.subject} ({self.folder})"


class EmailAttachment(models.Model):
    message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Письмо'
    )
    file = models.FileField(
        'Файл',
        upload_to='internal_emails/'
    )
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'

    def __str__(self):
        return f"Вложение к {self.message.subject}"


class EmailOAuthToken(models.Model):
    """
    OAuth 2.0 tokens for sending external email on behalf of the employee.
    Tokens are encrypted at rest with AES-256-GCM (see crypto.py).
    """

    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google Workspace'
        MICROSOFT = 'microsoft', 'Microsoft 365'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_oauth_token',
        verbose_name='Пользователь',
    )
    provider = models.CharField(
        'Провайдер',
        max_length=20,
        choices=Provider.choices,
    )
    encrypted_access_token = models.BinaryField(
        'Access Token (encrypted)',
        editable=False,
    )
    encrypted_refresh_token = models.BinaryField(
        'Refresh Token (encrypted)',
        editable=False,
    )
    token_expires_at = models.DateTimeField(
        'Срок действия Access Token',
    )
    scope = models.CharField(
        'Granted Scopes',
        max_length=500,
        blank=True,
    )
    user_email = models.EmailField(
        'Email провайдера',
        help_text='Email-адрес пользователя на стороне Google/Microsoft',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'OAuth-токен почты'
        verbose_name_plural = 'OAuth-токены почты'

    def __str__(self):
        return f'{self.user} — {self.get_provider_display()} ({self.user_email})'

    # ---- Transparent encrypt/decrypt properties ----

    @property
    def access_token(self) -> str:
        from .crypto import decrypt
        if self.encrypted_access_token:
            return decrypt(bytes(self.encrypted_access_token))
        return ''

    @access_token.setter
    def access_token(self, value: str):
        from .crypto import encrypt
        self.encrypted_access_token = encrypt(value)

    @property
    def refresh_token(self) -> str:
        from .crypto import decrypt
        if self.encrypted_refresh_token:
            return decrypt(bytes(self.encrypted_refresh_token))
        return ''

    @refresh_token.setter
    def refresh_token(self, value: str):
        from .crypto import encrypt
        self.encrypted_refresh_token = encrypt(value)

    def is_token_expired(self) -> bool:
        """True if access token is expired or expires within 5 minutes."""
        from django.utils import timezone
        if not self.token_expires_at:
            return True
        return timezone.now() >= self.token_expires_at - timezone.timedelta(minutes=5)
