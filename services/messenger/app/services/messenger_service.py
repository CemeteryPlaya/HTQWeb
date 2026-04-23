"""Messenger application layer."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import ChatUserReplica, Message, Room, RoomParticipant, ChatAttachment
from app.schemas.messenger import MessageCreate, RoomCreate
from app.api.socket import sio


class MessengerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_room(self, data: RoomCreate, creator_id: int) -> Room:
        """Create a room and add participants."""
        room = Room(name=data.name, room_type=data.room_type, is_e2ee=data.is_e2ee)
        self.session.add(room)
        await self.session.flush()

        participants = set(data.participant_ids)
        participants.add(creator_id)

        for uid in participants:
            rp = RoomParticipant(room_id=room.id, user_id=uid, role="admin" if uid == creator_id else "member")
            self.session.add(rp)
            
        await self.session.commit()
        await self.session.refresh(room, ["participants"])
        return room

    async def send_message(self, data: MessageCreate, sender_id: int) -> Message:
        """Save message to DB and emit via Socket.IO."""
        # 1. Verify user is in room
        rp = await self.session.get(RoomParticipant, (data.room_id, sender_id))
        if not rp:
            raise ValueError("Sender is not a participant in this room")

        # 2. Save message
        msg = Message(
            room_id=data.room_id,
            sender_id=sender_id,
            content=data.content,
            is_encrypted=data.is_encrypted,
            metadata_json=data.metadata_json,
        )
        self.session.add(msg)
        await self.session.flush()

        # 3. Handle attachments (simplified here)
        # In a real scenario, you'd fetch metadata from media-service or trust the client
        # For now, we skip attachment processing logic.

        await self.session.commit()

        # 4. Fetch with relations to broadcast
        result = await self.session.execute(
            select(Message).where(Message.id == msg.id).options(selectinload(Message.sender))
        )
        full_msg = result.scalar_one()

        # 5. Broadcast to room via Socket.IO
        # Room name in socket.io can be just the string of room_id
        await sio.emit(
            "new_message",
            {
                "id": str(full_msg.id),
                "room_id": full_msg.room_id,
                "sender_id": full_msg.sender_id,
                "content": full_msg.content,
                "created_at": full_msg.created_at.isoformat() if full_msg.created_at else None,
            },
            room=str(data.room_id),
        )

        return full_msg

    async def mark_read(self, room_id: int, message_id: uuid.UUID, user_id: int) -> None:
        """Mark a message as read for a user."""
        rp = await self.session.get(RoomParticipant, (room_id, user_id))
        if not rp:
            raise ValueError("User not in room")

        rp.last_read_message_id = message_id
        await self.session.commit()

        # Broadcast read receipt
        await sio.emit(
            "message_read",
            {"room_id": room_id, "user_id": user_id, "message_id": str(message_id)},
            room=str(room_id),
        )

    async def publish_typing(self, room_id: int, user_id: int) -> None:
        """Publish typing indicator."""
        await sio.emit(
            "typing",
            {"room_id": room_id, "user_id": user_id},
            room=str(room_id),
        )
