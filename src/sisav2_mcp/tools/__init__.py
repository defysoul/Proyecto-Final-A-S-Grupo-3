"""Tools MCP: consulta, reportes y previews de escritura dry-run."""

from __future__ import annotations

from .analysis_register import register_analysis_tools
from .context import SisavContext
from .register import (
    register_core_tools,
    register_document_tools,
    register_report_tools,
    register_write_tools,
)

__all__ = [
    "SisavContext",
    "register_analysis_tools",
    "register_core_tools",
    "register_document_tools",
    "register_report_tools",
    "register_write_tools",
]
