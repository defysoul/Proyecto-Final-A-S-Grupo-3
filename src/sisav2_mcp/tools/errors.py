"""Traducción de excepciones tipadas a mensajes accionables para Claude.

Las tools no deben filtrar stack traces al cliente MCP: este decorador convierte
los errores conocidos (auth, cliente HTTP, validación) en ``ToolError`` con un
mensaje claro y orientado a la acción. Lo inesperado se loguea (con traza) a
stderr y se devuelve como un mensaje genérico, sin traza.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastmcp.exceptions import ToolError

from ..auth.base import AuthError, CredentialsNotFound, InvalidCredentials
from ..client.errors import (
    ClientError,
    NetworkTimeout,
    NotFound,
    RateLimited,
    ReadOnlyViolation,
    ServerError,
)

logger = logging.getLogger("sisav2_mcp.tools")

_ONBOARDING_HINT = "Re-ejecuta el onboarding: python -m sisav2_mcp.onboarding"


def friendly_tool_errors(
    fn: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Envuelve una tool async traduciendo excepciones a ``ToolError`` accionable."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except CredentialsNotFound as exc:
            raise ToolError(str(exc)) from exc
        except InvalidCredentials as exc:
            raise ToolError(f"Credencial UTEM rechazada. {_ONBOARDING_HINT}") from exc
        except AuthError as exc:
            raise ToolError(
                f"Problema de autenticación: {exc}. Reintenta; si persiste, "
                f"{_ONBOARDING_HINT.lower()}"
            ) from exc
        except ReadOnlyViolation as exc:
            raise ToolError(
                f"Operación no permitida (servidor read-only): {exc}"
            ) from exc
        except NotFound as exc:
            raise ToolError(f"No encontrado: {exc}") from exc
        except RateLimited as exc:
            raise ToolError(
                f"La API está limitando solicitudes: {exc}. Reintenta en unos segundos."
            ) from exc
        except NetworkTimeout as exc:
            raise ToolError(f"La API no respondió a tiempo: {exc}. Reintenta.") from exc
        except ServerError as exc:
            raise ToolError(
                f"Error del servidor SISAV2: {exc}. Reintenta más tarde."
            ) from exc
        except ClientError as exc:
            raise ToolError(f"Error de la API SISAV2: {exc}") from exc
        except ValueError as exc:
            raise ToolError(f"Argumento inválido: {exc}") from exc
        except ToolError:
            raise
        except Exception as exc:
            logger.exception("Error inesperado en %s", getattr(fn, "__name__", "tool"))
            # Los detalles quedan en stderr para diagnóstico, no en la
            # conversación del usuario: pueden contener rutas, payloads o PII.
            raise ToolError(
                "Error inesperado al procesar la operación. Reintenta; si "
                "persiste, revisa los logs del MCP."
            ) from exc

    return wrapper
