"""Previews de escritura seguros para SISAV2.

Esta capa modela intenciones de escritura para la demo, pero es deliberadamente
incapaz de aplicarlas: sólo construye ``would_request`` y, cuando hace falta,
consulta contexto mediante ``GET``. Los métodos mutantes no se invocan aquí ni
se habilitan en :mod:`sisav2_mcp.client.http`.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any, Literal

from ..client import SisavClient
from ..models import BitacoraPage, DetalleIniciativa, Fase, etiqueta_estado
from ..models.writes import (
    CambiarFaseInput,
    CargarAsistenciaInput,
    ComentarioBitacoraInput,
    CrearPostulacionEspejoInput,
    CrearPostulacionInput,
    DryRunPreview,
    EditarPostulacionInput,
    EvaluarAdmisibilidadInput,
    PermisoEvaluado,
    ValidacionPreview,
    VeredictoAdmisibilidad,
    WouldRequest,
)

# Estas rutas son contratos esperados por la especificación del curso. No se
# observaron en una sesión de recon y se etiquetan como no verificados en cada
# preview. No se pasan al cliente HTTP.
_CREAR_PATH = "/convocatorias/postulacion"
_EVALUAR_PATH = "/convocatorias/postulacion/admisibilidad"
_CAMBIAR_FASE_PATH = "/proyectos/cambiar-fase"
_ASISTENCIA_PATH = "/proyectos/asistencia/cargar"

_DETALLE_PATH = "/convocatorias/postulacion/obtener"
_BITACORA_PATH = "/convocatorias/postulacion/listar-cambios"
_FASE_PATH = "/convocatorias/fases/obtener"

_LECTURA_POSTULACION_PERMISOS = frozenset(
    {
        "IPOLIST",
        "IPOVER",
        "POSVERT",
        "AEVLIST",
        "CFLIST",
        "EJSLIST",
        "EJSGES",
    }
)
_ASISTENCIA_PERMISOS = frozenset({"EJSGES", "EACEAC"})
_CAMPOS_ESPEJO_BLOQUEADOS = (
    "correo",
    "email",
    "rut",
    "encargad",
    "responsable",
    "telefono",
    "celular",
    "carrera",
    "facultad",
    "convocatoria",
    "dominio",
    "depend",
)
_TIPOS_ESPEJO_BLOQUEADOS = frozenset({"email", "endpoint", "checkbox-dependent"})


def _permisos_presentes(permisos: Collection[str]) -> set[str]:
    return {
        str(permiso).strip().upper()
        for permiso in permisos
        if str(permiso).strip()
    }


def _evaluar_permiso(
    permisos: Collection[str],
    *,
    requeridos: Collection[str],
    operacion: str,
    cualquiera: bool = False,
) -> PermisoEvaluado:
    """Hace RBAC local; ``ADMIN`` es el override explícito observado en SISAV2."""

    presentes = _permisos_presentes(permisos)
    requeridos_ordenados = sorted(set(requeridos))
    es_admin = "ADMIN" in presentes
    autorizados = (
        any(permiso in presentes for permiso in requeridos_ordenados)
        if cualquiera
        else all(permiso in presentes for permiso in requeridos_ordenados)
    )
    if not (autorizados or es_admin):
        conector = "uno de" if cualquiera else "todos"
        raise ValueError(
            f"Permiso insuficiente para {operacion}: se requiere {conector} "
            f"{requeridos_ordenados}; permisos disponibles: "
            f"{sorted(presentes) or ['ninguno']}."
        )

    concedidos = [permiso for permiso in requeridos_ordenados if permiso in presentes]
    if es_admin:
        concedidos.append("ADMIN")
    return PermisoEvaluado(
        requeridos=requeridos_ordenados,
        concedidos=sorted(set(concedidos)),
    )


def _validacion(
    regla: str, detalle: str, *, advertencia: bool = False
) -> ValidacionPreview:
    return ValidacionPreview(
        regla=regla,
        resultado="advertencia" if advertencia else "ok",
        detalle=detalle,
    )


def _preview(
    *,
    operacion: str,
    permiso: PermisoEvaluado,
    validaciones: list[ValidacionPreview],
    method: Literal["POST", "PUT"],
    path: str,
    body: dict[str, Any],
    diff: dict[str, Any],
    efecto_previsto: str,
    body_redactado: bool = False,
    advertencias: list[str] | None = None,
) -> dict[str, Any]:
    """Construye la forma estable que todas las tools de escritura retornan."""

    return DryRunPreview(
        operacion=operacion,
        permiso=permiso,
        validaciones=validaciones,
        advertencias=[
            "DEMO SEGURA: esta operación es un dry-run obligatorio; SISAV2 no fue "
            "modificado.",
            *(advertencias or []),
        ],
        diff=diff,
        efecto_previsto=efecto_previsto,
        would_request=WouldRequest(
            method=method,
            path=path,
            endpoint_esperado=path,
            body=body,
            body_redactado=body_redactado,
        ),
    ).model_dump(mode="json")


async def _obtener_detalle(
    client: SisavClient, id_postulacion: int
) -> DetalleIniciativa:
    return DetalleIniciativa.model_validate(
        await client.get(f"{_DETALLE_PATH}/{id_postulacion}")
    )


async def _obtener_bitacora(client: SisavClient, id_postulacion: int) -> BitacoraPage:
    return BitacoraPage.model_validate(
        await client.get(
            _BITACORA_PATH,
            {"idPostulacion": id_postulacion, "offset": 0, "limit": 1},
        )
    )


async def _obtener_fase(client: SisavClient, id_fase: int) -> Fase:
    return Fase.model_validate(await client.get(f"{_FASE_PATH}/{id_fase}"))


def _valores_formulario(detalle: DetalleIniciativa) -> dict[str, Any]:
    """Índice de valores actuales para construir un diff mínimo de edición."""

    return {
        campo.name: campo.value
        for paso in detalle.formulario.formulario
        for campo in paso.campos
    }


def _estado_actual_desde_bitacora(bitacora: BitacoraPage) -> str:
    """Toma el primer cambio, que es el estado vigente expuesto por la API actual."""

    if not bitacora.cambios or not bitacora.cambios[0].estadoActual:
        raise ValueError(
            "No se pudo confirmar el estado actual en la bitácora; no es seguro "
            "previsualizar una edición."
        )
    return bitacora.cambios[0].estadoActual.strip()


def _estado_por_veredicto(veredicto: VeredictoAdmisibilidad) -> int:
    return {
        VeredictoAdmisibilidad.ADMISIBLE: 3,
        VeredictoAdmisibilidad.REFORMULAR: 11,
        VeredictoAdmisibilidad.RECHAZAR: 7,
    }[veredicto]


def _campo_espejo_bloqueado(
    nombre: str, etiqueta: str | None, tipo: str | None
) -> bool:
    texto = f"{nombre} {etiqueta or ''}".lower()
    return (
        (tipo or "").lower() in _TIPOS_ESPEJO_BLOQUEADOS
        or any(fragmento in texto for fragmento in _CAMPOS_ESPEJO_BLOQUEADOS)
    )


def _sobrescritura_permitida(nombre: str) -> bool:
    return not _campo_espejo_bloqueado(nombre, None, None)


def _campos_espejo_seguro(
    detalle: DetalleIniciativa,
) -> tuple[dict[str, Any], list[str]]:
    """Copia sólo contenido independiente de persona, carrera y convocatoria."""

    seguros: dict[str, Any] = {}
    omitidos: list[str] = []
    for paso in detalle.formulario.formulario:
        for campo in paso.campos:
            if _campo_espejo_bloqueado(campo.name, campo.label, campo.type):
                omitidos.append(campo.name)
                continue
            seguros[campo.name] = campo.value

    # El título es contenido de la iniciativa y se conserva aunque el form no
    # exponga el campo convencional NOMBRE en una convocatoria futura.
    seguros.setdefault("NOMBRE", detalle.nombre)
    return seguros, sorted(set(omitidos))


def _mascarar_identificador(value: str) -> str:
    """Evita devolver RUT, correo o ID completo en la preview de asistencia."""
    value = value.strip()
    if "@" in value:
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _asistencia_para_preview(fila: dict[str, Any]) -> dict[str, Any]:
    """Muestra el efecto sin exponer datos personales en la conversación."""
    preview = dict(fila)
    preview["identificador"] = _mascarar_identificador(str(fila["identificador"]))
    if isinstance(preview.get("nombre"), str):
        preview["nombre"] = f"{preview['nombre'][:1]}***"
    return preview


async def crear_postulacion(
    *,
    permisos: Collection[str],
    modalidad: str,
    convocatoria_id: int,
    titulo: str,
    objetivo: str,
    campos_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Previsualiza una creación; no llama a la API mutante."""

    data = CrearPostulacionInput.model_validate(
        {
            "modalidad": modalidad,
            "convocatoria_id": convocatoria_id,
            "titulo": titulo,
            "objetivo": objetivo,
            "campos_extra": {} if campos_extra is None else campos_extra,
        }
    )
    permiso = _evaluar_permiso(
        permisos, requeridos={"IPOCRE"}, operacion="crear_postulacion"
    )
    campos = {
        **data.campos_extra,
        "NOMBRE": data.titulo,
        "OBJETIVO": data.objetivo,
    }
    body = {
        "modalidad": data.modalidad.value,
        "convocatoriaId": data.convocatoria_id,
        "campos": campos,
    }
    return _preview(
        operacion="crear_postulacion",
        permiso=permiso,
        validaciones=[
            _validacion("modalidad", f"Modalidad válida: {data.modalidad.value}."),
            _validacion(
                "campos_nucleo",
                "Título, objetivo y convocatoria fueron validados localmente.",
            ),
        ],
        method="POST",
        path=_CREAR_PATH,
        body=body,
        diff={"crear": body},
        efecto_previsto=(
            f"Crearía una postulación {data.modalidad.value} en la convocatoria "
            f"{data.convocatoria_id}."
        ),
    )


