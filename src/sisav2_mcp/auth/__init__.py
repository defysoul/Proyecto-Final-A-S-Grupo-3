"""Autenticación (Paso 4): TokenProvider + ROPC + keychain."""

from __future__ import annotations

from ..config import Settings
from .base import (
    AuthError,
    CredentialsNotFound,
    CredentialStore,
    InvalidCredentials,
    TokenProvider,
)
from .keyring_store import KeyringCredentialStore
from .pkce import PkceTokenProvider
from .ropc import RopcTokenProvider


def store_credentials(settings: Settings, username: str, password: str) -> None:
    """Onboarding: guarda la credencial UTEM en el keychain (una sola vez)."""
    KeyringCredentialStore(settings.keyring_service).save(username, password)


__all__ = [
    "TokenProvider",
    "CredentialStore",
    "AuthError",
    "InvalidCredentials",
    "CredentialsNotFound",
    "KeyringCredentialStore",
    "RopcTokenProvider",
    "PkceTokenProvider",
    "store_credentials",
]
