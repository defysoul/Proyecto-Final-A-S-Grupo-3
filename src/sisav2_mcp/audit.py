"""Registro de auditoría append-only para las escrituras aplicadas.

Cada commit (contra el backend mock) deja una línea JSONL con quién, qué,
cuándo y con qué ``request_id``. Es el rastro de "quién hizo qué" que exige la
operación con capacidad de escritura; el actor se guarda pseudonimizado
(``usuario#<id>``), sin PII.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLog:
    """Bitácora de auditoría en un archivo JSONL (una línea por evento)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: dict[str, Any]) -> None:
        """Agrega un evento sellado con la marca temporal UTC."""
        evento = {"ts": datetime.now(UTC).isoformat(), **record}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def registros(self) -> list[dict[str, Any]]:
        """Lee todos los eventos registrados (vacío si aún no hay archivo)."""
        if not self._path.exists():
            return []
        return [
            json.loads(linea)
            for linea in self._path.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]
