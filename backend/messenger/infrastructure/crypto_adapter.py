"""
Server-side cryptographic adapter.

The server is a BLIND RELAY for E2EE — it never decrypts message content.
This module provides only utility functions for:

1. Validating uploaded X25519 public key sizes
2. Verifying that msg_key length is correct
3. Generating random bytes for server-side needs (e.g., room IDs)

All actual encryption/decryption happens CLIENT-SIDE via Web Crypto API.
"""

import hashlib
import os

from messenger.domain.constants import (
    MSG_KEY_SIZE,
    X25519_PUBLIC_KEY_SIZE,
    AUTH_KEY_SIZE,
)


def validate_public_key(key_bytes: bytes) -> bool:
    """Validate that the public key has correct X25519 size (32 bytes)."""
    return isinstance(key_bytes, bytes) and len(key_bytes) == X25519_PUBLIC_KEY_SIZE


def validate_msg_key(msg_key: bytes) -> bool:
    """Validate that msg_key has correct size (16 bytes / 128 bits)."""
    return isinstance(msg_key, bytes) and len(msg_key) == MSG_KEY_SIZE


def generate_random_bytes(size: int = 32) -> bytes:
    """Generate cryptographically secure random bytes using OS entropy."""
    return os.urandom(size)


def compute_sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash. Uses hashlib (OpenSSL-backed), not custom crypto."""
    return hashlib.sha256(data).digest()


def validate_key_bundle(
    identity_pub_key: bytes,
    signed_prekey: bytes,
    prekey_signature: bytes,
) -> tuple[bool, str]:
    """
    Validate an uploaded key bundle.

    Returns (is_valid, error_message).
    """
    if not validate_public_key(identity_pub_key):
        return False, f'identity_pub_key must be {X25519_PUBLIC_KEY_SIZE} bytes'

    if not validate_public_key(signed_prekey):
        return False, f'signed_prekey must be {X25519_PUBLIC_KEY_SIZE} bytes'

    if not isinstance(prekey_signature, bytes) or len(prekey_signature) > 64:
        return False, 'prekey_signature must be <= 64 bytes'

    return True, ''
