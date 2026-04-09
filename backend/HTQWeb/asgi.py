"""
ASGI config for HTQWeb project.

Supports both HTTP and WebSocket protocols:
- HTTP requests → standard Django ASGI handler
- WebSocket connections → Django Channels consumers (messenger)

Production: run via Daphne
    daphne HTQWeb.asgi:application --bind 0.0.0.0 --port 8000

Development: `python manage.py runserver` (Daphne overrides runserver)
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

# Import after Django setup to avoid AppRegistryNotReady
from messenger.presentation.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    # HTTP → standard Django
    'http': django_asgi_app,

    # WebSocket → Channels with auth
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
