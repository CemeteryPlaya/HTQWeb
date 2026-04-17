"""Position (должность) model."""

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Position(BaseModel):
    __tablename__ = "hr_positions"

    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("hr_departments.id"))
    grade: Mapped[int] = mapped_column(Integer, default=1)  # 1–10
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, title='{self.title}', grade={self.grade})>"
