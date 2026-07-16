"""Tests de las tools de reportes + escape hatch (Paso 7) con respx."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from sisav2_mcp.auth.base import TokenProvider
from sisav2_mcp.client import SisavClient
from sisav2_mcp.config import Settings
from sisav2_mcp.tools import reports

SETTINGS = Settings()
API = SETTINGS.api_base_url
SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "discovery" / "samples"


def sample(name: str) -> Any:
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))


def resp(name: str) -> httpx.Response:
    return httpx.Response(200, json=sample(name))


class FakeProvider(TokenProvider):
    async def get_access_token(self) -> str:
        return "TESTTOKEN"


def run_tool(scenario: Callable[[SisavClient], Awaitable[Any]]) -> Any:
    async def main() -> Any:
        async with SisavClient(SETTINGS, FakeProvider(), max_retries=0) as client:
            return await scenario(client)

    return asyncio.run(main())


def test_resumen_indicadores_shape_and_modalidad() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/postulacion/totales/401").mock(
            return_value=resp("postulacion_totales_pregrado.json")
        )
        result = run_tool(
            lambda c: reports.resumen_indicadores(
                c, id_usuario=401, modalidad="PRE_GRADO"
            )
        )

    assert result["idUsuario"] == 401
    assert len(result["indicadores"]) == 11
    assert result["indicadores"][0] == {
        "idEstado": 1,
        "estado": "Incompleta",
        "total": 60,
    }
    assert result["totalGeneral"] == sum(i["total"] for i in result["indicadores"])
    assert route.calls.last.request.url.params["modalidad"] == "PRE_GRADO"


def test_avance_global_kpis() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/proyectos/estadisticas/globales-proyectos").mock(
            return_value=resp("estadisticas_globales-proyectos.json")
        )
        result = run_tool(reports.avance_global)

    assert result["totalProyectos"] == 1338
    assert result["totalPresupuesto"] == 24051600


def test_exportar_postulaciones_returns_url_not_data() -> None:
    body = sample("postulacion_exportar-excel.json")["_response_body"]
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(f"{API}/convocatorias/postulacion/exportar-excel").mock(
            return_value=httpx.Response(200, json=body)
        )
        result = run_tool(
            lambda c: reports.exportar_postulaciones(
                c,
                convocatoria_id=71,
                modalidad="PRE_GRADO",
                id_usuario=401,
                roles=[8, 3, 1, 24],
                es_admin=True,
            )
        )

    assert result["total"] == 88
    assert result["url"].startswith("https://")
    sent = json.loads(route.calls.last.request.content)
    assert sent["convocatoriaId"] == 71
    assert sent["idUsuario"] == 401
    assert sent["roles"] == [8, 3, 1, 24]
    assert sent["esAdmin"] is True
    assert sent["estado"] == []


def test_consulta_generica_allows_exact_path() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/listar-combo").mock(
            return_value=resp("convocatorias_listar-combo.json")
        )
        result = run_tool(
            lambda c: reports.sisav2_consulta_generica(
                c, path="/convocatorias/listar-combo"
            )
        )

    assert isinstance(result, list)
    assert result[0]["id"] == 71


def test_consulta_generica_allows_templated_prefix() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/postulacion/obtener/3033").mock(
            return_value=resp("postulacion_obtener_3033.json")
        )
        result = run_tool(
            lambda c: reports.sisav2_consulta_generica(
                c, path="/convocatorias/postulacion/obtener/3033"
            )
        )

    assert result["id"] == 3033


def test_consulta_generica_rejects_unlisted_path() -> None:
    with pytest.raises(ValueError, match="no permitido"):
        run_tool(
            lambda c: reports.sisav2_consulta_generica(c, path="/usuarios/listar")
        )


def test_is_allowed_generic_path() -> None:
    assert reports.is_allowed_generic_path("/convocatorias/estado/buscar")
    assert reports.is_allowed_generic_path("/convocatorias/fases/obtener/34")
    assert reports.is_allowed_generic_path("/proyectos/listar?offset=0")
    assert not reports.is_allowed_generic_path("/mantenedores/listarUsuarios")
    # El export es POST (no GET): fuera del escape hatch aunque exista en inventario.
    export_path = "/convocatorias/postulacion/exportar-excel"
    assert not reports.is_allowed_generic_path(export_path)


@pytest.mark.parametrize(
    "path",
    [
        "/convocatorias/fases/obtener/34/extra",
        "/convocatorias/postulacion/obtener/3033-extra",
        "/convocatorias/postulacion/totales/no-es-id",
    ],
)
def test_is_allowed_generic_path_rejects_prefix_extensions(path: str) -> None:
    assert not reports.is_allowed_generic_path(path)
