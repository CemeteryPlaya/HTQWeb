"""Storage abstraction layer.

Supports two backends:
- ``local``: file system via ``aiofiles`` (dev / early-prod)
- ``s3``: Amazon S3 via ``aioboto3`` (production)

Switch via ``STORAGE_BACKEND`` env var.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiofiles
import aiofiles.os

from app.core.settings import settings


@runtime_checkable
class Storage(Protocol):
    """Abstract storage protocol."""

    async def save(self, path: str, data: bytes) -> None: ...
    async def open(self, path: str, byte_range: tuple[int, int] | None = None) -> bytes: ...
    async def delete(self, path: str) -> None: ...
    async def exists(self, path: str) -> bool: ...
    async def size(self, path: str) -> int: ...


class LocalStorage:
    """File-system storage backed by aiofiles."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve path relative to base_dir with traversal protection."""
        resolved = (self.base_dir / path).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    async def save(self, path: str, data: bytes) -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target, "wb") as f:
            await f.write(data)

    async def open(self, path: str, byte_range: tuple[int, int] | None = None) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if byte_range is not None:
            start, end = byte_range
            length = end - start + 1
            async with aiofiles.open(target, "rb") as f:
                await f.seek(start)
                return await f.read(length)

        async with aiofiles.open(target, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        target = self._resolve(path)
        if target.exists():
            await aiofiles.os.remove(target)

    async def exists(self, path: str) -> bool:
        target = self._resolve(path)
        return target.exists()

    async def size(self, path: str) -> int:
        target = self._resolve(path)
        stat = await aiofiles.os.stat(target)
        return stat.st_size


class S3Storage:
    """S3-compatible object storage via aioboto3.

    Configured via environment variables:
    S3_BUCKET, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION
    """

    def __init__(
        self,
        bucket: str,
        endpoint: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "us-east-1",
    ) -> None:
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

    def _get_session(self):
        import aioboto3

        session = aioboto3.Session()
        kwargs = {
            "service_name": "s3",
            "region_name": self.region,
        }
        if self.endpoint:
            kwargs["endpoint_url"] = self.endpoint
        if self.access_key:
            kwargs["aws_access_key_id"] = self.access_key
            kwargs["aws_secret_access_key"] = self.secret_key
        return session, kwargs

    async def save(self, path: str, data: bytes) -> None:
        session, kwargs = self._get_session()
        async with session.client(**kwargs) as s3:
            await s3.put_object(Bucket=self.bucket, Key=path, Body=data)

    async def open(self, path: str, byte_range: tuple[int, int] | None = None) -> bytes:
        session, kwargs = self._get_session()
        async with session.client(**kwargs) as s3:
            get_kwargs = {"Bucket": self.bucket, "Key": path}
            if byte_range:
                get_kwargs["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
            response = await s3.get_object(**get_kwargs)
            return await response["Body"].read()

    async def delete(self, path: str) -> None:
        session, kwargs = self._get_session()
        async with session.client(**kwargs) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=path)

    async def exists(self, path: str) -> bool:
        session, kwargs = self._get_session()
        async with session.client(**kwargs) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=path)
                return True
            except Exception:
                return False

    async def size(self, path: str) -> int:
        session, kwargs = self._get_session()
        async with session.client(**kwargs) as s3:
            response = await s3.head_object(Bucket=self.bucket, Key=path)
            return response["ContentLength"]


def get_storage() -> Storage:
    """Factory — returns the configured storage backend."""
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
    return LocalStorage(base_dir=settings.media_root_path)
