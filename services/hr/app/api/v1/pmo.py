"""PMO API — CRUD + members + org-chart."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, require_hr_write, TokenPayload
from app.services.pmo_service import PMOService

router = APIRouter(prefix="/pmo", tags=["pmo"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> PMOService:
    return PMOService(db)


# ── Schemas ────────────────────────────────────────────────────────────

class PMOCreate(BaseModel):
    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=50)
    description: str | None = None
    head_employee_id: int | None = None
    status: Literal["active", "suspended", "closed"] = "active"


class PMOUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    head_employee_id: int | None = None
    status: Literal["active", "suspended", "closed"] | None = None


class PMOOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    head_employee_id: int | None
    status: str

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    employee_id: int
    membership_type: Literal["permanent", "assigned", "consulting"] = "permanent"
    position_in_pmo: str | None = Field(default=None, max_length=200)
    from_date: date | None = None
    to_date: date | None = None


# ── CRUD ──────────────────────────────────────────────────────────────

@router.get("/", response_model=list[PMOOut])
async def list_pmos(
    status_filter: str | None = Query(default=None, alias="status"),
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.list_pmos(status_filter=status_filter)


@router.post("/", response_model=PMOOut, status_code=status.HTTP_201_CREATED)
async def create_pmo(
    body: PMOCreate,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    return await svc.create_pmo(body.model_dump())


@router.get("/{id}", response_model=PMOOut)
async def get_pmo(
    id: int,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.get_pmo(id)


@router.patch("/{id}", response_model=PMOOut)
async def update_pmo(
    id: int,
    body: PMOUpdate,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    return await svc.update_pmo(id, body.model_dump(exclude_none=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pmo(
    id: int,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    await svc.delete_pmo(id)


# ── Members ────────────────────────────────────────────────────────────

@router.get("/{id}/members")
async def list_pmo_members(
    id: int,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.list_members(id)


@router.post("/{id}/members", status_code=status.HTTP_201_CREATED)
async def add_pmo_member(
    id: int,
    body: MemberAdd,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    return await svc.add_member(id, body.model_dump())


@router.delete("/{id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_pmo_member(
    id: int,
    member_id: int,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(require_hr_write),
):
    await svc.remove_member(id, member_id)


# ── Org-chart ──────────────────────────────────────────────────────────

@router.get("/{id}/org-chart")
async def pmo_org_chart(
    id: int,
    svc: PMOService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.get_pmo_org_chart(id)
