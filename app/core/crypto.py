"""AES-256-GCM helpers for conversation content at rest.

The encryption key is read from ``CONVERSATION_ENCRYPTION_KEY`` and must be a
base64-encoded 32-byte value (44 characters). Ciphertexts are stored as
``enc:v1:<base64(nonce || ciphertext || tag)>``. The leading prefix lets the
codebase tell encrypted strings apart from legacy plaintext, which keeps
reads working while the one-shot migration is in progress.

The same wire format is consumed by the AdminLLM console (Node).
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_PREFIX = "enc:v1:"
_NONCE_BYTES = 12
_KEY_BYTES = 32


class CryptoConfigError(RuntimeError):
    """Raised when the encryption key is missing or malformed."""


def _raw_key() -> str:
    """Read the key from Settings (which loads .env) with an env var fallback."""
    from app.core.config import get_settings

    raw = (get_settings().conversation_encryption_key or "").strip()
    if not raw:
        raw = os.environ.get("CONVERSATION_ENCRYPTION_KEY", "").strip()
    return raw


@lru_cache(maxsize=1)
def _get_key() -> bytes:
    raw = _raw_key()
    if not raw:
        raise CryptoConfigError(
            "CONVERSATION_ENCRYPTION_KEY is not set. Generate a 32-byte key "
            "with: python -c 'import os,base64;print(base64.b64encode(os.urandom(32)).decode())'"
        )
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise CryptoConfigError(
            f"CONVERSATION_ENCRYPTION_KEY is not valid base64: {exc}"
        ) from exc
    if len(key) != _KEY_BYTES:
        raise CryptoConfigError(
            f"CONVERSATION_ENCRYPTION_KEY must decode to {_KEY_BYTES} bytes, got {len(key)}"
        )
    return key


def is_encrypted(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt_text(plaintext: str) -> str:
    """Encrypt ``plaintext`` and return the ``enc:v1:...`` wire format.

    Idempotent: a value already in the ``enc:v1:`` form is returned unchanged.
    """
    if is_encrypted(plaintext):
        return plaintext
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)
    key = _get_key()
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return _PREFIX + base64.b64encode(nonce + ct).decode("ascii")


def decrypt_text(value: str) -> str:
    """Decrypt ``value`` if it carries the ``enc:v1:`` prefix; otherwise return as-is.

    Legacy plaintext records are returned untouched so reads keep working
    until the one-shot migration has been run.
    """
    if not is_encrypted(value):
        return value
    blob = base64.b64decode(value[len(_PREFIX):])
    if len(blob) <= _NONCE_BYTES:
        raise ValueError("Ciphertext too short")
    nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(_get_key()).decrypt(nonce, ct, None).decode("utf-8")


def ensure_key_loaded() -> None:
    """Eagerly validate the key at startup so misconfigurations fail fast."""
    _get_key()
