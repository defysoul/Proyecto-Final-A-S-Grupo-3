"""Enums confirmados de SISAV2."""

from __future__ import annotations

from enum import IntEnum, StrEnum

# Mapeo idEstado -> etiqueta legible (confirmado contra convocatorias/estado/buscar).
_ESTADO_ETIQUETAS: dict[int, str] = {
    1: "Incompleta",
    2: "Ingresada",
    3: "Admisible",
    4: "Pre-Aprobada",
    5: "Agendar",
    6: "Aprobada",
    7: "Rechazada",
    8: "Ejecución",
    9: "No-Realizada",
    10: "Finalizado",
    11: "Reformular",
}


class EstadoId(IntEnum):
    """Estados de una postulación/proyecto (valor = idEstado de la API)."""

    INCOMPLETA = 1
    INGRESADA = 2
    ADMISIBLE = 3
    PRE_APROBADA = 4
    AGENDAR = 5
    APROBADA = 6
    RECHAZADA = 7
    EJECUCION = 8
    NO_REALIZADA = 9
    FINALIZADO = 10
    REFORMULAR = 11

    @property
    def etiqueta(self) -> str:
        """Nombre legible (con tildes/guiones) tal como lo muestra SISAV2."""
        return _ESTADO_ETIQUETAS[self.value]


def etiqueta_estado(id_estado: int) -> str:
    """Etiqueta legible para un idEstado; tolera valores fuera del catálogo."""
    return _ESTADO_ETIQUETAS.get(id_estado, f"Estado {id_estado}")


class Modalidad(StrEnum):
    """Modalidad de la convocatoria/iniciativa."""

    PRE_GRADO = "PRE_GRADO"
    POST_GRADO = "POST_GRADO"
    EXTENSION = "EXTENSION"
