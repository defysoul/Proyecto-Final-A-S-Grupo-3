"""Contract/golden tests: cada uno de los 17 samples de Fase 0 debe parsear.

Verifican que los modelos pydantic toleran los payloads reales (anonimizados) sin
romper, y comprueban algunos campos clave por modelo. Si la API cambia de forma,
estos tests caen primero.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from sisav2_mcp.config import Settings
from sisav2_mcp.models import (
    AvanceGlobalKPIs,
    BitacoraPage,
    Carrera,
    Convocatoria,
    DetalleIniciativa,
    Estado,
    EstadoId,
    ExportResult,
    Facultad,
    Fase,
    Indicador,
    Modalidad,
    PostulacionesPage,
    ProyectosPage,
    RepositoriosResponse,
    Usuario,
    etiqueta_estado,
)

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "discovery" / "samples"


def load(name: str) -> Any:
    """Carga un sample JSON por nombre de archivo."""
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))


# --- postulacion/buscar (3 modalidades) -----------------------------------


def test_buscar_pregrado() -> None:
    page = PostulacionesPage.model_validate(load("postulacion_buscar_pregrado.json"))
    assert page.total == 1471
    assert len(page.postulaciones) == 4
    assert page.postulaciones[0].idpostulacion == 3033
    assert page.postulaciones[0].idestado == 2


def test_buscar_postgrado() -> None:
    page = PostulacionesPage.model_validate(load("postulacion_buscar_postgrado.json"))
    assert page.total == 22
    assert page.postulaciones[0].idpostulacion == 2873


def test_buscar_extension() -> None:
    page = PostulacionesPage.model_validate(load("postulacion_buscar_extension.json"))
    assert page.total == 1
    assert page.postulaciones[0].nombreestado == "Admisible"


def test_buscar_tolerates_null_nombrepostulacion() -> None:
    page = PostulacionesPage.model_validate(
        {
            "total": 1,
            "postulaciones": [
                {
                    "idpostulacion": 1,
                    "nombrepostulacion": None,
                    "idestado": 1,
                }
            ],
        }
    )
    assert page.postulaciones[0].nombrepostulacion is None


# --- proyectos/listar ------------------------------------------------------


def test_proyectos_listar() -> None:
    page = ProyectosPage.model_validate(load("proyectos_listar_pregrado.json"))
    assert page.total == 1299
    # `id` (proyecto) != `idpostulacion`
    assert page.data[0].id == 2912
    assert page.data[0].idpostulacion == 2992
    assert page.data[0].id != page.data[0].idpostulacion


# --- indicadores (lista directa) -------------------------------------------

_indicadores = TypeAdapter(list[Indicador])


def test_totales_convocatoria() -> None:
    indicadores = _indicadores.validate_python(
        load("convocatorias_postulacion_totales.json")
    )
    assert len(indicadores) == 11
    finalizado = next(i for i in indicadores if i.id == EstadoId.FINALIZADO)
    assert finalizado.total == 1199  # coacción str -> int


def test_totales_pregrado() -> None:
    indicadores = _indicadores.validate_python(
        load("postulacion_totales_pregrado.json")
    )
    assert len(indicadores) == 11
    assert all(isinstance(i.total, int) for i in indicadores)


# --- detalle (form-builder) ------------------------------------------------


def test_obtener_detalle() -> None:
    detalle = DetalleIniciativa.model_validate(load("postulacion_obtener_3033.json"))
    assert detalle.id == 3033
    assert detalle.formulario.formulario[0].posicion == 1
    campos = detalle.formulario.formulario[0].campos
    assert len(campos) > 0
    assert campos[0].name == "ESTANDAR_CORREO"  # parseado desde la clave `json`


# --- fase ------------------------------------------------------------------


def test_fase_obtener() -> None:
    fase = Fase.model_validate(load("convocatorias_fases_obtener_34.json"))
    assert fase.id == 34
    assert len(fase.estadoPostulacion) == 2
    assert fase.estadoPostulacion[0].rol is not None
    assert fase.estadoPostulacion[0].rol.nombre == "Analista"
    assert fase.plantillas == {"postulacion": 85, "informe": 86}


# --- bitácora --------------------------------------------------------------


def test_listar_cambios() -> None:
    page = BitacoraPage.model_validate(load("postulacion_listar-cambios_3033.json"))
    assert len(page.cambios) == 1
    assert page.cambios[0].estadoActual == "Reformular"
    assert page.cambios[0].idPostulacion == 3033


# --- export ----------------------------------------------------------------


def test_exportar_excel() -> None:
    sample = load("postulacion_exportar-excel.json")
    result = ExportResult.model_validate(sample["_response_body"])
    assert result.total == 88
    assert result.url.startswith("https://")
    assert result.nombreArchivo.endswith(".xlsx")


# --- avance global (KPIs) --------------------------------------------------


def test_avance_global() -> None:
    kpis = AvanceGlobalKPIs.model_validate(load("estadisticas_globales-proyectos.json"))
    assert kpis.totalProyectos == 1338
    assert kpis.totalPresupuesto == 24051600


# --- catálogos -------------------------------------------------------------


def test_convocatorias_combo() -> None:
    items = TypeAdapter(list[Convocatoria]).validate_python(
        load("convocatorias_listar-combo.json")
    )
    assert len(items) == 6
    assert items[0].id == 71


def test_carreras() -> None:
    items = TypeAdapter(list[Carrera]).validate_python(
        load("mantenedores_listarCarrera.json")
    )
    # Bachillerato tiene facultadId null -> tolerado
    assert any(c.facultadId is None for c in items)
    assert any(c.nombre == "Ingenieria Civil en Ciencia de Datos" for c in items)


def test_facultades() -> None:
    items = TypeAdapter(list[Facultad]).validate_python(
        load("mantenedores_listarFacultad.json")
    )
    # UTEM tiene idUnidad null -> tolerado
    assert any(f.idUnidad is None for f in items)
    assert any(f.sigla == "FING" for f in items)


def test_estados() -> None:
    items = TypeAdapter(list[Estado]).validate_python(
        load("convocatorias_estado_buscar.json")
    )
    assert len(items) == 11
    assert items[0].nombre == "Incompleta"
    # El catálogo coincide con el enum/etiquetas confirmadas.
    for estado in items:
        assert etiqueta_estado(estado.id) == estado.nombre


def test_repositorios() -> None:
    resp = RepositoriosResponse.model_validate(load("mantenedores_repositorios.json"))
    assert resp.success is True
    assert resp.data[0].categoria.nombre == "Docencia"
    assert resp.data[0].repositorios[0].nombre == "Documentos Docencia 2025"


# --- usuario / RBAC --------------------------------------------------------


def test_verifica_token() -> None:
    usuario = Usuario.model_validate(load("usuarios_verifica-token.json"))
    assert usuario.id == 401
    assert usuario.perfil is not None
    assert usuario.perfil.nombre == "Administrador"
    # El RBAC se resuelve aquí (no en el JWT).
    assert "IPOLIST" in usuario.permisos_nomenclaturas
    assert "ESTAVGL" in usuario.permisos_nomenclaturas  # Avance Global


# --- config ----------------------------------------------------------------


def test_settings_defaults() -> None:
    s = Settings()
    assert s.api_base_url == "https://sisav2-api.utem.cl"
    assert s.client_id == "SISAV2"
    assert s.token_endpoint == (
        "https://sso.utem.cl/auth/realms/prod/protocol/openid-connect/token"
    )


def test_modalidad_enum() -> None:
    assert Modalidad.PRE_GRADO == "PRE_GRADO"
    assert {m.value for m in Modalidad} == {"PRE_GRADO", "POST_GRADO", "EXTENSION"}
