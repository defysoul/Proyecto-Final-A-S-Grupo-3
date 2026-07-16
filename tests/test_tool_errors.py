"""Tests del decorador friendly_tool_errors: excepciones → ToolError accionable."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from sisav2_mcp.auth.base import AuthError, CredentialsNotFound, InvalidCredentials
from sisav2_mcp.client.errors import (
    ClientError,
    NetworkTimeout,
    NotFound,
    RateLimited,
    ReadOnlyViolation,
    ServerError,
)
from sisav2_mcp.tools.errors import friendly_tool_errors


def _raise(exc: Exception) -> Callable[[], Awaitable[Any]]:
    @friendly_tool_errors
    async def tool() -> Any:
        raise exc

    return tool


@pytest.mark.parametrize(
    ("exc", "needle"),
    [
        (CredentialsNotFound(), "onboarding"),
        (InvalidCredentials("nope"), "rechazada"),
        (AuthError("boom"), "autenticación"),
        (ReadOnlyViolation("PUT /x"), "read-only"),
        (NotFound("404"), "No encontrado"),
        (RateLimited("429"), "limitando"),
        (NetworkTimeout("slow"), "no respondió"),
        (ServerError("500"), "servidor"),
        (ClientError("weird"), "API SISAV2"),
        (ValueError("modalidad inválida"), "Argumento inválido"),
    ],
)
def test_typed_exceptions_become_tool_error(exc: Exception, needle: str) -> None:
    with pytest.raises(ToolError) as info:
        asyncio.run(_raise(exc)())
    assert needle.lower() in str(info.value).lower()


def test_unexpected_exception_is_wrapped_without_traceback() -> None:
    with pytest.raises(ToolError) as info:
        asyncio.run(_raise(RuntimeError("kaboom"))())
    msg = str(info.value)
    assert "inesperado" in msg.lower()
    assert "RuntimeError" not in msg
    assert "kaboom" not in msg
    assert "Traceback" not in msg


def test_success_passes_through() -> None:
    @friendly_tool_errors
    async def tool(x: int) -> dict[str, int]:
        return {"x": x}

    assert asyncio.run(tool(5)) == {"x": 5}
