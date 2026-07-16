"""Ventana pywebview del instalador + API expuesta al JavaScript de la vista.

La vista (``web/index.html``) llama a estos métodos vía ``window.pywebview.api``:
- ``verificar(usuario, clave)`` → login ROPC real + ``verifica-token``; si OK guarda
  la credencial en el keychain. Reusa exactamente el camino del onboarding CLI.
- ``detectar()`` → qué clientes MCP están instalados.
- ``configurar(seleccion)`` → registra el MCP en los clientes elegidos.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..auth import store_credentials
from ..auth.base import AuthError, InvalidCredentials
from ..auth.ropc import RopcTokenProvider
from ..config import Settings
from . import clients, install


class _MemoryStore:
    """``CredentialStore`` en memoria: verifica ANTES de guardar en el keychain."""

    def __init__(self, username: str, password: str) -> None:
        self._u = username
        self._p = password

    def load(self) -> tuple[str, str] | None:
        return (self._u, self._p)

    def save(self, username: str, password: str) -> None:
        self._u, self._p = username, password

    def clear(self) -> None:
        self._u = self._p = ""


class SetupApi:
    """API llamable desde el JS (vía ``window.pywebview.api``)."""

    def __init__(self) -> None:
        self._window: Any = None

    def verificar(self, usuario: str, clave: str) -> dict[str, Any]:
        """Verifica la credencial UTEM; si es válida, la guarda en el keychain."""
        usuario = (usuario or "").strip()
        clave = clave or ""
        if not usuario or not clave:
            return {"ok": False, "error": "Ingresa usuario y clave."}
        settings = Settings.from_env()
        provider = RopcTokenProvider(settings, _MemoryStore(usuario, clave))
        try:
            user = asyncio.run(provider.verifica_token())
        except InvalidCredentials:
            return {"ok": False, "error": "Usuario o clave incorrectos."}
        except AuthError as exc:
            return {
                "ok": False,
                "error": (
                    f"No se pudo contactar a UTEM ({exc}). "
                    "¿Estás en la red/VPN UTEM?"
                ),
            }
        except Exception as exc:
            # Cualquier otro error: feedback a la UI, sin tumbar la ventana.
            return {"ok": False, "error": f"Error inesperado: {exc}"}
        store_credentials(settings, usuario, clave)
        return {
            "ok": True,
            "nombre": user.nombre,
            "id": user.id,
            "permisos": len(user.permisos_nomenclaturas),
        }

    def detectar(self) -> dict[str, bool]:
        """Qué clientes MCP parecen instalados (para preseleccionar)."""
        return clients.detect()

    def configurar(self, seleccion: list[str]) -> dict[str, Any]:
        """Registra el MCP en los clientes seleccionados; devuelve el resumen."""
        command, args = install.serve_command()
        resultados = clients.configure(list(seleccion or []), command, args)
        return {"command": command, "args": args, "resultados": resultados}

    def salir(self) -> None:
        """Cierra la ventana."""
        if self._window is not None:
            self._window.destroy()


def run_setup() -> None:
    """Abre la ventana de configuración (bloquea hasta que se cierra)."""
    import webview

    api = SetupApi()
    index = Path(__file__).parent / "web" / "index.html"
    window = webview.create_window(
        "SISAV2 MCP — Configuración",
        url=index.resolve().as_uri(),
        js_api=api,
        width=600,
        height=680,
        resizable=True,
    )
    api._window = window
    webview.start()
