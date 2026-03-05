"""General-purpose helper functions."""

from __future__ import annotations

import hashlib


def sha256_hash(text: str) -> str:
    """Return the SHA-256 hex digest of *text*.

    Args:
        text: Input string.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
