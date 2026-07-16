"""Modelos del análisis semántico de iniciativas.

Los detalles de SISAV2 son formularios dinámicos, por lo que este módulo no
intenta reflejar cada campo del formulario. ``IniciativaSemantica`` es el DTO
normalizado y deliberadamente pequeño que se guarda en el índice local: solo
texto útil para el análisis, nunca los campos de identidad del formulario.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import SisavModel


class MiembroCohorte(SisavModel):
    """Metadatos no sensibles de una iniciativa que se cargará al corpus."""

    id_postulacion: int = Field(alias="idPostulacion", gt=0)
    modalidad: str | None = None
    facultad: str | None = None
    anio: int | None = None


class IniciativaSemantica(SisavModel):
    """Representación saneada de una iniciativa para embeddings y rankings."""

    id_postulacion: int = Field(alias="idPostulacion", gt=0)
    titulo: str
    texto: str
    modalidad: str | None = None
    facultad: str | None = None
    anio: int | None = None
    objetivos: list[str] = Field(default_factory=list)
    necesidades: list[str] = Field(default_factory=list)
    dominios: list[str] = Field(default_factory=list)
    ods: list[str] = Field(default_factory=list)


class MetadatosIndiceSemantico(SisavModel):
    """Datos que permiten invalidar una caché cuando cambia el corpus/modelo."""

    version: int = 1
    creado_en: datetime
    huella_cohorte: str
    encoder: str
    documentos: int
    dimension: int


class CacheIndiceSemantico(SisavModel):
    """Payload serializable de un índice local de embeddings."""

    metadatos: MetadatosIndiceSemantico
    iniciativas: list[IniciativaSemantica]
    embeddings: list[list[float]]


class ResultadoSimilar(SisavModel):
    """Una coincidencia ordenada por similitud coseno descendente."""

    id_postulacion: int = Field(alias="idPostulacion")
    titulo: str
    similitud: float
    modalidad: str | None = None
    facultad: str | None = None
    ods: list[str] = Field(default_factory=list)
    dominios: list[str] = Field(default_factory=list)


class ParDuplicado(SisavModel):
    """Posible par duplicado encontrado dentro de la cohorte."""

    izquierda: ResultadoSimilar
    derecha: ResultadoSimilar
    similitud: float
