"""Pruebas de las tools MCP que consultan el índice semántico preparado."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP

from sisav2_mcp.models.analysis import IniciativaSemantica
from sisav2_mcp.tools import analysis
from sisav2_mcp.tools.analysis_register import _id_or_text, register_analysis_tools


class TinyEncoder:
    model_name = "tests/analysis-register"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vectors.append([1.0, 0.1] if "salud" in text.casefold() else [0.0, 1.0])
        return vectors


class FakeContext:
    def __init__(self) -> None:
        self.calls = 0

    async def usuario(self) -> object:
        self.calls += 1
        return object()


class FakeStore:
    def __init__(self, index: analysis.SemanticIndex) -> None:
        self.index = index
        self.calls = 0

    def get(self) -> analysis.SemanticIndex:
        self.calls += 1
        return self.index


def _index() -> analysis.SemanticIndex:
    initiatives = [
        IniciativaSemantica(
            idPostulacion=1,
            titulo="Taller de salud",
            texto="salud comunitaria",
            facultad="Facultad A",
            ods=["ODS 3"],
            anio=2026,
        ),
        IniciativaSemantica(
            idPostulacion=2,
            titulo="Capacitación de salud",
            texto="salud territorial",
            facultad="Facultad A",
            ods=["ODS 3"],
            anio=2026,
        ),
        IniciativaSemantica(
            idPostulacion=3,
            titulo="Datos abiertos",
            texto="datos institucionales",
            facultad="Facultad B",
            ods=["ODS 4"],
            anio=2025,
        ),
    ]
    index, _cached = analysis.preparar_indice_semantico(
        initiatives, encoder=TinyEncoder()
    )
    return index


async def _call(mcp: FastMCP, name: str, **kwargs: Any) -> dict[str, Any]:
    tool = await mcp.get_tool(name)
    assert tool is not None
    return await tool.fn(**kwargs)


def test_id_or_text_normalizes_ids_and_queries() -> None:
    assert _id_or_text("3033") == (3033, None)
    assert _id_or_text(3033) == (3033, None)
    assert _id_or_text("salud comunitaria") == (None, "salud comunitaria")


def test_registered_analysis_tools_require_connected_context_and_use_store() -> None:
    mcp = FastMCP("analysis-test")
    context = FakeContext()
    store = FakeStore(_index())
    register_analysis_tools(mcp, context, store)  # type: ignore[arg-type]

    similar = asyncio.run(
        _call(mcp, "buscar_iniciativas_similares", id_o_texto=1, k=2)
    )
    duplicates = asyncio.run(
        _call(mcp, "detectar_duplicados", id_postulacion=1, umbral=0.95)
    )
    ranking = asyncio.run(
        _call(mcp, "ranking_facultades_por_ods", ods_id=3, anio=2026)
    )

    assert similar["resultados"][0]["idPostulacion"] == 2
    assert duplicates["idPostulacion"] == 1
    assert len(duplicates["duplicados"]) == 1
    assert ranking["ranking"][0]["ods"] == "ODS 3"
    assert context.calls == 3
    assert store.calls == 3
    assert ranking["fuente"].startswith("cohorte real")
