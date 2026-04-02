"""
Domain models for the messenger module.

ZERO-COUPLING: No ForeignKey references to auth.User, hr.Employee,
mainView.Profile, or any other external model. The ChatUserReplica
stores a denormalised copy of user data, synchronised via Event Bus
(see infrastructure/event_bus.py).

All message content is stored as encrypted BLOBs — the server never
has access to plaintext. Only public keys are stored server-side.
"""

from django.db import models

from messenger.domain.constants import (
    ROOM_TYPE_CHOICES,
    ROOM_TYPE_DIRECT,
    ROLE_CHOICES,
    ROLE_MEMBER,
    MSG_TYPE_CHOICES,
    MSG_TYPE_TEXT,
    X25519_PUBLIC_KEY_SIZE,
)
from messenger.infrastructure.ltree_fields import LTreeField


# ---------------------------------------------------------------------------
#  ChatAttachment
# ---------------------------------------------------------------------------
import uuid

class ChatAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField('Файл', upload_to='chat_attachments/%Y/%m/')
    uploaded_by = models.ForeignKey(
        'ChatUserReplica',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_attachments',
        verbose_name='Загрузил',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'messenger_chat_attachment'
        verbose_name = 'Вложение чата'
        verbose_name_plural = 'Вложения чатов'
        ordering = ['-created_at']

    def __str__(self):
        return f"Attachment {self.id} (by {self.uploaded_by})"


# ---------------------------------------------------------------------------
#  ChatUserReplica — local copy of user data (ZERO JOIN guarantee)
# ---------------------------------------------------------------------------


class ChatUserReplica(models.Model):
    """
    Denormalised copy of user data inside the messenger boundary.

    Populated and updated exclusively via the Event Bus — no direct
    queries to ``auth_user``, ``hr_employee``, or ``mainview_profile``.

    ``department_path`` uses ltree (PostgreSQL) for instant ancestor/
    descendant queries, e.g.::

        ChatUserReplica.objects.filter(
            department_path__descendant_of='Global.Engineering'
        )
    """
    # Integer ID matching auth.User.pk — NOT a ForeignKey!
    user_id = models.IntegerField(
        'ID пользователя',
        unique=True,
        db_index=True,
        help_text='Matches auth.User.pk — no FK constraint.',
    )
    username = models.CharField('Логин', max_length=150)
    full_name = models.CharField('ФИО', max_length=300)
    avatar_url = models.CharField(
        'URL аватара', max_length=500, blank=True, default='',
    )

    # Materialized path — e.g. "Global.Engineering.Backend"
    department_path = LTreeField('Путь отдела')
    department_name = models.CharField(
        'Название отдела', max_length=200, blank=True, default='',
    )
    position_title = models.CharField(
        'Должность', max_length=200, blank=True, default='',
    )

    is_online = models.BooleanField('Онлайн', default=False, db_index=True)
    last_seen = models.DateTimeField('Последний раз онлайн', auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messenger_chat_user_replica'
        verbose_name = 'Реплика пользователя (чат)'
        verbose_name_plural = 'Реплики пользователей (чат)'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} (uid={self.user_id})'


# ---------------------------------------------------------------------------
#  ChatRoom
# ---------------------------------------------------------------------------


class ChatRoom(models.Model):
    """
    Chat room. Supports three types:
    - ``direct``  — two participants, unencrypted (or server-side encrypted)
    - ``group``   — N participants, unencrypted
    - ``secret``  — two participants, end-to-end encrypted (E2EE)
    """
    room_type = models.CharField(
        'Тип',
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default=ROOM_TYPE_DIRECT,
        db_index=True,
    )
    title = models.CharField(
        'Название', max_length=300, blank=True, default='',
        help_text='For group chats. Direct/secret chats derive title from members.',
    )
    # Denormalised member list for quick listing queries
    members = models.ManyToManyField(
        ChatUserReplica,
        through='ChatMembership',
        related_name='rooms',
        verbose_name='Участники',
    )

    # Room-level pts counter — monotonically increasing
    current_pts = models.BigIntegerField(
        'Текущий PTS', default=0,
        help_text='Global sequence number for this room.',
    )

    # Metadata
    avatar_url = models.CharField(
        'Аватар комнаты', max_length=500, blank=True, default='',
    )
    is_archived = models.BooleanField('В архиве', default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messenger_chat_room'
        verbose_name = 'Комната чата'
        verbose_name_plural = 'Комнаты чатов'
        ordering = ['-updated_at']

    def __str__(self):
        return f'[{self.room_type}] {self.title or self.pk}'

    def next_pts(self, count: int = 1) -> int:
        """
        Atomically increment and return the next pts value.

        Uses F() expression to prevent race conditions under concurrency.
        """
        from django.db.models import F
        ChatRoom.objects.filter(pk=self.pk).update(
            current_pts=F('current_pts') + count,
        )
        self.refresh_from_db(fields=['current_pts'])
        return self.current_pts


# ---------------------------------------------------------------------------
#  ChatMembership — join table with per-user sync state
# ---------------------------------------------------------------------------


class ChatMembership(models.Model):
    """
    Association between a user and a room.

    Tracks per-user synchronisation state (``local_pts``) for gap detection:
        ``pts_before = message.pts - message.pts_count``
        if ``pts_before != membership.local_pts``:
            → request getDifference to fill the gap
    """
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Комната',
    )
    user = models.ForeignKey(
        ChatUserReplica,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Пользователь',
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MEMBER,
    )

    # Synchronisation state
    local_pts = models.BigIntegerField(
        'Локальный PTS', default=0,
        help_text='Last pts this user has acknowledged.',
    )
    unread_count = models.IntegerField('Непрочитанные', default=0)

    # Preferences
    is_muted = models.BooleanField('Без звука', default=False)
    is_pinned = models.BooleanField('Закреплён', default=False)

    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(
        'Последнее чтение', null=True, blank=True,
    )

    class Meta:
        db_table = 'messenger_chat_membership'
        verbose_name = 'Участие в чате'
        verbose_name_plural = 'Участия в чатах'
        unique_together = [('room', 'user')]
        ordering = ['-is_pinned', '-last_read_at']

    def __str__(self):
        return f'{self.user} in {self.room}'


# ---------------------------------------------------------------------------
#  EncryptedMessage — server stores ONLY ciphertext
# ---------------------------------------------------------------------------


class EncryptedMessage(models.Model):
    """
    A single message in a chat room.

    For ``secret`` rooms: ``encrypted_blob`` contains AES-256-GCM ciphertext,
    ``msg_key`` contains the 128-bit key used for KDF verification.
    The server NEVER decrypts — it is a blind relay.

    For ``direct``/``group`` rooms: ``encrypted_blob`` contains plaintext JSON
    (message body, type, etc.) and ``msg_key`` is empty. Encryption at rest
    can be added at the database level if needed.
    """
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Комната',
    )
    sender = models.ForeignKey(
        ChatUserReplica,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
        verbose_name='Отправитель',
    )

    # Content — always a binary blob
    encrypted_blob = models.BinaryField(
        'Зашифрованные данные',
        help_text='AES-256-GCM ciphertext (secret) or plaintext JSON (direct/group).',
    )
    msg_key = models.BinaryField(
        'Ключ сообщения',
        max_length=16,
        blank=True,
        default=b'',
        help_text='128-bit msg_key for E2EE verification. Empty for non-secret rooms.',
    )
    msg_type = models.CharField(
        'Тип сообщения',
        max_length=20,
        choices=MSG_TYPE_CHOICES,
        default=MSG_TYPE_TEXT,
    )

    # Synchronisation
    pts = models.BigIntegerField(
        'PTS',
        db_index=True,
        help_text='Room-level monotonic sequence number.',
    )
    pts_count = models.IntegerField(
        'PTS count', default=1,
        help_text='How many pts slots this update occupies.',
    )

    # Replay attack protection — per-sender monotonic counter inside E2EE payload
    # (stored encrypted, server cannot read; this field is for indexing only)
    seq_no = models.BigIntegerField(
        'Seq No (encrypted)',
        null=True, blank=True,
        help_text='Strictly increasing per-sender counter. Verified client-side.',
    )

    # Metadata
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='replies',
        verbose_name='Ответ на',
    )
    is_edited = models.BooleanField('Отредактировано', default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'messenger_encrypted_message'
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['pts']
        indexes = [
            models.Index(fields=['room', 'pts'], name='msg_room_pts_idx'),
            models.Index(fields=['room', 'created_at'], name='msg_room_created_idx'),
        ]

    def __str__(self):
        sender_name = self.sender.full_name if self.sender else 'system'
        return f'[{self.room_id}] pts={self.pts} from {sender_name}'


# ---------------------------------------------------------------------------
#  AuthKeyBundle — public keys for ECDH (private keys NEVER on server)
# ---------------------------------------------------------------------------


class AuthKeyBundle(models.Model):
    """
    Public key bundle for E2EE key exchange.

    Each user uploads their X25519 public key. During secret chat initiation,
    the initiator fetches the responder's public key and performs ECDH locally
    to derive the shared ``auth_key``.

    Private keys are generated and stored exclusively on the client
    (IndexedDB / Web Crypto API).
    """
    user = models.OneToOneField(
        ChatUserReplica,
        on_delete=models.CASCADE,
        related_name='auth_key_bundle',
        verbose_name='Пользователь',
    )

    # X25519 public key (32 bytes)
    identity_pub_key = models.BinaryField(
        'Публичный ключ X25519',
        max_length=X25519_PUBLIC_KEY_SIZE,
        help_text='32-byte X25519 public key for ECDH key exchange.',
    )

    # Signed pre-key for asynchronous key exchange
    signed_prekey = models.BinaryField(
        'Подписанный pre-key',
        max_length=X25519_PUBLIC_KEY_SIZE,
        help_text='Signed pre-key for async E2EE initiation.',
    )
    prekey_signature = models.BinaryField(
        'Подпись pre-key',
        max_length=64,
        help_text='Ed25519 signature over signed_prekey.',
    )

    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messenger_auth_key_bundle'
        verbose_name = 'Связка ключей'
        verbose_name_plural = 'Связки ключей'

    def __str__(self):
        return f'KeyBundle for {self.user}'
