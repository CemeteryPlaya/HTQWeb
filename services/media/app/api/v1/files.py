"""Files API endpoints."""

import mimetypes
import uuid
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user, get_optional_user, require_admin
from app.core.logging import get_logger
from app.core.settings import settings
from app.db import get_db_session
from app.models.file_metadata import FileMetadata
from app.schemas.file import FileMetadataRead, FileMetadataUpdate
from app.services.audit import record_action
from app.storage import get_storage

router = APIRouter(tags=["files"])
log = get_logger(__name__)


@router.post("/", response_model=FileMetadataRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    is_public: bool = False,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
) -> FileMetadata:
    """Upload a new file."""
    # Check mime type restrictions
    if settings.allowed_mime_types:
        allowed = [m.strip() for m in settings.allowed_mime_types.split(",")]
        if file.content_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type. Allowed: {settings.allowed_mime_types}",
            )

    # Read data and check size
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB",
        )

    # Generate unique path
    file_uuid = uuid.uuid4()
    ext = mimetypes.guess_extension(file.content_type or "") or ""
    # Store in YYYY/MM/DD structure or similar? For now, flat or simple structure.
    import datetime
    now = datetime.datetime.now()
    path = f"{now.year}/{now.month:02d}/{file_uuid}{ext}"

    storage = get_storage()
    await storage.save(path, data)

    # owner_id: when called by a regular user, use their JWT.user_id.
    # When called by another service (S2S JWT), read X-User-Id header
    # which the caller forwards so file ownership still resolves.
    owner_id = user.user_id
    if owner_id is None and user.is_service:
        raw = request.headers.get("x-user-id")
        if raw:
            try:
                owner_id = int(raw)
            except ValueError:
                owner_id = None

    meta = FileMetadata(
        id=file_uuid,
        path=path,
        original_filename=file.filename or "",
        owner_id=owner_id,
        size=len(data),
        mime=file.content_type or "application/octet-stream",
        storage_backend=settings.storage_backend,
        is_public=is_public,
    )
    session.add(meta)
    await session.flush()

    await record_action(
        session,
        user_id=owner_id,
        action="file_uploaded",
        resource_type="FileMetadata",
        resource_id=str(meta.id),
        changes={
            "path": path,
            "size": meta.size,
            "mime": meta.mime,
            "via_service": user.is_service,
        },
        request=request,
    )
    log.info(
        "file_uploaded",
        file_id=str(meta.id),
        size=meta.size,
        owner_id=owner_id,
        via_service=user.is_service,
    )

    # Optional: enqueue thumbnail generation if it's an image
    if meta.mime.startswith("image/"):
        from app.workers.actors import generate_thumbnail
        generate_thumbnail.send(str(meta.id))

    return meta


@router.get("/{file_id}")
async def download_file(
    request: Request,
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user: Optional[TokenPayload] = Depends(get_optional_user),
) -> Response:
    """Download a file with Range support (206 Partial Content)."""
    meta = await session.get(FileMetadata, file_id)
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Authorization
    if not meta.is_public:
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # Assuming only owner or admin can download private files for now
        # Expand based on business rules
        if user.user_id != meta.owner_id and not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    storage = get_storage()
    if not await storage.exists(meta.path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File physically missing")

    total_size = meta.size
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": meta.mime,
        "Content-Disposition": f'inline; filename="{meta.original_filename}"',
        "ETag": f'"{meta.id}-{meta.updated_at.timestamp()}"',
    }

    # Handle Range requests
    range_header = request.headers.get("Range")
    if range_header:
        # Example range format: bytes=0-1023 or bytes=1024-
        try:
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else total_size - 1
            if start >= total_size or end >= total_size or start > end:
                headers["Content-Range"] = f"bytes */{total_size}"
                return Response(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, headers=headers)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Range Header")

        headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
        headers["Content-Length"] = str(end - start + 1)
        data = await storage.open(meta.path, byte_range=(start, end))
        return Response(content=data, status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)

    # Full content
    headers["Content-Length"] = str(total_size)
    data = await storage.open(meta.path)
    return Response(content=data, headers=headers)


@router.get("/", response_model=list[FileMetadataRead])
async def list_files(
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(require_admin),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[FileMetadata]:
    """List all files (Admin only)."""
    stmt = select(FileMetadata).order_by(FileMetadata.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{file_id}", response_model=FileMetadataRead)
async def update_file_metadata(
    request: Request,
    file_id: uuid.UUID,
    payload: FileMetadataUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
) -> FileMetadata:
    meta = await session.get(FileMetadata, file_id)
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if user.user_id != meta.owner_id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    changes = payload.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(meta, k, v)
    await session.flush()

    await record_action(
        session,
        user_id=user.user_id,
        action="file_metadata_updated",
        resource_type="FileMetadata",
        resource_id=str(meta.id),
        changes=changes,
        request=request,
    )
    return meta


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    request: Request,
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
) -> None:
    meta = await session.get(FileMetadata, file_id)
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if user.user_id != meta.owner_id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    storage = get_storage()
    await storage.delete(meta.path)

    path = meta.path
    await session.delete(meta)

    await record_action(
        session,
        user_id=user.user_id,
        action="file_deleted",
        resource_type="FileMetadata",
        resource_id=str(file_id),
        changes={"path": path},
        request=request,
    )
    log.info("file_deleted", file_id=str(file_id), by=user.user_id)