async def editar_postulacion(
    client: SisavClient,
    *,
    permisos: Collection[str],
    id_postulacion: int,
    campos: dict[str, Any],
) -> dict[str, Any]:
    """Previsualiza una edición sólo si el contexto leído está Incompleta."""

    data = EditarPostulacionInput.model_validate(
        {"id_postulacion": id_postulacion, "campos": campos}
    )
    permiso = _evaluar_permiso(
        permisos, requeridos={"IPOEDI"}, operacion="editar_postulacion"
    )
    detalle = await _obtener_detalle(client, data.id_postulacion)
    estado_actual = _estado_actual_desde_bitacora(
        await _obtener_bitacora(client, data.id_postulacion)
    )
    if estado_actual.casefold() != "incompleta":
        raise ValueError(
            "editar_postulacion sólo admite postulaciones en estado Incompleta; "
            f"la bitácora indica '{estado_actual}'."
        )

    valores = _valores_formulario(detalle)
    cambios = {
        campo: {"antes": valores.get(campo), "despues": valor}
        for campo, valor in data.campos.items()
    }
    body = {"idPostulacion": data.id_postulacion, "campos": data.campos}
    return _preview(
        operacion="editar_postulacion",
        permiso=permiso,
        validaciones=[
            _validacion("postulacion_existe", f"Se leyó la postulación {detalle.id}."),
            _validacion(
                "estado_editable",
                "La bitácora confirma estado actual Incompleta.",
            ),
        ],
        method="PUT",
        path=f"{_CREAR_PATH}/{data.id_postulacion}",
        body=body,
        diff={"actualizar": cambios},
        efecto_previsto=(
            f"Actualizaría {len(cambios)} campo(s) de la postulación "
            f"{data.id_postulacion}."
        ),
    )


