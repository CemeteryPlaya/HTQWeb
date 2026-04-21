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
    weight: int = Field(default=100, ge=0)


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    department_id: int | None = None
    grade: int | None = Field(default=None, ge=1, le=10)
    description: str | None = None
    requirements: dict | None = None
    is_active: bool | None = None
    weight: int | None = Field(default=None, ge=0)


class PositionWeightUpdate(BaseModel):
    weight: int = Field(..., ge=0)


class PositionShort(BaseModel):
    id: int
    title: str
    grade: int
    weight: int
    level: int

    model_config = {"from_attributes": True}


class PositionOut(PositionBase):
    id: int
    level: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LevelThresholdOut(BaseModel):
    id: int
    level_number: int
    weight_from: int
    weight_to: int
    label: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LevelThresholdUpdate(BaseModel):
    weight_from: int = Field(..., ge=0)
    weight_to: int = Field(..., ge=0)
    label: str | None = Field(default=None, max_length=100)
