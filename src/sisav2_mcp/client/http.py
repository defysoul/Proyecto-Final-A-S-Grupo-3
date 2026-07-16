"""Cliente HTTP de SISAV2: read-only, con bearer, paginación y reintentos.

Guardia read-only: solo se permite ``GET``, salvo una allowlist explícita de
pares ``(método, path)``. El único par sancionado es el export, que es un POST
*de lectura* (no muta estado; devuelve una URL prefirmada).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ..auth.base import TokenProvider
from ..config import Settings
from .errors import (
    AuthError,
    ClientError,
    NetworkTimeout,
    NotFound,
    RateLimited,
    ReadOnlyViolation,
    ServerError,
)

logger = logging.getLogger("sisav2_mcp.client")

# Único POST permitido (lectura): devuelve una URL S3 prefirmada, no muta nada.
EXPORT_PATH = "/convocatorias/postulacion/exportar-excel"
WRITE_ALLOWLIST: frozenset[tuple[str, str]] = frozenset({("POST", EXPORT_PATH)})

_DEFAULT_PAGE_SIZE = 100


def _normalize_path(path: str) -> str:
    """Normaliza un path para comparar contra la allowlist (sin query/trailing)."""
    path = path.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def ensure_read_only(method: str, path: str) -> None:
    """Rechaza cualquier método ≠ GET que no esté en la allowlist explícita."""
    method = method.upper()
    if method == "GET":
        return
    if (method, _normalize_path(path)) in WRITE_ALLOWLIST:
        return
    raise ReadOnlyViolation(
        f"{method} {path} está bloqueado: el cliente SISAV2 es de solo lectura "
        f"(allowlist: {sorted(WRITE_ALLOWLIST)})."
    )


class SisavClient:
    """Cliente asíncrono read-only sobre la API de SISAV2."""

    def __init__(
        self,
        settings: Settings,
        token_provider: TokenProvider,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleeper = sleeper
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url, timeout=httpx.Timeout(timeout)
        )

    async def __aenter__(self) -> SisavClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- API pública -------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET tipado: devuelve el JSON parseado o lanza un error de cliente."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json_body: dict[str, Any] | None = None) -> Any:
        """POST (solo allowlisted): devuelve el JSON parseado."""
        return await self._request("POST", path, json=json_body)

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        items_key: str,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_items: int | None = None,
    ) -> list[Any]:
        """Itera offset/limit acumulando ``items_key`` hasta agotar o ``max_items``."""
        collected: list[Any] = []
        base_params = dict(params or {})
        offset = int(base_params.get("offset", 0))
        while True:
            page_params = {**base_params, "offset": offset, "limit": page_size}
            payload = await self.get(path, page_params)
            if isinstance(payload, dict):
                items = payload.get(items_key, [])
                total = payload.get("total")
            else:
                items, total = payload, None
            collected.extend(items)
            offset += page_size
            if max_items is not None and len(collected) >= max_items:
                logger.debug(
                    "get_paginated %s truncado a max_items=%d", path, max_items
                )
                return collected[:max_items]
            if not items or len(items) < page_size:
                break
            if total is not None and len(collected) >= int(total):
                break
        return collected

    # --- internos ----------------------------------------------------------

    def _backoff(self, attempt: int) -> float:
        return self._backoff_base * (2**attempt)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        ensure_read_only(method, path)
        for attempt in range(self._max_retries + 1):
            last_attempt = attempt == self._max_retries
            token = await self._token_provider.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = await self._client.request(
                    method, path, params=params, json=json, headers=headers
                )
            except httpx.TimeoutException as exc:
                if last_attempt:
                    raise NetworkTimeout(f"Timeout en {method} {path}: {exc}") from exc
                await self._sleeper(self._backoff(attempt))
                continue
            except httpx.HTTPError as exc:
                raise ClientError(f"Error de red en {method} {path}: {exc}") from exc

            status = resp.status_code
            if status < 400:
                return self._parse(resp)
            if status == 401:
                raise AuthError("La API devolvió 401 (token inválido o expirado).")
            if status == 404:
                raise NotFound(f"{method} {path} → 404.")
            if status == 429:
                retry_after = _retry_after_seconds(resp)
                if last_attempt:
                    raise RateLimited("429 Too Many Requests.", retry_after=retry_after)
                await self._sleeper(
                    retry_after if retry_after is not None else self._backoff(attempt)
                )
                continue
            if status >= 500:
                if last_attempt:
                    raise ServerError(f"{method} {path} → {status}.")
                await self._sleeper(self._backoff(attempt))
                continue
            raise ClientError(f"{method} {path} → {status}.")
        # El bucle siempre retorna o lanza dentro; esto es inalcanzable.
        raise ClientError(f"{method} {path}: reintentos agotados.")

    @staticmethod
    def _parse(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except ValueError as exc:
            raise ClientError(f"Respuesta no-JSON ({resp.status_code}).") from exc


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
