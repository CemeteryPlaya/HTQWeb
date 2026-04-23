"""Messenger Domain Models (Zero-Join Architecture)."""

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntIdMixin, TimestampMixin
from app.models.types import LtreeType


class ChatUserReplica(Base, TimestampMixin):
    """Denormalized user data to avoid cross-schema joins."""
    __tablename__ = "chat_user_replicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    department_path: Mapped[Optional[str]] = mapped_column(LtreeType, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Room(Base, IntIdMixin, TimestampMixin):
    """Chat room."""
    __tablename__ = "rooms"

    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    room_type: Mapped[str] = mapped_column(String(20), nullable=False, default="direct") # direct, group, department
    department_path: Mapped[Optional[str]] = mapped_column(LtreeType, nullable=True)
    is_e2ee: Mapped[bool] = mapped_column(Boolean, default=False)
    
    participants: Mapped[list["RoomParticipant"]] = relationship("RoomParticipant", back_populates="room")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="room")


class RoomParticipant(Base, TimestampMixin):
    """Participant in a room."""
    __tablename__ = "room_participants"

    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("chat_user_replicas.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member") # admin, member
    last_read_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    room: Mapped["Room"] = relationship("Room", back_populates="participants")
    user: Mapped["ChatUserReplica"] = relationship("ChatUserReplica")


class Message(Base, TimestampMixin):
    """Message inside a room."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("chat_user_replicas.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False) # Plaintext or encrypted blob
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    room: Mapped["Room"] = relationship("Room", back_populates="messages")
    sender: Mapped["ChatUserReplica"] = relationship("ChatUserReplica")


class ChatAttachment(Base, TimestampMixin):
    """Attachment metadata for a message."""
    __tablename__ = "chat_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=True)
    file_metadata_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # Refers to media-service if used
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("chat_user_replicas.id", ondelete="CASCADE"), nullable=False)


class UserKey(Base, TimestampMixin):
    """Public keys for E2EE."""
    __tablename__ = "user_keys"

    user_id: Mapped[int] = mapped_column(ForeignKey("chat_user_replicas.id", ondelete="CASCADE"), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    public_identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    signed_pre_key: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
