"""Position schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class PositionBase(BaseModel):
    title: str = Field(..., max_length=255)
    department_id: int
    grade: int = Field(default=1, ge=1, le=10)
    description: str | None = None
    requirements: dict | None = None
    is_active: bool = True


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    department_id: int | None = None
    grade: int | None = Field(default=None, ge=1, le=10)
    description: str | None = None
    requirements: dict | None = None
    is_active: bool | None = None


class PositionShort(BaseModel):
    id: int
    title: str
    grade: int

    model_config = {"from_attributes": True}


class PositionOut(PositionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
