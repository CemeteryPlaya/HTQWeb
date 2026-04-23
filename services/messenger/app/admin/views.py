"""sqladmin ModelViews for Messenger."""

from sqladmin import ModelView

from app.models.domain import ChatUserReplica, Message, Room, RoomParticipant, UserKey


class ChatUserReplicaAdmin(ModelView, model=ChatUserReplica):
    column_list = [ChatUserReplica.id, ChatUserReplica.username, ChatUserReplica.is_active]
    name = "User Replica"


class RoomAdmin(ModelView, model=Room):
    column_list = [Room.id, Room.name, Room.room_type, Room.is_e2ee]
    name = "Room"


class RoomParticipantAdmin(ModelView, model=RoomParticipant):
    column_list = [RoomParticipant.room_id, RoomParticipant.user_id, RoomParticipant.role]
    name = "Room Participant"


class MessageAdmin(ModelView, model=Message):
    column_list = [Message.id, Message.room_id, Message.sender_id, Message.is_encrypted, Message.created_at]
    name = "Message"


class UserKeyAdmin(ModelView, model=UserKey):
    column_list = [UserKey.user_id, UserKey.device_id]
    name = "User Key"
