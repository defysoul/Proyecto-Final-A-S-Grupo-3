"""Bitácora de cambios: `GET /convocatorias/postulacion/listar-cambios`."""

from __future__ import annotations

from .base import SisavModel


class BitacoraEntry(SisavModel):
    """Una transición de estado registrada en la bitácora.

    `fecha` llega como string de `Date` de JS (no ISO-8601), p.ej.
    "Wed Jun 03 2026 15:34:29 GMT+0000 (Coordinated Universal Time)"; se
    conserva como `str` (no se intenta parsear a `datetime`).
    """

    estadoActual: str | None = None
    estadoAnterior: str | None = None
    fecha: str | None = None
    idPostulacion: int
    observacion: str | None = None
    nombrePostulacion: str | None = None
    nombreUsuario: str | None = None


class BitacoraPage(SisavModel):
    """Respuesta de `listar-cambios` (clave raíz `cambios`)."""

    cambios: list[BitacoraEntry]
