"""Cliente HTTP (Paso 5): httpx GET-only + 1 excepción allowlisted, errores tipados."""

from __future__ import annotations

from .errors import (
    AuthError,
    ClientError,
    NetworkTimeout,
    NotFound,
    RateLimited,
    ReadOnlyViolation,
    ServerError,
)
from .http import EXPORT_PATH, WRITE_ALLOWLIST, SisavClient, ensure_read_only

__all__ = [
    "SisavClient",
    "ensure_read_only",
    "EXPORT_PATH",
    "WRITE_ALLOWLIST",
    "AuthError",
    "ClientError",
    "NotFound",
    "RateLimited",
    "ServerError",
    "NetworkTimeout",
    "ReadOnlyViolation",
]
