"""Detalle de una iniciativa: `GET /convocatorias/postulacion/obtener/{id}`.

El detalle es un *form-builder* genérico: `formulario.formulario[]` son los pasos
del wizard (posicion 1..N) y cada paso tiene un arreglo `json[]` de campos
heterogéneos (text, email, radio, endpoint, checkbox-dependent, ...). Se modela
de forma laxa: lo que importa estable son los metadatos (name/label/type/value).
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import SisavModel


class CampoFormulario(SisavModel):
    """Un campo del formulario. `value`/`options` varían según `type`."""

    name: str
    label: str | None = None
    type: str | None = None
    obligatorio: bool | None = None
    size: int | None = None
    value: Any = None
    options: list[Any] | None = None
    validations: list[Any] | None = None
    dependency: dict[str, Any] | None = None
    isEditable: bool | None = None
    limit: int | None = None


class PasoWizard(SisavModel):
    """Un paso del wizard (bloque). `campos` se parsea de la clave `json`."""

    descripcion: str | None = None
    posicion: int
    tipo: str | None = None
    eliminable: bool | None = None
    campos: list[CampoFormulario] = Field(default_factory=list, alias="json")


class FormularioWizard(SisavModel):
    """Contenedor del formulario (nombre de la convocatoria + pasos)."""

    nombre: str | None = None
    tipo: str | None = None
    formulario: list[PasoWizard] = Field(default_factory=list)


class DetalleIniciativa(SisavModel):
    """Detalle completo de una iniciativa (absorbe la vista *Evaluar admisibilidad*)."""

    id: int
    nombre: str
    fecha: str | None = None
    formulario: FormularioWizard