async def evaluar_admisibilidad(
    client: SisavClient,
    *,
    permisos: Collection[str],
    id_postulacion: int,
    modalidad: str,
    id_fase: int,
    veredicto: str,
    comentario: str,
) -> dict[str, Any]:
    """Previsualiza un veredicto de admisibilidad usando contexto de lectura."""

    data = EvaluarAdmisibilidadInput.model_validate(
        {
            "id_postulacion": id_postulacion,
            "modalidad": modalidad,
            "id_fase": id_fase,
            "veredicto": veredicto,
            "comentario": comentario,
        }
    )
    permiso = _evaluar_permiso(
        permisos,
        requeridos={"AEVADM", "AEVAPR"},
        operacion="evaluar_admisibilidad",
        cualquiera=True,
    )
    detalle = await _obtener_detalle(client, data.id_postulacion)
    fase = await _obtener_fase(client, data.id_fase)
    if fase.activo is False:
        raise ValueError(f"La fase {data.id_fase} está inactiva.")

    estado_destino_id = _estado_por_veredicto(data.veredicto)
    estados_configurados = {
        item.idEstado for item in fase.estadoPostulacion if item.idEstado is not None
    }
    estado_configurado = estado_destino_id in estados_configurados
    body = {
        "idPostulacion": data.id_postulacion,
        "modalidad": data.modalidad.value,
        "idFase": data.id_fase,
        "veredicto": data.veredicto.value,
        "idEstadoDestino": estado_destino_id,
        "comentario": data.comentario,
    }
    return _preview(
        operacion="evaluar_admisibilidad",
        permiso=permiso,
        validaciones=[
            _validacion("postulacion_existe", f"Se leyó la postulación {detalle.id}."),
            _validacion("fase_activa", f"La fase {fase.id} está activa."),
            _validacion(
                "estado_en_fase",
                (
                    f"El estado {estado_destino_id} "
                    f"({etiqueta_estado(estado_destino_id)}) "
                    "está configurado en la fase."
                    if estado_configurado
                    else (
                        f"El estado {estado_destino_id} "
                        "no aparece entre las transiciones leídas de la fase; el "
                        "contrato mutante sigue sin verificar."
                    )
                ),
                advertencia=not estado_configurado,
            ),
        ],
        method="POST",
        path=_EVALUAR_PATH,
        body=body,
        diff={
            "admisibilidad": {
                "idPostulacion": data.id_postulacion,
                "veredicto": data.veredicto.value,
                "estado_destino": {
                    "id": estado_destino_id,
                    "nombre": etiqueta_estado(estado_destino_id),
                },
                "comentario": data.comentario,
            }
        },
        efecto_previsto=(
            f"Emitiría el veredicto {data.veredicto.value} para la postulación "
            f"{data.id_postulacion}."
        ),
        advertencias=(
            [
                "La configuración de fase no incluye el estado previsto; se muestra "
                "sólo como intención de demo."
            ]
            if not estado_configurado
            else None
        ),
    )


