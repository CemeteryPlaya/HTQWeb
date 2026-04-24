"""Pydantic schemas for file metadata."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field


class FileMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    path: str
    original_filename: str
    owner_id: Optional[int]
    size: int
    mime: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> str:
        """Download URL — served by media-service (via nginx /api/media/).

        Callers (e.g., user-service storing avatarUrl) should persist this
        directly so the frontend can <img src={url} />.
        """
        return f"/api/media/v1/files/{self.id}"


class FileMetadataUpdate(BaseModel):
    is_public: Optional[bool] = None
    original_filename: Optional[str] = None
