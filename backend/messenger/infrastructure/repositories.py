"""
Repository layer — database access for messenger domain models.

Encapsulates all QuerySet operations. Views and consumers call these
instead of touching models directly. This allows easy swapping of
the storage backend in the future.
"""

from django.db import transaction
from django.db.models import F

from messenger.domain.models import (
    ChatRoom,
    ChatMembership,
    ChatUserReplica,
    EncryptedMessage,
    AuthKeyBundle,
)
from messenger.domain.constants import (
    ROOM_TYPE_DIRECT,
    ROOM_TYPE_SECRET,
    ROLE_OWNER,
    ROLE_MEMBER,
)


# ---------------------------------------------------------------------------
#  ChatUserReplica repository
# ---------------------------------------------------------------------------


class UserReplicaRepository:
    """Read-only access to ChatUserReplica from within the messenger module."""

    @staticmethod
    def get_by_user_id(user_id: int) -> ChatUserReplica | None:
        try:
            return ChatUserReplica.objects.get(user_id=user_id)
        except ChatUserReplica.DoesNotExist:
            return None

    @staticmethod
    def search_by_name(query: str, limit: int = 20):
        return ChatUserReplica.objects.filter(
            full_name__icontains=query
        )[:limit]

    @staticmethod
    def search_by_department(department_path: str, limit: int = 50):
        """
        Find all users in a department subtree.

        Uses ltree ``descendant_of`` lookup (PostgreSQL: ``<@`` operator,
        SQLite: ``LIKE`` fallback).
        """
        return ChatUserReplica.objects.filter(
            department_path__descendant_of=department_path,
        )[:limit]


# ---------------------------------------------------------------------------
#  ChatRoom repository
# ---------------------------------------------------------------------------


class RoomRepository:

    @staticmethod
    def get_rooms_for_user(user_replica: ChatUserReplica):
        """Get all rooms a user is a member of, ordered by last activity."""
        return ChatRoom.objects.filter(
            memberships__user=user_replica,
            is_archived=False,
        ).distinct().order_by('-updated_at')

    @staticmethod
    def find_direct_room(user_a: ChatUserReplica, user_b: ChatUserReplica):
        """Find existing direct room between two users, or None."""
        return ChatRoom.objects.filter(
            room_type=ROOM_TYPE_DIRECT,
            memberships__user=user_a,
            is_archived=False,
        ).filter(
            memberships__user=user_b,
        ).first()

    @staticmethod
    @transaction.atomic
    def create_direct_room(
        user_a: ChatUserReplica,
        user_b: ChatUserReplica,
        room_type: str = ROOM_TYPE_DIRECT,
    ) -> ChatRoom:
        """Create a direct (or secret) chat room between two users."""
        room = ChatRoom.objects.create(room_type=room_type)
        ChatMembership.objects.create(room=room, user=user_a, role=ROLE_OWNER)
        ChatMembership.objects.create(room=room, user=user_b, role=ROLE_MEMBER)
        return room

    @staticmethod
    @transaction.atomic
    def create_group_room(
        title: str,
        creator: ChatUserReplica,
        member_ids: list[int],
    ) -> ChatRoom:
        """Create a group chat room."""
        from messenger.domain.constants import ROOM_TYPE_GROUP

        room = ChatRoom.objects.create(
            room_type=ROOM_TYPE_GROUP,
            title=title,
        )
        ChatMembership.objects.create(room=room, user=creator, role=ROLE_OWNER)
        members = ChatUserReplica.objects.filter(user_id__in=member_ids)
        for member in members:
            if member.pk != creator.pk:
                ChatMembership.objects.create(
                    room=room, user=member, role=ROLE_MEMBER,
                )
        return room


# ---------------------------------------------------------------------------
#  Message repository
# ---------------------------------------------------------------------------


class MessageRepository:

    @staticmethod
    @transaction.atomic
    def store_message(
        room: ChatRoom,
        sender: ChatUserReplica,
        encrypted_blob: bytes,
        msg_key: bytes = b'',
        msg_type: str = 'text',
        pts_count: int = 1,
        reply_to_id: int | None = None,
    ) -> EncryptedMessage:
        """
        Store a message and atomically increment room pts.

        Returns the created EncryptedMessage with its assigned pts.
        """
        new_pts = room.next_pts(count=pts_count)

        msg = EncryptedMessage.objects.create(
            room=room,
            sender=sender,
            encrypted_blob=encrypted_blob,
            msg_key=msg_key,
            msg_type=msg_type,
            pts=new_pts,
            pts_count=pts_count,
            reply_to_id=reply_to_id,
        )

        # Update room's updated_at for sorting
        ChatRoom.objects.filter(pk=room.pk).update(
            updated_at=msg.created_at,
        )

        return msg

    @staticmethod
    def get_messages(room: ChatRoom, after_pts: int = 0, limit: int = 50):
        """Get messages after a given pts value (for sync/pagination)."""
        return EncryptedMessage.objects.filter(
            room=room,
            pts__gt=after_pts,
        ).select_related('sender')[:limit]

    @staticmethod
    def get_difference(room: ChatRoom, local_pts: int, limit: int = 100):
        """
        Fetch missed messages (gap detection).

        Client provides their local_pts, we return all messages
        with pts > local_pts.
        """
        return EncryptedMessage.objects.filter(
            room=room,
            pts__gt=local_pts,
        ).select_related('sender').order_by('pts')[:limit]


# ---------------------------------------------------------------------------
#  AuthKeyBundle repository
# ---------------------------------------------------------------------------


class KeyBundleRepository:

    @staticmethod
    def get_bundle(user_replica: ChatUserReplica) -> AuthKeyBundle | None:
        try:
            return user_replica.auth_key_bundle
        except AuthKeyBundle.DoesNotExist:
            return None

    @staticmethod
    def upsert_bundle(
        user_replica: ChatUserReplica,
        identity_pub_key: bytes,
        signed_prekey: bytes,
        prekey_signature: bytes,
    ) -> AuthKeyBundle:
        bundle, _ = AuthKeyBundle.objects.update_or_create(
            user=user_replica,
            defaults={
                'identity_pub_key': identity_pub_key,
                'signed_prekey': signed_prekey,
                'prekey_signature': prekey_signature,
            },
        )
        return bundle
