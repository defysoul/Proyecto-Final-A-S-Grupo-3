"""Lógica de las tools de reportes + escape hatch (Paso 7).

Como en ``core.py``, son funciones puras ``async`` que reciben el cliente y la
identidad ya resuelta. El escape hatch ``sisav2_consulta_generica`` es GET-only y
solo admite paths de la allowlist de ``API_INVENTORY.md``.
"""

from __future__ import annotations

import re
from typing import Any

from ..client import SisavClient
from ..models import AvanceGlobalKPIs, ExportResult, Indicador, etiqueta_estado
from .core import _valid_modalidad

_TOTALES_PATH = "/convocatorias/postulacion/totales"
_AVANCE_PATH = "/proyectos/estadisticas/globales-proyectos"
_EXPORT_PATH = "/convocatorias/postulacion/exportar-excel"

# Allowlist del escape hatch (GET-only), derivada de API_INVENTORY.md.
_GENERIC_GET_EXACT = frozenset(
    {
        "/usuarios/verifica-token",
        "/usuarios/roles/listar/si",
        "/convocatorias/postulacion/buscar",
        "/convocatorias/postulacion/listar-cambios",
        "/convocatorias/listar-combo",
        "/convocatorias/estado/buscar",
        "/proyectos/listar",
        "/proyectos/estadisticas/globales-proyectos",
        "/mantenedores/repositorios",
        "/mantenedores/listarFacultad",
        "/mantenedores/listarCarrera",
    }
)
# Endpoints con parámetro en el path. Se valida el patrón completo para no
# convertir un prefijo permitido en una vía de acceso a rutas no inventariadas.
_GENERIC_GET_PATTERNS = (
    re.compile(r"^/convocatorias/postulacion/totales/\d+$"),
    re.compile(r"^/convocatorias/postulacion/obtener/\d+$"),
    re.compile(r"^/convocatorias/fases/obtener/\d+$"),
)


def _norm(path: str) -> str:
    path = path.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def is_allowed_generic_path(path: str) -> bool:
    norm = _norm(path)
    if norm in _GENERIC_GET_EXACT:
        return True
    return any(pattern.fullmatch(norm) for pattern in _GENERIC_GET_PATTERNS)


async def resumen_indicadores(
    client: SisavClient,
    *,
    id_usuario: int,
    modalidad: str | None = None,
) -> dict[str, Any]:
    """Conteo de iniciativas por estado (KPIs por estado) del usuario."""
    params: dict[str, Any] = {}
    if modalidad is not None:
        params["modalidad"] = _valid_modalidad(modalidad)
    data = await client.get(f"{_TOTALES_PATH}/{id_usuario}", params or None)
    indicadores = sorted(
        (Indicador.model_validate(item) for item in data), key=lambda i: i.id
    )
    items = [
        {"idEstado": i.id, "estado": etiqueta_estado(i.id), "total": i.total}
        for i in indicadores
    ]
    return {
        "idUsuario": id_usuario,
        "modalidad": modalidad,
        "totalGeneral": sum(i.total for i in indicadores),
        "indicadores": items,
    }


async def avance_global(client: SisavClient) -> dict[str, Any]:
    """KPIs de Avance Global (solo KPIs; la grilla está diferida — 400 server-side)."""
    data = await client.get(_AVANCE_PATH)
    return AvanceGlobalKPIs.model_validate(data).model_dump()


async def exportar_postulaciones(
    client: SisavClient,
    *,
    convocatoria_id: int,
    modalidad: str,
    id_usuario: int,
    roles: list[int],
    estado: list[int] | None = None,
    convocatoria_nombre: str | None = None,
    es_admin: bool = False,
) -> dict[str, Any]:
    """Genera el XLSX de una convocatoria; devuelve la URL S3, NO los datos.

    POST de solo lectura (allowlisted en el cliente). La URL prefirmada expira
    ~900s; v1 no descarga ni parsea el binario.
    """
    modalidad = _valid_modalidad(modalidad)
    body: dict[str, Any] = {
        "convocatoriaId": convocatoria_id,
        "estado": estado if estado is not None else [],
        "modalidad": modalidad,
        "idUsuario": id_usuario,
        "roles": roles,
        "esAdmin": es_admin,
    }
    if convocatoria_nombre is not None:
        body["convocatoriaNombre"] = convocatoria_nombre
    result = ExportResult.model_validate(await client.post(_EXPORT_PATH, body))
    return {
        "url": result.url,
        "total": result.total,
        "nombreArchivo": result.nombreArchivo,
        "nota": "URL S3 prefirmada (expira ~900s); v1 no descarga el binario.",
    }


async def sisav2_consulta_generica(
    client: SisavClient,
    *,
    path: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """Escape hatch GET-only: consulta un endpoint de la allowlist de inventario."""
    if not is_allowed_generic_path(path):
        permitidos = sorted(_GENERIC_GET_EXACT) + [
            "/convocatorias/postulacion/totales/{id}",
            "/convocatorias/postulacion/obtener/{id}",
            "/convocatorias/fases/obtener/{id}",
        ]
        raise ValueError(
            f"Path no permitido en consulta genérica: '{path}'. Solo GET y dentro "
            f"de la allowlist: {permitidos}."
        )
    return await client.get(_norm(path), params)
