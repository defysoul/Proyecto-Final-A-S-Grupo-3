"""Registro de las tools del núcleo en una instancia FastMCP.

Cada tool es una envoltura fina: resuelve la identidad (idUsuario/roles) desde el
:class:`SisavContext` y delega en las funciones puras de :mod:`.core`.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..mock_backend import finalizar_escritura
from . import core, documents, reports, writes
from .context import SisavContext
from .errors import friendly_tool_errors


def register_core_tools(mcp: FastMCP, ctx: SisavContext) -> None:
    """Registra las tools del núcleo (Paso 6) sobre ``mcp``."""

    @mcp.tool
    @friendly_tool_errors
    async def listar_postulaciones(
        modalidad: str,
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
        """Lista postulaciones/ingresos de una modalidad VcM.

        modalidad ∈ {PRE_GRADO, POST_GRADO, EXTENSION}. Filtra por estado[],
        paginación offset/limit y orden. Devuelve total + filas concisas
        (postulación, encargado, carrera, facultad, convocatoria, estado).
        """
        id_usuario, roles = await ctx.identity()
        return await core.listar_postulaciones(
            ctx.client,
            modalidad=modalidad,
            id_usuario=id_usuario,
            roles=roles,
            estado=estado,
            ingreso=ingreso,
            convocatoria=convocatoria,
            facultad=facultad,
            carrera=carrera,
            busqueda=busqueda,
            ordenamiento=ordenamiento,
            offset=offset,
            limit=limit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def listar_admisibilidad(
        modalidad: str,
        ordenamiento: str = "codigo_desc",
        offset: int = 0,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Iniciativas en admisibilidad (preset estado=[3,6,2,4], ingreso=false)."""
        id_usuario, roles = await ctx.identity()
        return await core.listar_admisibilidad(
            ctx.client,
            modalidad=modalidad,
            id_usuario=id_usuario,
            roles=roles,
            ordenamiento=ordenamiento,
            offset=offset,
            limit=limit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def listar_planificacion(
        modalidad: str,
        ordenamiento: str = "codigo_desc",
        offset: int = 0,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Iniciativas en planificación/calendarización (preset estado=[5])."""
        id_usuario, roles = await ctx.identity()
        return await core.listar_planificacion(
            ctx.client,
            modalidad=modalidad,
            id_usuario=id_usuario,
            roles=roles,
            ordenamiento=ordenamiento,
            offset=offset,
            limit=limit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def listar_cambio_fase(
        modalidad: str,
        ordenamiento: str = "codigo_desc",
        offset: int = 0,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Iniciativas en la vista Cambio de Fase (preset: los 11 estados)."""
        id_usuario, roles = await ctx.identity()
        return await core.listar_cambio_fase(
            ctx.client,
            modalidad=modalidad,
            id_usuario=id_usuario,
            roles=roles,
            ordenamiento=ordenamiento,
            offset=offset,
            limit=limit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def listar_proyectos(
        modalidad: str,
        busqueda: str | None = None,
        ordenamiento: str = "codigo_desc",
        offset: int = 0,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Lista proyectos en Ejecución/Seguimiento (id de proyecto ≠ idpostulacion)."""
        id_usuario, _roles = await ctx.identity()
        return await core.listar_proyectos(
            ctx.client,
            modalidad=modalidad,
            id_usuario=id_usuario,
            busqueda=busqueda,
            ordenamiento=ordenamiento,
            offset=offset,
            limit=limit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def obtener_detalle_iniciativa(
        id_postulacion: int,
        id_fase: int | None = None,
    ) -> dict[str, Any]:
        """Detalle (form-builder, pasos+campos) de una iniciativa.

        Si se conoce ``id_fase`` adjunta la config de la fase (workflow rol→estado).
        """
        return await core.obtener_detalle_iniciativa(
            ctx.client, id_postulacion=id_postulacion, id_fase=id_fase
        )

    @mcp.tool
    @friendly_tool_errors
    async def ver_bitacora(
        id_postulacion: int,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Historial de cambios de estado/feedback (bitácora) de una postulación."""
        return await core.ver_bitacora(
            ctx.client, id_postulacion=id_postulacion, offset=offset, limit=limit
        )

    @mcp.tool
    @friendly_tool_errors
    async def listar_repositorios() -> dict[str, Any]:
        """Repositorios documentales por categoría (según los roles del usuario)."""
        _id_usuario, roles = await ctx.identity()
        return await core.listar_repositorios(ctx.client, roles=roles)


def register_report_tools(mcp: FastMCP, ctx: SisavContext) -> None:
    """Registra las tools de reportes + el escape hatch (Paso 7) sobre ``mcp``."""

    @mcp.tool
    @friendly_tool_errors
    async def resumen_indicadores(modalidad: str | None = None) -> dict[str, Any]:
        """Conteo de iniciativas por estado del usuario (opcional por modalidad)."""
        id_usuario, _roles = await ctx.identity()
        return await reports.resumen_indicadores(
            ctx.client, id_usuario=id_usuario, modalidad=modalidad
        )

    @mcp.tool
    @friendly_tool_errors
    async def avance_global() -> dict[str, Any]:
        """KPIs de Avance Global (proyectos, objetivos, hitos, actividades, gasto)."""
        return await reports.avance_global(ctx.client)

    @mcp.tool
    @friendly_tool_errors
    async def exportar_postulaciones(
        convocatoria_id: int,
        modalidad: str,
        estado: list[int] | None = None,
        convocatoria_nombre: str | None = None,
    ) -> dict[str, Any]:
        """Exporta a XLSX las postulaciones de una convocatoria; devuelve la URL S3.

        No descarga el binario: retorna url + total + nombreArchivo.
        """
        usuario = await ctx.usuario()
        roles = [rol.id for rol in usuario.perfil.roles] if usuario.perfil else []
        es_admin = "ADMIN" in usuario.permisos_nomenclaturas
        return await reports.exportar_postulaciones(
            ctx.client,
            convocatoria_id=convocatoria_id,
            modalidad=modalidad,
            id_usuario=usuario.id,
            roles=roles,
            estado=estado,
            convocatoria_nombre=convocatoria_nombre,
            es_admin=es_admin,
        )

    @mcp.tool
    @friendly_tool_errors
    async def sisav2_consulta_generica(
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Escape hatch GET-only: consulta un endpoint de la allowlist de inventario."""
        return await reports.sisav2_consulta_generica(
            ctx.client, path=path, params=params
        )


def register_document_tools(mcp: FastMCP, ctx: SisavContext) -> None:
    """Registra el skill de documentos (Paso 8): CATASTRO y EVIDENCIA en .docx."""

    @mcp.tool
    @friendly_tool_errors
    async def generar_catastro(
        carrera_id: int,
        carrera_nombre: str,
        facultad_nombre: str,
        anio: int | None = None,
        modalidad: str = "PRE_GRADO",
    ) -> dict[str, Any]:
        """Genera el CATASTRO (.docx) de una carrera/año desde SISAV2.
        
        Si no se especifica un año (anio=None), se extraerán los datos históricos completos.
        """
        # Se vuelve a la extracción original y segura utilizando ctx.identity()
        id_usuario, roles = await ctx.identity()
        return await documents.generar_catastro(
            ctx.client,
            id_usuario=id_usuario,
            roles=roles,
            carrera_id=carrera_id,
            carrera_nombre=carrera_nombre,
            facultad_nombre=facultad_nombre,
            anio=anio,
            modalidad=modalidad,
        )

    @mcp.tool
    @friendly_tool_errors
    async def generar_evidencia(
        id_postulacion: int,
        descripcion: str | None = None,
        fotos_base64: list[str] | None = None,
        asistentes: list[dict[str, str]] | None = None,
        difusion: str | None = None,
        resumen_asistencia: str | None = None,
    ) -> dict[str, Any]:
        """Genera el informe de EVIDENCIA (.docx) de una iniciativa.

        Utiliza una plantilla con portada, buscando etiquetas en tablas o párrafos.
        """
        # Extraemos el nombre del analista utilizando las propiedades del usuario Pydantic
        usuario = await ctx.usuario()
        nombre_analista = usuario.nombre if hasattr(usuario, "nombre") else "Analista SISAV"
        
        return await documents.generar_evidencia(
            ctx.client,
            id_postulacion=id_postulacion,
            nombre_analista=nombre_analista,
            descripcion=descripcion,
            fotos_base64=fotos_base64,
            asistentes=asistentes,
            difusion=difusion,
            resumen_asistencia=resumen_asistencia,
        )


def register_write_tools(mcp: FastMCP, ctx: SisavContext) -> None:
    """Registra las tools de escritura de la demo (dry-run -> commit mock).

    Por defecto cada tool devuelve un preview dry-run (``aplicado: false``). Con
    ``confirmar=True`` aplica la intención contra el backend SIMULADO en memoria
    (sólo si la demo lo habilitó con ``SISAV2_MOCK_WRITES=1``) y relee el efecto;
    SISAV2 real nunca se toca. Sin el simulador, ``confirmar`` se rechaza con un
    error claro: no existe camino para mutar el sistema institucional.
    """

    def _finalizar(
        preview: dict[str, Any], usuario: Any, confirmar: bool
    ) -> dict[str, Any]:
        return finalizar_escritura(
            preview,
            confirmar=confirmar,
            backend=ctx.mock_backend,
            actor=f"usuario#{usuario.id}",
            audit=ctx.audit,
        )

    @mcp.tool
    @friendly_tool_errors
    async def crear_postulacion(
        modalidad: str,
        convocatoria_id: int,
        titulo: str,
        objetivo: str,
        campos_extra: dict[str, Any] | None = None,
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de creación (IPOCRE); dry-run salvo confirmar+mock activo."""
        usuario = await ctx.usuario()
        preview = await writes.crear_postulacion(
            permisos=usuario.permisos_nomenclaturas,
            modalidad=modalidad,
            convocatoria_id=convocatoria_id,
            titulo=titulo,
            objetivo=objetivo,
            campos_extra=campos_extra,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def editar_postulacion(
        id_postulacion: int,
        campos: dict[str, Any],
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de edición en estado Incompleta (IPOEDI); dry-run por defecto."""
        usuario = await ctx.usuario()
        preview = await writes.editar_postulacion(
            ctx.client,
            permisos=usuario.permisos_nomenclaturas,
            id_postulacion=id_postulacion,
            campos=campos,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def evaluar_admisibilidad(
        id_postulacion: int,
        modalidad: str,
        id_fase: int,
        veredicto: str,
        comentario: str,
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de Admisible/Reformular/Rechazar (AEVADM/AEVAPR); dry-run."""
        usuario = await ctx.usuario()
        preview = await writes.evaluar_admisibilidad(
            ctx.client,
            permisos=usuario.permisos_nomenclaturas,
            id_postulacion=id_postulacion,
            modalidad=modalidad,
            id_fase=id_fase,
            veredicto=veredicto,
            comentario=comentario,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def cambiar_fase(
        id_postulacion: int,
        id_fase: int,
        estado_destino_id: int,
        observacion: str,
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de cambio de fase validado (IPRCES); dry-run por defecto."""
        usuario = await ctx.usuario()
        preview = await writes.cambiar_fase(
            ctx.client,
            permisos=usuario.permisos_nomenclaturas,
            id_postulacion=id_postulacion,
            id_fase=id_fase,
            estado_destino_id=estado_destino_id,
            observacion=observacion,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def agregar_comentario_bitacora(
        id_postulacion: int,
        texto: str,
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de feedback tras verificar acceso de lectura; dry-run."""
        usuario = await ctx.usuario()
        preview = await writes.agregar_comentario_bitacora(
            ctx.client,
            permisos=usuario.permisos_nomenclaturas,
            id_postulacion=id_postulacion,
            texto=texto,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def crear_postulacion_espejo(
        id_origen: int,
        modalidad_destino: str,
        convocatoria_destino_id: int,
        carrera_destino_id: int,
        sobrescrituras: dict[str, Any] | None = None,
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview espejo sin PII ni dependencias de carrera (IPOCRE); dry-run."""
        usuario = await ctx.usuario()
        preview = await writes.crear_postulacion_espejo(
            ctx.client,
            permisos=usuario.permisos_nomenclaturas,
            id_origen=id_origen,
            modalidad_destino=modalidad_destino,
            convocatoria_destino_id=convocatoria_destino_id,
            carrera_destino_id=carrera_destino_id,
            sobrescrituras=sobrescrituras,
        )
        return _finalizar(preview, usuario, confirmar)

    @mcp.tool
    @friendly_tool_errors
    async def cargar_asistencia(
        id_proyecto: int,
        asistentes: list[dict[str, Any]],
        confirmar: bool = False,
    ) -> dict[str, Any]:
        """Preview de carga masiva de asistencia (EJSGES/EACEAC); dry-run."""
        usuario = await ctx.usuario()
        preview = await writes.cargar_asistencia(
            permisos=usuario.permisos_nomenclaturas,
            id_proyecto=id_proyecto,
            asistentes=asistentes,
        )
        return _finalizar(preview, usuario, confirmar)