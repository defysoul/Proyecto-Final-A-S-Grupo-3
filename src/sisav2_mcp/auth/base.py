"""Interfaz de autenticación y errores tipados.

`TokenProvider` aísla *cómo* se obtiene el bearer token. v1 usa
:class:`~sisav2_mcp.auth.ropc.RopcTokenProvider` (ROPC + keychain). La ruta de
upgrade a PKCE-loopback queda como stub (ver :mod:`sisav2_mcp.auth.pkce`).
"""

from __future__ import annotations

import abc
from typing import Protocol

ONBOARDING_MESSAGE = (
    "No hay credenciales SISAV2 guardadas en el keychain. Ejecuta el onboarding "
    "para guardarlas una vez (usuario + clave UTEM); ver el README. La clave se "
    "almacena cifrada en el gestor de credenciales del SO, nunca en texto plano."
)


class AuthError(Exception):
    """Error genérico de autenticación."""


class InvalidCredentials(AuthError):
    """El IdP rechazó la credencial (grant inválido / 401)."""


class CredentialsNotFound(AuthError):
    """No hay credencial en el keychain: se requiere onboarding."""

    def __init__(self, message: str = ONBOARDING_MESSAGE) -> None:
        super().__init__(message)


class TokenProvider(abc.ABC):
    """Provee un access token válido, refrescando/re-autenticando en silencio."""

    @abc.abstractmethod
    async def get_access_token(self) -> str:
        """Devuelve un bearer token vigente (puede disparar login/refresh)."""
        raise NotImplementedError


class CredentialStore(Protocol):
    """Almacén de credenciales (usuario + clave). Implementado sobre keyring."""

    def load(self) -> tuple[str, str] | None:
        """Devuelve (usuario, clave) o ``None`` si no hay credencial guardada."""
        ...

    def save(self, username: str, password: str) -> None:
        """Persiste la credencial (cifrada en el keychain del SO)."""
        ...

    def clear(self) -> None:
        """Elimina la credencial guardada."""
        ...
