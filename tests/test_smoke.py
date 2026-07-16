"""Smoke test del scaffold (Paso 2).

Verifica que el paquete importa y que el servidor FastMCP arranca y responde el
handshake MCP in-memory (sin tools registradas todavía).
"""

import asyncio

import sisav2_mcp
from sisav2_mcp.server import mcp


def test_version() -> None:
    assert sisav2_mcp.__version__ == "0.2.0"


def test_server_name() -> None:
    assert mcp.name == "sisav2-mcp"


def test_mcp_handshake_lists_all_demo_tools() -> None:
    """El handshake expone las consultas, previews y análisis de la demo."""
    from fastmcp import Client

    async def _run() -> set[str]:
        async with Client(mcp) as client:
            return {t.name for t in await client.list_tools()}

    names = asyncio.run(_run())
    assert {
        "listar_postulaciones",
        "listar_admisibilidad",
        "listar_planificacion",
        "listar_cambio_fase",
        "listar_proyectos",
        "obtener_detalle_iniciativa",
        "ver_bitacora",
        "listar_repositorios",
        "resumen_indicadores",
        "avance_global",
        "exportar_postulaciones",
        "sisav2_consulta_generica",
        "consultar_catalogo",
        # Escritura segura: todas son previews dry-run.
        "crear_postulacion",
        "editar_postulacion",
        "evaluar_admisibilidad",
        "cambiar_fase",
        "agregar_comentario_bitacora",
        "crear_postulacion_espejo",
        "cargar_asistencia",
        # Análisis sobre la cohorte real prevalidada.
        "buscar_iniciativas_similares",
        "detectar_duplicados",
        "ranking_facultades_por_ods",
    } <= names
