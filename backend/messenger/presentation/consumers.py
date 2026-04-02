"""
WebSocket consumer for real-time chat messaging.

Uses Django Channels' JsonWebsocketConsumer for automatic JSON
serialization. Authentication via session middleware (set up in ASGI).

Protocol:
    Client → Server:
        { "type": "send_message", "encrypted_data": "<base64>", "msg_key": "<base64>", "msg_type": "text" }
        { "type": "mark_read", "pts": 42 }
        { "type": "typing" }

    Server → Client:
        { "type": "new_message", ...EncryptedMessageSerializer data }
        { "type": "user_typing", "user_id": 1, "full_name": "..." }
        { "type": "read_receipt", "user_id": 1, "pts": 42 }
"""

import base64
import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from messenger.domain.models import (
    ChatRoom,
    ChatMembership,
    ChatUserReplica,
)
from messenger.infrastructure.repositories import (
    UserReplicaRepository,
    MessageRepository,
)
from messenger.presentation.serializers import EncryptedMessageSerializer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for a single chat room.

    URL: ws/chat/<room_id>/

    On connect:
        - Validates user authentication
        - Validates room membership
        - Joins the Channels group for this room

    On receive_json:
        - Dispatches to handler based on 'type' field
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope.get('user')

        # Reject anonymous connections
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        # Verify room membership
        self.replica = await self._get_replica()
        if not self.replica:
            await self.close(code=4002)
            return

        is_member = await self._check_membership()
        if not is_member:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

        # Mark user as online
        await self._set_online(True)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )
        if hasattr(self, 'replica') and self.replica:
            await self._set_online(False)

    async def receive_json(self, content):
        msg_type = content.get('type', '')

        if msg_type == 'send_message':
            await self._handle_send_message(content)
        elif msg_type == 'mark_read':
            await self._handle_mark_read(content)
        elif msg_type == 'typing':
            await self._handle_typing()
        else:
            await self.send_json({'error': f'Unknown type: {msg_type}'})

    # --- Handlers ---

    async def _handle_send_message(self, content):
        try:
            encrypted_blob = base64.b64decode(content.get('encrypted_data', ''))
            msg_key = base64.b64decode(content.get('msg_key', '')) if content.get('msg_key') else b''
        except Exception:
            await self.send_json({'error': 'Invalid base64 data'})
            return

        msg = await self._store_message(
            encrypted_blob=encrypted_blob,
            msg_key=msg_key,
            msg_type=content.get('msg_type', 'text'),
        )

        msg_data = await self._serialize_message(msg)

        # Broadcast to all room members
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.new_message',
                'message': msg_data,
            },
        )

    async def _handle_mark_read(self, content):
        pts = content.get('pts', 0)
        await self._update_read_pts(pts)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.read_receipt',
                'user_id': self.replica.user_id,
                'full_name': self.replica.full_name,
                'pts': pts,
            },
        )

    async def _handle_typing(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.user_typing',
                'user_id': self.replica.user_id,
                'full_name': self.replica.full_name,
            },
        )

    # --- Group message handlers (called by channel_layer.group_send) ---

    async def chat_new_message(self, event):
        await self.send_json({
            'type': 'new_message',
            **event['message'],
        })

    async def chat_read_receipt(self, event):
        await self.send_json({
            'type': 'read_receipt',
            'user_id': event['user_id'],
            'full_name': event['full_name'],
            'pts': event['pts'],
        })

    async def chat_user_typing(self, event):
        # Don't send typing indicator back to the sender
        if event['user_id'] != self.replica.user_id:
            await self.send_json({
                'type': 'user_typing',
                'user_id': event['user_id'],
                'full_name': event['full_name'],
            })

    # --- Database operations (sync → async bridge) ---

    @database_sync_to_async
    def _get_replica(self):
        return UserReplicaRepository.get_by_user_id(self.user.pk)

    @database_sync_to_async
    def _check_membership(self):
        return ChatMembership.objects.filter(
            room_id=self.room_id,
            user=self.replica,
            room__is_archived=False,
        ).exists()

    @database_sync_to_async
    def _store_message(self, encrypted_blob, msg_key, msg_type):
        room = ChatRoom.objects.get(pk=self.room_id, is_archived=False)
        return MessageRepository.store_message(
            room=room,
            sender=self.replica,
            encrypted_blob=encrypted_blob,
            msg_key=msg_key,
            msg_type=msg_type,
        )

    @database_sync_to_async
    def _serialize_message(self, msg):
        return EncryptedMessageSerializer(msg).data

    @database_sync_to_async
    def _update_read_pts(self, pts):
        ChatMembership.objects.filter(
            room_id=self.room_id,
            user=self.replica,
        ).update(local_pts=pts, unread_count=0)

    @database_sync_to_async
    def _set_online(self, is_online):
        ChatUserReplica.objects.filter(pk=self.replica.pk).update(
            is_online=is_online,
        )
