"""Tests tool-level (Paso 6) con el cliente mockeado vía respx.

Verifican la construcción de params (estado[]/roles JSON, ingreso, modalidad,
csv de roles) y una forma de salida estable, sin tocar la red real.
"""

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
from sisav2_mcp.tools import core

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


def test_listar_postulaciones_params_and_output() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/postulacion/buscar").mock(
            return_value=resp("postulacion_buscar_pregrado.json")
        )
        result = run_tool(
            lambda c: core.listar_postulaciones(
                c, modalidad="PRE_GRADO", id_usuario=401, roles=[8, 3, 1, 24]
            )
        )

    assert result["total"] == 1471
    assert result["mostrando"] == 4
    first = result["postulaciones"][0]
    assert first["idpostulacion"] == 3033
    assert first["estado"] == {"id": 2, "nombre": "Ingresada"}

    params = route.calls.last.request.url.params
    assert params["modalidad"] == "PRE_GRADO"
    assert params["idUsuario"] == "401"
    assert params["roles"] == "[8,3,1,24]"
    assert params["estado"] == "[3,10,1,2,7,11,8]"  # preset Ingresos
    assert params["ingreso"] == "true"


def test_listar_admisibilidad_uses_preset() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/postulacion/buscar").mock(
            return_value=resp("postulacion_buscar_extension.json")
        )
        run_tool(
            lambda c: core.listar_admisibilidad(
                c, modalidad="EXTENSION", id_usuario=401, roles=[8, 3]
            )
        )

    params = route.calls.last.request.url.params
    assert params["estado"] == "[3,6,2,4]"
    assert params["ingreso"] == "false"


def test_listar_proyectos_output_and_search() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/proyectos/listar").mock(
            return_value=resp("proyectos_listar_pregrado.json")
        )
        result = run_tool(
            lambda c: core.listar_proyectos(
                c, modalidad="PRE_GRADO", id_usuario=401, busqueda="banco"
            )
        )

    assert result["total"] == 1299
    assert result["proyectos"][0]["id"] == 2912
    assert result["proyectos"][0]["idpostulacion"] == 2992
    assert route.calls.last.request.url.params["searchTerm"] == "banco"


def test_obtener_detalle_without_fase() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/postulacion/obtener/3033").mock(
            return_value=resp("postulacion_obtener_3033.json")
        )
        result = run_tool(
            lambda c: core.obtener_detalle_iniciativa(c, id_postulacion=3033)
        )

    assert result["id"] == 3033
    assert "fase" not in result
    campos = result["pasos"][0]["campos"]
    assert campos[0]["name"] == "ESTANDAR_CORREO"


def test_obtener_detalle_with_fase() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/postulacion/obtener/3033").mock(
            return_value=resp("postulacion_obtener_3033.json")
        )
        mock.get(f"{API}/convocatorias/fases/obtener/34").mock(
            return_value=resp("convocatorias_fases_obtener_34.json")
        )
        result = run_tool(
            lambda c: core.obtener_detalle_iniciativa(
                c, id_postulacion=3033, id_fase=34
            )
        )

    assert result["fase"]["id"] == 34
    primera = result["fase"]["transiciones"][0]
    assert primera == {"rol": "Analista", "estado": "Admisible"}


def test_ver_bitacora_output_and_params() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/postulacion/listar-cambios").mock(
            return_value=resp("postulacion_listar-cambios_3033.json")
        )
        result = run_tool(lambda c: core.ver_bitacora(c, id_postulacion=3033))

    assert result["cambios"][0]["estadoActual"] == "Reformular"
    assert route.calls.last.request.url.params["idPostulacion"] == "3033"


def test_listar_repositorios_roles_csv() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/mantenedores/repositorios").mock(
            return_value=resp("mantenedores_repositorios.json")
        )
        result = run_tool(lambda c: core.listar_repositorios(c, roles=[8, 3, 1, 24]))

    assert result["categorias"][0]["nombre"] == "Docencia"
    params = route.calls.last.request.url.params
    assert params["vista"] == "REPOSITORIO_VCM"
    assert params["roles"] == "8,3,1,24"


def test_invalid_modalidad_raises_before_network() -> None:
    with pytest.raises(ValueError, match="modalidad inválida"):
        run_tool(
            lambda c: core.listar_postulaciones(
                c, modalidad="XX", id_usuario=401, roles=[1]
            )
        )


@pytest.mark.parametrize(
    ("offset", "limit", "needle"),
    [(-1, 25, "offset"), (0, 0, "limit"), (0, 101, "limit")],
)
def test_invalid_pagination_raises_before_network(
    offset: int, limit: int, needle: str
) -> None:
    with pytest.raises(ValueError, match=needle):
        run_tool(
            lambda c: core.listar_postulaciones(
                c,
                modalidad="PRE_GRADO",
                id_usuario=401,
                roles=[1],
                offset=offset,
                limit=limit,
            )
        )
