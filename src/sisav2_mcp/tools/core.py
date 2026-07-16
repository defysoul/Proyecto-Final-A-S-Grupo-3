"""Lógica de las tools del núcleo (Paso 6), independiente de FastMCP.

Funciones puras ``async`` que reciben un :class:`SisavClient` y la identidad ya
resuelta (``id_usuario`` / ``roles``). Construyen los params confirmados en el
recon, parsean con los modelos y devuelven una salida concisa y estable. La capa
FastMCP (``register.py``) es una envoltura fina que resuelve la identidad.
"""

from __future__ import annotations

import json
from typing import Any

from ..client import SisavClient
from ..models import (
    BitacoraPage,
    DetalleIniciativa,
    Fase,
    Modalidad,
    Postulacion,
    PostulacionesPage,
    Proyecto,
    ProyectosPage,
    RepositoriosResponse,
    etiqueta_estado,
)

# Presets de estado[] confirmados en API_INVENTORY.md.
INGRESOS_ESTADOS = [3, 10, 1, 2, 7, 11, 8]
ADMISIBILIDAD_ESTADOS = [3, 6, 2, 4]
PLANIFICACION_ESTADOS = [5]
CAMBIO_FASE_ESTADOS = [3, 5, 6, 8, 10, 1, 2, 4, 7, 11, 9]

_BUSCAR_PATH = "/convocatorias/postulacion/buscar"
_PROYECTOS_PATH = "/proyectos/listar"
_DETALLE_PATH = "/convocatorias/postulacion/obtener"
_FASE_PATH = "/convocatorias/fases/obtener"
_BITACORA_PATH = "/convocatorias/postulacion/listar-cambios"
_REPOS_PATH = "/mantenedores/repositorios"


def _valid_modalidad(modalidad: str) -> str:
    try:
        return Modalidad(modalidad).value
    except ValueError as exc:
        opciones = ", ".join(m.value for m in Modalidad)
        raise ValueError(
            f"modalidad inválida '{modalidad}'. Opciones: {opciones}."
        ) from exc


def _valid_pagination(offset: int, limit: int) -> tuple[int, int]:
    """Valida los límites soportados por las vistas de SISAV2.

    La API admite tamaños pequeños y no documenta un máximo mayor a 100. Se
    valida aquí, antes de tocar la red, para que un LLM no pueda pedir una
    descarga accidentalmente enorme ni enviar offsets negativos.
    """
    if offset < 0:
        raise ValueError("offset debe ser mayor o igual a 0.")
    if not 1 <= limit <= 100:
        raise ValueError("limit debe estar entre 1 y 100.")
    return offset, limit


def _valid_estados(estados: list[int]) -> list[int]:
    """Comprueba que los estados pertenezcan al catálogo confirmado (1..11)."""
    invalidos = [estado for estado in estados if not 1 <= estado <= 11]
    if invalidos:
        raise ValueError(f"estado contiene IDs no válidos: {invalidos}.")
    return estados


def _json_array(values: list[int]) -> str:
    """Serializa un array de ints como lo hace el SPA: ``[3,6,2,4]`` (sin espacios)."""
    return json.dumps(values, separators=(",", ":"))


def _postulacion_out(p: Postulacion) -> dict[str, Any]:
    return {
        "idpostulacion": p.idpostulacion,
        "nombre": p.nombrepostulacion,
        "encargado": p.encargado,
        "carrera": p.carreraformulario,
        "facultad": p.facultadformulario,
        "convocatoria": {"id": p.idconvocatoria, "nombre": p.nombreconvocatoria},
        "estado": {
            "id": p.idestado,
            "nombre": p.nombreestado or etiqueta_estado(p.idestado),
        },
        "anio": p.anioInicioConvocatoria,
        "fecha": p.fecha,
    }


def _proyecto_out(p: Proyecto) -> dict[str, Any]:
    return {
        "id": p.id,
        "idpostulacion": p.idpostulacion,
        "nombre": p.nombrepostulacion,
        "encargado": p.encargado,
        "facultad": p.nombrefacultad or p.facultadformulario,
        "carrera": p.carreraformulario,
        "convocatoria": {"id": p.idconvocatoria, "nombre": p.nombreconvocatoria},
        "estado": {
            "id": p.idestado,
            "nombre": p.nombreestado or etiqueta_estado(p.idestado),
        },
    }