async def cambiar_fase(
    client: SisavClient,
    *,
    permisos: Collection[str],
    id_postulacion: int,
    id_fase: int,
    estado_destino_id: int,
    observacion: str,
) -> dict[str, Any]:
    """Previsualiza un cambio de fase sólo hacia una transición configurada."""

    data = CambiarFaseInput.model_validate(
        {
            "id_postulacion": id_postulacion,
            "id_fase": id_fase,
            "estado_destino_id": estado_destino_id,
            "observacion": observacion,
        }
    )
    permiso = _evaluar_permiso(
        permisos, requeridos={"IPRCES"}, operacion="cambiar_fase"
    )
    detalle = await _obtener_detalle(client, data.id_postulacion)
    fase = await _obtener_fase(client, data.id_fase)
    if fase.activo is False:
        raise ValueError(f"La fase {data.id_fase} está inactiva.")
    destino = next(
        (
            item
            for item in fase.estadoPostulacion
            if item.idEstado == data.estado_destino_id
        ),
        None,
    )
    if destino is None:
        disponibles = sorted(
            item.idEstado
            for item in fase.estadoPostulacion
            if item.idEstado is not None
        )
        raise ValueError(
            f"El estado destino {data.estado_destino_id} no es una transición válida "
            f"para la fase {data.id_fase}. Estados disponibles: {disponibles}."
        )

    nombre_estado = (
        destino.estado.nombre
        if destino.estado is not None
        else etiqueta_estado(data.estado_destino_id)
    )
    body = {
        "idPostulacion": data.id_postulacion,
        "idFase": data.id_fase,
        "idEstadoDestino": data.estado_destino_id,
        "observacion": data.observacion,
    }
    return _preview(
        operacion="cambiar_fase",
        permiso=permiso,
        validaciones=[
            _validacion("postulacion_existe", f"Se leyó la postulación {detalle.id}."),
            _validacion("fase_activa", f"La fase {fase.id} está activa."),
            _validacion(
                "transicion_valida",
                f"La fase permite estado {data.estado_destino_id} ({nombre_estado}).",
            ),
        ],
        method="POST",
        path=_CAMBIAR_FASE_PATH,
        body=body,
        diff={
            "cambio_fase": {
                "idPostulacion": data.id_postulacion,
                "fase": {"id": data.id_fase, "nombre": fase.nombre},
                "estado_destino": {
                    "id": data.estado_destino_id,
                    "nombre": nombre_estado,
                },
                "observacion": data.observacion,
            }
        },
        efecto_previsto=(
            f"Movería la postulación {data.id_postulacion} a {nombre_estado} "
            f"en la fase {data.id_fase}."
        ),
    )


