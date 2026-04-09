"""
S3-compatible storage backends (MinIO / AWS S3).

Follows the Adapter Pattern: wraps ``django-storages`` S3Boto3Storage
behind project-specific classes. All FileField / ImageField across
the project use these backends transparently via Django's STORAGES
setting — no model changes required.

When the ``STORAGE_BACKEND`` env var is not set to ``"s3"``, Django
falls back to local ``FileSystemStorage`` (see settings.py).
"""

import logging

from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class PublicMediaStorage(S3Boto3Storage):
    """
    Storage for publicly accessible media: avatars, news images.

    Files are uploaded with ``public-read`` ACL so Nginx / CDN can
    serve them directly without signed URLs.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False


class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage for private / sensitive files: HR documents, resumes,
    email attachments, task attachments.

    Files require signed URLs (``querystring_auth=True``) for access.
    """
    location = 'private'
    default_acl = 'private'
    file_overwrite = False
    querystring_auth = True
