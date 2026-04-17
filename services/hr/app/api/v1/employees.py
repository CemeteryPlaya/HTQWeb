"""Employees API router."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, TokenPayload
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut, EmployeeTransfer
from app.schemas.common import PaginatedResponse
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])
logger = structlog.get_logger()


def _svc(db: AsyncSession = Depends(get_db_session)) -> EmployeeService:
    return EmployeeService(db)


@router.get("/", response_model=PaginatedResponse[EmployeeOut])
async def list_employees(
    department_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    svc: EmployeeService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    items, total = await svc.list_employees(
        department_id=department_id, status=status, page=page, limit=limit
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(items=items, total=total, page=page, pages=pages, limit=limit)


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreate,
    svc: EmployeeService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    return await svc.create_employee(body, changed_by_id=current_user.user_id)


@router.get("/{id}/", response_model=EmployeeOut)
async def get_employee(
    id: int,
    svc: EmployeeService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.get_employee(id)


@router.put("/{id}/", response_model=EmployeeOut)
async def update_employee(
    id: int,
    body: EmployeeUpdate,
    svc: EmployeeService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    return await svc.update_employee(id, body, changed_by_id=current_user.user_id)


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    id: int,
    svc: EmployeeService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    await svc.delete_employee(id, changed_by_id=current_user.user_id)


@router.post("/{id}/transfer", response_model=EmployeeOut)
async def transfer_employee(
    id: int,
    body: EmployeeTransfer,
    svc: EmployeeService = Depends(_svc),
    current_user: TokenPayload = Depends(get_current_user),
):
    return await svc.transfer_employee(id, body, changed_by_id=current_user.user_id)


@router.get("/{id}/history")
async def employee_history(
    id: int,
    db: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == "employee", AuditLog.entity_id == id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "changed_by": log.changed_by,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/{id}/documents")
async def employee_documents(
    id: int,
    db: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.document import Document

    result = await db.execute(
        select(Document).where(Document.employee_id == id).order_by(Document.created_at.desc())
    )
    return result.scalars().all()
