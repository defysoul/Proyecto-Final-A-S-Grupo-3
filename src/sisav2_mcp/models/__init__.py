"""Modelos pydantic (Paso 3): derivados de los 17 samples de Fase 0."""

from __future__ import annotations

from .analysis import (
    CacheIndiceSemantico,
    IniciativaSemantica,
    MetadatosIndiceSemantico,
    MiembroCohorte,
    ParDuplicado,
    ResultadoSimilar,
)
from .base import SisavModel
from .bitacora import BitacoraEntry, BitacoraPage
from .catalogo import (
    Carrera,
    CategoriaConRepositorios,
    CategoriaRepositorio,
    Convocatoria,
    Estado,
    Facultad,
    Repositorio,
    RepositoriosResponse,
)
from .detalle import CampoFormulario, DetalleIniciativa, FormularioWizard, PasoWizard
from .enums import EstadoId, Modalidad, etiqueta_estado
from .fase import EstadoRef, Fase, FaseConvocatoria, FaseEstadoRol, RolRef
from .postulacion import Postulacion, PostulacionesPage, Proyecto, ProyectosPage
from .reportes import AvanceGlobalKPIs, ExportResult, Indicador
from .usuario import Perfil, Permiso, Rol, UnidadRef, Usuario
from .writes import (
    Asistente,
    CambiarFaseInput,
    CargarAsistenciaInput,
    ComentarioBitacoraInput,
    CrearPostulacionEspejoInput,
    CrearPostulacionInput,
    DryRunPreview,
    EditarPostulacionInput,
    EvaluarAdmisibilidadInput,
    VeredictoAdmisibilidad,
)

__all__ = [
    "SisavModel",
    # análisis semántico
    "MiembroCohorte",
    "IniciativaSemantica",
    "MetadatosIndiceSemantico",
    "CacheIndiceSemantico",
    "ResultadoSimilar",
    "ParDuplicado",
    # enums
    "EstadoId",
    "Modalidad",
    "etiqueta_estado",
    # postulaciones / proyectos
    "Postulacion",
    "PostulacionesPage",
    "Proyecto",
    "ProyectosPage",
    # detalle (form-builder)
    "CampoFormulario",
    "PasoWizard",
    "FormularioWizard",
    "DetalleIniciativa",
    # fase
    "RolRef",
    "EstadoRef",
    "FaseEstadoRol",
    "FaseConvocatoria",
    "Fase",
    # bitácora
    "BitacoraEntry",
    "BitacoraPage",
    # reportes
    "Indicador",
    "AvanceGlobalKPIs",
    "ExportResult",
    # catálogos
    "Convocatoria",
    "Carrera",
    "Facultad",
    "Estado",
    "Repositorio",
    "CategoriaRepositorio",
    "CategoriaConRepositorios",
    "RepositoriosResponse",
    # usuario / RBAC
    "Permiso",
    "Rol",
    "Perfil",
    "UnidadRef",
    "Usuario",
    # escritura dry-run
    "CrearPostulacionInput",
    "EditarPostulacionInput",
    "EvaluarAdmisibilidadInput",
    "CambiarFaseInput",
    "ComentarioBitacoraInput",
    "CrearPostulacionEspejoInput",
    "Asistente",
    "CargarAsistenciaInput",
    "VeredictoAdmisibilidad",
    "DryRunPreview",
]
