"""Catálogos: convocatorias, carreras, facultades, estados y repositorios."""

from __future__ import annotations

from .base import SisavModel


class Convocatoria(SisavModel):
    """`GET /convocatorias/listar-combo` → `[{id, nombre}]`."""

    id: int
    nombre: str


class Carrera(SisavModel):
    """`GET /mantenedores/listarCarrera`. `facultadId` puede ser null."""

    id: int
    nombre: str
    codigo: int | None = None
    facultadId: int | None = None


class Facultad(SisavModel):
    """`GET /mantenedores/listarFacultad`. `idUnidad` puede ser null."""

    id: int
    nombre: str
    sigla: str | None = None
    campus: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    idUnidad: int | None = None


class Estado(SisavModel):
    """`GET /convocatorias/estado/buscar` → `[{id, nombre, orden}]`."""

    id: int
    nombre: str
    orden: int | None = None


class Repositorio(SisavModel):
    """Repositorio dentro de una categoría (`/mantenedores/repositorios`)."""

    id: int
    nombre: str
    descripcion: str | None = None
    categoriaRepositorioId: int | None = None
    esPublico: bool | None = None
    tiposArchivosPermitidos: list[str] = []
    cantidadMaximaArchivos: int | None = None
    vigencia: bool | None = None
    roles: list[int] = []


class CategoriaRepositorio(SisavModel):
    """Categoría de repositorios."""

    id: int
    nombre: str
    bucket: str | None = None
    path: str | None = None
    vista: str | None = None
    orden: int | None = None
    vigencia: bool | None = None


class CategoriaConRepositorios(SisavModel):
    """Agrupación `{categoria, repositorios[]}` del endpoint de repositorios."""

    categoria: CategoriaRepositorio
    repositorios: list[Repositorio] = []


class RepositoriosResponse(SisavModel):
    """Respuesta de `GET /mantenedores/repositorios` (`{success, data[]}`)."""

    success: bool | None = None
    data: list[CategoriaConRepositorios] = []
