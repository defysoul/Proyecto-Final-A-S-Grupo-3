"""Tests de previews de escritura: RBAC, contexto y prohibición de mutaciones."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import pytest

from sisav2_mcp.tools import writes

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "discovery" / "samples"


def sample(name: str) -> Any:
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))


def run(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)


class ReadOnlyFakeClient:
    """Cliente mínimo que falla si una preview intenta mutar estado."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.get_calls: list[tuple[str, dict[str, Any] | None]] = []
        self.mutating_calls: list[str] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.get_calls.append((path, params))
        return self.responses[path]

    async def post(self, *args: Any, **kwargs: Any) -> Any:
        self.mutating_calls.append("POST")
        raise AssertionError("Una tool dry-run no debe llamar client.post().")

    async def put(self, *args: Any, **kwargs: Any) -> Any:
        self.mutating_calls.append("PUT")
        raise AssertionError("Una tool dry-run no debe llamar client.put().")


def _assert_preview(result: dict[str, Any]) -> None:
    assert result["modo"] == "dry_run"
    assert result["aplicado"] is False
    assert result["solicitud_mutante_enviada"] is False
    assert result["would_request"]["contrato"] == "no_verificado"
    assert result["would_request"]["verificado"] is False
    assert "DEMO SEGURA" in result["advertencias"][0]


def test_crear_postulacion_is_forced_dry_run_with_rbac() -> None:
    result = run(
        writes.crear_postulacion(
            permisos={"IPOCRE"},
            modalidad="PRE_GRADO",
            convocatoria_id=71,
            titulo="Taller de prueba",
            objetivo="Acercar el conocimiento a la comunidad.",
            campos_extra={"ODS": [4]},
        )
    )

    _assert_preview(result)
    assert result["permiso"]["concedidos"] == ["IPOCRE"]
    assert result["would_request"]["method"] == "POST"
    assert result["would_request"]["path"] == "/convocatorias/postulacion"
    assert result["would_request"]["body"]["campos"]["NOMBRE"] == "Taller de prueba"


def test_crear_postulacion_rejects_missing_permission_before_any_write() -> None:
    with pytest.raises(ValueError, match="Permiso insuficiente"):
        run(
            writes.crear_postulacion(
                permisos={"IPOLIST"},
                modalidad="PRE_GRADO",
                convocatoria_id=71,
                titulo="Taller",
                objetivo="Objetivo válido.",
            )
        )


def test_editar_postulacion_reads_context_and_only_previews_incompleta() -> None:
    bitacora = sample("postulacion_listar-cambios_3033.json")
    bitacora["cambios"][0]["estadoActual"] = "Incompleta"
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            ),
            "/convocatorias/postulacion/listar-cambios": bitacora,
        }
    )

    result = run(
        writes.editar_postulacion(
            client,  # type: ignore[arg-type]
            permisos={"IPOEDI"},
            id_postulacion=3033,
            campos={"NOMBRE": "Charlas actualizadas"},
        )
    )

    _assert_preview(result)
    assert result["would_request"]["method"] == "PUT"
    assert (
        result["diff"]["actualizar"]["NOMBRE"]["antes"]
        == "Charlas Profesionalizantes"
    )
    assert [path for path, _params in client.get_calls] == [
        "/convocatorias/postulacion/obtener/3033",
        "/convocatorias/postulacion/listar-cambios",
    ]
    assert client.mutating_calls == []


def test_editar_postulacion_rejects_non_incompleta_context() -> None:
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            ),
            "/convocatorias/postulacion/listar-cambios": sample(
                "postulacion_listar-cambios_3033.json"
            ),
        }
    )

    with pytest.raises(
        ValueError, match="sólo admite postulaciones en estado Incompleta"
    ):
        run(
            writes.editar_postulacion(
                client,  # type: ignore[arg-type]
                permisos={"IPOEDI"},
                id_postulacion=3033,
                campos={"NOMBRE": "No se aplicará"},
            )
        )
    assert client.mutating_calls == []


