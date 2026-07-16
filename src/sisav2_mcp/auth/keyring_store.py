"""Almacén de credenciales sobre `keyring` (Windows Credential Manager).

Se guardan dos entradas bajo el mismo *service*: el nombre de usuario (bajo una
clave fija) y la contraseña (bajo el nombre de usuario). Así un único service
name basta para recuperar ambos sin pedir el usuario por adelantado.
"""

from __future__ import annotations

import keyring
import keyring.errors

# Clave fija bajo la que se guarda el username dentro del service.
_USERNAME_KEY = "__sisav2_username__"


class KeyringCredentialStore:
    """Implementación de ``CredentialStore`` sobre el keychain del SO."""

    def __init__(self, service: str) -> None:
        self._service = service

    def load(self) -> tuple[str, str] | None:
        username = keyring.get_password(self._service, _USERNAME_KEY)
        if not username:
            return None
        password = keyring.get_password(self._service, username)
        if password is None:
            return None
        return (username, password)

    def save(self, username: str, password: str) -> None:
        keyring.set_password(self._service, _USERNAME_KEY, username)
        keyring.set_password(self._service, username, password)

    def clear(self) -> None:
        username = keyring.get_password(self._service, _USERNAME_KEY)
        if username:
            try:
                keyring.delete_password(self._service, username)
            except keyring.errors.PasswordDeleteError:
                pass
        try:
            keyring.delete_password(self._service, _USERNAME_KEY)
        except keyring.errors.PasswordDeleteError:
            pass
