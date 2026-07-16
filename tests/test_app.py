"""Pruebas del entrypoint y preflight semántico sin red real."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sisav2_mcp import app


def _cohort(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "miembros": [
                    {
                        "idPostulacion": 3033,
                        "modalidad": "PRE_GRADO",
                        "facultad": "FING",
                        "anio": 2026,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_load_cohort_accepts_wrapped_members(tmp_path: Path) -> None:
    path = tmp_path / "cohort.json"
    _cohort(path)

    members = app._load_cohort(str(path))

    assert members[0]["idPostulacion"] == 3033


def test_load_cohort_rejects_invalid_shapes(tmp_path: Path) -> None:
    path = tmp_path / "cohort.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="al menos una"):
        app._load_cohort(str(path))


def test_index_demo_dispatches_read_only_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cohort = tmp_path / "cohort.json"
    cache = tmp_path / "cache.json"
    _cohort(cohort)
    calls: dict[str, object] = {}

    async def fake_build(
        members: list[dict[str, object]], *, cache_path: Path, ttl_seconds: int
    ) -> tuple[int, bool, str]:
        calls["members"] = members
        calls["cache"] = cache_path
        calls["ttl"] = ttl_seconds
        return 1, False, "401"

    monkeypatch.setattr(app, "_build_demo_index", fake_build)

    result = app.main(
        ["index-demo", "--cohort", str(cohort), "--cache", str(cache)]
    )

    assert result == 0
    assert calls["cache"] == cache
    assert "índice semántico listo" in capsys.readouterr().out


def test_help_keeps_gui_and_server_out_of_the_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert app.main(["--help"]) == 0
    assert "index-demo" in capsys.readouterr().out
