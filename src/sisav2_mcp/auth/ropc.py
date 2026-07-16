"""Proveedor de tokens ROPC (Resource Owner Password Credentials).

Probe de Fase 0: el cliente público ``SISAV2`` rechaza redirects loopback, así
que PKCE-loopback queda descartado en v1 y se usa el grant ``password`` directo
contra el ``token_endpoint`` de Keycloak. La clave del usuario vive solo en el
keychain del SO; el proceso la ve únicamente al pedir token.

Ciclo de vida del token:
- access token válido en caché  → se devuelve.
- expirado pero refresh vigente → ``refresh_token`` grant (silencioso).
- refresh inválido / ausente    → re-login ROPC con la credencial del keychain.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from ..config import Settings
from ..models import Usuario
from .base import (
    AuthError,
    CredentialsNotFound,
    CredentialStore,
    InvalidCredentials,
    TokenProvider,
)

# Margen para refrescar antes del vencimiento real (segundos).
_EXPIRY_MARGIN_SECONDS = 30.0


@dataclass
class _TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: float
    refresh_expires_at: float | None


class RopcTokenProvider(TokenProvider):
    """Obtiene y mantiene el bearer token vía ROPC + keychain."""

    def __init__(
        self,
        settings: Settings,
        store: CredentialStore,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._store = store
        self._clock = clock
        self._tokens: _TokenSet | None = None
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        async with self._lock:
            if self._access_valid():
                assert self._tokens is not None
                return self._tokens.access_token
            if self._refresh_valid():
                try:
                    await self._refresh()
                except AuthError:
                    # refresh inválido → re-auth silenciosa con keychain
                    await self._login()
            else:
                await self._login()
            assert self._tokens is not None
            return self._tokens.access_token

    async def verifica_token(self) -> Usuario:
        """Resuelve identidad + permisos (RBAC) vía ``GET /usuarios/verifica-token``.

        Los roles de aplicación NO viajan en el JWT; se obtienen aquí.
        """
        token = await self.get_access_token()
        url = f"{self._settings.api_base_url}/usuarios/verifica-token"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url, headers={"Authorization": f"Bearer {token}"}
                )
        except httpx.HTTPError as exc:
            raise AuthError(f"Error de red en verifica-token: {exc}") from exc
        if resp.status_code == 401:
            raise InvalidCredentials("verifica-token devolvió 401 (token inválido).")
        if resp.status_code >= 400:
            raise AuthError(f"verifica-token respondió {resp.status_code}.")
        return Usuario.model_validate(resp.json())

    # --- internos ----------------------------------------------------------

    def _access_valid(self) -> bool:
        if self._tokens is None:
            return False
        return self._clock() < self._tokens.expires_at - _EXPIRY_MARGIN_SECONDS

    def _refresh_valid(self) -> bool:
        if self._tokens is None or self._tokens.refresh_token is None:
            return False
        if self._tokens.refresh_expires_at is None:
            return True
        return self._clock() < self._tokens.refresh_expires_at - _EXPIRY_MARGIN_SECONDS

    async def _login(self) -> None:
        creds = self._store.load()
        if creds is None:
            raise CredentialsNotFound()
        username, password = creds
        self._tokens = await self._token_request(
            {
                "grant_type": "password",
                "client_id": self._settings.client_id,
                "username": username,
                "password": password,
                "scope": "openid",
            }
        )

    async def _refresh(self) -> None:
        assert self._tokens is not None and self._tokens.refresh_token is not None
        self._tokens = await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self._settings.client_id,
                "refresh_token": self._tokens.refresh_token,
            }
        )

    async def _token_request(self, data: dict[str, str]) -> _TokenSet:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self._settings.token_endpoint, data=data)
        except httpx.HTTPError as exc:
            raise AuthError(
                f"Error de red al contactar el token endpoint: {exc}"
            ) from exc
        if resp.status_code in (400, 401):
            raise InvalidCredentials(self._describe_oidc_error(resp))
        if resp.status_code >= 400:
            raise AuthError(f"Token endpoint respondió {resp.status_code}.")
        payload = resp.json()
        now = self._clock()
        refresh_expires_in = payload.get("refresh_expires_in")
        return _TokenSet(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=now + float(payload.get("expires_in", 0)),
            refresh_expires_at=(
                now + float(refresh_expires_in)
                if refresh_expires_in is not None
                else None
            ),
        )

    @staticmethod
    def _describe_oidc_error(resp: httpx.Response) -> str:
        try:
            data = resp.json()
        except ValueError:
            return f"Autenticación ROPC falló ({resp.status_code})."
        desc = (
            data.get("error_description")
            or data.get("error")
            or "credenciales inválidas"
        )
        return f"Autenticación ROPC falló ({resp.status_code}): {desc}"
