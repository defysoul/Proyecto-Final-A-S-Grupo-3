"""Estado local del índice semántico usado por las tools MCP.

El preflight ``sisav2-mcp index-demo`` construye el archivo desde una cohorte
real autorizada. El servidor solo lo carga y consulta: no conserva credenciales
ni intenta descargar datos silenciosamente durante una conversación.
"""

from __future__ import annotations

import os
from pathlib import Path

from .analysis import SemanticIndex, cargar_indice_cache


def default_semantic_cache_path() -> Path:
    """Ruta por usuario para la caché de la demo, fuera del repositorio."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "sisav2-mcp" / "semantic-index.json"
    return Path.home() / ".sisav2-mcp" / "semantic-index.json"


class SemanticIndexStore:
    """Carga perezosa del índice y detecta si el preflight lo reemplazó."""

    def __init__(self, cache_path: str | Path | None = None) -> None:
        self._path = (
            Path(cache_path)
            if cache_path is not None
            else default_semantic_cache_path()
        )
        self._index: SemanticIndex | None = None
        self._mtime_ns: int | None = None

    @property
    def path(self) -> Path:
        """Ruta local, útil para el CLI y mensajes de recuperación."""
        return self._path

    def get(self) -> SemanticIndex:
        """Devuelve la caché válida estructuralmente o explica cómo prepararla."""
        try:
            mtime_ns = self._path.stat().st_mtime_ns
        except OSError as exc:
            raise ValueError(
                "No hay un índice semántico preparado para esta cuenta. Ejecuta "
                f"'sisav2-mcp index-demo --cohort <archivo>' antes de la demo. "
                f"Ruta esperada: {self._path}"
            ) from exc
        if self._index is None or self._mtime_ns != mtime_ns:
            try:
                self._index = cargar_indice_cache(self._path)
            except ValueError as exc:
                raise ValueError(
                    "El índice semántico local es inválido. Vuelve a ejecutar "
                    "'sisav2-mcp index-demo' con una cohorte autorizada."
                ) from exc
            self._mtime_ns = mtime_ns
        return self._index
