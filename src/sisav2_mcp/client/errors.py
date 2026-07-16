"""Errores tipados del cliente HTTP.

`AuthError` se reexporta desde la capa de auth: un 401 de la API significa que el
token ya no sirve → el llamador debe re-loguear (el TokenProvider lo hace).
"""

from __future__ import annotations

from ..auth.base import AuthError

__all__ = [
    "AuthError",
    "ClientError",
    "NotFound",
    "RateLimited",
    "ServerError",
    "NetworkTimeout",
    "ReadOnlyViolation",
]


class ClientError(Exception):
    """Error genérico del cliente HTTP (4xx no mapeados, payload inválido, etc.)."""


class NotFound(ClientError):
    """Recurso inexistente (HTTP 404)."""


class RateLimited(ClientError):
    """Demasiadas solicitudes (HTTP 429). Reintentar con backoff."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(ClientError):
    """Error del servidor (HTTP 5xx)."""


class NetworkTimeout(ClientError):
    """Timeout de red/lectura al contactar la API."""


class ReadOnlyViolation(ClientError):
    """Se intentó un método/path de escritura fuera de la allowlist read-only."""
