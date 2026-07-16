"""Fase de proyecto: `GET /convocatorias/fases/obtener/{id}`."""

from __future__ import annotations

from typing import Any

from .base import SisavModel


class RolRef(SisavModel):
    """Referencia mínima a un rol."""

    id: int
    nombre: str
    estado: bool | None = None


class EstadoRef(SisavModel):
    """Referencia mínima a un estado (con orden)."""

    id: int
    nombre: str
    orden: int | None = None


class FaseEstadoRol(SisavModel):
    """Transición estado↔rol dentro de una fase."""

    id: int
    idFase: int | None = None
    idEstado: int | None = None
    idRol: int | None = None
    rol: RolRef | None = None
    estado: EstadoRef | None = None


class FaseConvocatoria(SisavModel):
    """Convocatoria asociada a la fase."""

    id: int
    nombre: str
    publicacion: str | None = None
    estado: bool | None = None


class Fase(SisavModel):
    """Definición de una fase de proyecto."""

    id: int
    nombre: str
    activo: bool | None = None
    siempreVisible: bool | None = None
    rolEvalua: int | None = None
    estadoPostulacion: list[FaseEstadoRol] = []
    plantillas: dict[str, int] | None = None
    calendarizacion: list[Any] = []
    convocatorias: list[FaseConvocatoria] = []
    # `formulario` puede venir como "" (str) o como objeto; se deja crudo.
    formulario: Any = None
