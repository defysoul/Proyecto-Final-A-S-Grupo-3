"""Pruebas del acceso del servidor a la caché semántica local."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from sisav2_mcp.models.analysis import IniciativaSemantica
from sisav2_mcp.tools.analysis import preparar_indice_semantico
from sisav2_mcp.tools.semantic import SemanticIndexStore


class TinyEncoder:
    model_name = "tests/tiny"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, float(index + 1)] for index, _text in enumerate(texts)]


def _write_index(path: Path) -> None:
    preparar_indice_semantico(
        [
            IniciativaSemantica(
                idPostulacion=3033,
                titulo="Iniciativa de prueba",
                texto="iniciativa de prueba",
                modalidad="PRE_GRADO",
            )
        ],
        encoder=TinyEncoder(),
        cache_path=path,
    )


def test_store_loads_and_reuses_local_cache(tmp_path: Path) -> None:
    path = tmp_path / "semantic-index.json"
    _write_index(path)
    store = SemanticIndexStore(path)

    first = store.get()
    second = store.get()

    assert first is second
    assert first.iniciativas[0].id_postulacion == 3033


def test_store_explains_missing_preflight(tmp_path: Path) -> None:
    store = SemanticIndexStore(tmp_path / "missing.json")

    with pytest.raises(ValueError, match="index-demo"):
        store.get()
