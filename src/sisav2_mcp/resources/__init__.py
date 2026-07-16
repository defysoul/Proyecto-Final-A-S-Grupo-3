"""Resources MCP (Paso 8): catálogos con caché TTL."""

from __future__ import annotations

from .catalog import CatalogCache
from .register import register_catalog_resources

__all__ = ["CatalogCache", "register_catalog_resources"]
