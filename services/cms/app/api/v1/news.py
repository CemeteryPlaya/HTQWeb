"""News endpoints — ``/api/cms/v1/news/*``."""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_optional_user, require_admin
from app.core.logging import get_logger
from app.db import get_db_session
from app.models.news import News
from app.schemas.news import (
    NewsCreate,
    NewsRead,
    NewsTranslateRequest,
    NewsTranslateResponse,
    NewsUpdate,
)
from app.services.audit import record_action


router = APIRouter(tags=["news"])
log = get_logger(__name__)


def _apply_published_at(news: News) -> None:
    """Keep ``published_at`` consistent with ``published`` flag."""
    if news.published and not news.published_at:
        news.published_at = datetime.now(timezone.utc)
    elif not news.published and news.published_at:
        news.published_at = None


@router.get("/", response_model=list[NewsRead])
async def list_news(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[Optional[TokenPayload], Depends(get_optional_user)],
    category: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[News]:
    stmt = select(News).order_by(News.published_at.desc().nullslast(), News.created_at.desc())

    # Anonymous + non-admin see only published items.
    if not (user and user.is_admin):
        stmt = stmt.where(News.published.is_(True))

    if category:
        stmt = stmt.where(News.category == category)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{news_id}", response_model=NewsRead)
async def get_news(
    news_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[Optional[TokenPayload], Depends(get_optional_user)],
) -> News:
    news = await session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")
    if not news.published and not (user and user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")
    return news


@router.post("/", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
async def create_news(
    payload: NewsCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin: Annotated[TokenPayload, Depends(require_admin)],
) -> News:
    news = News(**payload.model_dump())
    _apply_published_at(news)
    session.add(news)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"News with slug '{payload.slug}' already exists",
        )
    await record_action(
        session,
        user_id=admin.user_id,
        action="news_created",
        resource_type="News",
        resource_id=str(news.id),
        changes=payload.model_dump(mode="json"),
        request=request,
    )
    log.info("news_created", news_id=news.id, slug=news.slug, by=admin.user_id)
    return news


@router.patch("/{news_id}", response_model=NewsRead)
async def update_news(
    news_id: int,
    payload: NewsUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin: Annotated[TokenPayload, Depends(require_admin)],
) -> News:
    news = await session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(news, key, value)
    _apply_published_at(news)

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug conflict")

    await record_action(
        session,
        user_id=admin.user_id,
        action="news_updated",
        resource_type="News",
        resource_id=str(news.id),
        changes=changes,
        request=request,
    )
    return news


@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_id: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin: Annotated[TokenPayload, Depends(require_admin)],
) -> None:
    news = await session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")
    slug = news.slug
    await session.delete(news)
    await record_action(
        session,
        user_id=admin.user_id,
        action="news_deleted",
        resource_type="News",
        resource_id=str(news_id),
        changes={"slug": slug},
        request=request,
    )
    log.info("news_deleted", news_id=news_id, slug=slug, by=admin.user_id)


@router.post(
    "/{news_id}/translate",
    response_model=NewsTranslateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def translate_news(
    news_id: int,
    payload: NewsTranslateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin: Annotated[TokenPayload, Depends(require_admin)],
) -> NewsTranslateResponse:
    news = await session.get(News, news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News not found")

    # Enqueue the background actor. The actor is a TODO stub until a real
    # translation provider is wired up (see app/workers/actors.py:translate_news).
    from app.workers.actors import translate_news as translate_actor

    message = translate_actor.send(news.id, payload.target)
    log.info(
        "translate_news_enqueued",
        news_id=news.id,
        target=payload.target,
        task_id=message.message_id,
        by=admin.user_id,
    )
    return NewsTranslateResponse(
        task_id=message.message_id,
        news_id=news.id,
        target=payload.target,
    )