def test_evaluar_admisibilidad_uses_read_context_and_observed_permission() -> None:
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            ),
            "/convocatorias/fases/obtener/34": sample(
                "convocatorias_fases_obtener_34.json"
            ),
        }
    )

    result = run(
        writes.evaluar_admisibilidad(
            client,  # type: ignore[arg-type]
            permisos={"AEVADM"},
            id_postulacion=3033,
            modalidad="PRE_GRADO",
            id_fase=34,
            veredicto="admisible",
            comentario="Cumple los antecedentes requeridos.",
        )
    )

    _assert_preview(result)
    assert result["would_request"]["body"]["veredicto"] == "Admisible"
    assert result["would_request"]["body"]["idEstadoDestino"] == 3
    assert client.mutating_calls == []


def test_cambiar_fase_validates_real_phase_transition_without_mutating() -> None:
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            ),
            "/convocatorias/fases/obtener/34": sample(
                "convocatorias_fases_obtener_34.json"
            ),
        }
    )

    result = run(
        writes.cambiar_fase(
            client,  # type: ignore[arg-type]
            permisos={"IPRCES"},
            id_postulacion=3033,
            id_fase=34,
            estado_destino_id=6,
            observacion="Aprobación simulada para la demo.",
        )
    )

    _assert_preview(result)
    assert result["diff"]["cambio_fase"]["estado_destino"] == {
        "id": 6,
        "nombre": "Aprobada",
    }
    assert client.mutating_calls == []


def test_agregar_comentario_bitacora_requires_read_access_and_never_posts() -> None:
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            )
        }
    )

    result = run(
        writes.agregar_comentario_bitacora(
            client,  # type: ignore[arg-type]
            permisos={"IPOVER"},
            id_postulacion=3033,
            texto="Se solicita aclarar el indicador de cobertura.",
        )
    )

    _assert_preview(result)
    assert result["would_request"]["path"].endswith("/3033/comentario")
    assert client.mutating_calls == []


def test_crear_postulacion_espejo_omits_pii_and_career_dependencies() -> None:
    client = ReadOnlyFakeClient(
        {
            "/convocatorias/postulacion/obtener/3033": sample(
                "postulacion_obtener_3033.json"
            )
        }
    )

    result = run(
        writes.crear_postulacion_espejo(
            client,  # type: ignore[arg-type]
            permisos={"IPOCRE"},
            id_origen=3033,
            modalidad_destino="PRE_GRADO",
            convocatoria_destino_id=71,
            carrera_destino_id=31,
            sobrescrituras={"NOMBRE": "Charlas profesionalizantes - nueva carrera"},
        )
    )

    _assert_preview(result)
    campos = result["would_request"]["body"]["campos"]
    assert "ESTANDAR_CORREO" not in campos
    assert "ENCARGADA" not in campos
    assert "Carrera" not in campos
    assert campos["NOMBRE"] == "Charlas profesionalizantes - nueva carrera"
    assert "Carrera" in result["diff"]["espejo"]["campos_omitidos"]
    assert client.mutating_calls == []


def test_cargar_asistencia_normalizes_rows_and_is_only_a_preview() -> None:
    result = run(
        writes.cargar_asistencia(
            permisos={"EACEAC"},
            id_proyecto=2912,
            asistentes=[
                {"rut": "11.111.111-1", "asistencia": True, "fecha": "2026-07-10"},
                {"idPersona": "42", "asistio": False},
            ],
        )
    )

    _assert_preview(result)
    assert result["diff"]["asistencia"] == {
        "idProyecto": 2912,
        "filas": 2,
        "presentes": 1,
        "ausentes": 1,
    }
    assert result["would_request"]["body"]["asistentes"][0] == {
        "identificador": "11***-1",
        "asistio": True,
        "fecha": "2026-07-10",
    }
    assert result["would_request"]["body_redactado"] is True
