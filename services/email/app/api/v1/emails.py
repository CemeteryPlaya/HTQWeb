"""Email API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import TokenPayload, get_current_user
from app.db import get_db_session
from app.models.email import EmailMessage, OAuthToken
from app.schemas.email import EmailMessageRead, EmailMessageDetail, EmailSendRequest
from app.services.dlp_scanner import dlp_scanner
from app.services.mta_connector import mta_connector

router = APIRouter(tags=["emails"])


@router.get("/folder/{folder}", response_model=list[EmailMessageRead])
async def list_emails(
    folder: str,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List emails in a specific folder (inbox, sent, drafts, trash)."""
    valid_folders = {"inbox", "sent", "drafts", "trash"}
    if folder not in valid_folders:
        raise HTTPException(status_code=400, detail="Invalid folder")

    stmt = (
        select(EmailMessage)
        .where(EmailMessage.user_id == user.user_id, EmailMessage.folder == folder)
        .order_by(EmailMessage.date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{message_id}", response_model=EmailMessageDetail)
async def get_email(
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """Get full email details."""
    stmt = select(EmailMessage).where(EmailMessage.id == message_id, EmailMessage.user_id == user.user_id)
    result = await session.execute(stmt)
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Optional: fetch attachments if needed (not fully joined here for simplicity)
    return msg


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
async def send_email(
    data: EmailSendRequest,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """Send an email."""
    # Validate OAuth token
    token = await session.get(OAuthToken, data.account_id)
    if not token or token.user_id != user.user_id or not token.is_active:
        raise HTTPException(status_code=400, detail="Invalid account or account not active")

    # DLP Scan
    content = (data.subject or "") + " " + (data.body_text or "") + " " + (data.body_html or "")
    if dlp_scanner.scan(content):
        # Depending on policy, reject or flag
        raise HTTPException(status_code=403, detail="DLP Policy Violation: Sensitive data detected.")

    # Create message in sent folder
    import datetime
    msg = EmailMessage(
        user_id=user.user_id,
        account_id=data.account_id,
        folder="sent",
        subject=data.subject,
        snippet=data.subject[:100],
        body_html=data.body_html,
        body_text=data.body_text,
        sender_email=token.provider_account_id,
        to_recipients=data.to_recipients,
        cc_recipients=data.cc_recipients,
        bcc_recipients=data.bcc_recipients,
        date=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)

    # In reality, this would be queued to Dramatiq. 
    # For now, we do a sync call to the async MTA stub.
    await mta_connector.send_message(msg, token)

    return {"status": "queued", "id": str(msg.id)}


@router.post("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    user: TokenPayload = Depends(get_current_user),
):
    """Mark email as read."""
    stmt = update(EmailMessage).where(
        EmailMessage.id == message_id, EmailMessage.user_id == user.user_id
    ).values(is_read=True)
    await session.execute(stmt)
    await session.commit()
