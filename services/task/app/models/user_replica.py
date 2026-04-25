"""User replica model for task service."""

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Denormalized user data — replica synced from user-service.

    Named `task_users` so it doesn't collide with `auth.users` when the
    role-level search_path falls through to auth.
    """
    __tablename__ = "task_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