async def agregar_comentario_bitacora(
    client: SisavClient,
    *,
    permisos: Collection[str],
    id_postulacion: int,
    texto: str,
) -> dict[str, Any]:
    """Previsualiza feedback de bitácora tras validar acceso de lectura."""

    data = ComentarioBitacoraInput.model_validate(
        {"id_postulacion": id_postulacion, "texto": texto}
    )
    permiso = _evaluar_permiso(
        permisos,
        requeridos=_LECTURA_POSTULACION_PERMISOS,
        operacion="agregar_comentario_bitacora",
        cualquiera=True,
    )
    detalle = await _obtener_detalle(client, data.id_postulacion)
    body = {"idPostulacion": data.id_postulacion, "texto": data.texto}
    return _preview(
        operacion="agregar_comentario_bitacora",
        permiso=permiso,
        validaciones=[
            _validacion(
                "acceso_lectura",
                f"Se leyó la postulación {detalle.id} antes de preparar el comentario.",
            )
        ],
        method="POST",
        path=f"{_CREAR_PATH}/{data.id_postulacion}/comentario",
        body=body,
        diff={
            "comentario_nuevo": {
                "idPostulacion": data.id_postulacion,
                "texto": data.texto,
            }
        },
        efecto_previsto=(
            f"Agregaría un comentario a la bitácora de {data.id_postulacion}."
        ),
    )


