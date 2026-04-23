"""Pydantic schemas for Messenger Service."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserReplicaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    is_active: bool


class RoomParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    role: str
    last_read_message_id: Optional[uuid.UUID]
    user: Optional[UserReplicaRead]


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: Optional[str]
    room_type: str
    is_e2ee: bool
    created_at: datetime
    participants: list[RoomParticipantRead] = []


class RoomCreate(BaseModel):
    name: Optional[str] = None
    room_type: str = "direct"
    is_e2ee: bool = False
    participant_ids: list[int]


class MessageAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    file_metadata_id: uuid.UUID
    name: str
    size: int
    mime: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    room_id: int
    sender_id: Optional[int]
    content: str
    is_encrypted: bool
    is_edited: bool
    created_at: datetime
    sender: Optional[UserReplicaRead] = None
    attachments: list[MessageAttachmentRead] = []


class MessageCreate(BaseModel):
    room_id: int
    content: str
    is_encrypted: bool = False
    metadata_json: Optional[dict] = None
    attachment_ids: list[uuid.UUID] = [] # list of file_metadata_id from media-service


class UserKeyBase(BaseModel):
    public_identity_key: str
    signed_pre_key: str
    signature: str


class UserKeyCreate(UserKeyBase):
    device_id: str


class UserKeyRead(UserKeyBase):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    device_id: str
