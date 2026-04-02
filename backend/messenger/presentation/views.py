"""
REST API Views for the messenger module.

All views require JWT authentication. The current user is resolved to
their ChatUserReplica via the event bus (auto-created on first request
if missing).
"""

import base64

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from messenger.domain.models import (
    ChatRoom,
    ChatMembership,
    ChatUserReplica,
    EncryptedMessage,
    AuthKeyBundle,
    ChatAttachment,
)
from messenger.infrastructure.repositories import (
    UserReplicaRepository,
    RoomRepository,
    MessageRepository,
    KeyBundleRepository,
)
from messenger.infrastructure.event_bus import _sync_user_replica
from messenger.presentation.serializers import (
    ChatUserReplicaSerializer,
    ChatRoomSerializer,
    EncryptedMessageSerializer,
    SendMessageSerializer,
    CreateRoomSerializer,
    AuthKeyBundleSerializer,
    UploadKeyBundleSerializer,
    ChatAttachmentSerializer,
)


def _get_or_create_replica(user) -> ChatUserReplica:
    """Get the ChatUserReplica for the authenticated user, creating if needed."""
    replica = UserReplicaRepository.get_by_user_id(user.pk)
    if not replica:
        _sync_user_replica(user)
        replica = UserReplicaRepository.get_by_user_id(user.pk)
    return replica


# ---------------------------------------------------------------------------
#  Users / Search
# ---------------------------------------------------------------------------


class UserSearchView(APIView):
    """Search for users to start a chat with."""

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        dept = request.query_params.get('department', '').strip()

        if dept:
            users = UserReplicaRepository.search_by_department(dept)
        elif q:
            users = UserReplicaRepository.search_by_name(q)
        else:
            users = ChatUserReplica.objects.all()[:30]

        return Response(ChatUserReplicaSerializer(users, many=True).data)


