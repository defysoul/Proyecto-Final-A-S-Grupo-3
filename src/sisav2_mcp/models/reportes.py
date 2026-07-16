"""Modelos de reportes: indicadores, KPIs de avance global y export."""

from __future__ import annotations

from .base import SisavModel


class Indicador(SisavModel):
    """Conteo por estado: `[{id: idEstado, total}]`.

    `total` llega como string en la API (p.ej. "1199"); se coacciona a `int`.
    """

    id: int
    total: int


class AvanceGlobalKPIs(SisavModel):
    """KPIs de `GET /proyectos/estadisticas/globales-proyectos` (solo KPIs)."""

    totalProyectos: int
    totalObjetivosEspecificos: int
    totalHitos: int
    totalActividades: int
    totalPresupuesto: int


class ExportResult(SisavModel):
    """Resultado de `POST .../postulacion/exportar-excel`.

    v1 devuelve la URL S3 prefirmada (expira ~900s) + total + nombre de archivo,
    NO los datos. La URL no se versiona ni se persiste.
    """

    url: str
    total: int
    nombreArchivo: str
