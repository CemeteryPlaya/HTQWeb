"""Socket.IO server configuration and handlers."""

import socketio
from app.core.settings import settings

# Configure Socket.IO with Redis Manager for scaling
mgr = socketio.AsyncRedisManager(settings.redis_url)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=mgr,
)

sio_app = socketio.ASGIApp(socketio_server=sio, socketio_path="socket.io")

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection. Auth dict should contain JWT."""
    # TODO: Validate JWT from auth dictionary
    # If invalid: raise socketio.exceptions.ConnectionRefusedError('unauthorized')
    
    # Store user info in session
    # await sio.save_session(sid, {'user_id': user_id})
    pass

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    pass

@sio.event
async def join_room(sid, data):
    """Join a chat room."""
    # session = await sio.get_session(sid)
    # room_id = data.get('room_id')
    # sio.enter_room(sid, room_id)
    pass

@sio.event
async def leave_room(sid, data):
    """Leave a chat room."""
    # room_id = data.get('room_id')
    # sio.leave_room(sid, room_id)
    pass

@sio.event
async def typing(sid, data):
    """Publish typing indicator."""
    # room_id = data.get('room_id')
    # await sio.emit('typing', {'user_id': ...}, room=room_id, skip_sid=sid)
    pass
