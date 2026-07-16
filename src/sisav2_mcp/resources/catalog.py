"""Caché de catálogos con TTL para los Resources MCP (Paso 8).

Los catálogos cambian poco; se cachean ``catalog_ttl_seconds`` para no golpear la
API en cada lectura. El reloj es inyectable para tests de expiración deterministas.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ..client import SisavClient
from ..models import Carrera, Convocatoria, Estado, Facultad, Fase

T = TypeVar("T")

_CATALOGOS = ("convocatorias", "carreras", "facultades", "estados", "fases")


class CatalogCache:
    """Lee y cachea los catálogos de SISAV2 (con TTL)."""

    def __init__(
        self,
        client: SisavClient,
        *,
        ttl: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._ttl = ttl
        self._clock = clock
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def _cached(self, key: str, fetch: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            now = self._clock()
            entry = self._cache.get(key)
            if entry is not None and now < entry[0]:
                return entry[1]
            value = await fetch()
            self._cache[key] = (now + self._ttl, value)
            return value

    async def convocatorias(self) -> list[dict[str, Any]]:
        async def fetch() -> list[dict[str, Any]]:
            data = await self._client.get("/convocatorias/listar-combo")
            return [Convocatoria.model_validate(x).model_dump() for x in data]

        return await self._cached("convocatorias", fetch)

    async def carreras(self, facultad_id: int | None = None) -> list[dict[str, Any]]:
        async def fetch() -> list[dict[str, Any]]:
            params = {"facultadId": facultad_id} if facultad_id is not None else None
            data = await self._client.get("/mantenedores/listarCarrera", params)
            return [Carrera.model_validate(x).model_dump() for x in data]

        return await self._cached(f"carreras:{facultad_id}", fetch)

    async def facultades(self) -> list[dict[str, Any]]:
        async def fetch() -> list[dict[str, Any]]:
            data = await self._client.get("/mantenedores/listarFacultad")
            return [Facultad.model_validate(x).model_dump() for x in data]

        return await self._cached("facultades", fetch)

    async def estados(self) -> list[dict[str, Any]]:
        async def fetch() -> list[dict[str, Any]]:
            data = await self._client.get("/convocatorias/estado/buscar")
            return [Estado.model_validate(x).model_dump() for x in data]

        return await self._cached("estados", fetch)

    async def fase(self, id_fase: int) -> dict[str, Any]:
        async def fetch() -> dict[str, Any]:
            data = await self._client.get(f"/convocatorias/fases/obtener/{id_fase}")
            return Fase.model_validate(data).model_dump()

        return await self._cached(f"fase:{id_fase}", fetch)

    async def consultar(
        self,
        nombre: str,
        *,
        id_fase: int | None = None,
        facultad_id: int | None = None,
    ) -> Any:
        """Dispatch por nombre de catálogo (respaldo del Resource equivalente)."""
        if nombre == "convocatorias":
            return await self.convocatorias()
        if nombre == "carreras":
            return await self.carreras(facultad_id)
        if nombre == "facultades":
            return await self.facultades()
        if nombre == "estados":
            return await self.estados()
        if nombre == "fases":
            if id_fase is None:
                raise ValueError("Para el catálogo 'fases' indica id_fase.")
            return await self.fase(id_fase)
        raise ValueError(
            f"Catálogo desconocido '{nombre}'. Opciones: {', '.join(_CATALOGOS)}."
        )
