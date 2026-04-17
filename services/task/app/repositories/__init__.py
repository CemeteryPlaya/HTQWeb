"""Repositories for task-related models."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import TaskComment
from app.models.attachment import TaskAttachment
from app.models.link import TaskLink
from app.models.activity import TaskActivity
from app.models.label import Label
from app.models.version import ProjectVersion
from app.models.notification import Notification
from app.repositories.base_repo import BaseRepository


class CommentRepository(BaseRepository[TaskComment]):
    """Repository for TaskComment."""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskComment, session)


class AttachmentRepository(BaseRepository[TaskAttachment]):
    """Repository for TaskAttachment."""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskAttachment, session)


class LinkRepository(BaseRepository[TaskLink]):
    """Repository for TaskLink."""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskLink, session)


class ActivityRepository(BaseRepository[TaskActivity]):
    """Repository for TaskActivity."""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskActivity, session)


class LabelRepository(BaseRepository[Label]):
    """Repository for Label."""

    def __init__(self, session: AsyncSession):
        super().__init__(Label, session)


class VersionRepository(BaseRepository[ProjectVersion]):
    """Repository for ProjectVersion."""

    def __init__(self, session: AsyncSession):
        super().__init__(ProjectVersion, session)


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification."""

    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)
