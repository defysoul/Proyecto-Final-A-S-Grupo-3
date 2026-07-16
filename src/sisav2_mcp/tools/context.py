"""Contexto compartido por las tools: cliente HTTP + identidad del usuario.

La identidad (idUsuario + ids de roles) se resuelve una vez vía
``verifica-token`` y se cachea; varias tools la necesitan como params de query.
La autenticación es perezosa: construir el contexto no hace red (solo al primer
uso de una tool).
"""

from __future__ import annotations

from ..audit import AuditLog
from ..auth import KeyringCredentialStore
from ..auth.ropc import RopcTokenProvider
from ..client import SisavClient
from ..config import Settings
from ..mock_backend import MockSisav2Backend
from ..models import Usuario


class SisavContext:
    """Mantiene el cliente, el proveedor de tokens y el Usuario cacheado.

    ``mock_backend`` y ``audit`` son opcionales: sólo se inyectan cuando la demo
    habilita el commit contra el simulador (``SISAV2_MOCK_WRITES=1``). Sin ellos,
    las tools de escritura permanecen en dry-run.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: SisavClient | None = None,
        token_provider: RopcTokenProvider | None = None,
        mock_backend: MockSisav2Backend | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self._settings = settings
        store = KeyringCredentialStore(settings.keyring_service)
        self._provider = token_provider or RopcTokenProvider(settings, store)
        self._client = client or SisavClient(settings, self._provider)
        self._usuario: Usuario | None = None
        self.mock_backend = mock_backend
        self.audit = audit

    @property
    def client(self) -> SisavClient:
        return self._client

    async def usuario(self) -> Usuario:
        """Devuelve el Usuario autenticado (verifica-token), cacheado."""
        if self._usuario is None:
            self._usuario = await self._provider.verifica_token()
        return self._usuario

    async def identity(self) -> tuple[int, list[int]]:
        """(idUsuario, ids de roles) para los params de las tools."""
        usuario = await self.usuario()
        roles = [rol.id for rol in usuario.perfil.roles] if usuario.perfil else []
        return usuario.id, roles

    async def aclose(self) -> None:
        await self._client.aclose()