class MeReplicaView(APIView):
    """Return the current user's ChatUserReplica."""

    def get(self, request):
        replica = _get_or_create_replica(request.user)
        if not replica:
            return Response(
                {'detail': 'User replica not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ChatUserReplicaSerializer(replica).data)


# ---------------------------------------------------------------------------
#  Rooms
# ---------------------------------------------------------------------------


class RoomListView(APIView):
    """List all chat rooms the current user belongs to."""

    def get(self, request):
        replica = _get_or_create_replica(request.user)
        if not replica:
            return Response([])
        rooms = RoomRepository.get_rooms_for_user(replica)
        return Response(ChatRoomSerializer(rooms, many=True).data)


class RoomCreateView(APIView):
    """Create a new chat room."""

    def post(self, request):
        ser = CreateRoomSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        creator = _get_or_create_replica(request.user)
        if not creator:
            return Response(
                {'detail': 'Cannot create replica for current user'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = ser.validated_data
        room_type = data['room_type']
        member_ids = data['member_user_ids']

        if room_type in ('direct', 'secret'):
            if len(member_ids) != 1:
                return Response(
                    {'detail': 'Direct/secret chats require exactly 1 other member'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            other = UserReplicaRepository.get_by_user_id(member_ids[0])
            if not other:
                return Response(
                    {'detail': f'User {member_ids[0]} not found in messenger'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # Check for existing direct room
            existing = RoomRepository.find_direct_room(creator, other)
            if existing and room_type == 'direct':
                return Response(ChatRoomSerializer(existing).data)
            room = RoomRepository.create_direct_room(creator, other, room_type)
        else:
            room = RoomRepository.create_group_room(
                title=data.get('title', ''),
                creator=creator,
                member_ids=member_ids,
            )

        room.refresh_from_db()
        return Response(
            ChatRoomSerializer(room).data,
            status=status.HTTP_201_CREATED,
        )


class RoomDetailView(APIView):
    """Get room details."""

    def get(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        try:
            room = ChatRoom.objects.get(pk=room_id, is_archived=False)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Check membership
        if not room.memberships.filter(user=replica).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(ChatRoomSerializer(room).data)


# ---------------------------------------------------------------------------
#  Messages
# ---------------------------------------------------------------------------


class MessageListView(APIView):
    """Get messages in a room, with optional pts-based pagination."""

    def get(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        try:
            room = ChatRoom.objects.get(pk=room_id, is_archived=False)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not room.memberships.filter(user=replica).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        after_pts = int(request.query_params.get('after_pts', 0))
        limit = min(int(request.query_params.get('limit', 50)), 200)

        messages = MessageRepository.get_messages(room, after_pts, limit)
        return Response(EncryptedMessageSerializer(messages, many=True).data)


class MessageSendView(APIView):
    """Send a message to a room."""

    def post(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        try:
            room = ChatRoom.objects.get(pk=room_id, is_archived=False)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not room.memberships.filter(user=replica).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        ser = SendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        msg = MessageRepository.store_message(
            room=room,
            sender=replica,
            encrypted_blob=ser.validated_data['encrypted_data'],
            msg_key=ser.validated_data['msg_key'],
            msg_type=ser.validated_data['msg_type'],
            reply_to_id=ser.validated_data.get('reply_to'),
        )

        # Update sender's local_pts
        ChatMembership.objects.filter(
            room=room, user=replica,
        ).update(local_pts=msg.pts)

        return Response(
            EncryptedMessageSerializer(msg).data,
            status=status.HTTP_201_CREATED,
        )


class MessageDifferenceView(APIView):
    """Get missed messages (gap detection via pts)."""

    def get(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        try:
            room = ChatRoom.objects.get(pk=room_id, is_archived=False)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not room.memberships.filter(user=replica).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        membership = room.memberships.get(user=replica)
        local_pts = int(request.query_params.get('local_pts', membership.local_pts))

        messages = MessageRepository.get_difference(room, local_pts)
        return Response(EncryptedMessageSerializer(messages, many=True).data)


# ---------------------------------------------------------------------------
#  Key Bundles
# ---------------------------------------------------------------------------


class KeyBundleView(APIView):
    """Upload or retrieve E2EE key bundles."""

    def get(self, request, user_id=None):
        """Get a user's public key bundle (for ECDH key exchange)."""
        if user_id:
            replica = UserReplicaRepository.get_by_user_id(user_id)
        else:
            replica = _get_or_create_replica(request.user)

        if not replica:
            return Response(status=status.HTTP_404_NOT_FOUND)

        bundle = KeyBundleRepository.get_bundle(replica)
        if not bundle:
            return Response(
                {'detail': 'No key bundle uploaded'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AuthKeyBundleSerializer(bundle).data)

    def post(self, request):
        """Upload the current user's key bundle."""
        replica = _get_or_create_replica(request.user)
        if not replica:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        ser = UploadKeyBundleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        bundle = KeyBundleRepository.upsert_bundle(
            user_replica=replica,
            identity_pub_key=ser.validated_data['identity_pub_key'],
            signed_prekey=ser.validated_data['signed_prekey'],
            prekey_signature=ser.validated_data['prekey_signature'],
        )
        return Response(
            AuthKeyBundleSerializer(bundle).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
#  Mark as Read
# ---------------------------------------------------------------------------


class MarkReadView(APIView):
    """Mark messages as read up to a given pts."""

    def post(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        pts = int(request.data.get('pts', 0))

        updated = ChatMembership.objects.filter(
            room_id=room_id,
            user=replica,
        ).update(
            local_pts=pts,
            unread_count=0,
        )

        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response({'status': 'ok'})


# ---------------------------------------------------------------------------
#  Attachments
# ---------------------------------------------------------------------------


class ChatAttachmentUploadView(APIView):
    """Upload a file attachment for a chat message."""
    
    # We need multipart or form parsers to handle file uploads
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        replica = _get_or_create_replica(request.user)
        if not replica:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Basic validation can be added here (e.g., file size, type restrictions)
        # We allow arbitrary file types as requested: zip, word, rar, 1:c, audio, etc.

        attachment = ChatAttachment.objects.create(
            file=file_obj,
            uploaded_by=replica,
        )

        return Response(
            ChatAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
#  Room Delete / Leave
# ---------------------------------------------------------------------------


class RoomDeleteView(APIView):
    """Delete or leave a chat room."""

    def delete(self, request, room_id):
        replica = _get_or_create_replica(request.user)
        try:
            room = ChatRoom.objects.get(pk=room_id, is_archived=False)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        membership = room.memberships.filter(user=replica).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if room.room_type in ('direct', 'secret'):
            # Direct/secret chats: archive the room instead of deleting
            room.is_archived = True
            room.save(update_fields=['is_archived'])
            return Response({'status': 'deleted'})

        # Group chats: owner can archive, others can leave
        if membership.role == 'owner':
            room.is_archived = True
            room.save(update_fields=['is_archived'])
            return Response({'status': 'deleted'})
        else:
            # Just leave
            membership.delete()
            return Response({'status': 'left'})


# ---------------------------------------------------------------------------
#  Admin: View all chats and messages (staff only)
# ---------------------------------------------------------------------------


class AdminAllRoomsView(APIView):
    """List ALL rooms (admin/staff only) for audit."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        rooms = ChatRoom.objects.all().order_by('-updated_at')
        return Response(ChatRoomSerializer(rooms, many=True).data)


class AdminRoomMessagesView(APIView):
    """View messages in ANY room (admin/staff only) for audit."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, room_id):
        try:
            room = ChatRoom.objects.get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        after_pts = int(request.query_params.get('after_pts', 0))
        limit = min(int(request.query_params.get('limit', 200)), 500)

        messages = MessageRepository.get_messages(room, after_pts, limit)
        return Response({
            'room': ChatRoomSerializer(room).data,
            'messages': EncryptedMessageSerializer(messages, many=True).data,
        })

