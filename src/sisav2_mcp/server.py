"""Punto de entrada del servidor MCP SISAV2 por stdio.

Registra consultas reales, previews de escritura dry-run y análisis sobre una
cohorte local preparada desde SISAV2. La autenticación permanece perezosa y la
guardia read-only del cliente sigue bloqueando cualquier mutación remota.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from ._logging import configure_logging
from .audit import AuditLog
from .config import Settings
from .mock_backend import MockSisav2Backend
from .resources import CatalogCache, register_catalog_resources
from .tools import (
    SisavContext,
    register_analysis_tools,
    register_core_tools,
    register_document_tools,
    register_report_tools,
    register_write_tools,
)
from .tools.semantic import SemanticIndexStore


def _audit_path() -> Path:
    """Ruta del log de auditoría de escrituras aplicadas (mock)."""
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "sisav2-mcp" / "audit.jsonl"


def _motor_semantico_disponible() -> bool:
    """True si el motor de embeddings (sentence-transformers) está instalado.

    El ejecutable portable se compila **sin** torch/sentence-transformers para
    mantenerlo liviano y de arranque rápido (así es confiable en Claude Desktop
    y Codex sin exceder su timeout de arranque MCP). En ese caso las tools de
    análisis semántico no se registran; el entorno de desarrollo (venv) sí las
    expone. Las tools de lectura y escritura funcionan igual en ambos.
    """
    return importlib.util.find_spec("sentence_transformers") is not None


settings = Settings.from_env()
mcp: FastMCP = FastMCP("sisav2-mcp")

if settings.mock_writes:
    # Demo con commit contra el SIMULADO en memoria; SISAV2 real intocable.
    _mock_backend: MockSisav2Backend | None = MockSisav2Backend()
    _audit: AuditLog | None = AuditLog(_audit_path())
    logging.getLogger("sisav2_mcp").info(
        "Commit contra backend MOCK habilitado (SISAV2_MOCK_WRITES=1): las tools "
        "de escritura pueden aplicar con confirmar=True sobre un simulador local; "
        "SISAV2 real no se modifica. Auditoría en %s",
        _audit_path(),
    )
else:
    _mock_backend = None
    _audit = None

context = SisavContext(settings, mock_backend=_mock_backend, audit=_audit)
register_core_tools(mcp, context)
register_report_tools(mcp, context)
register_write_tools(mcp, context)
register_document_tools(mcp, context)

if _motor_semantico_disponible():
    semantic_index_store = SemanticIndexStore()
    register_analysis_tools(mcp, context, semantic_index_store)
else:
    logging.getLogger("sisav2_mcp").info(
        "Análisis semántico deshabilitado: no se encontró el motor de embeddings "
        "(sentence-transformers) en esta instalación. Las tools de lectura y "
        "escritura siguen disponibles."
    )

catalog_cache = CatalogCache(context.client, ttl=settings.catalog_ttl_seconds)
register_catalog_resources(mcp, catalog_cache)


def main() -> None:
    """Arranca el servidor MCP por stdio (entrypoint `sisav2-mcp`)."""
    configure_logging()
    mcp.run()


if __name__ == "__main__":
    main()
