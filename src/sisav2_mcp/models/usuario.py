"""Identidad y permisos del usuario: `GET /usuarios/verifica-token`.

Los roles de aplicación NO están en el JWT; se resuelven aquí. `perfil.roles[]`
agrega los permisos (cada uno con `nomenclatura`, p.ej. "IPOLIST"), que es lo que
el servidor usa para decidir qué tools/acciones tiene disponibles el analista.
"""

from __future__ import annotations

from .base import SisavModel


class Permiso(SisavModel):
    """Permiso atómico dentro de un rol."""

    id: int
    nombre: str
    nomenclatura: str
    idModulo: int | None = None


class Rol(SisavModel):
    """Rol con su lista de permisos."""

    id: int
    nombre: str
    estado: bool | None = None
    permisos: list[Permiso] = []


class Perfil(SisavModel):
    """Perfil del usuario (agrupa roles)."""

    id: int
    nombre: str
    roles: list[Rol] = []


class UnidadRef(SisavModel):
    """Referencia mínima a la unidad del usuario."""

    id: int
    nombre: str


class Usuario(SisavModel):
    """Identidad del usuario autenticado + RBAC (perfil → roles → permisos)."""

    id: int
    username: str | None = None
    nombre: str | None = None
    email: str | None = None
    rut: str | None = None
    idPerfil: int | None = None
    idUnidad: int | None = None
    estado: bool | None = None
    unidad: UnidadRef | None = None
    perfil: Perfil | None = None

    @property
    def permisos_nomenclaturas(self) -> set[str]:
        """Conjunto de nomenclaturas de permiso del usuario (de todos sus roles)."""
        if self.perfil is None:
            return set()
        return {
            permiso.nomenclatura
            for rol in self.perfil.roles
            for permiso in rol.permisos
        }
