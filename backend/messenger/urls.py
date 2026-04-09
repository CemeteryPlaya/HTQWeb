from django.urls import path
from rest_framework.routers import DefaultRouter

from messenger.presentation.views import (
    UserSearchView,
    MeReplicaView,
    RoomListView,
    RoomCreateView,
    RoomDetailView,
    RoomDeleteView,
    MessageListView,
    MessageSendView,
    MessageDifferenceView,
    KeyBundleView,
    MarkReadView,
    AdminAllRoomsView,
    AdminRoomMessagesView,
    ChatAttachmentUploadView,
)

app_name = 'messenger'

urlpatterns = [
    # Users
    path('users/search/', UserSearchView.as_view(), name='user-search'),
    path('users/me/', MeReplicaView.as_view(), name='user-me'),

    # Rooms
    path('rooms/', RoomListView.as_view(), name='room-list'),
    path('rooms/create/', RoomCreateView.as_view(), name='room-create'),
    path('rooms/<int:room_id>/', RoomDetailView.as_view(), name='room-detail'),
    path('rooms/<int:room_id>/delete/', RoomDeleteView.as_view(), name='room-delete'),

    # Messages
    path('rooms/<int:room_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('rooms/<int:room_id>/messages/send/', MessageSendView.as_view(), name='message-send'),
    path('rooms/<int:room_id>/messages/difference/', MessageDifferenceView.as_view(), name='message-difference'),
    path('rooms/<int:room_id>/read/', MarkReadView.as_view(), name='mark-read'),

    # Key Bundles
    path('keys/', KeyBundleView.as_view(), name='key-bundle-me'),
    path('keys/<int:user_id>/', KeyBundleView.as_view(), name='key-bundle-user'),

    # Attachments
    path('attachments/upload/', ChatAttachmentUploadView.as_view(), name='attachment-upload'),

    # Admin (staff only)
    path('admin/rooms/', AdminAllRoomsView.as_view(), name='admin-rooms'),
    path('admin/rooms/<int:room_id>/messages/', AdminRoomMessagesView.as_view(), name='admin-room-messages'),
]
