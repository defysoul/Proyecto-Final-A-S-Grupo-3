"""Configuración de logging del servidor.

En un servidor MCP por stdio, **stdout transporta el protocolo**: todo log debe
ir a **stderr**. El nivel se controla con ``SISAV2_LOG_LEVEL`` (default INFO).
Pon ``DEBUG`` para ver los avisos de shapes inesperados de los modelos.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    """Envía los logs de ``sisav2_mcp`` a stderr (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("SISAV2_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger = logging.getLogger("sisav2_mcp")
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True
