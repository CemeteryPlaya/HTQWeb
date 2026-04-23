"""Email models."""

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntIdMixin, TimestampMixin


class OAuthToken(Base, IntIdMixin, TimestampMixin):
    """Encrypted OAuth 2.0 tokens for external providers."""
    __tablename__ = "oauth_tokens"

    user_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False) # google, microsoft
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Encrypted via AES-256-GCM in application layer
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmailMessage(Base, TimestampMixin):
    """Core email message."""
    __tablename__ = "email_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("oauth_tokens.id", ondelete="SET NULL"), nullable=True)
    
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True) # External MTA message-id
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    folder: Mapped[str] = mapped_column(String(50), nullable=False, default="inbox") # inbox, sent, drafts, trash
    
    subject: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body_html: Mapped[Text] = mapped_column(Text, nullable=True)
    body_text: Mapped[Text] = mapped_column(Text, nullable=True)
    
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    to_recipients: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list) # [{"email": "...", "name": "..."}]
    cc_recipients: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    bcc_recipients: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    dlp_flagged: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailAttachment(Base, TimestampMixin):
    """Attachments for emails."""
    __tablename__ = "email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("email_messages.id", ondelete="CASCADE"), index=True)
    
    file_metadata_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # Ref to media-service
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # For inline images


class RecipientStatus(Base, TimestampMixin):
    """Delivery tracking per recipient."""
    __tablename__ = "recipient_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("email_messages.id", ondelete="CASCADE"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, delivered, bounced
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
