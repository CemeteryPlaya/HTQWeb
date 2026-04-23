"""CMS database models.

Exports a shared ``Base`` so the admin-aggregator service (Phase 3.X) can
import the metadata by package path ``cms.app.models``.
"""

from app.models.audit_log import AuditLog
from app.models.base import Base, IntIdMixin, TimestampMixin
from app.models.contact_request import ContactRequest
from app.models.news import News


__all__ = [
    "Base",
    "AuditLog",
    "ContactRequest",
    "News",
    "TimestampMixin",
    "IntIdMixin",
]
