from django.contrib import admin

from messenger.domain.models import (
    ChatUserReplica,
    ChatRoom,
    ChatMembership,
    EncryptedMessage,
    AuthKeyBundle,
)


@admin.register(ChatUserReplica)
class ChatUserReplicaAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'full_name', 'department_name', 'position_title', 'is_online', 'last_seen')
    list_filter = ('is_online',)
    search_fields = ('full_name', 'username', 'department_name')
    readonly_fields = ('user_id', 'created_at', 'updated_at')


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('pk', 'room_type', 'title', 'is_archived', 'current_pts', 'created_at')
    list_filter = ('room_type', 'is_archived')
    search_fields = ('title',)
    readonly_fields = ('current_pts', 'created_at', 'updated_at')


@admin.register(ChatMembership)
class ChatMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'role', 'local_pts', 'unread_count', 'joined_at')
    list_filter = ('role',)
    raw_id_fields = ('user', 'room')


@admin.register(EncryptedMessage)
class EncryptedMessageAdmin(admin.ModelAdmin):
    list_display = ('pk', 'room', 'sender', 'msg_type', 'pts', 'created_at')
    list_filter = ('msg_type',)
    raw_id_fields = ('room', 'sender', 'reply_to')
    readonly_fields = ('pts', 'pts_count', 'created_at')


@admin.register(AuthKeyBundle)
class AuthKeyBundleAdmin(admin.ModelAdmin):
    list_display = ('user', 'uploaded_at')
    raw_id_fields = ('user',)
    readonly_fields = ('uploaded_at',)
