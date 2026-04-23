"""Integration tests for Messenger API."""

import pytest
from tests.conftest import user_headers, admin_headers

@pytest.mark.asyncio
async def test_ingest_user_replica(client):
    resp = await client.post(
        "/api/messenger/v1/users/ingest",
        json={
            "id": 2,
            "username": "user2",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "avatar_url": None
        },
        headers=admin_headers()
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_and_list_room(client):
    # Ingest another user to participate
    await client.post(
        "/api/messenger/v1/users/ingest",
        json={"id": 3, "username": "user3", "first_name": "Test3", "last_name": "User3", "is_active": True, "avatar_url": None},
        headers=admin_headers()
    )

    resp = await client.post(
        "/api/messenger/v1/rooms/",
        json={"name": "Dev Chat", "room_type": "group", "participant_ids": [3]},
        headers=user_headers()  # user_id 2
    )
    assert resp.status_code == 201
    room_id = resp.json()["id"]

    # List rooms
    resp = await client.get("/api/messenger/v1/rooms/", headers=user_headers())
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) >= 1
    
    return room_id


@pytest.mark.asyncio
async def test_send_and_list_messages(client):
    # Setup room
    room_id = await test_create_and_list_room(client)

    # Send message
    resp = await client.post(
        "/api/messenger/v1/messages/",
        json={"room_id": room_id, "content": "Hello World!"},
        headers=user_headers()
    )
    assert resp.status_code == 201
    msg_id = resp.json()["id"]

    # List messages
    resp = await client.get(f"/api/messenger/v1/messages/room/{room_id}", headers=user_headers())
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) >= 1
    assert msgs[0]["content"] == "Hello World!"


@pytest.mark.asyncio
async def test_e2ee_keys(client):
    resp = await client.post(
        "/api/messenger/v1/keys/",
        json={
            "device_id": "device_1",
            "public_identity_key": "id_key",
            "signed_pre_key": "pre_key",
            "signature": "sig"
        },
        headers=user_headers()
    )
    assert resp.status_code == 201

    resp = await client.get("/api/messenger/v1/keys/2", headers=user_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["device_id"] == "device_1"
