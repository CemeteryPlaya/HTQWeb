"""Chat attachment upload — локальный storage в messenger-service."""
import uuid
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, get_current_user
from app.core.settings import settings
from app.db import get_db_session
from app.models.domain import ChatAttachment
from app.services.audit import record_action

router = APIRouter(tags=["attachments"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> dict:
    dst_dir = Path(settings.attachment_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    dst = dst_dir / f"{file_id}_{file.filename}"
    async with aiofiles.open(dst, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
            
    attachment = ChatAttachment(
        id=file_id,
        filename=file.filename,
        content_type=file.content_type,
        size=dst.stat().st_size,
        uploaded_by=user.user_id
    )
    session.add(attachment)
    await session.commit()
    await record_action(session, user.user_id, "upload_attachment", "ChatAttachment", str(file_id))
    return {"id": str(file_id), "url": f"/attachments/{file_id}_{file.filename}"}