async def crear_postulacion_espejo(
    client: SisavClient,
    *,
    permisos: Collection[str],
    id_origen: int,
    modalidad_destino: str,
    convocatoria_destino_id: int,
    carrera_destino_id: int,
    sobrescrituras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Previsualiza una copia multi-carrera sin campos personales/dependientes."""

    data = CrearPostulacionEspejoInput.model_validate(
        {
            "id_origen": id_origen,
            "modalidad_destino": modalidad_destino,
            "convocatoria_destino_id": convocatoria_destino_id,
            "carrera_destino_id": carrera_destino_id,
            "sobrescrituras": {} if sobrescrituras is None else sobrescrituras,
        }
    )
    permiso = _evaluar_permiso(
        permisos, requeridos={"IPOCRE"}, operacion="crear_postulacion_espejo"
    )
    for campo in data.sobrescrituras:
        if not _sobrescritura_permitida(campo):
            raise ValueError(
                f"La sobrescritura '{campo}' no es segura para una postulación espejo; "
                "no se copian datos personales ni dependientes de carrera."
            )

    detalle = await _obtener_detalle(client, data.id_origen)
    campos, omitidos = _campos_espejo_seguro(detalle)
    campos.update(data.sobrescrituras)
    body = {
        "modalidad": data.modalidad_destino.value,
        "convocatoriaId": data.convocatoria_destino_id,
        "carreraId": data.carrera_destino_id,
        "campos": campos,
    }
    return _preview(
        operacion="crear_postulacion_espejo",
        permiso=permiso,
        validaciones=[
            _validacion(
                "origen_existe",
                f"Se leyó la postulación origen {detalle.id}.",
            ),
            _validacion(
                "campos_seguros",
                f"Se conservaron {len(campos)} campo(s) independientes de "
                "carrera/persona.",
            ),
            _validacion(
                "dependencias_limpiadas",
                (
                    f"Se omitieron {len(omitidos)} campo(s) personales o dependientes."
                    if omitidos
                    else (
                        "No se detectaron campos personales o dependientes en el "
                        "origen."
                    )
                ),
            ),
        ],
        method="POST",
        path=_CREAR_PATH,
        body=body,
        diff={
            "espejo": {
                "origen": {"idPostulacion": data.id_origen, "nombre": detalle.nombre},
                "destino": {
                    "modalidad": data.modalidad_destino.value,
                    "convocatoriaId": data.convocatoria_destino_id,
                    "carreraId": data.carrera_destino_id,
                },
                "campos_copiados": sorted(campos),
                "campos_omitidos": omitidos,
                "sobrescrituras": data.sobrescrituras,
            }
        },
        efecto_previsto=(
            f"Crearía una postulación espejo de {data.id_origen} para carrera "
            f"{data.carrera_destino_id}."
        ),
        advertencias=(
            [
                "Los campos omitidos se excluyeron por contener datos personales o "
                "dependencias de carrera/convocatoria."
            ]
            if omitidos
            else None
        ),
    )


async def cargar_asistencia(
    *,
    permisos: Collection[str],
    id_proyecto: int,
    asistentes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Previsualiza una carga masiva de asistencia; no la persiste."""

    data = CargarAsistenciaInput.model_validate(
        {"id_proyecto": id_proyecto, "asistentes": asistentes}
    )
    permiso = _evaluar_permiso(
        permisos,
        requeridos=_ASISTENCIA_PERMISOS,
        operacion="cargar_asistencia",
        cualquiera=True,
    )
    filas = [
        asistente.model_dump(mode="json", exclude_none=True)
        for asistente in data.asistentes
    ]
    presentes = sum(1 for fila in filas if fila["asistio"])
    ausentes = len(filas) - presentes
    body = {
        "idProyecto": data.id_proyecto,
        "asistentes": [_asistencia_para_preview(fila) for fila in filas],
    }
    return _preview(
        operacion="cargar_asistencia",
        permiso=permiso,
        validaciones=[
            _validacion(
                "id_proyecto",
                f"Identificador de proyecto válido: {data.id_proyecto}.",
            ),
            _validacion(
                "filas_asistencia",
                f"Se validaron {len(filas)} fila(s): identificador, asistencia y "
                "fecha opcional. La preview enmascara identificadores.",
            ),
        ],
        method="POST",
        path=_ASISTENCIA_PATH,
        body=body,
        body_redactado=True,
        diff={
            "asistencia": {
                "idProyecto": data.id_proyecto,
                "filas": len(filas),
                "presentes": presentes,
                "ausentes": ausentes,
            }
        },
        efecto_previsto=(
            f"Registraría {len(filas)} asistencia(s) para el proyecto "
            f"{data.id_proyecto}."
        ),
    )