async def listar_postulaciones(
    client: SisavClient,
    *,
    modalidad: str,
    id_usuario: int,
    roles: list[int],
    estado: list[int] | None = None,
    ingreso: bool = True,
    convocatoria: int | None = None,
    facultad: int | None = None,
    carrera: int | None = None,
    busqueda: str | None = None,
    ordenamiento: str = "codigo_desc",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """Lista postulaciones/iniciativas con filtros (`GET .../postulacion/buscar`)."""
    modalidad = _valid_modalidad(modalidad)
    offset, limit = _valid_pagination(offset, limit)
    estado = _valid_estados(estado if estado is not None else INGRESOS_ESTADOS)
    params: dict[str, Any] = {
        "modalidad": modalidad,
        "idUsuario": id_usuario,
        "roles": _json_array(roles),
        "estado": _json_array(estado),
        "ingreso": "true" if ingreso else "false",
        "ordenamiento": ordenamiento,
        "offset": offset,
        "limit": limit,
    }
    # Filtros NO confirmados en recon (validar en smoke real); solo si se proveen.
    if convocatoria is not None:
        params["idConvocatoria"] = convocatoria
    if facultad is not None:
        params["idFacultad"] = facultad
    if carrera is not None:
        params["idCarrera"] = carrera
    if busqueda is not None:
        params["searchTerm"] = busqueda

    page = PostulacionesPage.model_validate(await client.get(_BUSCAR_PATH, params))
    out: dict[str, Any] = {
        "total": page.total,
        "modalidad": modalidad,
        "mostrando": len(page.postulaciones),
        "postulaciones": [_postulacion_out(p) for p in page.postulaciones],
    }
    filtros_solicitados = {
        key: value
        for key, value in {
            "convocatoria": convocatoria,
            "facultad": facultad,
            "carrera": carrera,
            "busqueda": busqueda,
        }.items()
        if value is not None
    }
    if filtros_solicitados:
        # El recon en vivo mostró que algunos de estos filtros pueden ser
        # ignorados por el backend. No afirmamos que el total esté filtrado si
        # SISAV2 no lo confirma en la respuesta.
        out["filtros_solicitados"] = filtros_solicitados
        out["advertencias"] = [
            "SISAV2 puede ignorar filtros por convocatoria, facultad, carrera "
            "o búsqueda; revisa las filas devueltas antes de sacar conclusiones."
        ]
    return out


async def listar_admisibilidad(
    client: SisavClient,
    *,
    modalidad: str,
    id_usuario: int,
    roles: list[int],
    ordenamiento: str = "codigo_desc",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """Preset de admisibilidad (estado=[3,6,2,4], ingreso=false)."""
    return await listar_postulaciones(
        client,
        modalidad=modalidad,
        id_usuario=id_usuario,
        roles=roles,
        estado=ADMISIBILIDAD_ESTADOS,
        ingreso=False,
        ordenamiento=ordenamiento,
        offset=offset,
        limit=limit,
    )


async def listar_planificacion(
    client: SisavClient,
    *,
    modalidad: str,
    id_usuario: int,
    roles: list[int],
    ordenamiento: str = "codigo_desc",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """Preset de planificación/calendarización (estado=[5], ingreso=false)."""
    return await listar_postulaciones(
        client,
        modalidad=modalidad,
        id_usuario=id_usuario,
        roles=roles,
        estado=PLANIFICACION_ESTADOS,
        ingreso=False,
        ordenamiento=ordenamiento,
        offset=offset,
        limit=limit,
    )


async def listar_cambio_fase(
    client: SisavClient,
    *,
    modalidad: str,
    id_usuario: int,
    roles: list[int],
    ordenamiento: str = "codigo_desc",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """Preset de cambio de fase (los 11 estados, ingreso=false)."""
    return await listar_postulaciones(
        client,
        modalidad=modalidad,
        id_usuario=id_usuario,
        roles=roles,
        estado=CAMBIO_FASE_ESTADOS,
        ingreso=False,
        ordenamiento=ordenamiento,
        offset=offset,
        limit=limit,
    )


async def listar_proyectos(
    client: SisavClient,
    *,
    modalidad: str,
    id_usuario: int,
    busqueda: str | None = None,
    ordenamiento: str = "codigo_desc",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """Lista proyectos en Ejecución/Seguimiento (`GET /proyectos/listar`)."""
    modalidad = _valid_modalidad(modalidad)
    offset, limit = _valid_pagination(offset, limit)
    params: dict[str, Any] = {
        "modalidad": modalidad,
        "idUsuario": id_usuario,
        "ordenamiento": ordenamiento,
        "offset": offset,
        "limit": limit,
    }
    if busqueda is not None:
        params["searchTerm"] = busqueda

    page = ProyectosPage.model_validate(await client.get(_PROYECTOS_PATH, params))
    return {
        "total": page.total,
        "modalidad": modalidad,
        "mostrando": len(page.data),
        "proyectos": [_proyecto_out(p) for p in page.data],
    }


async def obtener_detalle_iniciativa(
    client: SisavClient,
    *,
    id_postulacion: int,
    id_fase: int | None = None,
) -> dict[str, Any]:
    """Detalle (form-builder) de una iniciativa; opcionalmente la fase asociada.

    ``id_fase`` es opcional porque el recon no halló un mapeo confiable
    postulación→fase; si se conoce (p. ej. por la convocatoria) se adjunta la
    config de la fase (workflow rol→estado), cubriendo la vista *Evaluar*.
    """
    detalle = DetalleIniciativa.model_validate(
        await client.get(f"{_DETALLE_PATH}/{id_postulacion}")
    )
    pasos = [
        {
            "posicion": paso.posicion,
            "descripcion": paso.descripcion,
            "campos": [
                {"name": c.name, "label": c.label, "type": c.type, "value": c.value}
                for c in paso.campos
            ],
        }
        for paso in detalle.formulario.formulario
    ]
    out: dict[str, Any] = {
        "id": detalle.id,
        "nombre": detalle.nombre,
        "fecha": detalle.fecha,
        "formulario": detalle.formulario.nombre,
        "pasos": pasos,
    }
    if id_fase is not None:
        fase = Fase.model_validate(await client.get(f"{_FASE_PATH}/{id_fase}"))
        out["fase"] = {
            "id": fase.id,
            "nombre": fase.nombre,
            "activo": fase.activo,
            "transiciones": [
                {
                    "rol": fe.rol.nombre if fe.rol else fe.idRol,
                    "estado": fe.estado.nombre if fe.estado else fe.idEstado,
                }
                for fe in fase.estadoPostulacion
            ],
        }
    return out


async def ver_bitacora(
    client: SisavClient,
    *,
    id_postulacion: int,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Historial de cambios de estado/feedback de una postulación."""
    params = {"idPostulacion": id_postulacion, "offset": offset, "limit": limit}
    page = BitacoraPage.model_validate(await client.get(_BITACORA_PATH, params))
    return {
        "idPostulacion": id_postulacion,
        "cambios": [c.model_dump(exclude_none=True) for c in page.cambios],
    }


async def listar_repositorios(
    client: SisavClient,
    *,
    roles: list[int],
) -> dict[str, Any]:
    """Repositorios documentales agrupados por categoría (módulo 25)."""
    params = {"vista": "REPOSITORIO_VCM", "roles": ",".join(str(r) for r in roles)}
    data = RepositoriosResponse.model_validate(await client.get(_REPOS_PATH, params))
    return {
        "categorias": [
            {
                "id": grupo.categoria.id,
                "nombre": grupo.categoria.nombre,
                "repositorios": [
                    {
                        "id": r.id,
                        "nombre": r.nombre,
                        "descripcion": r.descripcion,
                        "esPublico": r.esPublico,
                    }
                    for r in grupo.repositorios
                ],
            }
            for grupo in data.data
        ]
    }
