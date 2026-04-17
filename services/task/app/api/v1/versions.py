"""Project version API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.auth.dependencies import get_current_user
from app.repositories import VersionRepository
from app.schemas.version import (
    VersionCreate,
    VersionUpdate,
    VersionResponse,
)

router = APIRouter(prefix="/versions", tags=["versions"])


@router.get("/", response_model=list[VersionResponse])
async def list_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """List all project versions."""
    repo = VersionRepository(db)
    versions = await repo.get_all()
    return versions


@router.get("/{version_id}/", response_model=VersionResponse)
async def get_version(
    version_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Get version details."""
    repo = VersionRepository(db)
    version = await repo.get_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/", response_model=VersionResponse, status_code=201)
async def create_version(
    data: VersionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Create a new project version."""
    repo = VersionRepository(db)
    version = await repo.create(**data.model_dump())
    await db.commit()
    return version


@router.patch("/{version_id}/", response_model=VersionResponse)
async def update_version(
    version_id: int,
    data: VersionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Update a project version."""
    repo = VersionRepository(db)
    version = await repo.get_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    await repo.update(version, **data.model_dump(exclude_unset=True))
    await db.commit()
    return version


@router.delete("/{version_id}/", status_code=204)
async def delete_version(
    version_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Delete a project version."""
    repo = VersionRepository(db)
    version = await repo.get_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    await repo.delete(version)
    await db.commit()


@router.get("/{version_id}/tasks/")
async def get_version_tasks(
    version_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Get all tasks for a version."""
    from app.repositories.task_repo import TaskRepository
    
    repo = TaskRepository(db)
    tasks = await repo.get_list(version_id=version_id, limit=1000)
    return tasks
