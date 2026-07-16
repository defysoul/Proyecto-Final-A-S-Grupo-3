"""Tests del cliente HTTP con respx.

Cubren: inyección de bearer + parseo, paginación offset/limit, guardia
read-only (GET ok, POST/PUT fuera de allowlist rechazados, export POST sí pasa),
mapeo de cada error tipado y reintentos con backoff (sleeper mockeado).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest
import respx

from sisav2_mcp.auth.base import TokenProvider
from sisav2_mcp.client import (
    EXPORT_PATH,
    AuthError,
    ClientError,
    NetworkTimeout,
    NotFound,
    RateLimited,
    ReadOnlyViolation,
    ServerError,
    SisavClient,
    ensure_read_only,
)
from sisav2_mcp.config import Settings

SETTINGS = Settings()
API = SETTINGS.api_base_url


class FakeProvider(TokenProvider):
    def __init__(self, token: str = "TESTTOKEN") -> None:
        self._token = token

    async def get_access_token(self) -> str:
        return self._token


async def _no_sleep(_: float) -> None:
    return None


def run_with_client(
    scenario: Callable[[SisavClient], Awaitable[Any]],
    *,
    max_retries: int = 0,
) -> Any:
    """Ejecuta `scenario` con un SisavClient abierto/cerrado en un único loop."""

    async def main() -> Any:
        async with SisavClient(
            SETTINGS, FakeProvider(), max_retries=max_retries, sleeper=_no_sleep
        ) as client:
            return await scenario(client)

    return asyncio.run(main())


# --- bearer + parseo -------------------------------------------------------


def test_get_injects_bearer_and_parses() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/foo").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        result = run_with_client(lambda c: c.get("/foo"))

    assert result == {"ok": True}
    assert route.calls.last.request.headers["Authorization"] == "Bearer TESTTOKEN"


# --- paginación ------------------------------------------------------------


def test_pagination_iterates_offset_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        if offset == 0:
            return httpx.Response(200, json={"data": [1, 2], "total": 3})
        return httpx.Response(200, json={"data": [3], "total": 3})

    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/proyectos/listar").mock(side_effect=handler)
        items = run_with_client(
            lambda c: c.get_paginated(
                "/proyectos/listar", items_key="data", page_size=2
            )
        )

    assert items == [1, 2, 3]
    assert route.call_count == 2


# --- guardia read-only -----------------------------------------------------


def test_ensure_read_only_allows_get_and_export() -> None:
    ensure_read_only("GET", "/cualquier/cosa")
    ensure_read_only("POST", EXPORT_PATH)  # allowlisted, no lanza


def test_ensure_read_only_rejects_writes() -> None:
    for method, path in [("POST", "/otro/path"), ("PUT", "/x"), ("DELETE", "/y")]:
        with pytest.raises(ReadOnlyViolation):
            ensure_read_only(method, path)


def test_post_outside_allowlist_raises_before_network() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(f"{API}/otro/path").mock(
            return_value=httpx.Response(200, json={})
        )
        with pytest.raises(ReadOnlyViolation):
            run_with_client(lambda c: c.post("/otro/path", {"a": 1}))
    assert route.call_count == 0  # nunca tocó la red


def test_export_post_allowlisted_passes() -> None:
    body = {"url": "https://s3/export.xlsx", "total": 88, "nombreArchivo": "x.xlsx"}
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(f"{API}{EXPORT_PATH}").mock(
            return_value=httpx.Response(200, json=body)
        )
        result = run_with_client(
            lambda c: c.post(EXPORT_PATH, {"convocatoriaId": 71})
        )

    assert result["total"] == 88
    assert route.call_count == 1


# --- mapeo de errores ------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, AuthError),
        (404, NotFound),
        (429, RateLimited),
        (500, ServerError),
        (400, ClientError),
    ],
)
def test_status_maps_to_typed_error(status: int, expected: type[Exception]) -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/bar").mock(return_value=httpx.Response(status, json={}))
        with pytest.raises(expected):
            run_with_client(lambda c: c.get("/bar"), max_retries=0)


def test_retries_then_succeeds_on_503() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"ok": True})

    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/flaky").mock(side_effect=handler)
        result = run_with_client(lambda c: c.get("/flaky"), max_retries=2)

    assert result == {"ok": True}
    assert calls["n"] == 2


def test_timeout_retries_then_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(f"{API}/slow").mock(side_effect=handler)
        with pytest.raises(NetworkTimeout):
            run_with_client(lambda c: c.get("/slow"), max_retries=2)

    assert route.call_count == 3  # intento inicial + 2 reintentos


def test_rate_limited_respects_retry_after_then_raises() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{API}/limited").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "1"}, json={})
        )
        with pytest.raises(RateLimited) as excinfo:
            run_with_client(lambda c: c.get("/limited"), max_retries=1)

    assert excinfo.value.retry_after == 1.0
