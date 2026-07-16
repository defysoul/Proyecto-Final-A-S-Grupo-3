"""Postulaciones e iniciativas en ejecución (Proyectos).

`Proyecto` NO es `Postulacion`: vive en `/proyectos/listar`, tiene `id` propio
(≠ `idpostulacion`), su payload usa la clave raíz `data` (no `postulaciones`) y
sus estados típicos son 8 (Ejecución) / 10 (Finalizado).
"""

from __future__ import annotations

from .base import SisavModel


class Postulacion(SisavModel):
    """Fila de `GET /convocatorias/postulacion/buscar`."""

    idpostulacion: int
    # SISAV2 devuelve ``null`` en algunas postulaciones Incompletas. La fila
    # sigue siendo útil para que el analista la encuentre y la complete, por
    # lo que el nombre no puede invalidar toda la página.
    nombrepostulacion: str | None = None
    encargado: str | None = None
    carreraformulario: str | None = None
    facultadformulario: str | None = None
    idconvocatoria: int | None = None
    nombreconvocatoria: str | None = None
    idestado: int
    nombreestado: str | None = None
    anioInicioConvocatoria: int | None = None
    fecha: str | None = None


class PostulacionesPage(SisavModel):
    """Respuesta paginada de `postulacion/buscar`."""

    postulaciones: list[Postulacion]
    total: int


class Proyecto(SisavModel):
    """Fila de `GET /proyectos/listar` (Ejecución/Seguimiento)."""

    id: int
    idpostulacion: int
    nombrepostulacion: str | None = None
    encargado: str | None = None
    nombrefacultad: str | None = None
    idconvocatoria: int | None = None
    nombreconvocatoria: str | None = None
    idestado: int
    nombreestado: str | None = None
    carreraformulario: str | None = None
    facultadformulario: str | None = None


class ProyectosPage(SisavModel):
    """Respuesta paginada de `proyectos/listar` (clave raíz `data`)."""

    data: list[Proyecto]
    total: int
