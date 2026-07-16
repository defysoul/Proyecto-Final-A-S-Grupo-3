"""Configuración del servidor SISAV2 MCP.

Valores confirmados en Fase 0 (samples + probe de auth en vivo). Todos
sobreescribibles por variable de entorno con prefijo ``SISAV2_`` para no tener
que tocar código en otra instalación.

Seguridad: la credencial UTEM del usuario NUNCA vive aquí. Este config solo
guarda el *service name* del keychain; la clave se persiste cifrada en el
Windows Credential Manager vía ``keyring`` (ver Paso 4).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_API_BASE_URL = "https://sisav2-api.utem.cl"
DEFAULT_OIDC_ISSUER = "https://sso.utem.cl/auth/realms/prod"
DEFAULT_CLIENT_ID = "SISAV2"  # cliente público, sin secret (grant ROPC)
DEFAULT_KEYRING_SERVICE = "sisav2-mcp"
DEFAULT_CATALOG_TTL_SECONDS = 3600  # caché de catálogos (Resources, Paso 8)


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable del servidor. Usar :meth:`from_env` para cargar."""

    api_base_url: str = DEFAULT_API_BASE_URL
    oidc_issuer: str = DEFAULT_OIDC_ISSUER
    client_id: str = DEFAULT_CLIENT_ID
    keyring_service: str = DEFAULT_KEYRING_SERVICE
    catalog_ttl_seconds: int = DEFAULT_CATALOG_TTL_SECONDS
    # Habilita el commit contra el backend SIMULADO en memoria (nunca SISAV2
    # real). Apagado por defecto: las tools de escritura son dry-run.
    mock_writes: bool = False

    @property
    def token_endpoint(self) -> str:
        """Endpoint OIDC de tokens (password/refresh grant)."""
        return f"{self.oidc_issuer}/protocol/openid-connect/token"

    @classmethod
    def from_env(cls) -> Settings:
        """Construye la config con defaults confirmados + overrides de entorno."""
        return cls(
            api_base_url=os.getenv("SISAV2_API_BASE_URL", DEFAULT_API_BASE_URL),
            oidc_issuer=os.getenv("SISAV2_OIDC_ISSUER", DEFAULT_OIDC_ISSUER),
            client_id=os.getenv("SISAV2_CLIENT_ID", DEFAULT_CLIENT_ID),
            keyring_service=os.getenv(
                "SISAV2_KEYRING_SERVICE", DEFAULT_KEYRING_SERVICE
            ),
            catalog_ttl_seconds=int(
                os.getenv(
                    "SISAV2_CATALOG_TTL_SECONDS", str(DEFAULT_CATALOG_TTL_SECONDS)
                )
            ),
            mock_writes=os.getenv("SISAV2_MOCK_WRITES", "").strip().lower()
            in {"1", "true", "yes", "on"},
        )
