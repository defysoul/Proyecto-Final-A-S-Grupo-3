"""Registro de los Resources de catálogo (Paso 8) en una instancia FastMCP.

5 Resources confirmados: 4 estáticos + 1 templated (fases por id). Más un tool de
respaldo ``consultar_catalogo`` para clientes MCP que no soporten Resources bien.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..tools.errors import friendly_tool_errors
from .catalog import CatalogCache


def register_catalog_resources(mcp: FastMCP, cache: CatalogCache) -> None:
    """Registra los Resources ``sisav2://catalogo/*`` + el tool de respaldo."""

    @mcp.resource("sisav2://catalogo/convocatorias")
    async def _convocatorias() -> list[dict[str, Any]]:
        """Catálogo de convocatorias: [{id, nombre}]."""
        return await cache.convocatorias()

    @mcp.resource("sisav2://catalogo/carreras")
    async def _carreras() -> list[dict[str, Any]]:
        """Catálogo de carreras: [{id, nombre, codigo, facultadId}]."""
        return await cache.carreras()

    @mcp.resource("sisav2://catalogo/facultades")
    async def _facultades() -> list[dict[str, Any]]:
        """Catálogo de facultades: [{id, sigla, nombre, ...}]."""
        return await cache.facultades()

    @mcp.resource("sisav2://catalogo/estados")
    async def _estados() -> list[dict[str, Any]]:
        """Catálogo de estados de postulación: [{id, nombre, orden}] (11)."""
        return await cache.estados()

    @mcp.resource("sisav2://catalogo/fases/{id_fase}")
    async def _fase(id_fase: int) -> dict[str, Any]:
        """Config de una fase por id (workflow rol→estado, plantillas)."""
        return await cache.fase(id_fase)

    @mcp.tool
    @friendly_tool_errors
    async def consultar_catalogo(
        nombre: str,
        id_fase: int | None = None,
        facultad_id: int | None = None,
    ) -> Any:
        """Respaldo de los Resources sisav2://catalogo/* (clientes sin Resources).

        nombre ∈ {convocatorias, carreras, facultades, estados, fases}. Para
        'fases' indica id_fase; 'carreras' admite facultad_id opcional.
        """
        return await cache.consultar(nombre, id_fase=id_fase, facultad_id=facultad_id)
