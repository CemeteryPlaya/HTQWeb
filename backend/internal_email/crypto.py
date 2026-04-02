"""
AES-256-GCM encryption/decryption for OAuth tokens.

Wire format:  nonce (12 bytes) || ciphertext || tag (16 bytes)
Key:          32-byte key derived from base64-encoded OAUTH_ENCRYPTION_KEY env var.
"""

import base64
import os
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Key management
# ---------------------------------------------------------------------------

_cached_key: bytes | None = None


def _get_encryption_key() -> bytes:
    """
    Decode the base64-encoded 32-byte AES key from settings.
    Raises ValueError on misconfiguration so the app fails loudly at startup.
    """
    global _cached_key
    if _cached_key is not None:
        return _cached_key

    raw = getattr(settings, 'OAUTH_ENCRYPTION_KEY', '')
    if not raw:
        raise ValueError(
            'OAUTH_ENCRYPTION_KEY is not set. '
            'Generate one with: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"'
        )

    key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError(
            f'OAUTH_ENCRYPTION_KEY must decode to exactly 32 bytes (got {len(key)}). '
            'Use: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"'
        )

    _cached_key = key
    return _cached_key


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def encrypt(plaintext: str) -> bytes:
    """
    Encrypt a plaintext string with AES-256-GCM.

    Returns bytes: nonce (12) || ciphertext+tag
    Each call generates a fresh random nonce to avoid nonce-reuse vulnerabilities.
    """
    if not plaintext:
        raise ValueError('Cannot encrypt empty plaintext')

    key = _get_encryption_key()
    aesgcm = AESGCM(key)

    # 96-bit (12-byte) random nonce — recommended size for AES-GCM
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

    # Prepend nonce so we can extract it during decryption
    return nonce + ciphertext


def decrypt(blob: bytes) -> str:
    """
    Decrypt a blob produced by encrypt().

    Splits nonce (first 12 bytes) from the ciphertext+tag remainder.
    Raises cryptography.exceptions.InvalidTag on tampered data.
    """
    if not blob or len(blob) < 13:  # 12 nonce + at least 1 byte
        raise ValueError('Invalid encrypted blob: too short')

    key = _get_encryption_key()
    aesgcm = AESGCM(key)

    nonce = blob[:12]
    ciphertext = blob[12:]

    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext_bytes.decode('utf-8')
