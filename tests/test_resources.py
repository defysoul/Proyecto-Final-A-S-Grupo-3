"""Tests de los Resources de catálogo (Paso 8): caché TTL, parseo y registro."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fastmcp import Client, FastMCP

from sisav2_mcp.auth.base import TokenProvider
from sisav2_mcp.client import SisavClient
from sisav2_mcp.config import Settings
from sisav2_mcp.resources import CatalogCache, register_catalog_resources

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


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def run_with_client(scenario: Callable[[SisavClient], Awaitable[Any]]) -> Any:
    async def main() -> Any:
        async with SisavClient(SETTINGS, FakeProvider(), max_retries=0) as client:
            return await scenario(client)

    return asyncio.run(main())


def test_cache_hit_avoids_refetch() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/estado/buscar").mock(
            return_value=resp("convocatorias_estado_buscar.json")
        )

        async def scenario(client: SisavClient) -> list[Any]:
            cache = CatalogCache(client, ttl=300.0)
            first = await cache.estados()
            second = await cache.estados()
            assert first == second
            return first

        estados = run_with_client(scenario)

    assert len(estados) == 11
    assert estados[0] == {"id": 1, "nombre": "Incompleta", "orden": 1}
    assert route.call_count == 1  # segunda lectura sirvió de caché


def test_cache_expiration_refetches() -> None:
    clock = FakeClock()
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/convocatorias/estado/buscar").mock(
            return_value=resp("convocatorias_estado_buscar.json")
        )

        async def scenario(client: SisavClient) -> None:
            cache = CatalogCache(client, ttl=100.0, clock=clock)
            await cache.estados()
            clock.advance(101.0)  # expira el TTL
            await cache.estados()

        run_with_client(scenario)

    assert route.call_count == 2


def test_fase_templated_cache() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/fases/obtener/34").mock(
            return_value=resp("convocatorias_fases_obtener_34.json")
        )

        async def scenario(client: SisavClient) -> dict[str, Any]:
            cache = CatalogCache(client, ttl=300.0)
            return await cache.fase(34)

        fase = run_with_client(scenario)

    assert fase["id"] == 34
    assert fase["nombre"].startswith("Iniciativas")


def test_consultar_dispatch_and_errors() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/mantenedores/listarFacultad").mock(
            return_value=resp("mantenedores_listarFacultad.json")
        )

        async def scenario(client: SisavClient) -> Any:
            cache = CatalogCache(client, ttl=300.0)
            facultades = await cache.consultar("facultades")
            with pytest.raises(ValueError, match="desconocido"):
                await cache.consultar("usuarios")
            with pytest.raises(ValueError, match="id_fase"):
                await cache.consultar("fases")
            return facultades

        facultades = run_with_client(scenario)

    assert any(f["sigla"] == "FING" for f in facultades)


def test_resources_registered_and_readable() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/convocatorias/estado/buscar").mock(
            return_value=resp("convocatorias_estado_buscar.json")
        )

        async def scenario() -> None:
            async with SisavClient(SETTINGS, FakeProvider(), max_retries=0) as client:
                mcp = FastMCP("test")
                register_catalog_resources(mcp, CatalogCache(client, ttl=300.0))
                async with Client(mcp) as mcp_client:
                    uris = {str(r.uri) for r in await mcp_client.list_resources()}
                    assert "sisav2://catalogo/estados" in uris
                    assert "sisav2://catalogo/convocatorias" in uris
                    templates = {
                        t.uriTemplate
                        for t in await mcp_client.list_resource_templates()
                    }
                    assert "sisav2://catalogo/fases/{id_fase}" in templates
                    out = await mcp_client.read_resource("sisav2://catalogo/estados")
                    data = json.loads(out[0].text)
                    assert len(data) == 11

        asyncio.run(scenario())
