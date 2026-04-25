"""User-replica sync for task-service.

Subscribes to `user.upserted` / `user.deactivated` channels published by
user-service (services/user/app/workers/actors.py:user_upserted) and writes
into the local task-service `users` replica table.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db import async_session_factory
from app.models.user_replica import User as UserReplica


log = structlog.get_logger(__name__)


async def _upsert_replica(session: AsyncSession, payload: dict[str, Any]) -> None:
    user_id = int(payload["id"])
    existing = await session.get(UserReplica, user_id)
    fields = {
        "username": payload.get("username") or "",
        "first_name": payload.get("first_name") or "",
        "last_name": payload.get("last_name") or "",
        "is_active": bool(payload.get("is_active", True)),
    }
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        session.add(UserReplica(id=user_id, **fields))
    await session.commit()


async def _deactivate_replica(session: AsyncSession, user_id: int) -> None:
    existing = await session.get(UserReplica, user_id)
    if existing is None:
        return
    existing.is_active = False
    await session.commit()


async def _handle(channel: str, raw: bytes | str) -> None:
    try:
        payload = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("replica_sync_bad_json", channel=channel)
        return

    async with async_session_factory() as session:
        try:
            if channel == "user.upserted":
                await _upsert_replica(session, payload)
            elif channel == "user.deactivated":
                await _deactivate_replica(session, int(payload.get("id", 0)))
            else:
                return
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            log.exception("replica_sync_error", channel=channel, err=str(exc))
            return

    log.info("replica_synced", channel=channel, user_id=payload.get("id"))


async def run_user_replica_sync_loop() -> None:
    backoff = 1
    while True:
        try:
            client = aioredis.Redis.from_url(settings.redis_url)
            pubsub = client.pubsub()
            await pubsub.subscribe("user.upserted", "user.deactivated")
            log.info("replica_sync_subscribed", channels=["user.upserted", "user.deactivated"])
            backoff = 1
            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                channel = msg.get("channel")
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")
                await _handle(channel, msg.get("data") or b"")
        except asyncio.CancelledError:
            try:
                await pubsub.unsubscribe()
                await client.close()
            except Exception:  # noqa: BLE001
                pass
            log.info("replica_sync_stopped")
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("replica_sync_disconnected", err=str(exc), backoff=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
