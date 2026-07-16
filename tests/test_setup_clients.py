"""Tests de los adaptadores que registran el MCP en los clientes.

Redirigen las rutas de config a ``tmp_path`` (no tocan los archivos reales) y
verifican que el merge **preserva lo existente**.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from sisav2_mcp.setup_gui import clients, install

EXE = "C:/x/sisav2-mcp.exe"


def test_claude_desktop_merge_preserva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"mcpServers": {"otro": {"command": "x"}}}), encoding="utf-8"
    )
    monkeypatch.setattr(clients, "claude_desktop_config_path", lambda: cfg)
    res = clients.configure_claude_desktop(EXE, ["serve"])
    assert res["estado"] == "ok"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcpServers"]["otro"] == {"command": "x"}  # preservado
    assert data["mcpServers"]["sisav2"] == {"command": EXE, "args": ["serve"]}


def test_claude_desktop_crea_si_no_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "Claude" / "claude_desktop_config.json"
    monkeypatch.setattr(clients, "claude_desktop_config_path", lambda: cfg)
    res = clients.configure_claude_desktop(EXE, ["serve"])
    assert res["estado"] == "ok"
    assert cfg.exists()
    assert "sisav2" in json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]


def test_codex_desktop_merge_preserva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('[mcp_servers.otro]\ncommand = "x"\n', encoding="utf-8")
    monkeypatch.setattr(clients, "codex_config_path", lambda: cfg)
    res = clients.configure_codex_desktop(EXE, ["serve"])
    assert res["estado"] == "ok"
    assert res["cliente"] == "Codex Desktop"
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["mcp_servers"]["otro"]["command"] == "x"  # preservado
    assert data["mcp_servers"]["sisav2"]["command"] == EXE
    assert data["mcp_servers"]["sisav2"]["args"] == ["serve"]


def test_claude_code_fallback_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Forzar el fallback: `claude` no está en el PATH.
    monkeypatch.setattr(clients.shutil, "which", lambda name: None)
    cj = tmp_path / ".claude.json"
    cj.write_text(
        json.dumps({"mcpServers": {"otro": {"command": "x"}}, "extra": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(clients, "claude_json_path", lambda: cj)
    res = clients.configure_claude_code(EXE, ["serve"])
    assert res["estado"] == "ok"
    data = json.loads(cj.read_text(encoding="utf-8"))
    assert data["extra"] == 1  # preserva otras claves del archivo grande
    assert data["mcpServers"]["otro"] == {"command": "x"}
    assert data["mcpServers"]["sisav2"]["command"] == EXE


def test_configure_orquestador(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clients.shutil, "which", lambda name: None)
    monkeypatch.setattr(clients, "claude_json_path", lambda: tmp_path / ".claude.json")
    res = clients.configure(["claude_code", "desconocido"], EXE, ["serve"])
    estados = {r["cliente"]: r["estado"] for r in res}
    assert estados.get("Claude Code") == "ok"
    assert any(r["estado"] == "error" for r in res)  # cliente desconocido


def test_detect_devuelve_flags() -> None:
    det = clients.detect()
    assert set(det) == {
        "claude_code",
        "claude_desktop",
        "codex_desktop",
        "codex_cli",
    }
    assert all(isinstance(v, bool) for v in det.values())


def test_detect_marks_appx_codex_as_desktop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(clients, "_appx_package_installed", lambda _: True)
    monkeypatch.setattr(
        clients, "codex_desktop_executable_path", lambda: Path("C:/missing.exe")
    )
    monkeypatch.setattr(clients.shutil, "which", lambda _: None)

    detected = clients.detect()

    assert detected["codex_desktop"] is True
    assert detected["codex_cli"] is False


def test_detect_marks_known_codex_path_as_desktop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(clients, "_appx_package_installed", lambda _: False)
    monkeypatch.setattr(clients, "codex_desktop_executable_path", lambda: executable)
    monkeypatch.setattr(clients.shutil, "which", lambda _: None)

    detected = clients.detect()

    assert detected["codex_desktop"] is True
    assert detected["codex_cli"] is False


def test_detect_does_not_infer_desktop_from_codex_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clients, "_appx_package_installed", lambda _: False)
    monkeypatch.setattr(
        clients, "codex_desktop_executable_path", lambda: tmp_path / "missing.exe"
    )
    monkeypatch.setattr(clients.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        clients, "codex_config_path", lambda: tmp_path / ".codex" / "config.toml"
    )
    (tmp_path / ".codex").mkdir()

    detected = clients.detect()

    assert detected["codex_desktop"] is False
    assert detected["codex_cli"] is False


def test_detect_classifies_generic_codex_as_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(clients, "_appx_package_installed", lambda _: False)
    monkeypatch.setattr(
        clients, "codex_desktop_executable_path", lambda: Path("C:/missing.exe")
    )
    monkeypatch.setattr(clients.shutil, "which", lambda _: "C:/tools/codex.exe")

    detected = clients.detect()

    assert detected["codex_desktop"] is False
    assert detected["codex_cli"] is True


def test_serve_command_dev() -> None:
    # En desarrollo (no congelado) → python -m sisav2_mcp.app serve.
    command, args = install.serve_command()
    assert args[-1] == "serve"
    assert "sisav2_mcp.app" in args
