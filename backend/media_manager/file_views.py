"""
Secure, chunked file download view with HTTP Range request support.

Endpoint: GET /api/media/download/<path:filepath>/

- Requires authentication (JWT)
- Supports HTTP 206 Partial Content (Range requests) — enables video seeking, resumable downloads
- Streams file in 8 KB chunks — never loads entire file into memory
- Sets Content-Disposition: attachment for browser download prompt
- Returns 404 if file is outside MEDIA_ROOT (path traversal protection)
"""

import mimetypes
import hashlib
import logging
from pathlib import Path
from typing import Optional, Generator

from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8 * 1024  # 8 KB


def _safe_media_path(filepath: str) -> Optional[Path]:
    """Resolve filepath relative to MEDIA_ROOT; return None on path traversal."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    target = (media_root / filepath).resolve()
    if not str(target).startswith(str(media_root)):
        return None
    return target


def _file_etag(path: Path) -> str:
    """Generate ETag from file size + mtime (fast, no full-file hash)."""
    stat = path.stat()
    raw = f"{stat.st_size}-{stat.st_mtime}"
    return hashlib.md5(raw.encode()).hexdigest()


def _range_iterator(file_path: Path, byte_start: int, byte_length: int) -> Generator[bytes, None, None]:
    """Yield chunks of a file starting at byte_start for byte_length bytes."""
    with open(str(file_path), "rb") as f:
        f.seek(byte_start)
        remaining = byte_length
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def secure_media_download(request, filepath: str):
    """
    Stream a media file to an authenticated user.

    Supports:
      - Full download (HTTP 200)
      - Partial content via Range header (HTTP 206) — for video/audio seeking and resumable downloads
    """
    path = _safe_media_path(filepath)
    if path is None or not path.is_file():
        return HttpResponse(status=404)

    file_size: int = path.stat().st_size
    content_type, _ = mimetypes.guess_type(str(path))
    content_type = content_type or "application/octet-stream"
    etag: str = _file_etag(path)

    # ── ETag / conditional GET ────────────────────────────────────────────────
    if request.headers.get("If-None-Match") == f'"{etag}"':
        return HttpResponse(status=304)

    # ── Range request (partial content) ──────────────────────────────────────
    range_header: str = request.headers.get("Range", "")
    if range_header.startswith("bytes="):
        try:
            range_spec = range_header[6:]  # strip "bytes="
            start_str, _, end_str = range_spec.partition("-")
            start: int = int(start_str) if start_str else 0
            end: int = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)

            if start > end or start >= file_size:
                err_response = HttpResponse(status=416)
                err_response["Content-Range"] = f"bytes */{file_size}"
                return err_response

            length: int = end - start + 1

            response = StreamingHttpResponse(
                _range_iterator(path, start, length),
                status=206,
                content_type=content_type,
            )
            response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            response["Content-Length"] = str(length)
            response["Accept-Ranges"] = "bytes"
            response["ETag"] = f'"{etag}"'
            return response

        except (ValueError, IndexError):
            pass  # fall through to full response

    # ── Full file (HTTP 200) ──────────────────────────────────────────────────
    filename: str = path.name
    full_response = FileResponse(
        open(str(path), "rb"),  # FileResponse will close the file handle
        content_type=content_type,
        as_attachment=True,
        filename=filename,
    )
    full_response["Content-Length"] = str(file_size)
    full_response["Accept-Ranges"] = "bytes"
    full_response["ETag"] = f'"{etag}"'
    logger.info(
        "[secure_media_download] user=%s file=%s size=%d",
        request.user.username,
        filepath,
        file_size,
    )
    return full_response
