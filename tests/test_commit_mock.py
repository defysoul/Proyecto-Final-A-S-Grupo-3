"""Camino commit contra mock local.

Verifica el flujo dry-run -> confirmar -> aplicar-a-mock -> read-back, la
auditoría de cada commit y la garantía central: sin un backend mock, un
``confirmar=True`` NO puede aplicar nada (el SISAV2 real jamás se toca).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import pytest

from sisav2_mcp.audit import AuditLog
from sisav2_mcp.mock_backend import (
    CommitNoHabilitado,
    MockSisav2Backend,
    aplicar_commit,
    exigir_backend,
    finalizar_escritura,
)
from sisav2_mcp.tools import writes


def run(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)


def _preview_crear() -> dict[str, Any]:
    return run(
        writes.crear_postulacion(
            permisos={"IPOCRE"},
            modalidad="PRE_GRADO",
            convocatoria_id=71,
            titulo="Taller de prueba",
            objetivo="Acercar el conocimiento a la comunidad.",
        )
    )


def test_backend_aplica_create_asigna_id_y_lee_de_vuelta() -> None:
    backend = MockSisav2Backend()
    preview = _preview_crear()

    entidad_id, read_back = backend.aplicar(
        preview["operacion"], preview["would_request"], request_id="req-1"
    )

    assert entidad_id
    assert backend.leer(entidad_id) == read_back
    assert read_back["operacion"] == "crear_postulacion"


def test_update_persiste_y_readback_acumula_historial() -> None:
    backend = MockSisav2Backend()
    wr1 = {
        "method": "PUT",
        "path": "/convocatorias/postulacion/3033",
        "body": {"idPostulacion": 3033, "campos": {"NOMBRE": "v1"}},
    }
    wr2 = {
        "method": "PUT",
        "path": "/convocatorias/postulacion/3033",
        "body": {"idPostulacion": 3033, "campos": {"OBJETIVO": "v2"}},
    }

    id1, _ = backend.aplicar("editar_postulacion", wr1, request_id="r1")
    id2, read_back = backend.aplicar("editar_postulacion", wr2, request_id="r2")

    assert id1 == id2  # misma entidad (idPostulacion:3033)
    assert len(read_back["historial"]) == 2


def test_aplicar_commit_devuelve_commitresult_con_readback() -> None:
    backend = MockSisav2Backend()
    preview = _preview_crear()

    result = aplicar_commit(
        preview, backend=backend, actor="usuario#42", request_id="req-2"
    )

    assert result["modo"] == "commit_mock"
    assert result["aplicado"] is True
    assert result["backend"] == "mock"
    assert result["sisav2_real_modificado"] is False
    assert result["operacion"] == "crear_postulacion"
    assert result["permiso"]["concedidos"] == ["IPOCRE"]
    assert result["read_back"]["operacion"] == "crear_postulacion"


def test_commit_registra_auditoria(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    backend = MockSisav2Backend()
    preview = _preview_crear()

    aplicar_commit(
        preview,
        backend=backend,
        actor="usuario#42",
        request_id="req-3",
        audit=audit,
    )

    registros = audit.registros()
    assert len(registros) == 1
    registro = registros[0]
    assert registro["actor"] == "usuario#42"
    assert registro["operacion"] == "crear_postulacion"
    assert registro["request_id"] == "req-3"
    assert registro["aplicado"] is True
    assert registro["backend"] == "mock"
    assert "ts" in registro


def test_confirmar_true_sin_backend_falla() -> None:
    # Garantía: sin mock, un confirmar no puede aplicar -> SISAV2 real intacto.
    with pytest.raises(CommitNoHabilitado):
        exigir_backend(None, confirmar=True)


def test_confirmar_false_no_exige_backend() -> None:
    assert exigir_backend(None, confirmar=False) is None


def test_finalizar_dry_run_por_defecto_devuelve_preview_intacto() -> None:
    preview = _preview_crear()

    result = finalizar_escritura(
        preview, confirmar=False, backend=MockSisav2Backend(), actor="usuario#42"
    )

    assert result is preview
    assert result["aplicado"] is False
    assert result["modo"] == "dry_run"


def test_finalizar_con_confirmar_y_mock_aplica() -> None:
    preview = _preview_crear()

    result = finalizar_escritura(
        preview, confirmar=True, backend=MockSisav2Backend(), actor="usuario#42"
    )

    assert result["modo"] == "commit_mock"
    assert result["aplicado"] is True


def test_finalizar_con_confirmar_sin_mock_falla() -> None:
    preview = _preview_crear()

    with pytest.raises(CommitNoHabilitado):
        finalizar_escritura(preview, confirmar=True, backend=None, actor="usuario#42")


def test_write_tools_exponen_parametro_confirmar() -> None:
    # El registro debe cablear `confirmar` en el esquema de cada tool de escritura.
    from fastmcp import Client

    from sisav2_mcp.server import mcp

    async def _schemas() -> dict[str, Any]:
        async with Client(mcp) as client:
            return {t.name: t.inputSchema for t in await client.list_tools()}

    schemas = asyncio.run(_schemas())
    for tool in (
        "crear_postulacion",
        "editar_postulacion",
        "evaluar_admisibilidad",
        "cambiar_fase",
        "agregar_comentario_bitacora",
        "crear_postulacion_espejo",
        "cargar_asistencia",
    ):
        assert "confirmar" in schemas[tool]["properties"], tool
