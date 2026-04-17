"""Task API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.auth.dependencies import get_current_user
from app.services.task_service import TaskService
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskListResponse,
    TaskDetailResponse,
    TaskStats,
    Status,
)
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.attachment import AttachmentResponse
from app.repositories.task_repo import TaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskListResponse])
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Status | None = None,
    priority: str | None = None,
    task_type: str | None = None,
    assignee_id: int | None = None,
    reporter_id: int | None = None,
    department_id: int | None = None,
    version_id: int | None = None,
    parent_id: int | None = None,
    label_id: int | None = None,
    search: str | None = None,
):
    """List tasks with filtering and pagination."""
    service = TaskService(db)
    repo = TaskRepository(db)
    
    tasks = await repo.get_list(
        offset=offset,
        limit=limit,
        status=status,
        priority=priority,
        task_type=task_type,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        department_id=department_id,
        version_id=version_id,
        parent_id=parent_id,
        label_id=label_id,
        search=search,
    )
    
    # TODO: Map to response schema with denormalized fields
    return tasks


@router.get("/{task_id}/", response_model=TaskDetailResponse)
async def get_task(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Get task details with all relations."""
    service = TaskService(db)
    task = await service.task_repo.get_with_relations(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskDetailResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Create a new task."""
    service = TaskService(db)
    try:
        task = await service.create_task(data, user_id=current_user.get("id"))
        await db.commit()
        return await service.task_repo.get_with_relations(task.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{task_id}/", response_model=TaskDetailResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Update task."""
    service = TaskService(db)
    try:
        task = await service.update_task(task_id, data, user_id=current_user.get("id"))
        await db.commit()
        return await service.task_repo.get_with_relations(task.id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}/", status_code=204)
async def delete_task(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Soft delete a task."""
    service = TaskService(db)
    try:
        await service.delete_task(task_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{task_id}/transitions/")
async def get_task_transitions(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Get available status transitions for a task."""
    service = TaskService(db)
    try:
        transitions = await service.get_available_transitions(task_id)
        return [{"status": s.value} for s in transitions]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats/", response_model=TaskStats)
async def get_task_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
    department_id: int | None = None,
    version_id: int | None = None,
):
    """Get task statistics."""
    repo = TaskRepository(db)
    stats = await repo.get_stats(
        department_id=department_id,
        version_id=version_id,
    )
    return stats


@router.post("/{task_id}/comments/", response_model=CommentResponse, status_code=201)
async def add_comment(
    task_id: int,
    data: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a task."""
    from app.repositories import CommentRepository
    
    # Verify task exists
    task = await TaskRepository(db).get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    repo = CommentRepository(db)
    comment = await repo.create(
        task_id=task_id,
        author_id=current_user.get("id"),
        body=data.body,
    )
    await db.commit()
    return comment


@router.post("/{task_id}/attachments/", response_model=AttachmentResponse, status_code=201)
async def add_attachment(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: dict = Depends(get_current_user),
    file: UploadFile = File(...),
):
    """Add an attachment to a task."""
    from app.repositories import AttachmentRepository
    import os
    from pathlib import Path
    
    # Verify task exists
    task = await TaskRepository(db).get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Save file
    upload_dir = Path("uploads/task_attachments")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = file.filename or "unnamed"
    file_path = upload_dir / f"{task_id}_{filename}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    repo = AttachmentRepository(db)
    attachment = await repo.create(
        task_id=task_id,
        file_path=str(file_path),
        filename=filename,
        uploaded_by_id=current_user.get("id"),
    )
    await db.commit()
    return attachment
