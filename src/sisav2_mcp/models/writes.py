"""Modelos de entrada y salida para las tools de escritura en *dry-run*.

Los endpoints mutantes de SISAV2 no se han validado contra el sistema real. Por
ello estos modelos describen la intención de escritura que se mostraría durante
la demo, no un contrato confirmado de la API. Ningún modelo habilita un modo de
``commit``.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import AliasChoices, ConfigDict, Field, field_validator

from .base import SisavModel
from .enums import Modalidad


class WriteInput(SisavModel):
    """Base estricta para entradas de intención de escritura."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _texto_no_vacio(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("no puede estar vacío.")
    return value


def _campos_no_vacios(value: dict[str, Any]) -> dict[str, Any]:
    if not value:
        raise ValueError("debe incluir al menos un campo.")
    if any(not str(key).strip() for key in value):
        raise ValueError("los nombres de campo no pueden estar vacíos.")
    return value


class CrearPostulacionInput(WriteInput):
    modalidad: Modalidad
    convocatoria_id: int = Field(gt=0)
    titulo: str = Field(min_length=1, max_length=500)
    objetivo: str = Field(min_length=1, max_length=10_000)
    campos_extra: dict[str, Any] = Field(default_factory=dict)

    _titulo_no_vacio = field_validator("titulo")(_texto_no_vacio)
    _objetivo_no_vacio = field_validator("objetivo")(_texto_no_vacio)

    @field_validator("campos_extra")
    @classmethod
    def _nombres_de_campos_validos(cls, value: dict[str, Any]) -> dict[str, Any]:
        if any(not str(key).strip() for key in value):
            raise ValueError("los nombres de campos_extra no pueden estar vacíos.")
        return value


class EditarPostulacionInput(WriteInput):
    id_postulacion: int = Field(gt=0)
    campos: dict[str, Any]

    _campos_validos = field_validator("campos")(_campos_no_vacios)


class VeredictoAdmisibilidad(StrEnum):
    """Veredictos expuestos por la demo de admisibilidad."""

    ADMISIBLE = "Admisible"
    REFORMULAR = "Reformular"
    RECHAZAR = "Rechazar"


class EvaluarAdmisibilidadInput(WriteInput):
    id_postulacion: int = Field(gt=0)
    modalidad: Modalidad
    id_fase: int = Field(gt=0)
    veredicto: VeredictoAdmisibilidad
    comentario: str = Field(min_length=1, max_length=10_000)

    _comentario_no_vacio = field_validator("comentario")(_texto_no_vacio)

    @field_validator("veredicto", mode="before")
    @classmethod
    def _normalizar_veredicto(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().capitalize()
        return value


class CambiarFaseInput(WriteInput):
    id_postulacion: int = Field(gt=0)
    id_fase: int = Field(gt=0)
    estado_destino_id: int = Field(gt=0)
    observacion: str = Field(min_length=1, max_length=10_000)

    _observacion_no_vacia = field_validator("observacion")(_texto_no_vacio)


class ComentarioBitacoraInput(WriteInput):
    id_postulacion: int = Field(gt=0)
    texto: str = Field(min_length=1, max_length=10_000)

    _texto_valido = field_validator("texto")(_texto_no_vacio)


class CrearPostulacionEspejoInput(WriteInput):
    id_origen: int = Field(gt=0)
    modalidad_destino: Modalidad
    convocatoria_destino_id: int = Field(gt=0)
    carrera_destino_id: int = Field(gt=0)
    sobrescrituras: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sobrescrituras")
    @classmethod
    def _sobrescrituras_validas(cls, value: dict[str, Any]) -> dict[str, Any]:
        if any(not str(key).strip() for key in value):
            raise ValueError("los nombres de sobrescrituras no pueden estar vacíos.")
        return value


class Asistente(WriteInput):
    """Una fila normalizada de asistencia para carga masiva.

    ``rut``, ``email`` e ``idPersona`` se aceptan como alias de
    ``identificador``; la salida siempre usa el nombre neutro para no fijar un
    contrato de identidad aún no validado.
    """

    identificador: str = Field(
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("identificador", "rut", "email", "idPersona"),
    )
    asistio: bool = Field(validation_alias=AliasChoices("asistio", "asistencia"))
    fecha: date | None = None
    nombre: str | None = Field(default=None, max_length=500)

    _identificador_valido = field_validator("identificador")(_texto_no_vacio)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, value: str | None) -> str | None:
        return _texto_no_vacio(value) if value is not None else None


class CargarAsistenciaInput(WriteInput):
    id_proyecto: int = Field(gt=0)
    asistentes: list[Asistente] = Field(min_length=1, max_length=1_000)


class PermisoEvaluado(SisavModel):
    """Resultado del RBAC local incluido en cada preview."""

    autorizado: Literal[True] = True
    requeridos: list[str]
    concedidos: list[str]


class ValidacionPreview(SisavModel):
    """Una validación local o de contexto mostrada en la demo."""

    regla: str
    resultado: Literal["ok", "advertencia"] = "ok"
    detalle: str


class WouldRequest(SisavModel):
    """Solicitud mutante hipotética; el endpoint no está verificado."""

    method: Literal["POST", "PUT"]
    path: str
    endpoint_esperado: str
    body: dict[str, Any]
    body_redactado: bool = False
    contrato: Literal["no_verificado"] = "no_verificado"
    verificado: Literal[False] = False
    nota: str = (
        "Contrato esperado para demo; no fue validado contra endpoints mutantes "
        "de SISAV2. No se envió ninguna solicitud."
    )


class DryRunPreview(SisavModel):
    """Salida uniforme y no aplicable de una operación de escritura."""

    modo: Literal["dry_run"] = "dry_run"
    aplicado: Literal[False] = False
    solicitud_mutante_enviada: Literal[False] = False
    operacion: str
    permiso: PermisoEvaluado
    validaciones: list[ValidacionPreview]
    advertencias: list[str] = Field(default_factory=list)
    diff: dict[str, Any]
    efecto_previsto: str
    would_request: WouldRequest


_COMMIT_ADVERTENCIA = (
    "COMMIT SIMULADO: se aplicó contra un backend mock en memoria; SISAV2 real "
    "no fue modificado."
)


class CommitResult(SisavModel):
    """Resultado de aplicar una intención de escritura contra el backend mock.

    Es el otro extremo del patrón dry-run -> commit. ``sisav2_real_modificado``
    es ``Literal[False]`` por tipo: incluso al confirmar, SISAV2 real nunca se
    toca; el efecto se aplica y se relee (``read_back``) desde un simulador local.
    """

    modo: Literal["commit_mock"] = "commit_mock"
    aplicado: Literal[True] = True
    backend: Literal["mock"] = "mock"
    sisav2_real_modificado: Literal[False] = False
    operacion: str
    permiso: PermisoEvaluado
    request_id: str
    entidad_id: str
    diff: dict[str, Any]
    efecto_aplicado: str
    read_back: dict[str, Any]
    advertencias: list[str] = Field(default_factory=lambda: [_COMMIT_ADVERTENCIA])
