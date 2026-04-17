"""Applications (отклики кандидатов) API router."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.auth.dependencies import get_current_user, TokenPayload
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationOut, ApplicationStatusChange
from app.schemas.common import PaginatedResponse
from app.services.recruitment_service import RecruitmentService

router = APIRouter(prefix="/applications", tags=["applications"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> RecruitmentService:
    return RecruitmentService(db)


@router.get("/", response_model=PaginatedResponse[ApplicationOut])
async def list_applications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    items, total = await svc.list_applications(page=page, limit=limit)
    pages = (total + limit - 1) // limit
    return PaginatedResponse(items=items, total=total, page=page, pages=pages, limit=limit)


@router.post("/", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreate,
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.create_application(body)


@router.get("/{id}/", response_model=ApplicationOut)
async def get_application(
    id: int,
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.get_application(id)


@router.put("/{id}/", response_model=ApplicationOut)
async def update_application(
    id: int,
    body: ApplicationUpdate,
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.update_application(id, body)


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    id: int,
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    await svc.delete_application(id)


@router.post("/{id}/status", response_model=ApplicationOut)
async def change_application_status(
    id: int,
    body: ApplicationStatusChange,
    svc: RecruitmentService = Depends(_svc),
    _: TokenPayload = Depends(get_current_user),
):
    return await svc.change_status(id, body)
