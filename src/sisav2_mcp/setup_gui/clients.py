"""Adaptadores que registran el MCP ``sisav2`` en los clientes MCP locales.

Soportados en v1 (todos por **stdio local**): **Claude Code**, **Claude Desktop**,
**Codex CLI**. (ChatGPT Desktop no soporta MCP local; queda para la fase remota.)

Cada ``configure_*`` hace **merge preservando lo existente** y devuelve un dict
``{"cliente", "estado", "detalle"}`` con ``estado`` ∈ {ok, omitido, error}.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

SERVER_NAME = "sisav2"
CODEX_DESKTOP_PACKAGE = "OpenAI.Codex"


# --- rutas de config por cliente -------------------------------------------


def claude_json_path() -> Path:
    """`~/.claude.json` (config de usuario de Claude Code)."""
    return Path.home() / ".claude.json"


def claude_desktop_config_path() -> Path:
    """`%APPDATA%/Claude/claude_desktop_config.json`."""
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def codex_config_path() -> Path:
    """`~/.codex/config.toml`."""
    return Path.home() / ".codex" / "config.toml"


def codex_desktop_executable_path() -> Path:
    """Ruta de instalación por usuario de Codex Desktop en Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA") or str(
        Path.home() / "AppData" / "Local"
    )
    return (
        Path(local_app_data)
        / "Programs"
        / "OpenAI"
        / "Codex"
        / "bin"
        / "codex.exe"
    )


def _appx_package_installed(package_name: str) -> bool:
    """Comprueba un paquete AppX instalado sin modificar el sistema."""
    if os.name != "nt":
        return False
    command = (
        f"Get-AppxPackage -Name '{package_name}' -ErrorAction SilentlyContinue "
        "| Select-Object -First 1 -ExpandProperty PackageFullName"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def is_codex_desktop_installed() -> bool:
    """Detecta Codex Desktop por paquete AppX o ruta de instalación conocida."""
    return (
        _appx_package_installed(CODEX_DESKTOP_PACKAGE)
        or codex_desktop_executable_path().is_file()
    )


def detect() -> dict[str, bool]:
    """Qué clientes parecen instalados (para preseleccionar checkboxes en la GUI)."""
    has_claude = shutil.which("claude") is not None
    has_codex_desktop = is_codex_desktop_installed()
    has_codex_cli = shutil.which("codex") is not None and not has_codex_desktop
    return {
        "claude_code": has_claude or claude_json_path().exists(),
        "claude_desktop": claude_desktop_config_path().parent.exists(),
        "codex_desktop": has_codex_desktop,
        "codex_cli": has_codex_cli,
    }


# --- helpers ----------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _result(cliente: str, estado: str, detalle: str) -> dict[str, str]:
    return {"cliente": cliente, "estado": estado, "detalle": detalle}


# --- Claude Desktop ---------------------------------------------------------


def configure_claude_desktop(command: str, args: list[str]) -> dict[str, str]:
    """Merge en ``claude_desktop_config.json`` → ``mcpServers.sisav2``."""
    path = claude_desktop_config_path()
    data = _load_json(path)
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return _result("Claude Desktop", "error", "mcpServers no es un objeto")
    servers[SERVER_NAME] = {"command": command, "args": args}
    try:
        _write_json(path, data)
    except OSError as exc:
        return _result("Claude Desktop", "error", str(exc))
    return _result("Claude Desktop", "ok", str(path))


# --- Codex ------------------------------------------------------------------


def configure_codex(
    command: str, args: list[str], *, client_label: str = "Codex"
) -> dict[str, str]:
    """Merge en ``~/.codex/config.toml`` → ``[mcp_servers.sisav2]``."""
    import tomllib

    import tomli_w

    path = codex_config_path()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            return _result(client_label, "error", f"config.toml ilegible: {exc}")
    servers = data.setdefault("mcp_servers", {})
    if not isinstance(servers, dict):
        return _result(client_label, "error", "mcp_servers no es una tabla")
    servers[SERVER_NAME] = {"command": command, "args": args}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tomli_w.dumps(data), encoding="utf-8")
    except OSError as exc:
        return _result(client_label, "error", str(exc))
    return _result(client_label, "ok", str(path))


def configure_codex_desktop(command: str, args: list[str]) -> dict[str, str]:
    """Registra el MCP compartido para Codex Desktop."""
    return configure_codex(command, args, client_label="Codex Desktop")


def configure_codex_cli(command: str, args: list[str]) -> dict[str, str]:
    """Registra el MCP compartido para Codex CLI."""
    return configure_codex(command, args, client_label="Codex CLI")


# --- Claude Code ------------------------------------------------------------


def configure_claude_code(command: str, args: list[str]) -> dict[str, str]:
    """Registra en Claude Code vía CLI; si no, edita ``~/.claude.json``."""
    claude = shutil.which("claude")
    if claude:
        # Idempotente: quitar primero (ignorar si no existía), luego agregar.
        try:
            subprocess.run(
                [claude, "mcp", "remove", SERVER_NAME, "-s", "user"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            res = subprocess.run(
                [
                    claude, "mcp", "add", "--scope", "user",
                    SERVER_NAME, "--", command, *args,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return _result("Claude Code", "error", f"CLI claude falló: {exc}")
        if res.returncode == 0:
            return _result("Claude Code", "ok", "claude mcp add (scope user)")
        # si la CLI falló, intentamos el fallback de archivo
    # Fallback: editar ~/.claude.json (merge top-level mcpServers).
    path = claude_json_path()
    data = _load_json(path)
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return _result("Claude Code", "error", "mcpServers no es un objeto")
    servers[SERVER_NAME] = {"type": "stdio", "command": command, "args": args}
    try:
        _write_json(path, data)
    except OSError as exc:
        return _result("Claude Code", "error", str(exc))
    return _result("Claude Code", "ok", str(path))


# --- orquestador ------------------------------------------------------------

_CONFIGURERS = {
    "claude_code": configure_claude_code,
    "claude_desktop": configure_claude_desktop,
    "codex_desktop": configure_codex_desktop,
    "codex_cli": configure_codex_cli,
}


def configure(
    selected: list[str], command: str, args: list[str]
) -> list[dict[str, str]]:
    """Configura los clientes ``selected`` y devuelve la lista de resultados."""
    results: list[dict[str, str]] = []
    for key in selected:
        fn = _CONFIGURERS.get(key)
        if fn is None:
            results.append(_result(key, "error", "cliente desconocido"))
            continue
        results.append(fn(command, args))
    return results
