"""Ubicación de instalación y comando de arranque del servidor.

Resuelve **qué comando** se registra en los clientes para lanzar el MCP por stdio:

- **Empaquetado (.exe):** copia el ejecutable a un *hogar estable*
  ``%LOCALAPPDATA%\\sisav2-mcp\\sisav2-mcp.exe`` (así borrar la descarga no rompe la
  configuración) y registra ``"<hogar>\\sisav2-mcp.exe" serve``.
- **Desarrollo (python -m):** registra ``<python> -m sisav2_mcp.app serve``.

La credencial NO se guarda aquí: vive en el keychain del SO (ver ``auth``).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "sisav2-mcp"
EXE_NAME = "sisav2-mcp.exe"


def is_frozen() -> bool:
    """True si corremos como ejecutable PyInstaller (no como ``python -m``)."""
    return bool(getattr(sys, "frozen", False))


def install_home() -> Path:
    """Carpeta-hogar estable del instalador: ``%LOCALAPPDATA%\\sisav2-mcp``."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    home = Path(base) / APP_DIR_NAME
    home.mkdir(parents=True, exist_ok=True)
    return home


def ensure_installed_exe() -> Path | None:
    """Copia el .exe en ejecución al hogar estable y devuelve esa ruta.

    Devuelve ``None`` en modo desarrollo (no hay un único ejecutable).
    """
    if not is_frozen():
        return None
    src = Path(sys.executable).resolve()
    dst = (install_home() / EXE_NAME).resolve()
    if src == dst:
        return dst  # ya estamos corriendo desde el hogar
    try:
        shutil.copy2(src, dst)
    except OSError:
        return src  # no se pudo copiar: usar donde está
    return dst


def serve_command() -> tuple[str, list[str]]:
    """``(command, args)`` a registrar en los clientes para arrancar el MCP (stdio)."""
    exe = ensure_installed_exe()
    if exe is not None:
        return (str(exe), ["serve"])
    # Desarrollo: usa el intérprete actual del venv.
    return (sys.executable, ["-m", "sisav2_mcp.app", "serve"])
