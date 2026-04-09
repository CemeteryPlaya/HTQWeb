"""
WebSocket URL routing for the messenger module.
"""

from django.urls import path

from messenger.presentation.consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<int:room_id>/', ChatConsumer.as_asgi()),
]
