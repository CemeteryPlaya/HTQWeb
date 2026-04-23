"""Pydantic schemas for file metadata."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class FileMetadataUpdate(BaseModel):
    is_public: Optional[bool] = None
    original_filename: Optional[str] = None
