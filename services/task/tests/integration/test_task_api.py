"""Integration tests for Task APIs."""

import pytest
from tests.conftest import user_headers, admin_headers

@pytest.mark.asyncio
async def test_create_task(client):
    resp = await client.post(
        "/api/tasks/v1/tasks/",
        json={
            "summary": "Implement Calendar",
            "description": "Port calendar endpoints to FastAPI",
            "task_type": "story",
            "priority": "high",
        },
        headers=user_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["summary"] == "Implement Calendar"
    assert "TASK-" in data["key"]
    return data["id"]


@pytest.mark.asyncio
async def test_calendar_events(client):
    # Create event
    resp = await client.post(
        "/api/tasks/v1/calendar/",
        json={
            "title": "Release planning",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
        },
        headers=user_headers(),
    )
    assert resp.status_code == 201
    
    event_id = resp.json()["id"]
    
    # List events
    resp = await client.get("/api/tasks/v1/calendar/", headers=user_headers())
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    
    # Create exception
    resp = await client.post(
        f"/api/tasks/v1/calendar/{event_id}/exceptions/",
        json={"exception_date": "2026-05-02", "is_cancelled": True},
        headers=user_headers()
    )
    assert resp.status_code == 201
