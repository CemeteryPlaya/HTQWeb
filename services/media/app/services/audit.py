"""Audit service — records actions to the audit_log table."""

from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_action(
    session: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """Records an audit trail event.

    Extracts IP address and user-agent from the FastAPI request if provided.
    Extracts correlation ID from request state if the RequestIDMiddleware is used.
    """
    ip_address = None
    user_agent = None
    correlation_id = None

    if request:
        ip_address = request.client.host if request.client else None
        # Support running behind a proxy (e.g. Nginx or gateway)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()

        user_agent = request.headers.get("user-agent")

        # Assume request ID is injected into state by middleware
        correlation_id = getattr(request.state, "request_id", None)

    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )

    session.add(audit_entry)
    # Don't commit here — rely on the caller's session commit so that the
    # action and the audit log are saved transactionally.
