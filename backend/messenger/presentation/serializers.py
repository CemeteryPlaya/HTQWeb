"""
DRF Serializers for the messenger REST API.
"""

import base64

from rest_framework import serializers

from messenger.domain.models import (
    ChatUserReplica,
    ChatRoom,
    ChatMembership,
    EncryptedMessage,
    AuthKeyBundle,
    ChatAttachment,
)


class ChatUserReplicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatUserReplica
        fields = [
            'id', 'user_id', 'username', 'full_name', 'avatar_url',
            'department_path', 'department_name', 'position_title',
            'is_online', 'last_seen',
        ]
        read_only_fields = fields


class ChatAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = ChatUserReplicaSerializer(read_only=True)

    class Meta:
        model = ChatAttachment
        fields = ['id', 'file', 'uploaded_by', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class ChatMembershipSerializer(serializers.ModelSerializer):
    user = ChatUserReplicaSerializer(read_only=True)

    class Meta:
        model = ChatMembership
        fields = [
            'id', 'user', 'role', 'local_pts', 'unread_count',
            'is_muted', 'is_pinned', 'joined_at', 'last_read_at',
        ]
        read_only_fields = ['id', 'user', 'joined_at']


class ChatRoomSerializer(serializers.ModelSerializer):
    memberships = ChatMembershipSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_type', 'title', 'avatar_url',
            'current_pts', 'memberships', 'last_message',
            'is_archived', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-pts').first()
        if msg:
            return EncryptedMessageSerializer(msg).data
        return None


class EncryptedMessageSerializer(serializers.ModelSerializer):
    sender = ChatUserReplicaSerializer(read_only=True)
    # Encode binary blob as base64 for JSON transport
    encrypted_data = serializers.SerializerMethodField()
    msg_key_b64 = serializers.SerializerMethodField()

    class Meta:
        model = EncryptedMessage
        fields = [
            'id', 'room', 'sender', 'msg_type',
            'encrypted_data', 'msg_key_b64',
            'pts', 'pts_count', 'seq_no',
            'reply_to', 'is_edited', 'created_at',
        ]
        read_only_fields = fields

    def get_encrypted_data(self, obj):
        if obj.encrypted_blob:
            return base64.b64encode(bytes(obj.encrypted_blob)).decode('ascii')
        return ''

    def get_msg_key_b64(self, obj):
        if obj.msg_key:
            return base64.b64encode(bytes(obj.msg_key)).decode('ascii')
        return ''


class SendMessageSerializer(serializers.Serializer):
    """Input serializer for sending a message."""
    encrypted_data = serializers.CharField(
        help_text='Base64-encoded encrypted blob',
    )
    msg_key = serializers.CharField(
        required=False, default='',
        help_text='Base64-encoded msg_key (for E2EE rooms)',
    )
    msg_type = serializers.ChoiceField(
        choices=['text', 'file', 'system', 'key_exchange'],
        default='text',
    )
    reply_to = serializers.IntegerField(required=False, allow_null=True)

    def validate_encrypted_data(self, value):
        try:
            return base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError('Invalid base64 data')

    def validate_msg_key(self, value):
        if not value:
            return b''
        try:
            return base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError('Invalid base64 msg_key')


class CreateRoomSerializer(serializers.Serializer):
    """Input serializer for creating a chat room."""
    room_type = serializers.ChoiceField(
        choices=['direct', 'group', 'secret'],
        default='direct',
    )
    title = serializers.CharField(required=False, default='')
    member_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text='List of auth.User IDs to add as members',
    )


class AuthKeyBundleSerializer(serializers.ModelSerializer):
    identity_pub_key_b64 = serializers.SerializerMethodField()
    signed_prekey_b64 = serializers.SerializerMethodField()
    prekey_signature_b64 = serializers.SerializerMethodField()

    class Meta:
        model = AuthKeyBundle
        fields = [
            'id', 'user',
            'identity_pub_key_b64', 'signed_prekey_b64', 'prekey_signature_b64',
            'uploaded_at',
        ]
        read_only_fields = fields

    def get_identity_pub_key_b64(self, obj):
        return base64.b64encode(bytes(obj.identity_pub_key)).decode('ascii')

    def get_signed_prekey_b64(self, obj):
        return base64.b64encode(bytes(obj.signed_prekey)).decode('ascii')

    def get_prekey_signature_b64(self, obj):
        return base64.b64encode(bytes(obj.prekey_signature)).decode('ascii')


class UploadKeyBundleSerializer(serializers.Serializer):
    identity_pub_key = serializers.CharField(help_text='Base64')
    signed_prekey = serializers.CharField(help_text='Base64')
    prekey_signature = serializers.CharField(help_text='Base64')

    def _decode(self, value, field_name):
        try:
            return base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError({field_name: 'Invalid base64'})

    def validate_identity_pub_key(self, v):
        return self._decode(v, 'identity_pub_key')

    def validate_signed_prekey(self, v):
        return self._decode(v, 'signed_prekey')

    def validate_prekey_signature(self, v):
        return self._decode(v, 'prekey_signature')
