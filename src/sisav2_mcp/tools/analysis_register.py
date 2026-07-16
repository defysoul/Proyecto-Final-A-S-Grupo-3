"""Registro de las tools semánticas sobre una cohorte real prevalidada."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from . import analysis
from .context import SisavContext
from .errors import friendly_tool_errors
from .semantic import SemanticIndexStore


def _id_or_text(value: int | str) -> tuple[int | None, str | None]:
    """Interpreta un ID entero positivo o una consulta textual no vacía."""
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(
                "id_o_texto debe ser un ID positivo o una consulta textual."
            )
        return value, None
    text = value.strip()
    if not text:
        raise ValueError("id_o_texto no puede estar vacío.")
    if text.isdigit():
        identifier = int(text)
        if identifier <= 0:
            raise ValueError(
                "id_o_texto debe ser un ID positivo o una consulta textual."
            )
        return identifier, None
    return None, text


def _with_source(result: dict[str, Any], *, documents: int) -> dict[str, Any]:
    """Deja claro que el análisis proviene de la cohorte conectada preparada."""
    return {
        **result,
        "fuente": "cohorte real prevalidada de SISAV2 (solo lectura)",
        "documentosIndice": documents,
    }


def register_analysis_tools(
    mcp: FastMCP,
    ctx: SisavContext,
    store: SemanticIndexStore,
) -> None:
    """Registra búsqueda, duplicados y ranking sin modificar SISAV2."""

    @mcp.tool
    @friendly_tool_errors
    async def buscar_iniciativas_similares(
        id_o_texto: int | str,
        k: int = 5,
        similitud_minima: float = 0.0,
    ) -> dict[str, Any]:
        """Busca similares en la cohorte real preparada; no modifica SISAV2."""
        # La demo es conectada: comprobar identidad/red antes de usar una caché.
        await ctx.usuario()
        index = store.get()
        identifier, query = _id_or_text(id_o_texto)
        result = analysis.buscar_iniciativas_similares(
            index.iniciativas,
            id_postulacion=identifier,
            consulta=query,
            limite=k,
            similitud_minima=similitud_minima,
            indice=index,
        )
        return _with_source(result, documents=len(index.iniciativas))

    @mcp.tool
    @friendly_tool_errors
    async def detectar_duplicados(
        id_postulacion: int | None = None,
        umbral: float = 0.84,
        limite: int = 20,
    ) -> dict[str, Any]:
        """Detecta pares semánticamente cercanos para revisión humana."""
        await ctx.usuario()
        index = store.get()
        if id_postulacion is not None and id_postulacion not in {
            document.id_postulacion for document in index.iniciativas
        }:
            raise ValueError(
                f"La postulación {id_postulacion} no pertenece a la cohorte semántica."
            )
        result = analysis.detectar_duplicados(
            index.iniciativas,
            umbral=umbral,
            limite=limite,
            indice=index,
        )
        if id_postulacion is not None:
            result["idPostulacion"] = id_postulacion
            result["duplicados"] = [
                pair
                for pair in result["duplicados"]
                if id_postulacion
                in {
                    pair["izquierda"]["idPostulacion"],
                    pair["derecha"]["idPostulacion"],
                }
            ]
        return _with_source(result, documents=len(index.iniciativas))

    @mcp.tool
    @friendly_tool_errors
    async def ranking_facultades_por_ods(
        ods_id: int | str | None = None,
        anio: int | None = None,
        limite_facultades: int = 10,
    ) -> dict[str, Any]:
        """Agrupa la cohorte real por ODS y facultad, sin cambiar datos."""
        await ctx.usuario()
        index = store.get()
        result = analysis.ranking_facultades_por_ods(
            index.iniciativas,
            ods=str(ods_id) if ods_id is not None else None,
            anio=anio,
            limite_facultades=limite_facultades,
        )
        return _with_source(result, documents=len(index.iniciativas))
