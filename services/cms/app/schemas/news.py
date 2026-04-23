"""Pydantic schemas for News."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsBase(BaseModel):
    title: str = Field(..., max_length=300)
    slug: str = Field(..., max_length=320)
    summary: str = ""
    content: str = ""
    image: Optional[str] = Field(None, max_length=500)
    category: str = Field("", max_length=100)
    published: bool = False
    published_at: Optional[datetime] = None


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    slug: Optional[str] = Field(None, max_length=320)
    summary: Optional[str] = None
    content: Optional[str] = None
    image: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    published: Optional[bool] = None
    published_at: Optional[datetime] = None


class NewsRead(NewsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class NewsTranslateRequest(BaseModel):
    target: str = Field("en", min_length=2, max_length=10)


class NewsTranslateResponse(BaseModel):
    task_id: str
    news_id: int
    target: str
    status: str = "queued"
