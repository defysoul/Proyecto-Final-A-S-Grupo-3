"""Stub de PKCE-loopback: ruta de upgrade BLOQUEADA en v1.

Probe de Fase 0 (solo GETs) contra el Keycloak de UTEM:
- redirect ``http://localhost`` / ``http://127.0.0.1`` → HTTP 400 (rechazado).
- control ``https://sisav2.utem.cl/`` → HTTP 200 (login).

Conclusión: el cliente público ``SISAV2`` no tiene registrado un redirect
loopback, así que el Authorization Code Flow + PKCE local no es viable todavía.
v1 usa :class:`~sisav2_mcp.auth.ropc.RopcTokenProvider`. Cuando UTEM registre un
redirect loopback, implementar aquí el flujo PKCE y conmutar el provider sin
tocar las capas superiores (mismo contrato ``TokenProvider``).
"""

from __future__ import annotations

from .base import TokenProvider


class PkceTokenProvider(TokenProvider):
    """Placeholder no funcional; documenta el upgrade diferido a PKCE."""

    async def get_access_token(self) -> str:
        raise NotImplementedError(
            "PkceTokenProvider no está disponible en v1: el cliente público "
            "SISAV2 rechaza redirects loopback (probe Fase 0). Usa "
            "RopcTokenProvider. Upgrade pendiente de que UTEM registre el "
            "redirect loopback."
        )
